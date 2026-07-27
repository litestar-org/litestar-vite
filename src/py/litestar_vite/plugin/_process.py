"""Vite dev server process management."""

import atexit
import os
import platform
import shutil
import signal
import subprocess
import sys
import threading
import time
from collections import deque
from contextlib import suppress
from pathlib import Path
from typing import TYPE_CHECKING, Any, ClassVar

from litestar_vite.exceptions import ViteProcessError
from litestar_vite.plugin._utils import console

if TYPE_CHECKING:
    from litestar_vite.executor import JSExecutor

_CTRL_BREAK_EVENT: int = getattr(signal, "CTRL_BREAK_EVENT", 1)


class ViteProcess:
    """Manages the Vite development server process.

    This class handles starting and stopping the Vite dev server process,
    with proper thread safety and graceful shutdown. The active ASGI server owns
    top-level signals; one atexit hook remains as a last-resort cleanup path.
    """

    _instances: "list[ViteProcess]" = []
    _atexit_registered: bool = False
    _RESTART_BACKOFFS: ClassVar[tuple[float, ...]] = (1.0, 2.0, 4.0)
    _RESTART_STABILITY_SECONDS: ClassVar[float] = 5.0
    _COOPERATIVE_SHUTDOWN_SECONDS: ClassVar[float] = 2.0
    _WINDOWS_TREE_KILL_SECONDS: ClassVar[float] = 1.0

    def __init__(self, executor: "JSExecutor") -> None:
        """Initialize the Vite process manager.

        Args:
            executor: The JavaScript executor to use for running Vite.
        """
        self.process: "subprocess.Popen[Any] | None" = None
        self._lock = threading.RLock()
        self._executor = executor
        self._restart_command: "list[str] | None" = None
        self._restart_cwd: "Path | None" = None
        self._restart_error: "ViteProcessError | None" = None
        self._stopping = False
        self._watcher_generation = 0
        self._watcher_thread: "threading.Thread | None" = None
        self._stderr_captures: dict[int, tuple[deque[str], threading.Thread]] = {}
        self._stderr_thread: "threading.Thread | None" = None

        ViteProcess._instances.append(self)

        if not ViteProcess._atexit_registered:
            atexit.register(ViteProcess._cleanup_all_instances)
            ViteProcess._atexit_registered = True

    @classmethod
    def _cleanup_all_instances(cls) -> None:
        """Stop all tracked ViteProcess instances."""
        for instance in list(cls._instances):
            with suppress(Exception):
                instance.stop()
        cls._instances.clear()

    def start(self, command: list[str], cwd: "Path | str | None") -> None:
        """Start the Vite process.

        Args:
            command: The command to run (e.g., ["npm", "run", "dev"]).
            cwd: The working directory for the process.

        If the process exits immediately, this method captures stdout/stderr and raises a
        ViteProcessError with diagnostic details.

        Raises:
            ViteProcessError: If the process fails to start.
        """
        if cwd is not None and isinstance(cwd, str):
            cwd = Path(cwd)

        try:
            with self._lock:
                if self.process and self.process.poll() is None:
                    return

                if cwd:
                    self._ensure_tracked()
                    self._stopping = False
                    self._restart_error = None
                    self._restart_command = list(command)
                    self._restart_cwd = cwd
                    self.process = self._spawn_process(command, cwd, raise_immediate_exit=True)
                    self._watcher_generation += 1
                    self._start_watcher(self._watcher_generation)
        except Exception as e:
            if isinstance(e, ViteProcessError):
                raise
            console.print(f"[red]Failed to start Vite process: {e!s}[/]")
            msg = f"Failed to start Vite process: {e!s}"
            raise ViteProcessError(msg) from e

    def stop(self, timeout: float = 5.0) -> None:
        """Stop the Vite process and all its child processes.

        Uses process groups to ensure child processes (node, astro, nuxt, vite, etc.)
        are terminated along with the parent npm/npx process.

        Args:
            timeout: Seconds to wait for graceful shutdown before killing.

        Raises:
            ViteProcessError: If the process fails to stop.
        """
        try:
            with self._lock:
                self._stopping = True
                self._watcher_generation += 1
                self._terminate_process_group(timeout)
        except Exception as e:
            console.print(f"[red]Failed to stop Vite process: {e!s}[/]")
            msg = f"Failed to stop Vite process: {e!s}"
            raise ViteProcessError(msg) from e
        finally:
            with suppress(ValueError):
                ViteProcess._instances.remove(self)

    def _ensure_tracked(self) -> None:
        """Ensure this process manager participates in global signal cleanup."""
        if self not in ViteProcess._instances:
            ViteProcess._instances.append(self)

    def _spawn_process(self, command: list[str], cwd: Path, *, raise_immediate_exit: bool) -> "subprocess.Popen[Any]":
        """Start a child process and optionally fail fast for immediate exits."""
        process = self._executor.run(command, cwd)
        self._start_stderr_drain(process)
        if process and process.poll() is not None:
            error = self._build_immediate_exit_error(process, command)
            self._restart_error = error
            if raise_immediate_exit:
                raise error
        return process

    def _build_immediate_exit_error(self, process: "subprocess.Popen[Any]", command: list[str]) -> ViteProcessError:
        capture = self._stderr_captures.pop(id(process), None)
        if capture is not None:
            stderr_buffer, stderr_thread = capture
            stderr_thread.join(timeout=0.5)
        else:
            stderr_buffer = deque[str]()
        out_str = ""
        err_str = "".join(stderr_buffer)
        console.print(
            "[red]Vite process exited immediately.[/]\n"
            f"[red]Command:[/] {' '.join(command)}\n"
            f"[red]Exit code:[/] {process.returncode}\n"
            f"[red]Stdout:[/]\n{out_str or '<empty>'}\n"
            f"[red]Stderr:[/]\n{err_str or '<empty>'}\n"
            "[yellow]Hint: Run `litestar assets doctor` to diagnose configuration issues.[/]"
        )
        msg = f"Vite process failed to start (exit {process.returncode})"
        return ViteProcessError(msg, command=command, exit_code=process.returncode, stderr=err_str, stdout=out_str)

    def _start_stderr_drain(self, process: "subprocess.Popen[Any]") -> None:
        """Continuously capture and mirror a sidecar's piped stderr."""
        stderr = getattr(process, "stderr", None)
        if stderr is None:
            self._stderr_thread = None
            return
        stderr_buffer: deque[str] = deque(maxlen=200)
        self._stderr_thread = threading.Thread(
            target=self._drain_stderr, args=(stderr, stderr_buffer), name="litestar-vite-stderr-drain", daemon=True
        )
        self._stderr_captures[id(process)] = (stderr_buffer, self._stderr_thread)
        self._stderr_thread.start()

    @staticmethod
    def _drain_stderr(stderr: Any, stderr_buffer: deque[str]) -> None:
        """Mirror stderr lines to the terminal and retain recent diagnostics."""
        with suppress(Exception):
            while True:
                line = stderr.readline()
                if not isinstance(line, (bytes, str)) or not line:
                    return
                text = line.decode(errors="replace") if isinstance(line, bytes) else str(line)
                stderr_buffer.append(text)
                sys.stderr.write(text)
                sys.stderr.flush()

    def _start_watcher(self, generation: int) -> None:
        """Start a daemon watcher for unexpected process exits."""
        if self.process is None:
            return
        self._watcher_thread = threading.Thread(
            target=self._watch_process, args=(generation,), name="litestar-vite-process-watchdog", daemon=True
        )
        self._watcher_thread.start()

    def _watch_process(self, generation: int) -> None:
        """Restart the child process after unexpected exits with capped backoff."""
        attempts = 0
        last_error: BaseException | None = None

        while True:
            with self._lock:
                if self._watcher_generation != generation or self._stopping or self.process is None:
                    return
                process = self.process
                command = self._restart_command
                cwd = self._restart_cwd

            wait_started = time.monotonic()
            exit_code = process.wait()
            process_runtime = time.monotonic() - wait_started

            with self._lock:
                if self._watcher_generation != generation or self._stopping or process is not self.process:
                    return
                self.process = None

            self._terminate_exited_process_group(process, timeout=0.5)
            self._stderr_captures.pop(id(process), None)
            if command is None or cwd is None:
                return

            if process_runtime >= self._RESTART_STABILITY_SECONDS:
                attempts = 0
                last_error = None

            restarted = False
            while attempts < len(self._RESTART_BACKOFFS):
                backoff = self._RESTART_BACKOFFS[attempts]
                attempts += 1
                console.print(
                    "[yellow]Vite process exited unexpectedly "
                    f"(exit {exit_code}). Restarting in {backoff:g}s "
                    f"(attempt {attempts}/{len(self._RESTART_BACKOFFS)}).[/]"
                )
                time.sleep(backoff)

                with self._lock:
                    if self._watcher_generation != generation or self._stopping:
                        return

                try:
                    next_process = self._spawn_process(command, cwd, raise_immediate_exit=False)
                except BaseException as exc:  # noqa: BLE001
                    last_error = exc
                    continue

                with self._lock:
                    if self._watcher_generation != generation or self._stopping:
                        self._terminate_specific_process_group(next_process, 0.1)
                        return
                    self.process = next_process
                restarted = True
                break

            if restarted:
                continue

            self._record_restart_failure(command, exit_code, last_error)
            return

    def _record_restart_failure(
        self, command: list[str], exit_code: int | None, last_error: BaseException | None
    ) -> None:
        """Store and log the terminal restart failure."""
        detail = f"Last restart error: {last_error!s}. " if last_error is not None else ""
        msg = (
            f"Vite process exited unexpectedly after {len(self._RESTART_BACKOFFS)} restart attempts "
            f"(last exit {exit_code}). {detail}"
            f"Command: {' '.join(command)}. Run `litestar assets doctor` to diagnose configuration issues."
        )
        error = ViteProcessError(msg, command=command, exit_code=exit_code)
        with self._lock:
            self._restart_error = error
            self._stopping = True
            self.process = None
            with suppress(ValueError):
                ViteProcess._instances.remove(self)
        console.print(f"[red]{msg}[/]")

    def _terminate_process_group(self, timeout: float) -> None:
        """Terminate the process group, waiting and killing if needed.

        When available, uses process group termination to ensure all child processes are stopped
        (e.g., Vite spawning Node/SSR framework processes). The process is started with
        ``start_new_session=True`` so the process id is the group id.
        """
        if not self.process:
            self.process = None
            return
        process = self.process
        if process.poll() is not None:
            self._stderr_captures.pop(id(process), None)
            self.process = None
            return
        deadline = time.monotonic() + max(0.0, timeout)
        tree_kill_reserve = (
            min(self._WINDOWS_TREE_KILL_SECONDS, max(0.0, timeout)) if platform.system() == "Windows" else 0.0
        )
        stdin = getattr(process, "stdin", None)
        if stdin is not None and not getattr(stdin, "closed", False):
            with suppress(Exception):
                stdin.close()
            try:
                cooperative_timeout = max(0.0, self._remaining_timeout(deadline) - tree_kill_reserve)
                process.wait(timeout=min(self._COOPERATIVE_SHUTDOWN_SECONDS, cooperative_timeout))
            except subprocess.TimeoutExpired:
                pass
            else:
                self._stderr_captures.pop(id(process), None)
                self.process = None
                return
        self._terminate_specific_process_group_until(process, deadline)
        self._stderr_captures.pop(id(process), None)
        self.process = None

    def _terminate_specific_process_group(self, process: "subprocess.Popen[Any]", timeout: float) -> None:
        """Terminate one process group without changing manager state."""
        self._terminate_specific_process_group_until(process, time.monotonic() + max(0.0, timeout))

    def _terminate_specific_process_group_until(self, process: "subprocess.Popen[Any]", deadline: float) -> None:
        """Terminate one process group within an existing shutdown deadline."""
        is_windows = platform.system() == "Windows"
        try:
            if is_windows:
                process.send_signal(_CTRL_BREAK_EVENT)
            else:
                os.killpg(process.pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
        remaining_timeout = self._remaining_timeout(deadline)
        tree_kill_reserve = min(self._WINDOWS_TREE_KILL_SECONDS, remaining_timeout) if is_windows else 0.0
        try:
            process.wait(timeout=max(0.0, remaining_timeout - tree_kill_reserve))
        except subprocess.TimeoutExpired:
            self._force_kill_specific_process_group(process, timeout=self._remaining_timeout(deadline))
            with suppress(subprocess.TimeoutExpired):
                process.wait(timeout=min(1.0, self._remaining_timeout(deadline)))

    @staticmethod
    def _remaining_timeout(deadline: float) -> float:
        """Return the non-negative time remaining in a shutdown budget."""
        return max(0.0, deadline - time.monotonic())

    def _terminate_exited_process_group(self, process: "subprocess.Popen[Any]", *, timeout: float) -> None:
        """Best-effort cleanup for child processes left in an exited process group."""
        if platform.system() == "Windows":
            self._force_kill_specific_process_group(process)
            return
        try:
            os.killpg(process.pid, signal.SIGTERM)
        except ProcessLookupError:
            return
        time.sleep(timeout)
        self._force_kill_specific_process_group(process)

    def _force_kill_specific_process_group(self, process: "subprocess.Popen[Any]", *, timeout: float = 1.0) -> None:
        """Force kill a specific process group if still alive."""
        if platform.system() == "Windows":
            taskkill = self._resolve_taskkill()
            if taskkill is None:
                process.kill()
                return
            taskkill_timeout = max(0.0, min(self._WINDOWS_TREE_KILL_SECONDS, timeout))
            try:
                subprocess.run(
                    [taskkill, "/PID", str(process.pid), "/T", "/F"],
                    check=False,
                    shell=False,
                    capture_output=True,
                    timeout=taskkill_timeout,
                )
            except (OSError, subprocess.TimeoutExpired):
                process.kill()
            return
        with suppress(ProcessLookupError):
            os.killpg(process.pid, signal.SIGKILL)

    @staticmethod
    def _resolve_taskkill() -> str | None:
        """Resolve Windows tree termination without invoking a command shell."""
        if taskkill := shutil.which("taskkill"):
            return taskkill
        if system_root := os.environ.get("SYSTEMROOT"):
            candidate = Path(system_root) / "System32" / "taskkill.exe"
            if candidate.is_file():
                return str(candidate)
        return None
