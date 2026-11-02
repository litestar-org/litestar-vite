"""Asynchronous stdio subprocess transport communicating via line-delimited JSON (NDJSON)."""

import asyncio
import collections
import contextlib
import itertools
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any, cast

import anyio
import anyio.abc
from litestar.exceptions import SerializationException
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
        "_reader_tasks",
        "_restart_count",
        "_stderr_buffer",
        "_write_lock",
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
        self._reader_tasks: list[asyncio.Task[None]] = []
        self._pending: dict[int, tuple[anyio.Event, dict[str, Any]]] = {}
        self._id_counter = itertools.count(1)
        self._stderr_buffer: collections.deque[str] = collections.deque(maxlen=100)
        self._lock = anyio.Lock()
        self._write_lock = anyio.Lock()
        self._is_closing = False

    @property
    def command(self) -> list[str]:
        """Return the worker command list."""
        return list(self._command)

    @property
    def cwd(self) -> Path | None:
        """Return the configured working directory for the worker process."""
        return self._cwd

    @property
    def is_running(self) -> bool:
        """Return True if the transport is running and ready to handle requests.

        Returns:
            Boolean indicating process health and ready state.
        """
        return (
            self._process is not None
            and self._process.returncode is None
            and not self._is_closing
            and bool(self._reader_tasks)
            and not self._reader_tasks[-1].done()
        )

    async def start(self) -> None:
        """Spawn the background worker process and launch asynchronous I/O readers."""
        async with self._lock:
            if self.is_running:
                return

            if self._process is not None:
                if self._restart_count >= self._max_restarts:
                    msg = f"Worker exceeded maximum automatic restarts ({self._max_restarts})"
                    raise IPCWorkerCrashError(msg)
                self._restart_count += 1
                await self._close()

            stale_tasks = list(self._reader_tasks)
            self._reader_tasks.clear()
            for task in stale_tasks:
                if not task.done():
                    task.cancel()
            if stale_tasks:
                with contextlib.suppress(Exception):
                    await asyncio.gather(*stale_tasks, return_exceptions=True)

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

            self._reader_tasks = [
                asyncio.create_task(self._drain_stderr()),
                asyncio.create_task(self._dispatch_stdout()),
            ]

    async def _drain_stderr(self) -> None:
        """Continuously drain worker stderr into a rolling buffer to prevent OS pipe deadlocks."""
        if self._process is None or self._process.stderr is None:
            return
        stderr = self._process.stderr

        buf = bytearray()
        while True:
            try:
                chunk = await stderr.receive()
            except (anyio.EndOfStream, anyio.ClosedResourceError, anyio.BrokenResourceError, OSError):
                break
            buf.extend(chunk)
            while (nl_pos := buf.find(b"\n")) != -1:
                line = bytes(buf[:nl_pos])
                del buf[: nl_pos + 1]
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
        stdout = self._process.stdout

        buf = bytearray()
        while True:
            try:
                chunk = await stdout.receive()
            except (anyio.EndOfStream, anyio.ClosedResourceError, anyio.BrokenResourceError, OSError):
                break
            buf.extend(chunk)
            while (nl_pos := buf.find(b"\n")) != -1:
                line = bytes(buf[:nl_pos])
                del buf[: nl_pos + 1]
                stripped = line.strip()
                if not stripped:
                    continue
                try:
                    decoded: Any = decode_json(stripped)
                except (ValueError, TypeError, SerializationException):
                    continue
                if not isinstance(decoded, dict):
                    continue
                payload = cast("dict[str, Any]", decoded)

                msg_id = payload.get("id")
                if isinstance(msg_id, int) and msg_id in self._pending:
                    event, container = self._pending[msg_id]
                    if "result" not in payload and "error" not in payload:
                        container["error"] = IPCError("Worker response has neither result nor error")
                    else:
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
        req_id = payload.get("id")
        if req_id is None:
            req_id = next(self._id_counter)
        if not isinstance(req_id, int) or req_id in self._pending:
            msg = "IPC request id must be a unique integer"
            raise IPCError(msg)
        event = anyio.Event()
        container: dict[str, Any] = {}
        pending = (event, container)
        try:
            with anyio.fail_after(timeout):
                if not self.is_running:
                    await self.start()
                process = self._process
                if process is None or process.stdin is None:
                    msg = "Process stdin is unavailable"
                    raise IPCError(msg)
                stdin = process.stdin
                if req_id in self._pending:
                    msg = "IPC request id must be a unique integer"
                    raise IPCError(msg)
                self._pending[req_id] = pending
                encoded = encode_json({**payload, "id": req_id}) + b"\n"
                async with self._write_lock:
                    if self._process is not process or self._is_closing:
                        msg = "Worker transport closed before request could be sent"
                        raise IPCWorkerCrashError(msg)
                    await stdin.send(encoded)
                await event.wait()
        except TimeoutError as exc:
            msg = f"IPC request {req_id} timed out after {timeout} seconds"
            raise IPCTimeoutError(msg) from exc
        except (OSError, anyio.ClosedResourceError, anyio.BrokenResourceError) as exc:
            msg = f"Failed to write to worker stdin: {exc}"
            raise IPCWorkerCrashError(msg) from exc
        finally:
            if self._pending.get(req_id) is pending:
                self._pending.pop(req_id, None)

        if "error" in container:
            err = container["error"]
            if isinstance(err, Exception):
                raise err
            raise IPCError(str(err))

        response = container.get("response", {})
        if response.get("error") is not None:
            raise IPCError(str(response["error"]))

        self._restart_count = 0
        return response

    async def close(self) -> None:
        """Gracefully terminate worker subprocess and release reader tasks."""
        with anyio.CancelScope(shield=True):
            async with self._lock:
                self._restart_count = 0
                await self._close()

    async def _close(self) -> None:
        with anyio.CancelScope(shield=True):
            self._is_closing = True
            for event, container in self._pending.values():
                container["error"] = IPCWorkerCrashError("Worker transport closed")
                event.set()
            self._pending.clear()
            proc = self._process
            self._process = None

            if proc is not None:
                if proc.stdin is not None:
                    with contextlib.suppress(OSError, anyio.ClosedResourceError, anyio.BrokenResourceError):
                        with anyio.move_on_after(0.1):
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

            tasks = list(self._reader_tasks)
            self._reader_tasks.clear()
            for task in tasks:
                if not task.done():
                    task.cancel()
            if tasks:
                with contextlib.suppress(Exception):
                    await asyncio.gather(*tasks, return_exceptions=True)
