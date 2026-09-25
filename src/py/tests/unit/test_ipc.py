"""Unit tests for cross-platform IPC transports, manager, and circuit breaker."""

import sys
from pathlib import Path
from typing import Any

import anyio
import anyio.abc
import pytest
from litestar.serialization import decode_json, encode_json

from litestar_vite.ipc import (
    BaseIPCTransport,
    CircuitBreakerOpenError,
    CircuitState,
    IPCError,
    IPCTransportManager,
    IPCWorkerCrashError,
    SSRCircuitBreaker,
    StdioIPCTransport,
    TCPStreamIPCTransport,
    UnixSocketIPCTransport,
    UnsupportedPlatformError,
    prepare_socket_path,
    resolve_socket_path,
)

pytestmark = pytest.mark.anyio


def test_create_transport_respects_explicit_modes(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify IPCTransportManager.create_transport honors explicit mode even when url is present."""
    stdio_transport = IPCTransportManager.create_transport(
        mode="stdio",
        command=["node", "ssr.js", "--stdio"],
        url="http://127.0.0.1:13714/render",
    )
    assert isinstance(stdio_transport, StdioIPCTransport)

    tcp_transport = IPCTransportManager.create_transport(
        mode="tcp",
        command=["node", "ssr.js"],
        url="http://127.0.0.1:13714/render",
    )
    assert isinstance(tcp_transport, TCPStreamIPCTransport)
    assert tcp_transport.host == "127.0.0.1"
    assert tcp_transport.port == 13714
    assert tcp_transport.path == "/render"

    monkeypatch.setattr("litestar_vite.ipc._manager.os.name", "posix")
    monkeypatch.setattr("litestar_vite.ipc._uds.os.name", "posix")
    sock_file = tmp_path / "ssr.sock"
    uds_transport = IPCTransportManager.create_transport(
        mode="uds",
        socket_path=sock_file,
        url="http://127.0.0.1:13714/render",
    )
    assert isinstance(uds_transport, UnixSocketIPCTransport)


def test_uds_windows_guard_raises_unsupported_platform(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify UnixSocketIPCTransport and create_transport reject UDS on Windows."""
    monkeypatch.setattr("litestar_vite.ipc._uds.os.name", "nt")
    monkeypatch.setattr("litestar_vite.ipc._manager.os.name", "nt")

    with pytest.raises(UnsupportedPlatformError, match="Windows"):
        UnixSocketIPCTransport("/tmp/test.sock")

    with pytest.raises(UnsupportedPlatformError, match="Windows"):
        IPCTransportManager.create_transport(mode="uds", socket_path="/tmp/test.sock")


def test_resolve_and_prepare_socket_path_truncates_long_and_macos_paths(tmp_path: Path) -> None:
    """Verify macOS var/folders and >90 char paths are shortened to /tmp/lv-<hash>.sock."""
    short_path = "/tmp/my-ssr.sock"
    assert resolve_socket_path(short_path) == short_path

    macos_tmpdir_path = "/var/folders/zz/zyxvpxvq6csfxvn_n0000000000000/T/litestar-vite-ssr-worker.sock"
    resolved_macos = resolve_socket_path(macos_tmpdir_path)
    assert len(resolved_macos) < 40
    assert resolved_macos.endswith(".sock")
    assert "lv-" in resolved_macos

    long_path = "/" + ("a" * 100) + "/ssr.sock"
    resolved_long = resolve_socket_path(long_path)
    assert len(resolved_long) < 40

    stale_sock = tmp_path / "stale.sock"
    stale_sock.write_text("stale")
    assert stale_sock.exists()
    prepared = prepare_socket_path(stale_sock)
    assert not prepared.exists()


async def test_stdio_transport_roundtrip_and_stderr_drain() -> None:
    """Verify StdioIPCTransport exchanges NDJSON requests and drains stderr without deadlocking."""
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
        res1, res2 = await anyio.gather(
            transport.send_request({"method": "render", "params": {"component": "A"}}),
            transport.send_request({"method": "render", "params": {"component": "B"}}),
        )
    except AttributeError:
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
            assert b"POST /render HTTP/1.1" in data
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
        transport = TCPStreamIPCTransport(host="127.0.0.1", port=port, path="/render")
        result = await transport.send_request({"method": "render", "params": {"component": "Home"}}, timeout=3.0)
        tg.cancel_scope.cancel()

    await listener.aclose()
    assert result["result"]["body"] == "<div>ok</div>"
    assert result["result"]["head"] == ["<title>TCP</title>"]


@pytest.mark.skipif(sys.platform == "win32", reason="AF_UNIX not supported on Windows")
async def test_uds_transport_roundtrip(tmp_path: Path) -> None:
    """Verify UnixSocketIPCTransport communicates over a local AF_UNIX socket."""
    raw_sock = tmp_path / "uds-test.sock"
    sock_path = prepare_socket_path(raw_sock)
    listener = await anyio.create_unix_listener(sock_path)

    async def handle_client(stream: anyio.abc.ByteStream) -> None:
        async with stream:
            data = await stream.receive(4096)
            msg = decode_json(data.strip())
            reply = encode_json({"id": msg.get("id", 1), "result": {"html": "<span>UDS</span>"}}) + b"\n"
            await stream.send(reply)

    async with anyio.create_task_group() as tg:
        tg.start_soon(listener.serve, handle_client)
        transport = UnixSocketIPCTransport(socket_path=sock_path)
        await transport.start()
        res = await transport.send_request({"method": "render_fragment", "params": {"component": "Badge.vue"}})
        await transport.close()
        tg.cancel_scope.cancel()

    await listener.aclose()
    sock_path.unlink(missing_ok=True)
    assert res["result"]["html"] == "<span>UDS</span>"


async def test_circuit_breaker_state_transitions_and_manager_fallback() -> None:
    """Verify SSRCircuitBreaker trips after threshold, fast-fails, recovers after cooldown, and triggers fallback."""
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

    class FailingTransport(BaseIPCTransport):
        @property
        def is_running(self) -> bool:
            return True

        async def start(self) -> None:
            return None

        async def close(self) -> None:
            return None

        async def send_request(self, payload: dict[str, Any], timeout: float = 10.0) -> dict[str, Any]:
            msg = "primary transport down"
            raise IPCError(msg)

    class FallbackTransport(BaseIPCTransport):
        @property
        def is_running(self) -> bool:
            return True

        async def start(self) -> None:
            return None

        async def close(self) -> None:
            return None

        async def send_request(self, payload: dict[str, Any], timeout: float = 10.0) -> dict[str, Any]:
            return {"result": {"body": "fallback-ok", "echo": payload}}

    manager = IPCTransportManager(
        transport=FailingTransport(),
        circuit_breaker=SSRCircuitBreaker(failure_threshold=1, reset_timeout=10.0),
        fallback_transport=FallbackTransport(),
    )
    await manager.start()
    first = await manager.send_request({"method": "render"})
    assert first["result"]["body"] == "fallback-ok"
    assert manager.circuit_breaker is not None
    assert manager.circuit_breaker.state == CircuitState.OPEN

    second = await manager.send_request({"method": "render"})
    assert second["result"]["body"] == "fallback-ok"
    await manager.close()
