from pathlib import Path
from types import SimpleNamespace
from typing import AsyncGenerator, cast
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import httpx
import pytest

from litestar_vite.plugin import VitePlugin
from litestar_vite.plugin._proxy import (
    ViteProxyMiddleware,
    _extract_proxy_response,
    _proxy_stream_response,
    _stream_request_body,
    build_hmr_target_url,
    build_proxy_url,
    extract_forward_headers,
    check_http2_support,
    create_hmr_target_getter,
    create_ssr_proxy_controller,
    create_target_url_getter,
    create_vite_hmr_handler,
    extract_forward_headers,
    extract_subprotocols,
    normalize_proxy_prefixes,
)
from litestar.exceptions import WebSocketDisconnect
from litestar.response.streaming import ASGIStreamingResponse


class _DummyStreamContext:
    def __init__(self, response: object, body_stream: object | None = None) -> None:
        self._response = response
        self._body_stream = body_stream
        self.request_body_chunks: list[bytes] = []
        self.exited = False
        self.entered = False

    async def __aenter__(self) -> object:
        self.entered = True
        if self._body_stream is not None:
            async for chunk in cast("AsyncGenerator[bytes, None]", self._body_stream):
                if chunk:
                    self.request_body_chunks.append(chunk)
        return self._response

    async def __aexit__(self, *_args: object) -> None:
        self.exited = True


class DummyAsyncClient:
    def __init__(self, response: object) -> None:
        self._response = response
        self.stream_calls: list[tuple[tuple[object, ...], dict[str, object]]] = []
        self.stream_context: _DummyStreamContext | None = None

    async def request(self, *_args: object, **_kwargs: object) -> httpx.Response:
        return self._response

    def stream(self, *args: object, **kwargs: object) -> _DummyStreamContext:
        self.stream_calls.append((args, kwargs))
        body_stream = kwargs.get("content")
        self.stream_context = _DummyStreamContext(self._response, body_stream)
        return self.stream_context


class _DummyStreamingResponse:
    def __init__(
        self,
        chunks: list[bytes],
        status_code: int = 200,
        headers: list[tuple[str, str]] | None = None,
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
    collected: list[bytes] = []
    async for chunk in generator:
        collected.append(chunk)

    assert collected == [b"first", b"second"]


async def test_proxy_stream_response_streams_chunks_and_closes() -> None:
    response = _DummyStreamingResponse([b"one", b"two"])
    events: list[dict[str, object]] = []

    async def send(event: dict[str, object]) -> None:
        events.append(event)

    await _proxy_stream_response(cast("httpx.Response", response), send)

    status = [event for event in events if event.get("type") == "http.response.start"][0]
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
        headers=[("content-type", "text/plain"), ("set-cookie", "a=1"), ("set-cookie", "b=2"), ("connection", "keep-alive")],
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
    plugin = cast("VitePlugin", SimpleNamespace(proxy_client=cast("httpx.AsyncClient", DummyAsyncClient(response))))

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
        nonlocal chunks
        if chunks:
            return {"type": "http.request", "body": chunks.pop(0), "more_body": bool(chunks)}
        return {"type": "http.request", "body": b"", "more_body": False}

    chunks = [b"up-", b"streaming"]

    async def send(event: dict[str, object]) -> None:
        events.append(event)

    await middleware._proxy_http(scope, receive, send)

    assert events[0]["status"] == 200
    assert events[1]["body"] == b"ok"
    assert plugin.proxy_client.stream_context is not None
    assert plugin.proxy_client.stream_context.request_body_chunks == [b"up-", b"streaming"]


async def test_proxy_http_no_target(tmp_path: Path) -> None:
    hotfile = tmp_path / "hot"
    middleware = ViteProxyMiddleware(app=Mock(), hotfile_path=hotfile, asset_url="/static/")

    scope = {"method": "GET", "raw_path": b"/@vite/client", "query_string": b"", "headers": [], "path": "/@vite/client"}
    events: list[dict[str, object]] = []

    async def receive() -> dict[str, object]:
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(event: dict[str, object]) -> None:
        events.append(event)

    await middleware._proxy_http(scope, receive, send)
    assert events[0]["status"] == 503


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
    socket.scope = {
        "path": "/vite-hmr",
        "query_string": b"",
        "headers": [(b"sec-websocket-protocol", b"json,graphql")],
    }
    socket.accept = AsyncMock()
    socket.close = AsyncMock()
    socket.receive_text = AsyncMock(side_effect=WebSocketDisconnect(code=1000, detail="Client disconnected"))

    class _DummyUpstream:
        async def __aenter__(self) -> "_DummyUpstream":
            return self

        async def __aexit__(self, *_args: object) -> None:
            return None

        def __aiter__(self) -> "_DummyUpstream":
            return self

        async def __anext__(self):
            raise StopAsyncIteration

        async def send(self, *_args: object, **_kwargs: object) -> None:
            return None

        async def close(self) -> None:
            return None

    with patch("litestar_vite.plugin._proxy.websockets.connect") as mock_connect:
        mock_connect.return_value.__aenter__.return_value = _DummyUpstream()
        await handler.fn(socket)

    socket.accept.assert_awaited_once_with(subprotocols=["json", "graphql"])


async def test_ssr_proxy_http_success() -> None:
    response = _DummyStreamingResponse(
        chunks=[b"ok"],
        status_code=200,
        headers=[("content-type", "text/plain"), ("set-cookie", "a=1"), ("set-cookie", "b=2"), ("connection", "keep-alive")],
    )
    plugin = cast("VitePlugin", SimpleNamespace(proxy_client=cast("httpx.AsyncClient", DummyAsyncClient(response))))

    Controller = create_ssr_proxy_controller(target="http://localhost:3000", plugin=plugin, http2=False)
    controller = Controller(owner=MagicMock())

    async def request_stream() -> AsyncGenerator[bytes, None]:
        if False:
            yield b""

    request = SimpleNamespace(
        method="GET",
        url=SimpleNamespace(path="/", query=""),
        headers={"x-test": "ok"},
        stream=request_stream,
    )

    response_obj = await controller.http_proxy.fn(controller, request)
    assert response_obj.status_code == 200
    assert isinstance(response_obj, ASGIStreamingResponse)
    streamed_body = b"".join([chunk async for chunk in response_obj.iterator])  # type: ignore[var-annotated]
    assert streamed_body == b"ok"
    assert (b"connection", b"keep-alive") not in response_obj.encoded_headers
    assert response_obj.encoded_headers.count((b"set-cookie", b"a=1")) == 1
    assert response_obj.encoded_headers.count((b"set-cookie", b"b=2")) == 1


async def test_ssr_proxy_http_no_target() -> None:
    Controller = create_ssr_proxy_controller(target=None, hotfile_path=None, http2=False)
    controller = Controller(owner=MagicMock())

    request = SimpleNamespace(
        method="GET", url=SimpleNamespace(path="/", query=""), headers={}, body=AsyncMock(return_value=b"")
    )

    response_obj = await controller.http_proxy.fn(controller, request)
    assert response_obj.status_code == 503


def test_build_proxy_url_and_http2_support() -> None:
    assert build_proxy_url("http://localhost:3000", "/path", "a=1") == "http://localhost:3000/path?a=1"
    assert build_proxy_url("http://localhost:3000", "/path", "") == "http://localhost:3000/path"
    assert check_http2_support(False) is False
