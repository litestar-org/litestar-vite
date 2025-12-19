from pathlib import Path
from typing import Any

import pytest
from litestar.types import HTTPRequestEvent, Receive, Scope, Send

from litestar_vite.plugin import ViteProxyMiddleware


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

    # Project paths (resource_dir) are proxied when configured
    middleware_with_src = ViteProxyMiddleware(noop, hotfile_path=hotfile, resource_dir=Path("src"))
    assert middleware_with_src._should_proxy("/src/main.ts", dummy_scope)

    # Custom resource dir
    middleware_with_resources = ViteProxyMiddleware(noop, hotfile_path=hotfile, resource_dir=Path("resources"))
    assert middleware_with_resources._should_proxy("/resources/app.tsx", dummy_scope)
    assert not middleware_with_resources._should_proxy("/src/main.ts", dummy_scope)


@pytest.mark.anyio
async def test_proxy_response_includes_more_body_field(hotfile: Path) -> None:
    """Test that proxy response body includes 'more_body': False per ASGI spec.

    This is important for compatibility with middleware that expects the more_body
    field, such as logging hooks that check message["more_body"] to detect end of response.
    """
    sent = _Recorder()

    async def downstream(scope: Scope, receive: Receive, send: Send) -> None:
        # This won't be called for Vite paths
        pass

    ViteProxyMiddleware(downstream, hotfile_path=hotfile)

    # Test the 503 response when Vite server is not running (hotfile doesn't exist)
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
