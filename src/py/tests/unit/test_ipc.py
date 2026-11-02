"""Unit tests for cross-platform IPC transports and circuit breaker."""

import sys

import anyio
import anyio.abc
import anyio.lowlevel
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
        try:
            result = await transport.send_request({"method": "render", "params": {"component": "Home"}}, timeout=3.0)
        finally:
            await transport.close()
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


async def test_stdio_timeout_includes_stalled_request_write() -> None:
    """A worker that stops reading cannot hold the request beyond its timeout."""
    from litestar_vite.ipc import IPCTimeoutError

    transport = StdioIPCTransport(command=[sys.executable, "-u", "-c", "import time; time.sleep(10)"])
    try:
        with anyio.fail_after(1), pytest.raises(IPCTimeoutError):
            await transport.send_request({"method": "render", "params": {"text": "x" * 2_000_000}}, timeout=0.03)
        assert not transport._pending
    finally:
        await transport.close()


async def test_stdio_ignores_non_envelope_stdout_and_keeps_dispatching() -> None:
    """Application diagnostics cannot terminate the response reader."""
    script = (
        "import sys,json\n"
        "for line in sys.stdin:\n"
        "    msg=json.loads(line)\n"
        "    print('123', flush=True)\n"
        "    print('[1,2]', flush=True)\n"
        "    print('diagnostic', flush=True)\n"
        "    print(json.dumps({'id':msg['id'],'result':msg['method']}), flush=True)\n"
    )
    transport = StdioIPCTransport(command=[sys.executable, "-u", "-c", script])
    try:
        for method in ("first", "second"):
            response = await transport.send_request({"method": method}, timeout=1)
            assert response["result"] == method
    finally:
        await transport.close()


async def test_stdio_cancelled_write_cleans_pending_request() -> None:
    """Caller cancellation releases request bookkeeping even during a blocked write."""
    transport = StdioIPCTransport(command=[sys.executable, "-u", "-c", "import time; time.sleep(10)"])
    try:
        with anyio.move_on_after(0.05):
            await transport.send_request({"method": "render", "params": {"text": "x" * 2_000_000}})
        assert not transport._pending
    finally:
        await transport.close()


async def test_stdio_cold_start_rejects_duplicate_ids_without_stealing_response() -> None:
    """Concurrent startup cannot let two callers claim the same response slot."""
    import asyncio

    script = (
        "import sys,json,time\n"
        "for line in sys.stdin:\n"
        "    msg=json.loads(line)\n"
        "    time.sleep(.05)\n"
        "    print(json.dumps({'id':msg['id'],'result':msg['params']}),flush=True)\n"
    )
    transport = StdioIPCTransport(command=[sys.executable, "-u", "-c", script])
    try:
        first: dict[str, object] | BaseException
        second: dict[str, object] | BaseException
        first, second = await asyncio.gather(
            transport.send_request({"id": 7, "method": "render", "params": "first"}, timeout=1),
            transport.send_request({"id": 7, "method": "render", "params": "second"}, timeout=1),
            return_exceptions=True,
        )
        assert isinstance(first, dict) and first["result"] == "first"
        assert isinstance(second, IPCError) and "unique integer" in str(second)
    finally:
        await transport.close()


async def test_stdio_shutdown_finishes_when_caller_is_cancelled() -> None:
    """Cancellation during shutdown cannot orphan the worker or reader tasks."""
    transport = StdioIPCTransport(command=[sys.executable, "-u", "-c", "import time; time.sleep(10)"])
    await transport.start()
    process = transport._process
    with anyio.move_on_after(0.01):
        await transport.close()
    assert process is not None and process.returncode is not None
    assert not transport._reader_tasks


async def test_stdio_queued_write_reports_worker_shutdown() -> None:
    """A queued request cannot write to a closed or replaced worker."""
    import asyncio

    transport = StdioIPCTransport(command=[sys.executable, "-u", "-c", "import sys; sys.stdin.read()"])
    await transport.start()
    async with transport._write_lock:
        request = asyncio.create_task(transport.send_request({"method": "render"}))
        await anyio.lowlevel.checkpoint()
        assert transport._pending
        await transport.close()
    with pytest.raises(IPCWorkerCrashError, match="closed"):
        await request


async def test_stdio_transport_enforces_max_restarts_and_resets_on_close() -> None:
    """Verify StdioIPCTransport enforces max_restarts across repeated crashes and resets after close()."""
    crash_script = "import sys\nsys.exit(1)\n"
    transport = StdioIPCTransport(command=[sys.executable, "-u", "-c", crash_script], max_restarts=1)
    try:
        with pytest.raises(IPCWorkerCrashError):
            await transport.send_request({"method": "render"}, timeout=1.0)
        await anyio.sleep(0.05)

        with pytest.raises(IPCWorkerCrashError):
            await transport.send_request({"method": "render"}, timeout=1.0)
        await anyio.sleep(0.05)

        with pytest.raises(IPCWorkerCrashError, match=r"exceeded maximum automatic restarts \(1\)"):
            await transport.send_request({"method": "render"}, timeout=1.0)

        await transport.close()
        assert transport._restart_count == 0
    finally:
        await transport.close()
