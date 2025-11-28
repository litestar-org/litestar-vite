from typing import Any

import anyio
import httpx
import pytest
from litestar.types import Receive, Scope, Send

from litestar_vite import plugin
from litestar_vite.plugin import ViteProxyMiddleware

pytestmark = pytest.mark.anyio


async def test_proxy_http_forwarding(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ensure HTTP requests to Vite paths are proxied to the upstream server."""

    def responder(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, headers={"x-upstream": "1"}, text="from-upstream")

    transport = httpx.MockTransport(responder)

    class MockAsyncClient(httpx.AsyncClient):
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            kwargs["transport"] = transport
            super().__init__(*args, **kwargs)

    monkeypatch.setattr(plugin.httpx, "AsyncClient", MockAsyncClient)

    sent: list[dict[str, object]] = []

    async def receive() -> dict[str, object]:
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(message: dict[str, object]) -> None:
        sent.append(message)

    scope = {
        "type": "http",
        "path": "/@vite/client",
        "raw_path": b"/@vite/client",
        "query_string": b"",
        "headers": [],
        "method": "GET",
    }

    async def downstream(_scope: Scope, _receive: Receive, _send: Send) -> None:
        return None

    middleware = ViteProxyMiddleware(downstream, target_base_url="http://upstream")
    await middleware(scope, receive, send)  # type: ignore[arg-type]
    statuses = [m for m in sent if m.get("type") == "http.response.start"]
    bodies = [m for m in sent if m.get("type") == "http.response.body"]
    assert statuses and statuses[0]["status"] == 200
    assert bodies and bodies[0]["body"] == b"from-upstream"


class _FakeUpstream:
    def __init__(self) -> None:
        self._send_stream, self._recv_stream = anyio.create_memory_object_stream[object](10)

    async def __aenter__(self) -> "_FakeUpstream":
        return self

    async def __aexit__(self, *_: object) -> None:
        await self.close()

    async def send(self, data: object) -> None:
        # Echo back any data we receive
        await self._send_stream.send(data)

    def __aiter__(self) -> "_FakeUpstream":
        return self

    async def __anext__(self) -> object:
        try:
            return await self._recv_stream.receive()
        except anyio.EndOfStream:
            raise StopAsyncIteration
        except anyio.ClosedResourceError:
            raise StopAsyncIteration

    async def close(self) -> None:
        await self._send_stream.aclose()
        await self._recv_stream.aclose()


async def test_proxy_websocket_forwarding(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ensure websocket traffic is proxied to the upstream Vite server."""

    monkeypatch.setattr(plugin.websockets, "connect", lambda *args, **kwargs: _FakeUpstream())

    async def downstream(_scope: Scope, _receive: Receive, _send: Send) -> None:
        return None

    middleware = ViteProxyMiddleware(downstream, target_base_url="http://127.0.0.1:5173")

    messages: list[dict[str, object]] = []

    async def receive() -> dict[str, object]:
        if not messages:
            messages.append({"type": "websocket.connect"})
            return {"type": "websocket.connect"}
        if len(messages) == 1:
            return {"type": "websocket.receive", "text": "ping", "bytes": None}
        return {"type": "websocket.disconnect", "code": 1000}

    async def send(message: dict[str, object]) -> None:
        messages.append(message)

    scope = {
        "type": "websocket",
        "path": "/@vite/client",
        "raw_path": b"/@vite/client",
        "query_string": b"",
        "headers": [(b"sec-websocket-key", b"test")],
    }

    await middleware(scope, receive, send)  # type: ignore[arg-type]

    assert any(m["type"] == "websocket.accept" for m in messages)
    assert any(m.get("text") == "ping" for m in messages if m["type"] == "websocket.send")
