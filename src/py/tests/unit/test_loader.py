"""Unit tests for ViteAssetLoader manifest spec compliance, CSP nonces, SRI, and preload headers."""

from litestar import Litestar, get
from litestar.testing import RequestFactory

from litestar_vite.config import PathConfig, RuntimeConfig, ViteConfig
from litestar_vite.loader import ViteAssetLoader, render_asset_tag, render_hmr_client, render_routes
from litestar_vite.plugin import VitePlugin


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
