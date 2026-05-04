import json
from pathlib import Path
from typing import Any

import pytest
from litestar.types import HTTPRequestEvent, Receive, Scope, Send

from litestar_vite.plugin import ViteProxyMiddleware
from litestar_vite.utils import read_bridge_config


class _Recorder:
    def __init__(self) -> None:
        self.events: list[dict[str, Any]] = []

    async def __call__(self, event: dict[str, Any]) -> None:
        self.events.append(event)


@pytest.fixture
def hotfile(tmp_path: Path) -> Path:
    """Create a hotfile with a test Vite server URL.

    Returns:
        The fixture value.
    """
    hotfile_path = tmp_path / "hot"
    hotfile_path.write_text("http://127.0.0.1:9999")
    return hotfile_path


@pytest.mark.anyio
async def test_proxy_http_short_circuits_non_vite_paths(hotfile: Path) -> None:
    sent = _Recorder()

    async def downstream(scope: Scope, receive: Receive, send: Send) -> None:
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": b"ok"})  # type: ignore[arg-type]

    middleware = ViteProxyMiddleware(downstream, hotfile_path=hotfile)

    scope = {
        "type": "http",
        "method": "GET",
        "path": "/not-a-vite-path",
        "raw_path": b"/not-a-vite-path",
        "query_string": b"",
        "headers": [],
    }

    async def receive() -> HTTPRequestEvent:
        return {"type": "http.request", "body": b"", "more_body": False}

    await middleware(scope, receive, sent.__call__)  # type: ignore[arg-type]

    assert any(ev.get("status") == 200 for ev in sent.events)


@pytest.mark.anyio
async def test_proxy_should_proxy_matches_vite_paths(hotfile: Path) -> None:
    # We don't actually hit upstream; just check that _should_proxy matches prefixes
    async def noop(scope: Scope, receive: Receive, send: Send) -> None:
        return None

    middleware = ViteProxyMiddleware(noop, hotfile_path=hotfile)
    dummy_scope: Scope = {"type": "http", "path": "/", "headers": [], "app": None}  # type: ignore

    # Vite internal paths are always proxied
    assert middleware._should_proxy("/@vite/client", dummy_scope)
    assert middleware._should_proxy("/node_modules/.vite/chunk.js", dummy_scope)
    assert middleware._should_proxy("/vite-hmr", dummy_scope)
    assert middleware._should_proxy("/@analogjs/vite-plugin-angular", dummy_scope)
    assert not middleware._should_proxy("/api/users", dummy_scope)

    # Static file extensions from any path should be proxied
    assert middleware._should_proxy("/fonts/my-font.woff2", dummy_scope)
    assert middleware._should_proxy("/fonts/my-font.WOFF2", dummy_scope)
    assert middleware._should_proxy("/assets/logo.png", dummy_scope)
    assert middleware._should_proxy("/favicon.ico", dummy_scope)
    assert middleware._should_proxy("/assets/manifest.webmanifest", dummy_scope)
    assert middleware._should_proxy("/assets/bundle.wasm", dummy_scope)
    assert middleware._should_proxy("/deep/path/to/script.ts", dummy_scope)

    # Files without static extensions and not in Vite paths should not be proxied
    assert not middleware._should_proxy("/api/data", dummy_scope)
    assert not middleware._should_proxy("/login", dummy_scope)

    # node_modules paths for npm packages with static assets (e.g., @fontsource fonts)
    assert middleware._should_proxy("/node_modules/@fontsource/geist/files/font.woff2", dummy_scope)

    # Project paths (resource_dir) are proxied when configured
    middleware_with_src = ViteProxyMiddleware(noop, hotfile_path=hotfile, resource_dir=Path("src"))
    assert middleware_with_src._should_proxy("/src/main.ts", dummy_scope)

    # Custom resource dir
    middleware_with_resources = ViteProxyMiddleware(noop, hotfile_path=hotfile, resource_dir=Path("resources"))
    assert middleware_with_resources._should_proxy("/resources/app.tsx", dummy_scope)
    assert not middleware_with_resources._should_proxy("/src/README.md", dummy_scope)


@pytest.mark.anyio
async def test_proxy_should_proxy_uses_decoded_path_for_litestar_routes(hotfile: Path) -> None:
    """Decode path before route checks so encoded API/static boundary routes are respected."""

    async def noop(scope: Scope, receive: Receive, send: Send) -> None:
        return None

    middleware = ViteProxyMiddleware(noop, hotfile_path=hotfile)

    class MockRoute:
        def __init__(self, path: str) -> None:
            self.path = path

    class MockState:
        pass

    class MockApp:
        def __init__(self) -> None:
            self.routes = [MockRoute("/api"), MockRoute("/schema")]
            self.openapi_config = None
            self.state = MockState()

    scope_with_app: Scope = {"type": "http", "path": "/", "headers": [], "app": MockApp()}  # type: ignore

    assert not middleware._should_proxy("/api%2Fusers", scope_with_app)
    assert not middleware._should_proxy("/schema%2Fopenapi%2Ejson", scope_with_app)
    assert middleware._should_proxy("/assets%2Fmain%2Ejs", scope_with_app)


@pytest.mark.anyio
async def test_proxy_response_includes_more_body_field(hotfile: Path) -> None:
    """Test that fallback response bodies include 'more_body': False per ASGI spec.

    This is important for compatibility with middleware that expects the more_body
    field, such as logging hooks that check message["more_body"] to detect end of response.
    """
    sent = _Recorder()

    async def downstream(scope: Scope, receive: Receive, send: Send) -> None:
        await send({"type": "http.response.start", "status": 404, "headers": []})
        await send({"type": "http.response.body", "body": b"downstream", "more_body": False})

    ViteProxyMiddleware(downstream, hotfile_path=hotfile)

    # Test the fallback response when Vite server is not running (hotfile doesn't exist)
    no_hotfile = Path("/nonexistent/hot")
    middleware_no_server = ViteProxyMiddleware(downstream, hotfile_path=no_hotfile)

    scope = {
        "type": "http",
        "method": "GET",
        "path": "/@vite/client",  # A Vite path that should be proxied
        "raw_path": b"/@vite/client",
        "query_string": b"",
        "headers": [],
    }

    async def receive() -> HTTPRequestEvent:
        return {"type": "http.request", "body": b"", "more_body": False}

    await middleware_no_server(scope, receive, sent.__call__)  # type: ignore[arg-type]

    # Find the response body event
    body_events = [ev for ev in sent.events if ev.get("type") == "http.response.body"]
    assert len(body_events) == 1
    assert "more_body" in body_events[0], "Response body must include 'more_body' field per ASGI spec"
    assert body_events[0]["more_body"] is False


@pytest.mark.anyio
async def test_proxy_respects_litestar_routes_when_asset_url_is_root(hotfile: Path) -> None:
    """Test that when asset_url='/', Litestar routes are NOT proxied.

    This ensures that routes like /schema, /api, etc. are handled by Litestar
    even when the Vite proxy is configured to capture everything (asset_url='/').
    """

    async def noop(scope: Scope, receive: Receive, send: Send) -> None:
        return None

    # Configure middleware with asset_url="/" (catch-all)
    middleware = ViteProxyMiddleware(noop, hotfile_path=hotfile, asset_url="/")

    # Mock app structure for route detection
    class MockRoute:
        def __init__(self, path: str) -> None:
            self.path = path

    class MockState:
        pass

    class MockApp:
        def __init__(self) -> None:
            self.routes = [MockRoute("/schema"), MockRoute("/api/users")]
            self.openapi_config = None
            self.state = MockState()

    mock_app = MockApp()
    scope_with_app: Scope = {"type": "http", "path": "/", "headers": [], "app": mock_app}  # type: ignore

    # 1. Registered Litestar route -> Should NOT proxy
    assert not middleware._should_proxy("/schema", scope_with_app)
    assert not middleware._should_proxy("/api/users", scope_with_app)

    # 2. Non-existent route (presumed Vite asset) -> Should proxy
    # Since asset_url="/", everything matches the prefix
    assert middleware._should_proxy("/assets/main.js", scope_with_app)
    assert middleware._should_proxy("/unknown-route", scope_with_app)

    # 3. Vite internal paths -> Should proxy
    assert middleware._should_proxy("/@vite/client", scope_with_app)


# ===== Path Traversal Protection =====


def test_should_proxy_rejects_path_traversal(hotfile: Path) -> None:
    """Paths containing traversal sequences after URL decoding must be rejected."""

    async def downstream(scope: Scope, receive: Receive, send: Send) -> None:
        pass

    middleware = ViteProxyMiddleware(downstream, hotfile_path=hotfile)
    scope: Scope = {"type": "http", "path": "/", "headers": []}  # type: ignore

    # Encoded traversal: %2e%2e/
    assert not middleware._should_proxy("/%2e%2e/etc/passwd", scope)
    # Double-encoded traversal
    assert not middleware._should_proxy("/%252e%252e/etc/passwd", scope)
    # Plain traversal in a suffix-matching path
    assert not middleware._should_proxy("/static/../../../etc/passwd.js", scope)
    # Traversal with backslashes (Windows-style)
    assert not middleware._should_proxy("/static/..\\..\\etc\\passwd.js", scope)
    # Normal paths with dots should still work
    assert middleware._should_proxy("/static/file.name.js", scope)
    assert middleware._should_proxy("/node_modules/.vite/deps/vue.js", scope)


# ===== Bridge-config target precedence (litestar-vite-c1t) =====


def _write_bridge(tmp_path: Path, payload: object) -> Path:
    bridge = tmp_path / ".litestar.json"
    bridge.write_text(json.dumps(payload))
    return bridge


@pytest.fixture(autouse=False)
def _clear_bridge_cache() -> None:
    read_bridge_config.cache_clear()


def test_proxy_target_preserves_resolved_vite_hotfile_url_when_bridge_exists(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The hotfile is the resolved upstream URL even when bridge config exists.

    ``proxyMode='vite'`` still needs the loader to anchor browser-facing asset
    URLs on bridge ``appUrl``, but the proxy target itself must remain the actual
    Vite URL written by the JS side. Rebuilding from bridge ``host``+``port``
    drops HTTPS and IPv6/wildcard normalization.
    """
    read_bridge_config.cache_clear()
    hotfile = tmp_path / "hot"
    hotfile.write_text("https://[::1]:5173")
    bridge = _write_bridge(
        tmp_path, {"appUrl": "https://litestar-bridge:8443", "host": "::", "port": 5173, "proxyMode": "vite"}
    )
    monkeypatch.setenv("LITESTAR_VITE_CONFIG_PATH", str(bridge))

    async def noop(scope: Scope, receive: Receive, send: Send) -> None:
        return None

    middleware = ViteProxyMiddleware(noop, hotfile_path=hotfile)
    target = middleware._get_target_base_url()

    assert target == "https://[::1]:5173"
    read_bridge_config.cache_clear()


def test_proxy_target_preserves_hotfile_for_framework_proxy_mode(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Framework/external proxy modes must not route asset requests to bridge host:port."""
    read_bridge_config.cache_clear()
    hotfile = tmp_path / "hot"
    hotfile.write_text("http://framework-dev-server:4321")
    bridge = _write_bridge(
        tmp_path, {"appUrl": "http://litestar-bridge:8000", "host": "127.0.0.1", "port": 5173, "proxyMode": "proxy"}
    )
    monkeypatch.setenv("LITESTAR_VITE_CONFIG_PATH", str(bridge))

    async def noop(scope: Scope, receive: Receive, send: Send) -> None:
        return None

    middleware = ViteProxyMiddleware(noop, hotfile_path=hotfile)
    target = middleware._get_target_base_url()

    assert target == "http://framework-dev-server:4321"
    read_bridge_config.cache_clear()


def test_proxy_target_falls_back_to_hotfile_when_bridge_missing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    read_bridge_config.cache_clear()
    hotfile = tmp_path / "hot"
    hotfile.write_text("http://127.0.0.1:9999")
    monkeypatch.setenv("LITESTAR_VITE_CONFIG_PATH", str(tmp_path / "missing.json"))

    async def noop(scope: Scope, receive: Receive, send: Send) -> None:
        return None

    middleware = ViteProxyMiddleware(noop, hotfile_path=hotfile)
    target = middleware._get_target_base_url()

    assert target == "http://127.0.0.1:9999"
    read_bridge_config.cache_clear()


def test_proxy_target_falls_back_to_hotfile_when_bridge_lacks_host_port(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Bridge metadata never changes the hotfile target."""
    read_bridge_config.cache_clear()
    hotfile = tmp_path / "hot"
    hotfile.write_text("http://127.0.0.1:9999")
    bridge = _write_bridge(tmp_path, {"appUrl": "http://anywhere", "host": "127.0.0.1", "port": "not-an-int"})
    monkeypatch.setenv("LITESTAR_VITE_CONFIG_PATH", str(bridge))

    async def noop(scope: Scope, receive: Receive, send: Send) -> None:
        return None

    middleware = ViteProxyMiddleware(noop, hotfile_path=hotfile)
    target = middleware._get_target_base_url()

    assert target == "http://127.0.0.1:9999"
    read_bridge_config.cache_clear()


def test_proxy_target_returns_none_when_neither_present(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    read_bridge_config.cache_clear()
    monkeypatch.setenv("LITESTAR_VITE_CONFIG_PATH", str(tmp_path / "missing.json"))

    async def noop(scope: Scope, receive: Receive, send: Send) -> None:
        return None

    middleware = ViteProxyMiddleware(noop, hotfile_path=tmp_path / "no-hot")
    target = middleware._get_target_base_url()

    assert target is None
    read_bridge_config.cache_clear()


def test_proxy_target_cache_invariant(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Second call to _get_target_base_url must not re-read the hotfile.

    The middleware-level ``_cache_initialized`` flag ensures target resolution
    happens at most once per middleware instance lifetime. The hotfile is the
    upstream target source and readiness signal.
    """
    import litestar_vite.plugin._proxy as proxy_module

    read_bridge_config.cache_clear()
    hotfile = tmp_path / "hot"
    hotfile.write_text("http://bridge")

    call_count = 0
    real_read = proxy_module.read_hotfile_url

    def counting_read(hotfile_path: Path) -> str:
        nonlocal call_count
        call_count += 1
        return real_read(hotfile_path)

    monkeypatch.setattr(proxy_module, "read_hotfile_url", counting_read)

    async def noop(scope: Scope, receive: Receive, send: Send) -> None:
        return None

    middleware = ViteProxyMiddleware(noop, hotfile_path=hotfile)

    middleware._get_target_base_url()
    middleware._get_target_base_url()
    middleware._get_target_base_url()

    assert call_count == 1
    read_bridge_config.cache_clear()
