"""Vite dev server process management."""

import os
import signal
import subprocess
import threading
import time
from contextlib import suppress
from pathlib import Path
from typing import TYPE_CHECKING, Any, ClassVar

from litestar_vite.exceptions import ViteProcessError
from litestar_vite.plugin._utils import console

if TYPE_CHECKING:
    from litestar_vite.executor import JSExecutor


class ViteProcess:
    """Manages the Vite development server process.

    This class handles starting and stopping the Vite dev server process,
    with proper thread safety and graceful shutdown. It registers signal
    handlers for SIGTERM and SIGINT to ensure child processes are terminated
    even if Python is killed externally.
    """

    _instances: "list[ViteProcess]" = []
    _signals_registered: bool = False
    _original_handlers: "dict[int, Any]" = {}
    _RESTART_BACKOFFS: ClassVar[tuple[float, ...]] = (1.0, 2.0, 4.0)

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

        ViteProcess._instances.append(self)

        if not ViteProcess._signals_registered:
            self._register_signal_handlers()
            ViteProcess._signals_registered = True

            import atexit

            atexit.register(ViteProcess._cleanup_all_instances)

    @classmethod
    def _register_signal_handlers(cls) -> None:
        """Register signal handlers for graceful shutdown on SIGTERM/SIGINT."""
        for sig in (signal.SIGTERM, signal.SIGINT):
            try:
                original = signal.signal(sig, cls._signal_handler)
                cls._original_handlers[sig] = original
            except (OSError, ValueError):
                pass

    @classmethod
    def _signal_handler(cls, signum: int, frame: Any) -> None:
        """Handle termination signals by stopping all Vite processes first."""
        cls._cleanup_all_instances()

        original = cls._original_handlers.get(signum, signal.SIG_DFL)
        if callable(original) and original not in {signal.SIG_IGN, signal.SIG_DFL}:
            original(signum, frame)
        elif original == signal.SIG_DFL:
            signal.signal(signum, signal.SIG_DFL)
            os.kill(os.getpid(), signum)

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
        if process and process.poll() is not None:
            error = self._build_immediate_exit_error(process, command)
            self._restart_error = error
            if raise_immediate_exit:
                raise error
        return process

    def _build_immediate_exit_error(self, process: "subprocess.Popen[Any]", command: list[str]) -> ViteProcessError:
        stdout, stderr = process.communicate()
        out_str = stdout.decode(errors="ignore") if stdout else ""
        err_str = stderr.decode(errors="ignore") if stderr else ""
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

            exit_code = process.wait()
            self._terminate_exited_process_group(process, timeout=0.5)

            with self._lock:
                if self._watcher_generation != generation or self._stopping or process is not self.process:
                    return
                self.process = None
                if command is None or cwd is None:
                    return

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
        if not self.process or self.process.poll() is not None:
            self.process = None
            return
        process = self.process
        self._terminate_specific_process_group(process, timeout)
        self.process = None

    def _terminate_specific_process_group(self, process: "subprocess.Popen[Any]", timeout: float) -> None:
        """Terminate one process group without changing manager state."""
        pid = process.pid
        try:
            os.killpg(pid, signal.SIGTERM)
        except AttributeError:
            process.terminate()
        except ProcessLookupError:
            pass
        try:
            process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            self._force_kill_specific_process_group(process)
            process.wait(timeout=1.0)

    def _terminate_exited_process_group(self, process: "subprocess.Popen[Any]", *, timeout: float) -> None:
        """Best-effort cleanup for child processes left in an exited process group."""
        try:
            os.killpg(process.pid, signal.SIGTERM)
        except AttributeError:
            return
        except ProcessLookupError:
            return
        time.sleep(timeout)
        self._force_kill_specific_process_group(process)

    def _force_kill_process_group(self) -> None:
        """Force kill the process group if still alive."""
        if not self.process:
            return
        self._force_kill_specific_process_group(self.process)

    def _force_kill_specific_process_group(self, process: "subprocess.Popen[Any]") -> None:
        """Force kill a specific process group if still alive."""
        pid = process.pid
        try:
            os.killpg(pid, signal.SIGKILL)
        except AttributeError:
            process.kill()
        except ProcessLookupError:
            pass

    def _atexit_stop(self) -> None:
        """Best-effort stop on interpreter exit."""
        with suppress(Exception):
            self.stop()
