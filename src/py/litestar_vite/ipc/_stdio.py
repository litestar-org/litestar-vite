"""Asynchronous stdio subprocess transport communicating via line-delimited JSON (NDJSON)."""

import collections
import contextlib
import itertools
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any

import anyio
import anyio.abc
from litestar.serialization import decode_json, encode_json

from litestar_vite.ipc._base import BaseIPCTransport, IPCError, IPCTimeoutError, IPCWorkerCrashError

__all__ = ("StdioIPCTransport",)


class StdioIPCTransport(BaseIPCTransport):
    """Asynchronous process transport communicating across stdin and stdout using NDJSON."""

    __slots__ = (
        "_command",
        "_cwd",
        "_env",
        "_id_counter",
        "_is_closing",
        "_lock",
        "_max_restarts",
        "_pending",
        "_process",
        "_restart_count",
        "_stderr_buffer",
        "_task_group_cm",
        "_tg",
    )

    def __init__(
        self,
        command: list[str] | None = None,
        cwd: Path | str | None = None,
        env: dict[str, str] | None = None,
        max_restarts: int = 3,
    ) -> None:
        """Initialize the Stdio subprocess transport.

        Args:
            command: Command array for starting the worker process. Defaults to node ssr.js.
            cwd: Optional working directory for the worker subprocess.
            env: Optional environment dictionary override for the worker.
            max_restarts: Maximum number of automatic restarts upon worker crash.
        """
        self._command = list(command) if command else ["node", "ssr.js"]
        self._cwd = Path(cwd) if cwd else None
        self._env = env
        self._max_restarts = max_restarts
        self._restart_count = 0
        self._process: anyio.abc.Process | None = None
        self._tg: anyio.abc.TaskGroup | None = None
        self._task_group_cm: Any = None
        self._pending: dict[int, tuple[anyio.Event, dict[str, Any]]] = {}
        self._id_counter = itertools.count(1)
        self._stderr_buffer: collections.deque[str] = collections.deque(maxlen=100)
        self._lock = anyio.Lock()
        self._is_closing = False

    @property
    def is_running(self) -> bool:
        """Return True if the transport is running and ready to handle requests.

        Returns:
            Boolean indicating process health and ready state.
        """
        return self._process is not None and self._process.returncode is None and not self._is_closing

    async def start(self) -> None:
        """Spawn the background worker process and launch asynchronous I/O readers."""
        async with self._lock:
            if self.is_running:
                return

            self._is_closing = False
            cmd = list(self._command)
            if os.name == "nt" and cmd:
                resolved = shutil.which(cmd[0])
                if resolved:
                    cmd[0] = resolved

            self._process = await anyio.open_process(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=str(self._cwd) if self._cwd else None,
                env=self._env,
            )

            task_group_cm = anyio.create_task_group()
            self._task_group_cm = task_group_cm
            tg = await task_group_cm.__aenter__()
            self._tg = tg
            tg.start_soon(self._drain_stderr)
            tg.start_soon(self._dispatch_stdout)

    async def _drain_stderr(self) -> None:
        """Continuously drain worker stderr into a rolling buffer to prevent OS pipe deadlocks."""
        if self._process is None or self._process.stderr is None:
            return

        buf = bytearray()
        while True:
            try:
                chunk = await self._process.stderr.receive()
            except anyio.EndOfStream:
                break
            buf.extend(chunk)
            while b"\n" in buf:
                line, _, rest = buf.partition(b"\n")
                buf = bytearray(rest)
                decoded = line.decode("utf-8", errors="replace").strip()
                if decoded:
                    self._stderr_buffer.append(decoded)

        if buf:
            leftover = bytes(buf).decode("utf-8", errors="replace").strip()
            if leftover:
                self._stderr_buffer.append(leftover)

    async def _dispatch_stdout(self) -> None:
        """Continuously read worker stdout, decode NDJSON packets, and correlate responses."""
        if self._process is None or self._process.stdout is None:
            return

        buf = bytearray()
        while True:
            try:
                chunk = await self._process.stdout.receive()
            except anyio.EndOfStream:
                break
            buf.extend(chunk)
            while b"\n" in buf:
                line, _, rest = buf.partition(b"\n")
                buf = bytearray(rest)
                stripped = line.strip()
                if not stripped:
                    continue
                try:
                    payload: dict[str, Any] = decode_json(bytes(stripped))
                except (ValueError, TypeError):
                    payload = {}
                if not payload:
                    continue

                msg_id = payload.get("id")
                if isinstance(msg_id, int) and msg_id in self._pending:
                    event, container = self._pending[msg_id]
                    container["response"] = payload
                    event.set()

        if not self._is_closing and self._pending:
            recent_logs = "\n".join(self._stderr_buffer)
            detail = recent_logs or "Subprocess closed stdout pipe prematurely"
            crash_error = IPCWorkerCrashError(f"Worker crashed: {detail}")
            for event, container in list(self._pending.values()):
                container["error"] = crash_error
                event.set()
            self._pending.clear()

    async def send_request(self, payload: dict[str, Any], timeout: float = 10.0) -> dict[str, Any]:
        """Send an NDJSON request to the worker and await the correlated response.

        Args:
            payload: Request dictionary payload.
            timeout: Maximum time in seconds to await response.

        Returns:
            Worker response dictionary.

        Raises:
            IPCTimeoutError: When response is not received within timeout.
            IPCWorkerCrashError: When child worker exits unexpectedly.
            IPCError: When worker reports an execution failure.
        """
        if not self.is_running:
            await self.start()

        if self._process is None or self._process.stdin is None:
            msg = "Process stdin is unavailable"
            raise IPCError(msg)

        req_id = payload.get("id")
        if req_id is None:
            req_id = next(self._id_counter)
            payload["id"] = req_id

        event = anyio.Event()
        container: dict[str, Any] = {}
        self._pending[req_id] = (event, container)

        encoded = encode_json(payload) + b"\n"
        try:
            await self._process.stdin.send(encoded)
        except (OSError, anyio.ClosedResourceError) as exc:
            self._pending.pop(req_id, None)
            msg_0 = f"Failed to write to worker stdin: {exc}"
            raise IPCWorkerCrashError(msg_0) from exc

        try:
            with anyio.fail_after(timeout):
                await event.wait()
        except TimeoutError as exc:
            self._pending.pop(req_id, None)
            msg_0 = f"IPC request {req_id} timed out after {timeout} seconds"
            raise IPCTimeoutError(msg_0) from exc
        finally:
            self._pending.pop(req_id, None)

        if "error" in container:
            err = container["error"]
            if isinstance(err, Exception):
                raise err
            raise IPCError(str(err))

        response = container.get("response", {})
        if response.get("error") is not None:
            raise IPCError(str(response["error"]))

        return response

    async def close(self) -> None:
        """Gracefully terminate worker subprocess and release reader tasks."""
        self._is_closing = True
        proc = self._process
        self._process = None

        if proc is not None:
            if proc.stdin is not None:
                with contextlib.suppress(OSError, anyio.ClosedResourceError):
                    await proc.stdin.aclose()

            try:
                with anyio.fail_after(2.0):
                    await proc.wait()
            except TimeoutError:
                try:
                    proc.terminate()
                    with anyio.fail_after(1.0):
                        await proc.wait()
                except TimeoutError:
                    proc.kill()
                    await proc.wait()
                except ProcessLookupError:
                    pass
            except ProcessLookupError:
                pass

        if self._task_group_cm is not None:
            try:
                await self._task_group_cm.__aexit__(None, None, None)
            except (OSError, anyio.ClosedResourceError, RuntimeError):
                pass
            finally:
                self._task_group_cm = None
                self._tg = None
