"""Unit tests for cross-platform IPC transports and circuit breaker."""

import sys

import anyio
import anyio.abc
import pytest
from litestar.serialization import encode_json

from litestar_vite.ipc import (
    CircuitBreakerOpenError,
    CircuitState,
    IPCError,
    IPCWorkerCrashError,
    SSRCircuitBreaker,
    StdioIPCTransport,
    TCPStreamIPCTransport,
)

pytestmark = pytest.mark.anyio


async def test_stdio_transport_roundtrip_and_stderr_drain() -> None:
    """Verify StdioIPCTransport exchanges newline-delimited JSON requests and drains stderr without deadlocking."""
    worker_script = (
        "import sys, json\n"
        "for line in sys.stdin:\n"
        "    line = line.strip()\n"
        "    if not line:\n"
        "        continue\n"
        "    sys.stderr.write('worker diagnostic log line\\n' * 20)\n"
        "    sys.stderr.flush()\n"
        "    msg = json.loads(line)\n"
        "    resp = {'id': msg.get('id'), 'result': {'echo': msg.get('params'), 'method': msg.get('method')}}\n"
        "    sys.stdout.write(json.dumps(resp) + '\\n')\n"
        "    sys.stdout.flush()\n"
    )
    transport = StdioIPCTransport(command=[sys.executable, "-u", "-c", worker_script])
    await transport.start()
    try:
        assert transport.is_running
        res1 = await transport.send_request({"method": "render", "params": {"component": "A"}})
        res2 = await transport.send_request({"method": "render", "params": {"component": "B"}})
    finally:
        await transport.close()

    assert not transport.is_running
    assert res1["result"]["echo"] == {"component": "A"}
    assert res2["result"]["echo"] == {"component": "B"}


async def test_stdio_transport_worker_crash_raises_error() -> None:
    """Verify StdioIPCTransport raises IPCWorkerCrashError when worker exits mid-request."""
    crash_script = "import sys\nsys.stderr.write('fatal worker crash\\n')\nsys.exit(1)\n"
    transport = StdioIPCTransport(command=[sys.executable, "-u", "-c", crash_script], max_restarts=0)
    await transport.start()
    try:
        with pytest.raises((IPCWorkerCrashError, IPCError)):
            await transport.send_request({"method": "render"}, timeout=2.0)
    finally:
        await transport.close()


async def test_tcp_stream_transport_http_and_chunked_response() -> None:
    """Verify TCPStreamIPCTransport handles HTTP/1.1 chunked responses over raw AnyIO sockets."""
    listener = await anyio.create_tcp_listener(local_host="127.0.0.1", local_port=0)
    port = listener.extra(anyio.abc.SocketAttribute.local_port)

    async def handle_client(stream: anyio.abc.ByteStream) -> None:
        async with stream:
            data = await stream.receive(4096)
            assert b"POST /__litestar_ssr__ HTTP/1.1" in data
            payload_bytes = encode_json({"result": {"head": ["<title>TCP</title>"], "body": "<div>ok</div>"}})
            chunk_header = f"{len(payload_bytes):x}\r\n".encode("ascii")
            http_resp = (
                b"HTTP/1.1 200 OK\r\n"
                b"Content-Type: application/json\r\n"
                b"Transfer-Encoding: chunked\r\n"
                b"Connection: close\r\n\r\n" + chunk_header + payload_bytes + b"\r\n0\r\n\r\n"
            )
            await stream.send(http_resp)

    async with anyio.create_task_group() as tg:
        tg.start_soon(listener.serve, handle_client)
        transport = TCPStreamIPCTransport(host="127.0.0.1", port=port, path="/__litestar_ssr__")
        result = await transport.send_request({"method": "render", "params": {"component": "Home"}}, timeout=3.0)
        tg.cancel_scope.cancel()

    await listener.aclose()
    assert result["result"]["body"] == "<div>ok</div>"
    assert result["result"]["head"] == ["<title>TCP</title>"]


async def test_circuit_breaker_state_transitions() -> None:
    """Verify SSRCircuitBreaker trips after threshold, fast-fails, and recovers after cooldown."""
    cb = SSRCircuitBreaker(failure_threshold=2, reset_timeout=0.05)
    assert cb.state == CircuitState.CLOSED
    assert cb.allow_request()

    cb.record_failure()
    assert cb.state == CircuitState.CLOSED
    cb.record_failure()
    assert cb.state == CircuitState.OPEN
    assert not cb.allow_request()

    with pytest.raises(CircuitBreakerOpenError):
        async with cb:
            pass

    await anyio.sleep(0.06)
    assert cb.allow_request()
    assert cb.state == CircuitState.HALF_OPEN

    cb.record_success()
    assert cb.state == CircuitState.CLOSED
