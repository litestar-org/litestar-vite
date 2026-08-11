import json
from pathlib import Path
from urllib.parse import urlparse

import httpx
import pytest
from litestar.exceptions import ImproperlyConfiguredException

from litestar_vite.config import PathConfig, RuntimeConfig, ViteConfig
from litestar_vite.exceptions import AssetNotFoundError, HTMLEntryResolutionError
from litestar_vite.loader import ViteAssetLoader
from litestar_vite.utils import read_bridge_config


def test_parse_manifest_when_file_exists(tmp_path: Path) -> None:
    bundle_dir = tmp_path / "public"
    bundle_dir.mkdir()
    manifest = bundle_dir / "manifest.json"
    manifest.write_text('{"main.js": {"file": "assets/main.123456.js"}}')

    config = ViteConfig(paths=PathConfig(bundle_dir=bundle_dir), runtime=RuntimeConfig(dev_mode=False))
    loader = ViteAssetLoader.initialize_loader(config=config)

    assert loader._manifest == {"main.js": {"file": "assets/main.123456.js"}}


def test_asset_loader_manifest_property_exposes_parsed_dict(tmp_path: Path) -> None:
    bundle_dir = tmp_path / "public"
    bundle_dir.mkdir()
    (bundle_dir / "manifest.json").write_text('{"main.js": {"file": "assets/main.123456.js"}}')

    config = ViteConfig(paths=PathConfig(bundle_dir=bundle_dir), runtime=RuntimeConfig(dev_mode=False))
    loader = ViteAssetLoader.initialize_loader(config=config)

    assert loader.manifest == {"main.js": {"file": "assets/main.123456.js"}}


def test_parse_manifest_when_file_exists_in_vite_dir(tmp_path: Path) -> None:
    bundle_dir = tmp_path / "public"
    (bundle_dir / ".vite").mkdir(parents=True)
    manifest = bundle_dir / ".vite" / "manifest.json"
    manifest.write_text('{"main.js": {"file": "assets/main.123456.js"}}')

    config = ViteConfig(paths=PathConfig(bundle_dir=bundle_dir), runtime=RuntimeConfig(dev_mode=False))
    loader = ViteAssetLoader.initialize_loader(config=config)

    assert loader._manifest == {"main.js": {"file": "assets/main.123456.js"}}


def test_parse_manifest_when_file_not_exists(tmp_path: Path) -> None:
    bundle_dir = tmp_path / "public"
    # Do not create directory or file

    config = ViteConfig(paths=PathConfig(bundle_dir=bundle_dir), runtime=RuntimeConfig(dev_mode=False))

    # Should not raise
    loader = ViteAssetLoader.initialize_loader(config=config)
    assert loader._manifest == {}


def test_parse_manifest_hot_reload_mode(tmp_path: Path) -> None:
    bundle_dir = tmp_path / "public"
    bundle_dir.mkdir()
    hot_file = bundle_dir / "hot"
    hot_file.write_text("http://localhost:3000")

    config = ViteConfig(paths=PathConfig(bundle_dir=bundle_dir), runtime=RuntimeConfig(dev_mode=True))
    loader = ViteAssetLoader.initialize_loader(config=config)

    assert loader._vite_base_path == "http://localhost:3000"


def test_generate_asset_tags_prod_mode() -> None:
    config = ViteConfig(paths=PathConfig(asset_url="/static/"), runtime=RuntimeConfig(dev_mode=False))
    loader = ViteAssetLoader(config)
    loader._manifest = {
        "main.js": {"file": "assets/main.js", "css": ["assets/main.css"]},
        "vendor.js": {"file": "assets/vendor.js"},
    }

    tags = loader.generate_asset_tags("main.js")
    assert '<link rel="stylesheet" href="/static/assets/main.css" />' in tags
    assert '<script type="module" async="" defer="" src="/static/assets/main.js"></script>' in tags


def test_generate_asset_tags_dev_mode(tmp_path: Path) -> None:
    # Empty bundle_dir guarantees no hotfile is found by the lazy-retry path,
    # forcing the host:port fallback we're asserting on.
    config = ViteConfig(paths=PathConfig(bundle_dir=tmp_path), runtime=RuntimeConfig(dev_mode=True))
    loader = ViteAssetLoader(config)

    tags = loader.generate_asset_tags("main.js")
    # Should point to vite server
    assert 'src="http://127.0.0.1:5173/static/main.js"' in tags


def test_generate_asset_tags_dev_mode_uses_litestar_origin_from_hotfile(tmp_path: Path) -> None:
    bundle_dir = tmp_path / "public"
    bundle_dir.mkdir()
    (bundle_dir / "hot").write_text("http://localhost:5006")

    config = ViteConfig(
        paths=PathConfig(bundle_dir=bundle_dir, asset_url="/static/dist/"), runtime=RuntimeConfig(dev_mode=True)
    )
    loader = ViteAssetLoader.initialize_loader(config)

    tags = loader.generate_asset_tags("src/main.js")

    assert 'src="http://localhost:5006/static/dist/src/main.js"' in tags
    assert "127.0.0.1:5173" not in tags


def test_generate_asset_tags_dev_mode_rereads_hotfile_when_initially_missing(tmp_path: Path) -> None:
    """Race scenario: loader initializes before the JS plugin has written the hotfile.

    The first ``parse_manifest()`` call sees no hotfile and leaves ``_vite_base_path``
    as ``None``. Without a lazy retry, every subsequent asset URL silently falls back
    to ``http://<host>:<port>`` (the raw Vite dev server origin), breaking the
    single-port-via-ASGI contract. The loader MUST re-read the hotfile on demand once
    it appears.
    """
    bundle_dir = tmp_path / "public"
    bundle_dir.mkdir()

    config = ViteConfig(
        paths=PathConfig(bundle_dir=bundle_dir, asset_url="/static/dist/"), runtime=RuntimeConfig(dev_mode=True)
    )
    loader = ViteAssetLoader.initialize_loader(config)
    assert loader._vite_base_path is None

    # Simulate the JS plugin writing the resolved Vite URL after Vite has started.
    (bundle_dir / "hot").write_text("http://localhost:5006")

    tags = loader.generate_asset_tags("src/main.js")

    assert 'src="http://localhost:5006/static/dist/src/main.js"' in tags


def test_load_hot_file_strips_trailing_whitespace(tmp_path: Path) -> None:
    """Hotfile written by Node tooling commonly has a trailing newline; that newline
    must not survive into ``urljoin`` (where it produces malformed URLs like
    ``http://localhost:5006\\n/static/...``).
    """
    bundle_dir = tmp_path / "public"
    bundle_dir.mkdir()
    (bundle_dir / "hot").write_text("http://localhost:5006\n")

    config = ViteConfig(
        paths=PathConfig(bundle_dir=bundle_dir, asset_url="/static/dist/"), runtime=RuntimeConfig(dev_mode=True)
    )
    loader = ViteAssetLoader.initialize_loader(config)

    assert loader._vite_base_path == "http://localhost:5006"
    tags = loader.generate_asset_tags("src/main.js")
    assert "\n" not in tags


def test_generate_asset_tags_missing_entry() -> None:
    config = ViteConfig(runtime=RuntimeConfig(dev_mode=False))
    loader = ViteAssetLoader(config)
    loader._manifest = {}

    with pytest.raises(ImproperlyConfiguredException) as exc_info:
        loader.generate_asset_tags("missing.js")

    assert "litestar assets build" in str(exc_info.value)
    assert str(config.resolve_manifest_path()) not in str(exc_info.value)


def test_get_static_asset_dev_mode(tmp_path: Path) -> None:
    config = ViteConfig(paths=PathConfig(bundle_dir=tmp_path), runtime=RuntimeConfig(dev_mode=True))
    loader = ViteAssetLoader(config)
    assert loader.get_static_asset("test.png") == "http://127.0.0.1:5173/static/test.png"


def test_react_hmr_preamble_includes_csp_nonce() -> None:
    config = ViteConfig(runtime=RuntimeConfig(dev_mode=True, is_react=True, csp_nonce="abc123"))
    loader = ViteAssetLoader(config)
    tags = loader.generate_react_hmr_tags()

    assert 'nonce="abc123"' in tags


def test_get_static_asset_prod_mode_found() -> None:
    config = ViteConfig(
        paths=PathConfig(bundle_dir=Path("tests/fixtures"), asset_url="/static/"), runtime=RuntimeConfig(dev_mode=False)
    )
    loader = ViteAssetLoader(config)
    # Mock manifest
    loader._manifest = {"test.png": {"file": "assets/test.hash.png"}}
    assert loader.get_static_asset("test.png") == "/static/assets/test.hash.png"


def test_get_static_asset_prod_mode_not_found() -> None:
    config = ViteConfig(runtime=RuntimeConfig(dev_mode=False))
    loader = ViteAssetLoader(config)
    loader._manifest = {}
    with pytest.raises(AssetNotFoundError) as exc_info:
        loader.get_static_asset("missing.png")

    assert "litestar assets build" in str(exc_info.value)
    assert str(config.resolve_manifest_path()) not in str(exc_info.value)


def test_get_static_asset_with_absolute_asset_url() -> None:
    config = ViteConfig(
        paths=PathConfig(asset_url="https://cdn.example.com/"),
        runtime=RuntimeConfig(dev_mode=False),
        base_url="https://app.example.com/",
    )
    loader = ViteAssetLoader(config)
    loader._manifest = {"test.png": {"file": "assets/test.hash.png"}}
    # Production assets are resolved from asset_url
    assert loader.get_static_asset("test.png") == "https://cdn.example.com/assets/test.hash.png"


@pytest.mark.anyio
async def test_async_initialization(tmp_path: Path) -> None:
    """Test async initialization of the asset loader."""
    bundle_dir = tmp_path / "public"
    bundle_dir.mkdir()
    manifest = bundle_dir / "manifest.json"
    manifest.write_text('{"main.js": {"file": "assets/main.123456.js"}}')

    config = ViteConfig(paths=PathConfig(bundle_dir=bundle_dir), runtime=RuntimeConfig(dev_mode=False))
    loader = ViteAssetLoader(config)
    await loader.initialize()

    assert loader._manifest == {"main.js": {"file": "assets/main.123456.js"}}
    assert loader._initialized is True


@pytest.mark.anyio
async def test_async_initialization_manifest_in_vite_dir(tmp_path: Path) -> None:
    """Async initialization should resolve bundle_dir/.vite/manifest.json."""
    bundle_dir = tmp_path / "public"
    (bundle_dir / ".vite").mkdir(parents=True)
    manifest = bundle_dir / ".vite" / "manifest.json"
    manifest.write_text('{"main.js": {"file": "assets/main.123456.js"}}')

    config = ViteConfig(paths=PathConfig(bundle_dir=bundle_dir), runtime=RuntimeConfig(dev_mode=False))
    loader = ViteAssetLoader(config)
    await loader.initialize()

    assert loader._manifest == {"main.js": {"file": "assets/main.123456.js"}}
    assert loader._initialized is True


@pytest.mark.anyio
async def test_async_initialization_dev_mode(tmp_path: Path) -> None:
    """Test async initialization in dev mode reads hot file."""
    bundle_dir = tmp_path / "public"
    bundle_dir.mkdir()
    hot_file = bundle_dir / "hot"
    hot_file.write_text("http://localhost:3000")

    config = ViteConfig(paths=PathConfig(bundle_dir=bundle_dir), runtime=RuntimeConfig(dev_mode=True))
    loader = ViteAssetLoader(config)
    await loader.initialize()

    assert loader._vite_base_path == "http://localhost:3000"
    assert loader._initialized is True


# ===== Bridge-config preference (litestar-vite-c1t) =====


def _write_bridge_config(tmp_path: Path, payload: object) -> Path:
    bridge = tmp_path / ".litestar.json"
    bridge.write_text(json.dumps(payload))
    return bridge


def test_vite_server_url_prefers_bridge_appurl_over_hotfile(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Bridge appUrl beats the hotfile for the loader-side anchor URL.

    This is the dual-consumer-conflict resolution test on the loader side: even
    when the hotfile carries the real Vite origin for proxy/HMR consumers, the
    bridge appUrl wins for browser-facing asset emission.
    """
    read_bridge_config.cache_clear()
    bundle_dir = tmp_path / "public"
    bundle_dir.mkdir()
    (bundle_dir / "hot").write_text("http://127.0.0.1:9999")
    bridge = _write_bridge_config(tmp_path, {"appUrl": "http://localhost:8000", "host": "127.0.0.1", "port": 9999})
    monkeypatch.setenv("LITESTAR_VITE_CONFIG_PATH", str(bridge))

    config = ViteConfig(
        paths=PathConfig(bundle_dir=bundle_dir, asset_url="/static/"), runtime=RuntimeConfig(dev_mode=True)
    )
    loader = ViteAssetLoader.initialize_loader(config)

    url = loader._vite_server_url("foo.ts")

    assert url.startswith("http://localhost:8000"), url
    assert "127.0.0.1:9999" not in url
    read_bridge_config.cache_clear()


def test_vite_server_url_falls_back_to_hotfile_when_bridge_missing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    read_bridge_config.cache_clear()
    bundle_dir = tmp_path / "public"
    bundle_dir.mkdir()
    (bundle_dir / "hot").write_text("http://hot:5006")
    monkeypatch.setenv("LITESTAR_VITE_CONFIG_PATH", str(tmp_path / "missing.json"))

    config = ViteConfig(
        paths=PathConfig(bundle_dir=bundle_dir, asset_url="/static/"), runtime=RuntimeConfig(dev_mode=True)
    )
    loader = ViteAssetLoader.initialize_loader(config)

    url = loader._vite_server_url("main.js")

    assert url.startswith("http://hot:5006"), url
    read_bridge_config.cache_clear()


def test_vite_server_url_falls_back_to_host_port_when_neither_present(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Neither bridge nor hotfile: legacy ``protocol://host:port`` fallback wins.

    Mirrors the contract asserted by ``test_generate_asset_tags_dev_mode`` but
    pinned to ``_vite_server_url`` directly so a regression here is unambiguous.
    """
    read_bridge_config.cache_clear()
    monkeypatch.setenv("LITESTAR_VITE_CONFIG_PATH", str(tmp_path / "missing.json"))

    config = ViteConfig(paths=PathConfig(bundle_dir=tmp_path), runtime=RuntimeConfig(dev_mode=True))
    loader = ViteAssetLoader(config)

    url = loader._vite_server_url("main.js")

    assert url.startswith("http://127.0.0.1:5173"), url
    read_bridge_config.cache_clear()


def test_vite_server_url_ignores_bridge_when_appurl_null(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Real-world: backend env vars not set → bridge writer emits ``appUrl: null``."""
    read_bridge_config.cache_clear()
    bundle_dir = tmp_path / "public"
    bundle_dir.mkdir()
    (bundle_dir / "hot").write_text("http://hot:5006")
    bridge = _write_bridge_config(tmp_path, {"appUrl": None, "host": "127.0.0.1", "port": 5173})
    monkeypatch.setenv("LITESTAR_VITE_CONFIG_PATH", str(bridge))

    config = ViteConfig(
        paths=PathConfig(bundle_dir=bundle_dir, asset_url="/static/"), runtime=RuntimeConfig(dev_mode=True)
    )
    loader = ViteAssetLoader.initialize_loader(config)

    url = loader._vite_server_url("main.js")

    assert url.startswith("http://hot:5006"), url
    read_bridge_config.cache_clear()


# ===== Secondary HTML entry resolution =====


@pytest.mark.anyio
async def test_vite_asset_loader_resolve_html_entry_returns_production_file_without_hot_target(tmp_path: Path) -> None:
    production = tmp_path / "dist" / "offline.html"
    production.parent.mkdir()
    production.write_text("<html>offline</html>")
    loader = ViteAssetLoader(
        ViteConfig(paths=PathConfig(root=tmp_path, bundle_dir="dist"), runtime=RuntimeConfig(dev_mode=True))
    )

    assert (
        await loader.resolve_html_entry("/offline.html", production_path="dist/offline.html") == "<html>offline</html>"
    )


@pytest.mark.parametrize(
    "entry",
    [
        "https://example.com/offline.html",
        "//example.com/offline.html",
        "offline.html?x=1",
        "offline.html#x",
        "../offline.html",
        "%2e%2e/offline.html",
        "%252e%252e/offline.html",
        "nested\\offline.html",
        "offline.js",
        "offline.html\x00",
    ],
)
def test_vite_asset_loader_resolve_html_entry_rejects_unsafe_entry(tmp_path: Path, entry: str) -> None:
    loader = ViteAssetLoader(ViteConfig(paths=PathConfig(root=tmp_path), runtime=RuntimeConfig(dev_mode=False)))

    with pytest.raises(ValueError):
        loader.resolve_html_entry_sync(entry, production_path="offline.html")


@pytest.mark.anyio
async def test_vite_asset_loader_resolve_html_entry_rereads_hot_file_and_posts_exact_entry(tmp_path: Path) -> None:
    bundle = tmp_path / "dist"
    bundle.mkdir()
    (bundle / "offline.html").write_text("production")
    hot = bundle / "hot"
    requests: list[httpx.Request] = []

    async def handle(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, text="<html>development</html>")

    loader = ViteAssetLoader(
        ViteConfig(paths=PathConfig(root=tmp_path, bundle_dir="dist"), runtime=RuntimeConfig(dev_mode=True))
    )
    async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as client:
        loader._bind_http_client(client)
        assert (
            await loader.resolve_html_entry("pages/offline.html", production_path="dist/offline.html") == "production"
        )
        hot.write_text("https://[::1]:43123")
        assert await loader.resolve_html_entry("pages/offline.html", production_path="dist/offline.html") == (
            "<html>development</html>"
        )

    assert urlparse(str(requests[0].url)).netloc == "[::1]:43123"
    assert json.loads(requests[0].content) == {"entry": "pages/offline.html"}


@pytest.mark.anyio
async def test_vite_asset_loader_resolve_html_entry_raises_for_active_stale_server(tmp_path: Path) -> None:
    bundle = tmp_path / "dist"
    bundle.mkdir()
    (bundle / "hot").write_text("http://127.0.0.1:9")
    production = bundle / "offline.html"
    production.write_text("production")
    loader = ViteAssetLoader(
        ViteConfig(paths=PathConfig(root=tmp_path, bundle_dir="dist"), runtime=RuntimeConfig(dev_mode=True))
    )

    with pytest.raises(HTMLEntryResolutionError) as exc_info:
        await loader.resolve_html_entry("offline.html", production_path=production)

    assert str(production) not in str(exc_info.value)
    assert "127.0.0.1" not in str(exc_info.value)
    assert exc_info.value.development_url == "http://127.0.0.1:9"
    assert isinstance(exc_info.value.cause, httpx.ConnectError)


@pytest.mark.anyio
async def test_vite_asset_loader_resolve_html_entry_reports_upstream_status_without_fallback(tmp_path: Path) -> None:
    bundle = tmp_path / "dist"
    bundle.mkdir()
    (bundle / "hot").write_text("https://vite.example.test")
    production = bundle / "offline.html"
    production.write_text("production")

    async def handle(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, request=request)

    loader = ViteAssetLoader(
        ViteConfig(paths=PathConfig(root=tmp_path, bundle_dir="dist"), runtime=RuntimeConfig(dev_mode=True))
    )
    async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as client:
        loader._bind_http_client(client)
        with pytest.raises(HTMLEntryResolutionError) as exc_info:
            await loader.resolve_html_entry("offline.html", production_path=production)

    assert exc_info.value.status_code == 404
    assert "vite.example.test" not in str(exc_info.value)


@pytest.mark.parametrize("hot_value", ["", "not-a-url", "ftp://localhost/offline", "http://[invalid"])
def test_vite_asset_loader_resolve_html_entry_malformed_hot_file_uses_production(
    tmp_path: Path, hot_value: str
) -> None:
    bundle = tmp_path / "dist"
    bundle.mkdir()
    (bundle / "hot").write_text(hot_value)
    production = bundle / "offline.html"
    production.write_text("production")
    loader = ViteAssetLoader(
        ViteConfig(paths=PathConfig(root=tmp_path, bundle_dir="dist"), runtime=RuntimeConfig(dev_mode=True))
    )

    assert loader.resolve_html_entry_sync("offline.html", production_path=production) == "production"


def test_vite_asset_loader_resolve_html_entry_sync_rewrites_only_vite_assets(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    read_bridge_config.cache_clear()
    bundle = tmp_path / "dist"
    bundle.mkdir()
    (bundle / "hot").write_text("https://vite.internal:5173")
    bridge = _write_bridge_config(tmp_path, {"appUrl": "https://app.example.com:8443"})
    monkeypatch.setenv("LITESTAR_VITE_CONFIG_PATH", str(bridge))
    production = bundle / "offline.html"
    production.write_text("production")
    html = """<script type="module" src="/src/app.ts"></script>
<script type="module">import RefreshRuntime from '/@react-refresh'</script>
<link rel="stylesheet" href="/src/app.css"><link rel="modulepreload" href="/@vite/client">
<a href="/account">Account</a><form action="/submit"></form><img src="/logo.svg">"""

    def handle(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text=html)

    loader = ViteAssetLoader(
        ViteConfig(paths=PathConfig(root=tmp_path, bundle_dir="dist"), runtime=RuntimeConfig(dev_mode=True))
    )
    with httpx.Client(transport=httpx.MockTransport(handle)) as client:
        loader._http_client_sync = client
        result = loader.resolve_html_entry_sync(
            "offline.html", production_path=production, absolute_dev_asset_urls=True
        )

    assert 'src="https://app.example.com:8443/src/app.ts"' in result
    assert "from 'https://app.example.com:8443/@react-refresh'" in result
    assert 'href="https://app.example.com:8443/src/app.css"' in result
    assert 'href="https://app.example.com:8443/@vite/client"' in result
    assert '<a href="/account">' in result
    assert '<form action="/submit">' in result
    assert '<img src="/logo.svg">' in result
    read_bridge_config.cache_clear()


def test_vite_asset_loader_resolve_html_entry_missing_production_file_has_safe_error(tmp_path: Path) -> None:
    production = tmp_path / "secret" / "offline.html"
    loader = ViteAssetLoader(ViteConfig(paths=PathConfig(root=tmp_path), runtime=RuntimeConfig(dev_mode=False)))

    with pytest.raises(HTMLEntryResolutionError) as exc_info:
        loader.resolve_html_entry_sync("offline.html", production_path=production)

    assert str(production) not in str(exc_info.value)
    assert exc_info.value.production_path == production
