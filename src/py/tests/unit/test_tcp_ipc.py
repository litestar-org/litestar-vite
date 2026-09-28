"""Development SSR HTTP transport framing and lifecycle regressions."""

import gzip
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import anyio
import httpx2
import pytest
from anyio.abc import ByteStream, SocketAttribute

from litestar_vite.ipc import IPCError, IPCTimeoutError, TCPStreamIPCTransport

pytestmark = pytest.mark.anyio


@asynccontextmanager
async def rpc_server(parts: list[tuple[float, bytes]]) -> AsyncIterator[tuple[int, list[ByteStream]]]:
    connections: list[ByteStream] = []

    async def serve(stream: ByteStream) -> None:
        connections.append(stream)
        async with stream:
            try:
                while True:
                    request = bytearray()
                    while b"\r\n\r\n" not in request:
                        request.extend(await stream.receive())
                    headers, body = bytes(request).split(b"\r\n\r\n", 1)
                    length = next(
                        int(line.split(b":", 1)[1])
                        for line in headers.split(b"\r\n")
                        if line.lower().startswith(b"content-length:")
                    )
                    while len(body) < length:
                        body += await stream.receive()
                    for delay, chunk in parts:
                        if delay:
                            await anyio.sleep(delay)
                        await stream.send(chunk)
            except (anyio.EndOfStream, anyio.BrokenResourceError):
                return

    listener = await anyio.create_tcp_listener(local_host="127.0.0.1", local_port=0)
    async with listener, anyio.create_task_group() as tasks:
        tasks.start_soon(listener.serve, serve)
        try:
            yield listener.extra(SocketAttribute.local_port), connections
        finally:
            tasks.cancel_scope.cancel()


@pytest.mark.parametrize("chunked", [False, True])
async def test_tcp_ipc_handles_early_hints_compression_and_keepalive(
    chunked: bool, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("HTTP_PROXY", "http://127.0.0.1:1")
    monkeypatch.setenv("ALL_PROXY", "http://127.0.0.1:1")
    monkeypatch.setenv("NO_PROXY", "")
    compressed = gzip.compress(b'{"result":{"body":"<div>ok</div>"}}')
    framing = (
        b"Transfer-Encoding: chunked\r\n" if chunked else b"Content-Length: " + str(len(compressed)).encode() + b"\r\n"
    )
    body = f"{len(compressed):x}\r\n".encode() + compressed + b"\r\n0\r\n\r\n" if chunked else compressed
    wire = (
        b"HTTP/1.1 103 Early Hints\r\nLink: </app.js>; rel=preload\r\n\r\n"
        b"HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nContent-Encoding: gzip\r\n" + framing + b"\r\n" + body
    )
    async with rpc_server([(0.0, wire)]) as (port, connections):
        transport = TCPStreamIPCTransport(port=port)
        try:
            for _ in range(2):
                result = await transport.send_request({"method": "render"}, timeout=1)
                assert result == {"result": {"body": "<div>ok</div>"}}
            assert len(connections) == 1
        finally:
            await transport.close()
        assert transport._client is None


async def test_tcp_ipc_total_deadline_includes_active_response_stream() -> None:
    parts = [(0.0, b"HTTP/1.1 200 OK\r\nTransfer-Encoding: chunked\r\n\r\n")]
    parts.extend((0.08, b"1\r\n" + chunk + b"\r\n") for chunk in (b"{", b'"', b"r", b"e"))
    async with rpc_server(parts) as (port, _):
        transport = TCPStreamIPCTransport(port=port)
        try:
            with pytest.raises(IPCTimeoutError), anyio.fail_after(0.7):
                await transport.send_request({"method": "render"}, timeout=0.2)
        finally:
            await transport.close()


@pytest.mark.parametrize("body", [b"not JSON", b"[]", b"123", b'{"unexpected":true}'])
async def test_tcp_ipc_rejects_malformed_response_envelopes(body: bytes) -> None:
    wire = b"HTTP/1.1 200 OK\r\nContent-Length: " + str(len(body)).encode() + b"\r\n\r\n" + body
    async with rpc_server([(0.0, wire)]) as (port, _):
        transport = TCPStreamIPCTransport(port=port)
        try:
            with pytest.raises(IPCError):
                await transport.send_request({"method": "render"})
        finally:
            await transport.close()


@pytest.mark.parametrize("status", [200, 500])
async def test_tcp_ipc_preserves_worker_error_envelope_and_rejects_http_errors(status: int) -> None:
    body = b'{"error":"render failed"}'
    wire = f"HTTP/1.1 {status} Result\r\nContent-Length: {len(body)}\r\n\r\n".encode() + body
    async with rpc_server([(0.0, wire)]) as (port, _):
        transport = TCPStreamIPCTransport(port=port)
        try:
            if status == 200:
                assert await transport.send_request({"method": "render"}) == {"error": "render failed"}
            else:
                with pytest.raises(IPCError, match="HTTP 500"):
                    await transport.send_request({"method": "render"})
        finally:
            await transport.close()


async def test_tcp_ipc_uses_https_and_closes_client(monkeypatch: pytest.MonkeyPatch) -> None:
    requests: list[httpx2.Request] = []

    def handle(request: httpx2.Request) -> httpx2.Response:
        requests.append(request)
        return httpx2.Response(200, json={"result": {}})

    client = httpx2.AsyncClient(transport=httpx2.MockTransport(handle))
    monkeypatch.setattr(httpx2, "AsyncClient", lambda **_kwargs: client)
    transport = TCPStreamIPCTransport(host="::1", port=5173, scheme="https", path="rpc")
    try:
        await transport.send_request({"method": "render"})
    finally:
        await transport.close()
    assert str(requests[0].url) == "https://[::1]:5173/rpc"
    assert transport.scheme == "https"
    assert client.is_closed
