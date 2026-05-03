from collections.abc import AsyncGenerator
from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import httpx
import pytest
from litestar.exceptions import WebSocketDisconnect
from typing_extensions import Self

from litestar_vite.plugin import VitePlugin
from litestar_vite.plugin._proxy import (
    SSRProxyMiddleware,
    ViteProxyMiddleware,
    _extract_proxy_response,
    _proxy_stream_response,
    _stream_request_body,
    build_hmr_target_url,
    build_proxy_url,
    check_http2_support,
    create_hmr_target_getter,
    create_ssr_proxy_controller,
    create_ssr_websocket_handler,
    create_target_url_getter,
    create_vite_hmr_handler,
    extract_forward_headers,
    extract_subprotocols,
    normalize_proxy_prefixes,
)


class _DummyStreamContext:
    def __init__(self, response: object, body_stream: object | None = None) -> None:
        self._response = response
        self._body_stream = body_stream
        self.request_body_chunks: list[bytes] = []
        self.exited = False
        self.entered = False

    async def __aenter__(self) -> httpx.Response:
        self.entered = True
        if self._body_stream is not None:
            async for chunk in cast("AsyncGenerator[bytes, None]", self._body_stream):
                if chunk:
                    self.request_body_chunks.append(chunk)
        return cast("httpx.Response", self._response)

    async def __aexit__(self, *_args: object) -> None:
        self.exited = True


class DummyAsyncClient:
    def __init__(self, response: httpx.Response) -> None:
        self._response = response
        self.stream_calls: list[tuple[tuple[object, ...], dict[str, object]]] = []
        self.stream_context: _DummyStreamContext | None = None

    async def request(self, *_args: object, **_kwargs: object) -> httpx.Response:
        return cast("httpx.Response", self._response)

    def stream(self, *args: object, **kwargs: object) -> _DummyStreamContext:
        self.stream_calls.append((args, kwargs))
        body_stream = kwargs.get("content")
        self.stream_context = _DummyStreamContext(self._response, body_stream)
        return self.stream_context


class _DummyStreamingResponse:
    def __init__(
        self, chunks: list[bytes], status_code: int = 200, headers: list[tuple[str, str]] | None = None
    ) -> None:
        self.status_code = status_code
        self.headers = httpx.Headers(headers or {})
        self._chunks = chunks
        self.closed = False

    async def aiter_bytes(self) -> AsyncGenerator[bytes, None]:
        for chunk in self._chunks:
            yield chunk

    async def aclose(self) -> None:
        self.closed = True


async def test_stream_request_body_reads_chunks_preserving_order() -> None:
    chunks: list[bytes] = []

    async def receive() -> dict[str, object]:
        if not chunks:
            chunks.extend([b"first", b"second"])
        if chunks:
            body = chunks.pop(0)
            return {"type": "http.request", "body": body, "more_body": bool(chunks)}
        return {"type": "http.request", "body": b"", "more_body": False}

    generator = _stream_request_body(receive)
    collected: list[bytes] = [chunk async for chunk in generator]

    assert collected == [b"first", b"second"]


async def test_proxy_stream_response_streams_chunks_and_closes() -> None:
    response = _DummyStreamingResponse([b"one", b"two"])
    events: list[dict[str, object]] = []

    async def send(event: dict[str, object]) -> None:
        events.append(event)

    await _proxy_stream_response(cast("httpx.Response", response), send)

    status = next(event for event in events if event.get("type") == "http.response.start")
    bodies = [event for event in events if event.get("type") == "http.response.body"]

    assert status["status"] == 200
    assert bodies[0]["body"] == b"one"
    assert bodies[0]["more_body"] is True
    assert bodies[1]["body"] == b"two"
    assert bodies[1]["more_body"] is True
    assert bodies[2]["body"] == b""
    assert bodies[2]["more_body"] is False
    assert response.closed


pytestmark = pytest.mark.anyio


def test_extract_proxy_response_filters_headers() -> None:
    response = httpx.Response(
        200,
        headers=[
            ("content-type", "text/plain"),
            ("set-cookie", "a=1"),
            ("set-cookie", "b=2"),
            ("connection", "keep-alive"),
        ],
        content=b"ok",
    )
    status, headers, body = _extract_proxy_response(response)
    assert status == 200
    assert (b"content-type", b"text/plain") in headers
    assert all(key != b"connection" for key, _ in headers)
    assert headers.count((b"set-cookie", b"a=1")) == 1
    assert headers.count((b"set-cookie", b"b=2")) == 1
    assert body == b"ok"


def test_build_hmr_target_url_includes_query(tmp_path: Path) -> None:
    hotfile = tmp_path / "hot"
    hotfile.write_text("http://localhost:5173")
    scope = {"path": "/vite-hmr", "query_string": b"token=1"}

    target = build_hmr_target_url(hotfile, scope, "/vite-hmr", "/static/")
    assert target == "ws://localhost:5173/vite-hmr?token=1"


def test_extract_headers_and_subprotocols() -> None:
    scope = {
        "headers": [(b"host", b"example.com"), (b"x-test", b"value"), (b"sec-websocket-protocol", b"json,graphql")]
    }
    assert extract_forward_headers(scope) == [("x-test", "value")]
    assert extract_subprotocols(scope) == ["json", "graphql"]


def test_extract_forward_headers_drops_connection_derived_headers() -> None:
    scope = {
        "headers": [
            (b"Host", b"example.com"),
            (b"Connection", b"Upgrade, Keep-Alive"),
            (b"Upgrade", b"websocket"),
            (b"Sec-WebSocket-Key", b"abc123"),
            (b"Sec-WebSocket-Version", b"13"),
            (b"X-Test", b"value"),
        ]
    }

    assert extract_forward_headers(scope) == [("X-Test", "value")]


def test_normalize_proxy_prefixes(tmp_path: Path) -> None:
    prefixes = normalize_proxy_prefixes(
        ("/@vite",),
        asset_url="/static",
        resource_dir=tmp_path / "src",
        bundle_dir=tmp_path / "public",
        root_dir=tmp_path,
    )
    assert "/@vite" in prefixes
    assert "/static/" in prefixes


def test_target_url_getter_caches(tmp_path: Path) -> None:
    hotfile = tmp_path / "hot"
    hotfile.write_text("http://localhost:5173")
    cached: list[str | None] = [None]
    getter = create_target_url_getter(None, hotfile, cached)

    assert getter() == "http://localhost:5173"
    hotfile.write_text("http://changed:1234")
    assert getter() == "http://localhost:5173"


def test_hmr_target_getter_caches(tmp_path: Path) -> None:
    hotfile = tmp_path / "hot"
    hotfile.write_text("http://localhost:5173")
    (tmp_path / "hot.hmr").write_text("http://127.0.0.1:24678")

    getter = create_hmr_target_getter(hotfile, [None])
    assert getter() == "http://127.0.0.1:24678"


async def test_proxy_http_with_plugin_client(tmp_path: Path) -> None:
    hotfile = tmp_path / "hot"
    hotfile.write_text("http://localhost:5173")

    response = httpx.Response(200, headers={"content-type": "text/plain"}, content=b"ok")
    plugin_client = DummyAsyncClient(response)
    plugin = cast("VitePlugin", SimpleNamespace(proxy_client=cast("httpx.AsyncClient", plugin_client)))

    middleware = ViteProxyMiddleware(app=Mock(), hotfile_path=hotfile, asset_url="/static/", plugin=plugin)

    # Use POST to test body streaming (GET no longer sends body per #242)
    scope = {
        "method": "POST",
        "raw_path": b"/@vite/client",
        "query_string": b"",
        "headers": [(b"host", b"example.com")],
        "path": "/@vite/client",
    }
    events: list[dict[str, object]] = []

    chunks = [b"up-", b"streaming"]

    async def receive() -> dict[str, object]:
        if chunks:
            return {"type": "http.request", "body": chunks.pop(0), "more_body": bool(chunks)}
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(event: dict[str, object]) -> None:
        events.append(event)

    await middleware._proxy_http(scope, receive, send)

    assert events[0]["status"] == 200
    assert events[1]["body"] == b"ok"
    assert plugin_client.stream_context is not None
    assert plugin_client.stream_context.request_body_chunks == [b"up-", b"streaming"]


async def test_proxy_http_no_target(tmp_path: Path) -> None:
    hotfile = tmp_path / "hot"

    scope = {"method": "GET", "raw_path": b"/@vite/client", "query_string": b"", "headers": [], "path": "/@vite/client"}
    events: list[dict[str, object]] = []

    async def receive() -> dict[str, object]:
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(event: dict[str, object]) -> None:
        events.append(event)

    async def downstream(_scope: object, _receive: object, _send: object) -> None:
        await send({"type": "http.response.start", "status": 404, "headers": []})
        await send({"type": "http.response.body", "body": b"downstream", "more_body": False})

    middleware = ViteProxyMiddleware(app=downstream, hotfile_path=hotfile, asset_url="/static/")

    await middleware._proxy_http(scope, receive, send)
    assert events[0]["status"] == 404
    assert events[1]["body"] == b"downstream"


async def test_vite_hmr_handler_timeout(tmp_path: Path) -> None:
    hotfile = tmp_path / "hot"
    hotfile.write_text("http://localhost:5173")

    handler = create_vite_hmr_handler(hotfile)

    socket = MagicMock()
    socket.scope = {"path": "/vite-hmr", "query_string": b"", "headers": []}
    socket.accept = AsyncMock()
    socket.close = AsyncMock()

    class FailingConnect:
        async def __aenter__(self) -> None:
            raise TimeoutError

        async def __aexit__(self, *_args: object) -> None:
            return None

    with patch("litestar_vite.plugin._proxy.websockets.connect", return_value=FailingConnect()):
        await handler.fn(socket)

    socket.close.assert_called()


async def test_vite_hmr_handler_accepts_multiple_subprotocols(tmp_path: Path) -> None:
    hotfile = tmp_path / "hot"
    hotfile.write_text("http://localhost:5173")

    handler = create_vite_hmr_handler(hotfile)

    socket = MagicMock()
    socket.scope = {"path": "/vite-hmr", "query_string": b"", "headers": [(b"sec-websocket-protocol", b"json,graphql")]}
    socket.accept = AsyncMock()
    socket.close = AsyncMock()
    socket.receive_text = AsyncMock(side_effect=WebSocketDisconnect(code=1000, detail="Client disconnected"))

    class _DummyUpstream:
        async def __aenter__(self) -> Self:
            return self

        async def __aexit__(self, *_args: object) -> None:
            return None

        def __aiter__(self) -> "_DummyUpstream":
            return self

        async def __anext__(self) -> bytes:
            raise StopAsyncIteration

        async def send(self, *_args: object, **_kwargs: object) -> None:
            return None

        async def close(self) -> None:
            return None

    with patch("litestar_vite.plugin._proxy.websockets.connect") as mock_connect:
        mock_connect.return_value.__aenter__.return_value = _DummyUpstream()
        await handler.fn(socket)

    socket.accept.assert_awaited_once_with(subprotocols="json")


async def test_ssr_proxy_middleware_http_success() -> None:
    """SSRProxyMiddleware streams upstream response and filters hop-by-hop headers."""
    response = cast(
        "httpx.Response",
        _DummyStreamingResponse(
            chunks=[b"ok"],
            status_code=200,
            headers=[
                ("content-type", "text/plain"),
                ("set-cookie", "a=1"),
                ("set-cookie", "b=2"),
                ("connection", "keep-alive"),
            ],
        ),
    )
    plugin = cast("VitePlugin", SimpleNamespace(proxy_client=cast("httpx.AsyncClient", DummyAsyncClient(response))))

    inner_app = AsyncMock()
    middleware = SSRProxyMiddleware(app=inner_app, target="http://localhost:3000", http2=False, plugin=plugin)

    send_events: list[dict[str, object]] = []

    async def receive() -> dict[str, object]:
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(event: dict[str, object]) -> None:
        send_events.append(event)

    scope: dict[str, object] = {"method": "GET", "raw_path": b"/", "query_string": b"", "headers": [(b"x-test", b"ok")]}
    await middleware._proxy_http(scope, receive, send, "http://localhost:3000")

    start = next(event for event in send_events if event["type"] == "http.response.start")
    bodies = [event for event in send_events if event["type"] == "http.response.body"]

    assert start["status"] == 200
    assert (b"connection", b"keep-alive") not in cast("list[tuple[bytes, bytes]]", start["headers"])
    assert cast("list[tuple[bytes, bytes]]", start["headers"]).count((b"set-cookie", b"a=1")) == 1
    assert cast("list[tuple[bytes, bytes]]", start["headers"]).count((b"set-cookie", b"b=2")) == 1

    streamed_body = b"".join(cast("bytes", event["body"]) for event in bodies)
    assert streamed_body.startswith(b"ok")


async def test_ssr_proxy_middleware_falls_through_when_target_unavailable() -> None:
    """When framework dev server is unavailable, the middleware falls through to the next ASGI app."""
    inner_app = AsyncMock()
    middleware = SSRProxyMiddleware(app=inner_app, target=None, hotfile_path=None, http2=False)

    scope = cast("Any", {"type": "http", "method": "GET", "path": "/", "raw_path": b"/", "query_string": b""})
    receive = AsyncMock()
    send = AsyncMock()

    await middleware(scope, receive, send)

    inner_app.assert_awaited_once_with(scope, receive, send)


def test_build_proxy_url_and_http2_support() -> None:
    assert build_proxy_url("http://localhost:3000", "/path", "a=1") == "http://localhost:3000/path?a=1"
    assert build_proxy_url("http://localhost:3000", "/path", "") == "http://localhost:3000/path"
    assert check_http2_support(False) is False


# ===== Issue #242: GET requests should not send a request body =====


async def test_proxy_http_get_does_not_send_body(tmp_path: Path) -> None:
    """GET requests must pass content=None so httpx does not add Transfer-Encoding: chunked.

    Regression test for https://github.com/litestar-org/litestar-vite/issues/242
    """
    hotfile = tmp_path / "hot"
    hotfile.write_text("http://localhost:5173")

    response = httpx.Response(200, headers={"content-type": "text/plain"}, content=b"ok")
    plugin_client = DummyAsyncClient(response)
    plugin = cast("VitePlugin", SimpleNamespace(proxy_client=cast("httpx.AsyncClient", plugin_client)))

    middleware = ViteProxyMiddleware(app=Mock(), hotfile_path=hotfile, asset_url="/static/", plugin=plugin)

    scope = {
        "method": "GET",
        "raw_path": b"/@vite/client",
        "query_string": b"",
        "headers": [(b"host", b"example.com")],
        "path": "/@vite/client",
    }
    events: list[dict[str, object]] = []

    async def receive() -> dict[str, object]:
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(event: dict[str, object]) -> None:
        events.append(event)

    await middleware._proxy_http(scope, receive, send)

    # Verify the response was successful
    assert events[0]["status"] == 200

    # Verify content=None was passed (no body for GET)
    assert len(plugin_client.stream_calls) == 1
    _, kwargs = plugin_client.stream_calls[0]
    assert kwargs["content"] is None, "GET requests must not send a request body to avoid chunked encoding"


async def test_proxy_http_head_does_not_send_body(tmp_path: Path) -> None:
    """HEAD requests must pass content=None.

    Regression test for https://github.com/litestar-org/litestar-vite/issues/242
    """
    hotfile = tmp_path / "hot"
    hotfile.write_text("http://localhost:5173")

    response = httpx.Response(200, headers={"content-type": "text/plain"}, content=b"")
    plugin_client = DummyAsyncClient(response)
    plugin = cast("VitePlugin", SimpleNamespace(proxy_client=cast("httpx.AsyncClient", plugin_client)))

    middleware = ViteProxyMiddleware(app=Mock(), hotfile_path=hotfile, asset_url="/static/", plugin=plugin)

    scope = {
        "method": "HEAD",
        "raw_path": b"/@vite/client",
        "query_string": b"",
        "headers": [(b"host", b"example.com")],
        "path": "/@vite/client",
    }
    events: list[dict[str, object]] = []

    async def receive() -> dict[str, object]:
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(event: dict[str, object]) -> None:
        events.append(event)

    await middleware._proxy_http(scope, receive, send)

    assert len(plugin_client.stream_calls) == 1
    _, kwargs = plugin_client.stream_calls[0]
    assert kwargs["content"] is None, "HEAD requests must not send a request body"


async def test_proxy_http_options_does_not_send_body(tmp_path: Path) -> None:
    """OPTIONS requests must pass content=None.

    Regression test for https://github.com/litestar-org/litestar-vite/issues/242
    """
    hotfile = tmp_path / "hot"
    hotfile.write_text("http://localhost:5173")

    response = httpx.Response(200, headers={"content-type": "text/plain"}, content=b"")
    plugin_client = DummyAsyncClient(response)
    plugin = cast("VitePlugin", SimpleNamespace(proxy_client=cast("httpx.AsyncClient", plugin_client)))

    middleware = ViteProxyMiddleware(app=Mock(), hotfile_path=hotfile, asset_url="/static/", plugin=plugin)

    scope = {
        "method": "OPTIONS",
        "raw_path": b"/@vite/client",
        "query_string": b"",
        "headers": [(b"host", b"example.com")],
        "path": "/@vite/client",
    }
    events: list[dict[str, object]] = []

    async def receive() -> dict[str, object]:
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(event: dict[str, object]) -> None:
        events.append(event)

    await middleware._proxy_http(scope, receive, send)

    assert len(plugin_client.stream_calls) == 1
    _, kwargs = plugin_client.stream_calls[0]
    assert kwargs["content"] is None, "OPTIONS requests must not send a request body"


async def test_proxy_http_post_still_sends_body(tmp_path: Path) -> None:
    """POST requests must still stream the request body.

    Ensures the fix for #242 does not break body-carrying methods.
    """
    hotfile = tmp_path / "hot"
    hotfile.write_text("http://localhost:5173")

    response = httpx.Response(200, headers={"content-type": "text/plain"}, content=b"ok")
    plugin_client = DummyAsyncClient(response)
    plugin = cast("VitePlugin", SimpleNamespace(proxy_client=cast("httpx.AsyncClient", plugin_client)))

    middleware = ViteProxyMiddleware(app=Mock(), hotfile_path=hotfile, asset_url="/static/", plugin=plugin)

    scope = {
        "method": "POST",
        "raw_path": b"/@vite/client",
        "query_string": b"",
        "headers": [(b"host", b"example.com")],
        "path": "/@vite/client",
    }
    events: list[dict[str, object]] = []
    chunks = [b"post-data"]

    async def receive() -> dict[str, object]:
        if chunks:
            return {"type": "http.request", "body": chunks.pop(0), "more_body": bool(chunks)}
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(event: dict[str, object]) -> None:
        events.append(event)

    await middleware._proxy_http(scope, receive, send)

    assert events[0]["status"] == 200
    assert len(plugin_client.stream_calls) == 1
    _, kwargs = plugin_client.stream_calls[0]
    assert kwargs["content"] is not None, "POST requests must still send a request body"
    # Verify body was actually consumed
    assert plugin_client.stream_context is not None
    assert plugin_client.stream_context.request_body_chunks == [b"post-data"]


async def test_proxy_http_put_still_sends_body(tmp_path: Path) -> None:
    """PUT requests must still stream the request body."""
    hotfile = tmp_path / "hot"
    hotfile.write_text("http://localhost:5173")

    response = httpx.Response(200, headers={"content-type": "text/plain"}, content=b"ok")
    plugin_client = DummyAsyncClient(response)
    plugin = cast("VitePlugin", SimpleNamespace(proxy_client=cast("httpx.AsyncClient", plugin_client)))

    middleware = ViteProxyMiddleware(app=Mock(), hotfile_path=hotfile, asset_url="/static/", plugin=plugin)

    scope = {
        "method": "PUT",
        "raw_path": b"/@vite/client",
        "query_string": b"",
        "headers": [(b"host", b"example.com")],
        "path": "/@vite/client",
    }
    events: list[dict[str, object]] = []

    async def receive() -> dict[str, object]:
        return {"type": "http.request", "body": b"put-data", "more_body": False}

    async def send(event: dict[str, object]) -> None:
        events.append(event)

    await middleware._proxy_http(scope, receive, send)

    assert len(plugin_client.stream_calls) == 1
    _, kwargs = plugin_client.stream_calls[0]
    assert kwargs["content"] is not None, "PUT requests must still send a request body"


async def test_ssr_proxy_middleware_get_does_not_send_body() -> None:
    """SSRProxyMiddleware GET requests must pass content=None (#246 invariant).

    Regression test for https://github.com/litestar-org/litestar-vite/issues/242
    """
    response = cast(
        "httpx.Response",
        _DummyStreamingResponse(chunks=[b"ok"], status_code=200, headers=[("content-type", "text/plain")]),
    )
    dummy_client = DummyAsyncClient(response)
    plugin = cast("VitePlugin", SimpleNamespace(proxy_client=cast("httpx.AsyncClient", dummy_client)))

    middleware = SSRProxyMiddleware(app=AsyncMock(), target="http://localhost:3000", http2=False, plugin=plugin)

    async def receive() -> dict[str, object]:
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(_event: dict[str, object]) -> None:
        return None

    scope: dict[str, object] = {"method": "GET", "raw_path": b"/", "query_string": b"", "headers": []}
    await middleware._proxy_http(scope, receive, send, "http://localhost:3000")

    assert len(dummy_client.stream_calls) == 1
    _, kwargs = dummy_client.stream_calls[0]
    assert kwargs["content"] is None, "SSR proxy GET requests must not send a request body"


async def test_ssr_proxy_middleware_post_still_sends_body() -> None:
    """SSRProxyMiddleware POST requests must still stream the request body."""
    response = cast(
        "httpx.Response",
        _DummyStreamingResponse(chunks=[b"ok"], status_code=200, headers=[("content-type", "text/plain")]),
    )
    dummy_client = DummyAsyncClient(response)
    plugin = cast("VitePlugin", SimpleNamespace(proxy_client=cast("httpx.AsyncClient", dummy_client)))

    middleware = SSRProxyMiddleware(app=AsyncMock(), target="http://localhost:3000", http2=False, plugin=plugin)

    async def receive() -> dict[str, object]:
        return {"type": "http.request", "body": b"post-body", "more_body": False}

    async def send(_event: dict[str, object]) -> None:
        return None

    scope: dict[str, object] = {"method": "POST", "raw_path": b"/submit", "query_string": b"", "headers": []}
    await middleware._proxy_http(scope, receive, send, "http://localhost:3000")

    assert len(dummy_client.stream_calls) == 1
    _, kwargs = dummy_client.stream_calls[0]
    assert kwargs["content"] is not None, "SSR proxy POST requests must still send a request body"


async def test_create_ssr_proxy_controller_emits_deprecation_warning(recwarn: pytest.WarningsRecorder) -> None:
    """create_ssr_proxy_controller is deprecated; the alias still returns a WS-only Controller."""
    handler_class = create_ssr_proxy_controller(target="http://localhost:3000")

    assert handler_class.__name__ == "SSRProxyWebSocketHandler"
    assert any(issubclass(w.category, DeprecationWarning) for w in recwarn.list)


def test_create_ssr_websocket_handler_returns_ws_only_controller() -> None:
    """create_ssr_websocket_handler returns a Controller hosting only the WS handler."""
    handler_class = create_ssr_websocket_handler(target="http://localhost:3000")
    assert handler_class.__name__ == "SSRProxyWebSocketHandler"


def test_ssr_proxy_middleware_falls_through_to_user_root_route(monkeypatch: pytest.MonkeyPatch) -> None:
    """Regression guard: a user-defined / handler in framework mode no longer collides with the proxy.

    Pre-C4 the SSRProxyController hard-bound path=['/', '/{path:path}'] which raised
    ``Handler already registered for path '/'`` at app construction. Middleware falls through
    to user routes naturally.
    """
    from litestar import Litestar, get
    from litestar.testing import TestClient

    from litestar_vite.config import ExternalDevServer, PathConfig, RuntimeConfig, ViteConfig
    from litestar_vite.config._runtime import _cached_resolve_proxy_mode
    from litestar_vite.plugin import VitePlugin

    monkeypatch.delenv("VITE_PROXY_MODE", raising=False)
    _cached_resolve_proxy_mode.cache_clear()

    @get("/", name="user_root", sync_to_thread=False)
    def user_root() -> str:
        return "user-served root"

    config = ViteConfig(
        mode="framework",
        paths=PathConfig(),
        runtime=RuntimeConfig(dev_mode=True, external_dev_server=ExternalDevServer(target="http://127.0.0.1:14321")),
    )
    app = Litestar(plugins=[VitePlugin(config=config)], route_handlers=[user_root])

    with TestClient(app=app) as client:
        response = client.get("/")
        assert response.status_code == 200
        assert response.text == "user-served root"


def test_framework_mode_proxies_root_when_no_user_handler_at_root(monkeypatch: pytest.MonkeyPatch) -> None:
    """Regression: GET / must proxy to the framework dev server when no user handler claims '/'.

    Pre-fix the plugin registered SSRProxyMiddleware (per-route) plus a WS-only Controller at
    path=['/', '/{path:path}']. Litestar matched the WS route for HTTP GET / and returned
    405 Method Not Allowed before the middleware ever ran. The fix re-introduces the HTTP
    catch-all as an actual route handler so Litestar matches it and dispatches to the proxy.
    """
    from litestar import Litestar
    from litestar.testing import TestClient

    from litestar_vite.config import ExternalDevServer, PathConfig, RuntimeConfig, ViteConfig
    from litestar_vite.config._runtime import _cached_resolve_proxy_mode
    from litestar_vite.plugin import VitePlugin

    monkeypatch.delenv("VITE_PROXY_MODE", raising=False)
    _cached_resolve_proxy_mode.cache_clear()

    config = ViteConfig(
        mode="framework",
        paths=PathConfig(),
        runtime=RuntimeConfig(dev_mode=True, external_dev_server=ExternalDevServer(target="http://127.0.0.1:14321")),
    )
    app = Litestar(plugins=[VitePlugin(config=config)])

    with TestClient(app=app) as client:
        response = client.get("/")
        # Framework dev server is not running, so the proxy handler should surface the
        # connect error as 503. The previous regression returned 405 because the WS-only
        # '/' route was matched by Litestar before any proxy code ran.
        assert response.status_code != 405, "GET / must not 405; framework mode must proxy when no user '/' handler"
        assert response.status_code == 503


def test_framework_mode_proxies_arbitrary_path_when_user_owns_root(monkeypatch: pytest.MonkeyPatch) -> None:
    """User-defined GET / coexists with the proxy: '/' is user-served, other paths are proxied.

    Tests the collision-detection path: when app_config.route_handlers contains an HTTP
    handler at '/', the plugin must drop '/' from the proxy handler's path list (keeping
    only '/{path:path}'). The user handler answers GET /; everything else proxies.
    """
    from litestar import Litestar, get
    from litestar.testing import TestClient

    from litestar_vite.config import ExternalDevServer, PathConfig, RuntimeConfig, ViteConfig
    from litestar_vite.config._runtime import _cached_resolve_proxy_mode
    from litestar_vite.plugin import VitePlugin

    monkeypatch.delenv("VITE_PROXY_MODE", raising=False)
    _cached_resolve_proxy_mode.cache_clear()

    @get("/", name="user_root", sync_to_thread=False)
    def user_root() -> str:
        return "user-served root"

    config = ViteConfig(
        mode="framework",
        paths=PathConfig(),
        runtime=RuntimeConfig(dev_mode=True, external_dev_server=ExternalDevServer(target="http://127.0.0.1:14321")),
    )
    app = Litestar(plugins=[VitePlugin(config=config)], route_handlers=[user_root])

    with TestClient(app=app) as client:
        # User handler wins for / (no collision exception, plugin dropped its own '/')
        root = client.get("/")
        assert root.status_code == 200
        assert root.text == "user-served root"
        # Proxy handler still claims everything else
        other = client.get("/some-framework-page")
        assert other.status_code == 503


def test_get_litestar_route_prefixes_excludes_websocket_only_routes() -> None:
    """get_litestar_route_prefixes must filter out WebSocket-only routes.

    The proxy middlewares (Vite/SSR) declare scopes={ScopeType.HTTP}, so the route check
    must be HTTP-only. WebSocket routes must not poison the cached prefix list and cause
    HTTP requests at the same path to skip the proxy.
    """
    from typing import Any

    from litestar import Controller, Litestar, WebSocket, websocket

    from litestar_vite.plugin import get_litestar_route_prefixes

    class _WSOnly(Controller):
        @websocket(path=["/", "/{path:path}"], name="ws_only")
        async def handler(self, socket: WebSocket[Any, Any, Any]) -> None:  # pragma: no cover
            await socket.accept()

    app = Litestar(route_handlers=[_WSOnly])

    prefixes = get_litestar_route_prefixes(app)

    assert "/" not in prefixes, f"WebSocket-only '/' must not appear in HTTP route prefixes; got {prefixes}"
    assert "/{path:path}" not in prefixes, (
        f"WebSocket-only '/{{path:path}}' must not appear in HTTP route prefixes; got {prefixes}"
    )
