"""Unit tests for ViteAssetLoader manifest spec compliance, CSP nonces, SRI, and preload headers."""

import json
import re
from pathlib import Path

import httpx2
import markupsafe
import pytest
from litestar import Litestar, get
from litestar.testing import RequestFactory

from litestar_vite.config import PathConfig, RuntimeConfig, ViteConfig
from litestar_vite.loader import ViteAssetLoader, render_asset_tag, render_hmr_client, render_routes
from litestar_vite.plugin import VitePlugin
from litestar_vite.utils import read_bridge_config


def test_generate_asset_tags_recursive_modulepreload_and_css() -> None:
    """Verify multi-level imports emit modulepreload links and transitive CSS in deterministic order."""
    config = ViteConfig(paths=PathConfig(asset_url="/static/"), runtime=RuntimeConfig(dev_mode=False))
    loader = ViteAssetLoader(config)
    loader._manifest = {
        "src/main.ts": {
            "file": "assets/main-111.js",
            "src": "src/main.ts",
            "isEntry": True,
            "css": ["assets/main-111.css"],
            "imports": ["_vendor-a.js"],
        },
        "_vendor-a.js": {
            "file": "assets/vendor-a-222.js",
            "css": ["assets/vendor-a-222.css"],
            "imports": ["_vendor-b.js"],
        },
        "_vendor-b.js": {
            "file": "assets/vendor-b-333.js",
            "css": ["assets/vendor-b-333.css"],
            "imports": ["_vendor-a.js"],
        },
    }

    tags = loader.generate_asset_tags("src/main.ts")

    assert '<link rel="stylesheet" href="/static/assets/main-111.css" />' in tags
    assert '<link rel="stylesheet" href="/static/assets/vendor-a-222.css" />' in tags
    assert '<link rel="stylesheet" href="/static/assets/vendor-b-333.css" />' in tags
    assert '<script type="module" src="/static/assets/main-111.js"></script>' in tags
    assert '<link rel="modulepreload" crossorigin href="/static/assets/vendor-a-222.js" />' in tags
    assert '<link rel="modulepreload" crossorigin href="/static/assets/vendor-b-333.js" />' in tags
    assert 'src="/static/assets/vendor-a-222.js"' not in tags
    assert 'src="/static/assets/vendor-b-333.js"' not in tags
    assert "async=" not in tags


def test_generate_asset_tags_deduplicates_across_multiple_entries() -> None:
    """Verify shared imports and CSS are deduplicated when rendering multiple entries."""
    config = ViteConfig(paths=PathConfig(asset_url="/static/"), runtime=RuntimeConfig(dev_mode=False))
    loader = ViteAssetLoader(config)
    loader._manifest = {
        "src/main.ts": {"file": "assets/main-111.js", "css": ["assets/shared.css"], "imports": ["_shared.js"]},
        "src/admin.ts": {
            "file": "assets/admin-222.js",
            "css": ["assets/shared.css", "assets/admin.css"],
            "imports": ["_shared.js"],
        },
        "_shared.js": {"file": "assets/shared-333.js", "css": ["assets/shared-vendor.css"]},
    }

    tags = str(loader.render_asset_tag(["src/main.ts", "src/admin.ts"]))

    assert tags.count('href="/static/assets/shared.css"') == 1
    assert tags.count('href="/static/assets/shared-vendor.css"') == 1
    assert tags.count('href="/static/assets/admin.css"') == 1
    assert tags.count('href="/static/assets/shared-333.js"') == 1
    assert tags.count('src="/static/assets/main-111.js"') == 1
    assert tags.count('src="/static/assets/admin-222.js"') == 1


def test_generate_asset_tags_respects_explicit_scripts_attrs() -> None:
    """Verify explicit scripts_attrs are preserved on entry script tags."""
    config = ViteConfig(paths=PathConfig(asset_url="/static/"), runtime=RuntimeConfig(dev_mode=False))
    loader = ViteAssetLoader(config)
    loader._manifest = {"src/main.ts": {"file": "assets/main-111.js"}}

    tags = loader.generate_asset_tags("src/main.ts", scripts_attrs={"type": "module", "async": ""})
    assert '<script type="module" async="" src="/static/assets/main-111.js"></script>' in tags


def test_generate_asset_tags_csp_nonce_and_sri_integrity() -> None:
    """Verify CSP nonce and manifest SRI integrity attributes are rendered and HTML-escaped."""
    config = ViteConfig(
        paths=PathConfig(asset_url="/static/"), runtime=RuntimeConfig(dev_mode=False, csp_nonce='nonce-"123"')
    )
    loader = ViteAssetLoader(config)
    loader._manifest = {
        "src/main.ts": {
            "file": "assets/main-111.js",
            "css": ["assets/main-111.css"],
            "imports": ["_vendor.js"],
            "integrity": "sha384-mainhash",
        },
        "_vendor.js": {"file": "assets/vendor-222.js", "integrity": 'sha384-vendor"hash'},
    }

    tags = loader.generate_asset_tags("src/main.ts")

    assert 'nonce="nonce-&quot;123&quot;"' in tags
    assert (
        '<script type="module" integrity="sha384-mainhash" crossorigin="anonymous" '
        'nonce="nonce-&quot;123&quot;" src="/static/assets/main-111.js"></script>'
    ) in tags
    assert (
        '<link rel="modulepreload" crossorigin="anonymous" '
        'integrity="sha384-vendor&quot;hash" nonce="nonce-&quot;123&quot;" '
        'href="/static/assets/vendor-222.js" />'
    ) in tags
    assert '<link rel="stylesheet" nonce="nonce-&quot;123&quot;" href="/static/assets/main-111.css" />' in tags


def test_generate_ws_client_tags_includes_csp_nonce() -> None:
    """Verify Vite dev client script tag includes configured or per-call CSP nonce."""
    config = ViteConfig(runtime=RuntimeConfig(dev_mode=True, is_react=True, csp_nonce="dev-nonce-1"))
    loader = ViteAssetLoader(config)

    ws_tags = loader.generate_ws_client_tags()
    assert 'nonce="dev-nonce-1"' in ws_tags

    override_hmr = str(loader.render_hmr_client(csp_nonce="req-nonce-2"))
    assert override_hmr.count('nonce="req-nonce-2"') == 2


def test_template_callables_resolve_per_request_csp_nonce() -> None:
    """Verify render_asset_tag, render_hmr_client, and render_routes read csp_nonce from context or request state."""
    config = ViteConfig(paths=PathConfig(asset_url="/static/"), runtime=RuntimeConfig(dev_mode=False))
    plugin = VitePlugin(config=config)

    @get("/items", name="items")
    async def get_items() -> list[str]:
        return []

    app = Litestar(route_handlers=[get_items], plugins=[plugin])
    plugin.asset_loader._manifest = {"src/main.ts": {"file": "assets/main-111.js", "integrity": "sha384-abc"}}

    req = RequestFactory(app=app).get("/items", state={"csp_nonce": "state-nonce-99"})
    ctx = {"request": req}
    asset_markup = str(render_asset_tag(ctx, "src/main.ts"))
    routes_markup = str(render_routes(ctx))

    assert 'nonce="state-nonce-99"' in asset_markup
    assert 'integrity="sha384-abc"' in asset_markup
    assert 'nonce="state-nonce-99"' in routes_markup

    ctx_override = {"request": req, "csp_nonce": "ctx-nonce-77"}
    assert 'nonce="ctx-nonce-77"' in str(render_asset_tag(ctx_override, "src/main.ts"))
    assert 'nonce="ctx-nonce-77"' in str(render_routes(ctx_override))
    assert 'nonce="explicit-nonce-55"' in str(render_routes(ctx_override, csp_nonce="explicit-nonce-55"))
    _ = render_hmr_client(ctx_override)


def test_render_preload_headers_formats_rfc8288_links() -> None:
    """Verify render_preload_headers returns RFC 8288 Link header values for entry scripts, chunks, and CSS."""
    config = ViteConfig(paths=PathConfig(asset_url="/static/"), runtime=RuntimeConfig(dev_mode=False))
    loader = ViteAssetLoader(config)
    loader._manifest = {
        "src/main.ts": {
            "file": "assets/main-abc12345.js",
            "src": "src/main.ts",
            "isEntry": True,
            "css": ["assets/main-def67890.css"],
            "imports": ["_vendor.js"],
        },
        "_vendor.js": {"file": "assets/vendor-99887766.js", "css": ["assets/vendor-11223344.css"]},
    }

    links = loader.render_preload_headers("src/main.ts")
    assert "</static/assets/main-abc12345.js>; rel=modulepreload; as=script; crossorigin" in links
    assert "</static/assets/vendor-99887766.js>; rel=modulepreload; as=script; crossorigin" in links
    assert "</static/assets/main-def67890.css>; rel=preload; as=style" in links
    assert "</static/assets/vendor-11223344.css>; rel=preload; as=style" in links

    auto_links = loader.render_preload_headers()
    assert auto_links == links


def test_render_preload_headers_returns_empty_in_dev_mode() -> None:
    """Verify render_preload_headers returns an empty list in hot dev mode."""
    config = ViteConfig(paths=PathConfig(asset_url="/static/"), runtime=RuntimeConfig(dev_mode=True))
    loader = ViteAssetLoader(config)
    assert loader.render_preload_headers("src/main.ts") == []


def _extract_routes_json_literal(markup: str) -> str:
    """Extract the assigned JSON literal from render_routes script markup."""
    match = re.search(r"window\.Litestar\.routes = (.*);\n\}\)\(\);", markup, re.DOTALL)
    assert match is not None
    return match.group(1)


@pytest.mark.parametrize(
    ("route_name", "component", "include_components"),
    [
        ("x</script><!--<script>", None, False),
        ("page_script_close", "Page</script>", True),
        ("page_comment_script", "Page</script><!--<script>", True),
    ],
)
def test_render_routes_escapes_script_breakout_sequences(
    route_name: str, component: str | None, include_components: bool
) -> None:
    """Verify render_routes escapes script closing tags and HTML comment script openers."""
    config = ViteConfig(paths=PathConfig(asset_url="/static/"), runtime=RuntimeConfig(dev_mode=False))
    plugin = VitePlugin(config=config)
    opt = {"component": component} if component is not None else None

    @get("/items", name=route_name, opt=opt)
    async def get_items() -> list[str]:
        return []

    app = Litestar(route_handlers=[get_items], plugins=[plugin])
    req = RequestFactory(app=app).get("/items")
    result = render_routes({"request": req}, include_components=include_components)

    assert isinstance(result, markupsafe.Markup)
    markup = str(result)
    assert markup.count("</script>") == 1
    assert r"\u003c/script\u003e" in markup
    if "<!--<script>" in route_name or (component is not None and "<!--<script>" in component):
        assert r"\u003c!--\u003cscript\u003e" in markup
        assert "<!--<script>" not in markup

    routes_literal = _extract_routes_json_literal(markup)
    parsed = json.loads(routes_literal)
    assert route_name in parsed["routes"]
    if include_components and component is not None:
        assert parsed["routes"][route_name]["component"] == component


@pytest.mark.parametrize(
    ("raw_char", "expected_escape"),
    [
        ("<", r"\u003c"),
        (">", r"\u003e"),
        ("&", r"\u0026"),
        ("'", r"\u0027"),
        ("\u2028", r"\u2028"),
        ("\u2029", r"\u2029"),
    ],
)
def test_render_routes_escapes_html_script_special_characters(raw_char: str, expected_escape: str) -> None:
    """Verify render_routes unicode-escapes all six HTML5 and JS line-separator special characters."""
    config = ViteConfig(paths=PathConfig(asset_url="/static/"), runtime=RuntimeConfig(dev_mode=False))
    plugin = VitePlugin(config=config)
    route_name = f"route_{raw_char}_item"
    component = f"Page_{raw_char}_View"

    @get("/special", name=route_name, opt={"component": component})
    async def get_special() -> dict[str, str]:
        return {}

    app = Litestar(route_handlers=[get_special], plugins=[plugin])
    req = RequestFactory(app=app).get("/special")
    result = render_routes({"request": req}, include_components=True)

    assert isinstance(result, markupsafe.Markup)
    markup = str(result)
    assert markup.count("</script>") == 1

    routes_literal = _extract_routes_json_literal(markup)
    assert raw_char not in routes_literal
    assert expected_escape in routes_literal

    parsed = json.loads(routes_literal)
    assert route_name in parsed["routes"]
    assert parsed["routes"][route_name]["component"] == component


def test_render_routes_standard_route_with_csp_nonce() -> None:
    """Verify render_routes preserves CSP nonce escaping and valid JSON for standard routes."""
    config = ViteConfig(paths=PathConfig(asset_url="/static/"), runtime=RuntimeConfig(dev_mode=False))
    plugin = VitePlugin(config=config)

    @get("/items", name="items")
    async def get_items() -> list[str]:
        return []

    app = Litestar(route_handlers=[get_items], plugins=[plugin])
    req = RequestFactory(app=app).get("/items")
    result = render_routes({"request": req}, csp_nonce="nonce-1")

    assert isinstance(result, markupsafe.Markup)
    markup = str(result)
    assert '<script type="text/javascript" nonce="nonce-1">' in markup
    assert markup.count("</script>") == 1

    parsed = json.loads(_extract_routes_json_literal(markup))
    assert parsed["routes"]["items"]["uri"] == "/items"


@pytest.mark.parametrize("proxy_token", ["tok-loader", None, ""])
def test_vite_asset_loader_post_transform_index_sync_proxy_token_header(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, proxy_token: str | None
) -> None:
    """_post_transform_index_sync attaches X-Litestar-Proxy-Token only when configured in the bridge file."""
    read_bridge_config.cache_clear()
    if proxy_token is not None:
        bridge = tmp_path / ".litestar.json"
        bridge.write_text(json.dumps({"proxyToken": proxy_token}))
        monkeypatch.setenv("LITESTAR_VITE_CONFIG_PATH", str(bridge))
    else:
        monkeypatch.setenv("LITESTAR_VITE_CONFIG_PATH", str(tmp_path / "missing.json"))
    read_bridge_config.cache_clear()

    captured: list[httpx2.Request] = []

    def handle(request: httpx2.Request) -> httpx2.Response:
        captured.append(request)
        return httpx2.Response(200, text="<html>entry</html>")

    client = httpx2.Client(transport=httpx2.MockTransport(handle))
    monkeypatch.setattr(httpx2, "Client", lambda **_kwargs: client)

    result = ViteAssetLoader._post_transform_index_sync(
        "http://127.0.0.1:5173/__litestar__/transform-index",
        {"entry": "pages/offline.html"},
        "pages/offline.html",
        "http://127.0.0.1:5173",
    )

    assert result == "<html>entry</html>"
    assert len(captured) == 1
    assert captured[0].headers.get("content-type") == "application/json"
    if proxy_token:
        assert captured[0].headers.get("x-litestar-proxy-token") == proxy_token
    else:
        assert "x-litestar-proxy-token" not in captured[0].headers
