import os
from pathlib import Path
from typing import Any, cast
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import anyio
import pytest
from litestar.exceptions import WebSocketDisconnect
from litestar.types import Receive, Send
from typing_extensions import Self

from litestar_vite.plugin._proxy import (
    SSRProxyMiddleware,
    ViteProxyMiddleware,
    _extract_proxy_response_headers,
    _stream_chunked_body,
    _stream_request_body,
    build_hmr_target_url,
    build_proxy_url,
    check_http2_support,
    create_hmr_target_getter,
    create_ssr_ws_proxy_handler,
    create_target_url_getter,
    create_vite_hmr_handler,
    extract_forward_headers,
    extract_subprotocols,
    normalize_proxy_prefixes,
)


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


async def test_stream_chunked_body_decodes_http11_chunks() -> None:
    class _FakeStream:
        def __init__(self, chunks: list[bytes]) -> None:
            self._chunks = list(chunks)

        async def receive(self, _max_bytes: int = 65536) -> bytes:
            if self._chunks:
                return self._chunks.pop(0)
            raise anyio.EndOfStream

    raw = b"3\r\none\r\n3\r\ntwo\r\n0\r\n\r\n"
    stream = _FakeStream([raw[4:]])
    events: list[dict[str, object]] = []

    async def send(event: dict[str, object]) -> None:
        events.append(event)

    await _stream_chunked_body(cast("Any", stream), bytearray(raw[:4]), send)
    body_bytes = b"".join(cast("bytes", e["body"]) for e in events if e.get("type") == "http.response.body")
    assert body_bytes == b"onetwo"


pytestmark = pytest.mark.anyio


def test_extract_proxy_response_headers_filters_headers() -> None:
    raw_headers = [
        (b"content-type", b"text/plain"),
        (b"set-cookie", b"a=1"),
        (b"set-cookie", b"b=2"),
        (b"connection", b"keep-alive"),
    ]
    headers = _extract_proxy_response_headers(raw_headers)
    assert (b"content-type", b"text/plain") in headers
    assert all(key != b"connection" for key, _ in headers)
    assert headers.count((b"set-cookie", b"a=1")) == 1
    assert headers.count((b"set-cookie", b"b=2")) == 1


def test_build_hmr_target_url_includes_query(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Hotfile-only fallback: bridge cleared so legacy hotfile semantics apply."""
    from litestar_vite.utils import read_bridge_config

    read_bridge_config.cache_clear()
    monkeypatch.setenv("LITESTAR_VITE_CONFIG_PATH", str(tmp_path / "no-bridge.json"))
    hotfile = tmp_path / "hot"
    hotfile.write_text("http://localhost:5173")
    scope = {"path": "/vite-hmr", "query_string": b"token=1"}

    target = build_hmr_target_url(hotfile, scope, "/vite-hmr", "/static/")
    assert target == "ws://localhost:5173/vite-hmr?token=1"
    read_bridge_config.cache_clear()


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


def test_collect_connection_tokens_returns_shared_empty_sentinel_when_absent() -> None:
    """No Connection header returns the shared sentinel instead of allocating a set."""
    from litestar_vite.plugin._proxy import _NO_CONNECTION_TOKENS, _collect_connection_tokens

    result = _collect_connection_tokens([(b"host", b"example.com"), (b"x-test", b"value")])

    assert result is _NO_CONNECTION_TOKENS


def test_extract_request_headers_avoids_set_copy_without_connection_header(monkeypatch: pytest.MonkeyPatch) -> None:
    """No Connection header uses the immutable skip set directly."""
    from litestar_vite.plugin._proxy import _extract_request_headers

    set_calls = 0

    class _CountingSet(set[object]):
        def __new__(cls, *args: object, **kwargs: object) -> Self:
            nonlocal set_calls
            set_calls += 1
            return super().__new__(cls)

    monkeypatch.setattr("builtins.set", _CountingSet)

    headers = [(b"X-Test", b"value"), (b"Host", b"example.com")]
    result = _extract_request_headers(headers)

    assert result == [("X-Test", "value"), ("Host", "example.com")]
    assert set_calls == 0, f"expected zero set() allocations with no Connection header, got {set_calls}"


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


def test_target_url_getter_caches(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    hotfile = tmp_path / "hot"
    hotfile.write_text("http://localhost:5173")
    cached: list[str | None] = [None]
    fake_time = [1000.0]
    monkeypatch.setattr("litestar_vite.plugin._proxy.time.monotonic", lambda: fake_time[0])
    getter = create_target_url_getter(None, hotfile, cached)

    assert getter() == "http://localhost:5173"
    assert getter() == "http://localhost:5173"

    hotfile.write_text("http://changed:1234")
    current_mtime = hotfile.stat().st_mtime_ns
    os.utime(hotfile, ns=(current_mtime + 1_000_000, current_mtime + 1_000_000))

    fake_time[0] += 1.0
    assert getter() == "http://changed:1234"


def test_target_url_getter_recovers_after_initial_missing_hotfile(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    hotfile = tmp_path / "hot"
    cached: list[str | None] = [None]
    fake_time = [1000.0]
    monkeypatch.setattr("litestar_vite.plugin._proxy.time.monotonic", lambda: fake_time[0])
    getter = create_target_url_getter(None, hotfile, cached)

    assert getter() is None

    hotfile.write_text("http://localhost:5173")

    fake_time[0] += 1.0
    assert getter() == "http://localhost:5173"


def test_target_url_getter_throttles_stat_within_ttl_window(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    hotfile = tmp_path / "hot"
    hotfile.write_text("http://localhost:5173")
    cached: list[str | None] = [None]
    fake_time = [1000.0]
    monkeypatch.setattr("litestar_vite.plugin._proxy.time.monotonic", lambda: fake_time[0])
    stat_calls = 0
    real_stat = Path.stat

    def counting_stat(self: Path, *, follow_symlinks: bool = True) -> os.stat_result:
        nonlocal stat_calls
        stat_calls += 1
        return real_stat(self, follow_symlinks=follow_symlinks)

    monkeypatch.setattr(Path, "stat", counting_stat)
    getter = create_target_url_getter(None, hotfile, cached)

    for _ in range(5):
        assert getter() == "http://localhost:5173"

    assert stat_calls == 1


def test_target_url_getter_caches_negative_result_without_reread(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    hotfile = tmp_path / "hot"
    hotfile.write_text("http://localhost:5173")
    cached: list[str | None] = [None]
    fake_time = [1000.0]
    monkeypatch.setattr("litestar_vite.plugin._proxy.time.monotonic", lambda: fake_time[0])
    read_calls = 0

    def failing_read(_path: Path) -> str:
        nonlocal read_calls
        read_calls += 1
        raise OSError("simulated malformed hotfile read")

    monkeypatch.setattr("litestar_vite.plugin._proxy.read_hotfile_url", failing_read)
    getter = create_target_url_getter(None, hotfile, cached)

    assert getter() is None
    fake_time[0] += 1.0
    assert getter() is None
    assert read_calls == 1


def test_hmr_target_getter_hoists_hmr_path_once(tmp_path: Path) -> None:
    """The '<hotfile>.hmr' Path must be constructed once per getter, not once per call."""
    hotfile = tmp_path / "hot"
    hotfile.write_text("http://localhost:5173")
    (tmp_path / "hot.hmr").write_text("http://127.0.0.1:24678")

    with patch("litestar_vite.plugin._proxy.Path", wraps=Path) as path_spy:
        getter = create_hmr_target_getter(hotfile, [None])
        for _ in range(5):
            assert getter() == "http://127.0.0.1:24678"

    assert path_spy.call_count == 1, (
        f"expected Path(...) to be constructed once for the .hmr sibling, got {path_spy.call_count}"
    )


def test_hmr_target_getter_ttls_negative_result(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """When no '.hmr' sibling exists, repeated calls within the TTL window must not re-stat either candidate."""
    hotfile = tmp_path / "hot"
    hotfile.write_text("http://localhost:5173")
    fake_time = [1000.0]
    monkeypatch.setattr("litestar_vite.plugin._proxy.time.monotonic", lambda: fake_time[0])

    stat_calls = 0
    real_stat = Path.stat

    def counting_stat(self: Path, *, follow_symlinks: bool = True) -> os.stat_result:
        nonlocal stat_calls
        stat_calls += 1
        return real_stat(self, follow_symlinks=follow_symlinks)

    monkeypatch.setattr(Path, "stat", counting_stat)

    getter = create_hmr_target_getter(hotfile, [None])
    for _ in range(5):
        assert getter() == "http://localhost:5173"

    assert stat_calls == 2, f"expected exactly 2 stat() calls across 5 getter() calls, got {stat_calls}"


def test_hmr_target_getter_caches(tmp_path: Path) -> None:
    hotfile = tmp_path / "hot"
    hotfile.write_text("http://localhost:5173")
    (tmp_path / "hot.hmr").write_text("http://127.0.0.1:24678")

    getter = create_hmr_target_getter(hotfile, [None])
    assert getter() == "http://127.0.0.1:24678"


class _FakeTCPStream:
    def __init__(self, response_bytes: list[bytes]) -> None:
        self.sent_chunks: list[bytes] = []
        self._response_bytes = list(response_bytes)

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(self, *_args: object) -> None:
        return None

    def __aiter__(self) -> Self:
        return self

    async def __anext__(self) -> bytes:
        if self._response_bytes:
            return self._response_bytes.pop(0)
        raise StopAsyncIteration

    async def send(self, data: bytes) -> None:
        self.sent_chunks.append(data)

    async def receive(self, _max_bytes: int = 65536) -> bytes:
        if self._response_bytes:
            return self._response_bytes.pop(0)
        raise anyio.EndOfStream


async def test_proxy_http_streams_post_body_via_anyio(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    hotfile = tmp_path / "hot"
    hotfile.write_text("http://localhost:5173")

    fake_stream = _FakeTCPStream([b"HTTP/1.1 200 OK\r\nContent-Type: text/plain\r\n\r\nok"])
    monkeypatch.setattr("anyio.connect_tcp", AsyncMock(return_value=fake_stream))

    middleware = ViteProxyMiddleware(app=Mock(), hotfile_path=hotfile, asset_url="/static/")

    scope: dict[str, Any] = {
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

    await middleware._proxy_http(scope, cast("Receive", receive), cast("Send", send))

    assert events[0]["status"] == 200
    assert events[1]["body"] == b"ok"
    sent_payload = b"".join(fake_stream.sent_chunks)
    assert b"3\r\nup-\r\n9\r\nstreaming\r\n0\r\n\r\n" in sent_payload


async def test_proxy_http_no_target(tmp_path: Path) -> None:
    hotfile = tmp_path / "hot"

    scope: dict[str, Any] = {
        "method": "GET",
        "raw_path": b"/@vite/client",
        "query_string": b"",
        "headers": [],
        "path": "/@vite/client",
    }
    events: list[dict[str, object]] = []

    async def receive() -> dict[str, object]:
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(event: dict[str, object]) -> None:
        events.append(event)

    async def downstream(_scope: object, _receive: object, _send: object) -> None:
        await send({"type": "http.response.start", "status": 404, "headers": []})
        await send({"type": "http.response.body", "body": b"downstream", "more_body": False})

    middleware = ViteProxyMiddleware(app=downstream, hotfile_path=hotfile, asset_url="/static/")

    await middleware._proxy_http(scope, cast("Receive", receive), cast("Send", send))
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


async def test_ssr_proxy_middleware_http_success(monkeypatch: pytest.MonkeyPatch) -> None:
    """SSRProxyMiddleware streams upstream response and filters hop-by-hop headers."""
    raw_resp = (
        b"HTTP/1.1 200 OK\r\n"
        b"Content-Type: text/plain\r\n"
        b"Set-Cookie: a=1\r\n"
        b"Set-Cookie: b=2\r\n"
        b"Connection: keep-alive\r\n\r\n"
        b"ok"
    )
    fake_stream = _FakeTCPStream([raw_resp])
    monkeypatch.setattr("anyio.connect_tcp", AsyncMock(return_value=fake_stream))

    inner_app = AsyncMock()
    middleware = SSRProxyMiddleware(app=inner_app, target="http://localhost:3000", http2=False)

    send_events: list[dict[str, object]] = []

    async def receive() -> dict[str, object]:
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(event: dict[str, object]) -> None:
        send_events.append(event)

    scope: dict[str, Any] = {"method": "GET", "raw_path": b"/", "query_string": b"", "headers": [(b"x-test", b"ok")]}
    await middleware._proxy_http(scope, cast("Receive", receive), cast("Send", send), "http://localhost:3000")

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


@pytest.mark.parametrize("method", ["GET", "HEAD", "OPTIONS"])
async def test_proxy_http_bodyless_methods_do_not_send_body(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, method: str
) -> None:
    """GET, HEAD, and OPTIONS requests must not send a request body over the TCP stream."""
    hotfile = tmp_path / "hot"
    hotfile.write_text("http://localhost:5173")

    fake_stream = _FakeTCPStream([b"HTTP/1.1 200 OK\r\nContent-Type: text/plain\r\n\r\nok"])
    monkeypatch.setattr("anyio.connect_tcp", AsyncMock(return_value=fake_stream))

    middleware = ViteProxyMiddleware(app=Mock(), hotfile_path=hotfile, asset_url="/static/")

    scope: dict[str, Any] = {
        "method": method,
        "raw_path": b"/@vite/client",
        "query_string": b"",
        "headers": [(b"host", b"example.com")],
        "path": "/@vite/client",
    }
    receive_called = False

    async def receive() -> dict[str, object]:
        nonlocal receive_called
        receive_called = True
        return {"type": "http.request", "body": b"unexpected", "more_body": False}

    events: list[dict[str, object]] = []

    async def send(event: dict[str, object]) -> None:
        events.append(event)

    await middleware._proxy_http(scope, cast("Receive", receive), cast("Send", send))

    assert events[0]["status"] == 200
    assert receive_called is False
    assert len(fake_stream.sent_chunks) == 1


def test_create_ssr_ws_proxy_handler_defaults_to_catch_all_paths() -> None:
    """The WS HMR factory registers both ``/`` and the catch-all so no HMR path 404s."""
    handler = create_ssr_ws_proxy_handler(target="http://localhost:3000")

    assert handler.paths == {"/", "/{path:path}"}
    assert handler.opt.get("exclude_from_auth") is True


def test_create_ssr_ws_proxy_handler_honors_explicit_paths() -> None:
    """Callers can narrow the WS paths when the framework uses a single HMR endpoint."""
    handler = create_ssr_ws_proxy_handler(target="http://localhost:3000", paths=["/_hmr"])

    assert handler.paths == {"/_hmr"}


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


def test_ssr_proxy_should_proxy_get_root_when_only_websocket_routes_claim_it() -> None:
    """GET / must still proxy when only a WebSocket handler is registered at '/'.

    Regression for the 405 fall-through: a framework HMR WebSocket at '/' used to
    poison the HTTP prefix list, making SSRProxyMiddleware skip the proxy and hand
    GET / to a WebSocket handler that has no HTTP method.
    """
    from typing import Any

    from litestar import Controller, Litestar, WebSocket, websocket

    from litestar_vite.plugin._proxy import SSRProxyMiddleware

    class _WSOnly(Controller):
        @websocket(path=["/", "/{path:path}"], name="ws_only")
        async def handler(self, socket: WebSocket[Any, Any, Any]) -> None:  # pragma: no cover
            await socket.accept()

    app = Litestar(route_handlers=[_WSOnly])
    middleware = SSRProxyMiddleware.__new__(SSRProxyMiddleware)
    scope = {"type": "http", "method": "GET", "path": "/", "app": app}

    assert middleware._should_proxy(cast("Any", scope)) is True  # pyright: ignore[reportPrivateUsage]


# ===== Bridge-config preference for HMR target (litestar-vite-c1t) =====


def _write_bridge_for_hmr(tmp_path: Path, payload: object) -> Path:
    import json

    bridge = tmp_path / ".litestar.json"
    bridge.write_text(json.dumps(payload))
    return bridge


def test_build_hmr_target_url_preserves_resolved_hotfile_url(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """The Vite HMR handler preserves the resolved hotfile target.

    The resolved hotfile URL already carries HTTPS, IPv6 brackets, wildcard
    normalization, and any HMR clientPort override. Rebuilding from bridge
    ``host``+``port`` loses those details.
    """
    from litestar_vite.utils import read_bridge_config

    read_bridge_config.cache_clear()
    hotfile = tmp_path / "hot"
    hotfile.write_text("https://[::1]:32001")
    bridge = _write_bridge_for_hmr(
        tmp_path, {"appUrl": "https://litestar-bridge:8443", "host": "::", "port": 5173, "proxyMode": "vite"}
    )
    monkeypatch.setenv("LITESTAR_VITE_CONFIG_PATH", str(bridge))
    scope = {"path": "/vite-hmr", "query_string": b"token=1"}

    target = build_hmr_target_url(hotfile, scope, "/vite-hmr", "/static/")

    assert target == "wss://[::1]:32001/vite-hmr?token=1"
    read_bridge_config.cache_clear()


def test_build_hmr_target_url_falls_back_to_hotfile_when_bridge_missing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from litestar_vite.utils import read_bridge_config

    read_bridge_config.cache_clear()
    hotfile = tmp_path / "hot"
    hotfile.write_text("http://localhost:5173")
    monkeypatch.setenv("LITESTAR_VITE_CONFIG_PATH", str(tmp_path / "missing.json"))
    scope = {"path": "/vite-hmr", "query_string": b""}

    target = build_hmr_target_url(hotfile, scope, "/vite-hmr", "/static/")

    assert target == "ws://localhost:5173/vite-hmr"
    read_bridge_config.cache_clear()


def test_create_hmr_target_getter_sibling_overrides_bridge(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """``<hotfile>.hmr`` sibling continues to win for the HMR clientPort override.

    The sibling carries Vite's HMR-specific target (often a different port than
    the dev server's HTTP port), so it must take precedence even when bridge
    config is present.
    """
    from litestar_vite.utils import read_bridge_config

    read_bridge_config.cache_clear()
    hotfile = tmp_path / "hot"
    hotfile.write_text("http://localhost:5173")
    (tmp_path / "hot.hmr").write_text("http://127.0.0.1:24678")
    bridge = _write_bridge_for_hmr(tmp_path, {"appUrl": "http://bridge", "host": "127.0.0.1", "port": 5173})
    monkeypatch.setenv("LITESTAR_VITE_CONFIG_PATH", str(bridge))

    getter = create_hmr_target_getter(hotfile, [None])

    assert getter() == "http://127.0.0.1:24678"
    read_bridge_config.cache_clear()


def test_create_hmr_target_getter_uses_hotfile_when_sibling_missing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Framework HMR fallback must keep the hotfile target outside Vite proxy mode."""
    from litestar_vite.utils import read_bridge_config

    read_bridge_config.cache_clear()
    hotfile = tmp_path / "hot"
    hotfile.write_text("https://framework-dev-server:4321")
    bridge = _write_bridge_for_hmr(
        tmp_path, {"appUrl": "http://litestar-bridge:8000", "host": "127.0.0.1", "port": 5173, "proxyMode": "proxy"}
    )
    monkeypatch.setenv("LITESTAR_VITE_CONFIG_PATH", str(bridge))

    getter = create_hmr_target_getter(hotfile, [None])

    assert getter() == "https://framework-dev-server:4321"
    read_bridge_config.cache_clear()
