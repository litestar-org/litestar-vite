from typing import Any
from unittest.mock import AsyncMock

import pytest
from litestar.exceptions import WebSocketDisconnect
from typing_extensions import Self

from litestar_vite.plugin._proxy import _run_websocket_proxy

pytestmark = pytest.mark.anyio


class _FakeUpstream:
    def __init__(self, incoming: list[str | bytes] | None = None) -> None:
        self._incoming = list(incoming or [])
        self.sent: list[str | bytes] = []
        self.closed = False

    def __aiter__(self) -> Self:
        return self

    async def __anext__(self) -> str | bytes:
        if self._incoming:
            return self._incoming.pop(0)
        raise StopAsyncIteration

    async def send(self, data: str | bytes) -> None:
        self.sent.append(data)

    async def close(self) -> None:
        self.closed = True


class _FakeClientSocket:
    def __init__(self, events: list[dict[str, Any]]) -> None:
        self._events = list(events)
        self.sent_text: list[str] = []
        self.sent_bytes: list[bytes] = []
        self.closed = False

    async def receive(self) -> dict[str, Any]:
        if self._events:
            return self._events.pop(0)
        return {"type": "websocket.disconnect", "code": 1000}

    async def send_text(self, data: str) -> None:
        self.sent_text.append(data)

    async def send_bytes(self, data: bytes) -> None:
        self.sent_bytes.append(data)

    async def close(self) -> None:
        self.closed = True


async def test_run_websocket_proxy_forwards_text_frames_to_upstream() -> None:
    """Verify text WebSocket frames from the client are forwarded to upstream as str."""
    socket = _FakeClientSocket(
        [
            {"type": "websocket.receive", "text": "ping"},
            {"type": "websocket.disconnect", "code": 1000},
        ]
    )
    upstream = _FakeUpstream()

    await _run_websocket_proxy(socket, upstream)

    assert upstream.sent == ["ping"]
    assert upstream.closed is True
    assert socket.closed is True


async def test_run_websocket_proxy_forwards_binary_frames_to_upstream() -> None:
    """Verify binary WebSocket frames from the client are forwarded to upstream as bytes."""
    payload = b"\x00\x01\x02\xff"
    socket = _FakeClientSocket(
        [
            {"type": "websocket.receive", "bytes": payload},
            {"type": "websocket.disconnect", "code": 1000},
        ]
    )
    upstream = _FakeUpstream()

    await _run_websocket_proxy(socket, upstream)

    assert upstream.sent == [payload]
    assert isinstance(upstream.sent[0], bytes)
    assert upstream.closed is True
    assert socket.closed is True


async def test_run_websocket_proxy_forwards_mixed_text_and_binary_bidirectional() -> None:
    """Verify mixed text and binary frames are forwarded in both directions."""
    socket = _FakeClientSocket(
        [
            {"type": "websocket.receive", "text": "hello"},
            {"type": "websocket.receive", "bytes": b"\xde\xad\xbe\xef"},
            {"type": "websocket.receive", "text": "world"},
            {"type": "websocket.disconnect", "code": 1000},
        ]
    )
    upstream = _FakeUpstream(incoming=["server-text", b"\xca\xfe"])

    await _run_websocket_proxy(socket, upstream)

    assert upstream.sent == ["hello", b"\xde\xad\xbe\xef", "world"]
    assert socket.sent_text == ["server-text"]
    assert socket.sent_bytes == [b"\xca\xfe"]
    assert upstream.closed is True
    assert socket.closed is True


async def test_run_websocket_proxy_exits_cleanly_on_websocket_disconnect_exception() -> None:
    """Verify WebSocketDisconnect raised by socket.receive terminates the proxy loop cleanly."""
    socket = _FakeClientSocket([])
    setattr(socket, "receive", AsyncMock(side_effect=WebSocketDisconnect(code=1000, detail="Client disconnected")))
    upstream = _FakeUpstream()

    await _run_websocket_proxy(socket, upstream)

    assert upstream.sent == []
    assert upstream.closed is True
    assert socket.closed is True
