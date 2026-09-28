"""HTTP proxy regressions exercised against a real local TCP server."""

import gzip
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

import anyio
import httpx2
import pytest
from anyio.abc import ByteStream, SocketAttribute

from litestar_vite.plugin._proxy import _proxy_http_request
from litestar_vite.plugin._utils import create_proxy_client

pytestmark = pytest.mark.anyio


@asynccontextmanager
async def upstream(parts: list[tuple[float, bytes]]) -> AsyncIterator[tuple[str, list[bytes], list[ByteStream]]]:
    """Serve scripted responses while recording requests and accepted connections."""
    requests: list[bytes] = []
    connections: list[ByteStream] = []

    async def serve(stream: ByteStream) -> None:
        connections.append(stream)
        async with stream:
            try:
                while True:
                    request = bytearray()
                    while b"\r\n\r\n" not in request:
                        request.extend(await stream.receive())
                    requests.append(bytes(request))
                    for delay, data in parts:
                        if delay:
                            await anyio.sleep(delay)
                        await stream.send(data)
            except (anyio.EndOfStream, anyio.BrokenResourceError):
                return

    listener = await anyio.create_tcp_listener(local_host="127.0.0.1", local_port=0)
    port = listener.extra(SocketAttribute.local_address)[1]
    async with listener, anyio.create_task_group() as tasks:
        tasks.start_soon(listener.serve, serve)
        try:
            yield f"http://127.0.0.1:{port}/asset.js", requests, connections
        finally:
            tasks.cancel_scope.cancel()


@pytest.mark.parametrize(
    "informational",
    [b"", b"HTTP/1.1 100 Continue\r\n\r\n", b"HTTP/1.1 103 Early Hints\r\nLink: </app.js>; rel=preload\r\n\r\n"],
)
async def test_proxy_preserves_compression_and_consumes_informational_responses(informational: bytes) -> None:
    content = b'console.log("hello")'
    compressed = gzip.compress(content)
    wire = informational + (
        b"HTTP/1.1 200 OK\r\nContent-Encoding: gzip\r\nContent-Length: "
        + str(len(compressed)).encode()
        + b"\r\nSet-Cookie: a=1\r\nSet-Cookie: b=2\r\n\r\n"
        + compressed
    )
    events: list[dict[str, Any]] = []

    async def send(event: dict[str, Any]) -> None:
        events.append(event)

    async with upstream([(0, wire)]) as (url, _, _):
        await _proxy_http_request(url, "GET", [("Accept-Encoding", "gzip")], None, send)

    assert events[0]["status"] == 200
    assert (b"content-encoding", b"gzip") in events[0]["headers"]
    assert [value for key, value in events[0]["headers"] if key == b"set-cookie"] == [b"a=1", b"b=2"]
    assert gzip.decompress(b"".join(event.get("body", b"") for event in events)) == content
    assert events[-1]["more_body"] is False


async def test_proxy_keeps_active_stream_open_past_inactivity_timeout() -> None:
    parts = [(0.0, b"HTTP/1.1 200 OK\r\nTransfer-Encoding: chunked\r\n\r\n")]
    parts.extend((0.08, b"1\r\n" + chunk + b"\r\n") for chunk in (b"a", b"b", b"c", b"d"))
    parts.append((0.0, b"0\r\n\r\n"))
    events: list[dict[str, Any]] = []

    async def send(event: dict[str, Any]) -> None:
        events.append(event)

    async with upstream(parts) as (url, _, _):
        await _proxy_http_request(url, "GET", [], None, send, timeout_duration=0.2)

    assert b"".join(event.get("body", b"") for event in events) == b"abcd"
    assert events[-1]["more_body"] is False


async def test_proxy_reuses_connections_preserves_host_and_ignores_environment_proxy(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("HTTP_PROXY", "http://127.0.0.1:1")
    monkeypatch.setenv("ALL_PROXY", "http://127.0.0.1:1")
    monkeypatch.setenv("NO_PROXY", "")
    wire = b"HTTP/1.1 200 OK\r\nContent-Length: 2\r\n\r\nok"
    events: list[dict[str, Any]] = []

    async def send(event: dict[str, Any]) -> None:
        events.append(event)

    async with upstream([(0, wire)]) as (url, requests, connections), create_proxy_client() as client:
        for _ in range(2):
            await _proxy_http_request(
                url, "GET", [("Host", "localhost:8000"), ("Origin", "http://localhost:8000")], None, send, client=client
            )
        assert len(connections) == 1
        assert len(requests) == 2
        assert all(b"Host: localhost:8000\r\n" in request for request in requests)
        assert all(b"Origin: http://localhost:8000\r\n" in request for request in requests)
        assert all(event["status"] == 200 for event in events if event["type"] == "http.response.start")


async def test_proxy_aborts_stalled_response_without_signalling_success() -> None:
    events: list[dict[str, Any]] = []

    async def send(event: dict[str, Any]) -> None:
        events.append(event)

    parts = [(0.0, b"HTTP/1.1 200 OK\r\nContent-Length: 5\r\n\r\na"), (1.0, b"bcde")]
    async with upstream(parts) as (url, _, _):
        with pytest.raises(httpx2.ReadTimeout):
            await _proxy_http_request(url, "GET", [], None, send, timeout_duration=0.1)
    assert events[0]["status"] == 200
    assert not any(event.get("more_body") is False for event in events)
