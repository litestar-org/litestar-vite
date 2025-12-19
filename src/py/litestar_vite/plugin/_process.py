"""Vite dev server process management."""

import os
import signal
import subprocess
import threading
from contextlib import suppress
from pathlib import Path
from typing import TYPE_CHECKING, Any

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

    def __init__(self, executor: "JSExecutor") -> None:
        """Initialize the Vite process manager.

        Args:
            executor: The JavaScript executor to use for running Vite.
        """
        self.process: "subprocess.Popen[Any] | None" = None
        self._lock = threading.Lock()
        self._executor = executor

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
        for instance in cls._instances:
            with suppress(Exception):
                instance.stop()

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
                    self.process = self._executor.run(command, cwd)
                    if self.process and self.process.poll() is not None:
                        stdout, stderr = self.process.communicate()
                        out_str = stdout.decode(errors="ignore") if stdout else ""
                        err_str = stderr.decode(errors="ignore") if stderr else ""
                        console.print(
                            "[red]Vite process exited immediately.[/]\n"
                            f"[red]Command:[/] {' '.join(command)}\n"
                            f"[red]Exit code:[/] {self.process.returncode}\n"
                            f"[red]Stdout:[/]\n{out_str or '<empty>'}\n"
                            f"[red]Stderr:[/]\n{err_str or '<empty>'}\n"
                            "[yellow]Hint: Run `litestar assets doctor` to diagnose configuration issues.[/]"
                        )
                        msg = f"Vite process failed to start (exit {self.process.returncode})"
                        raise ViteProcessError(  # noqa: TRY301
                            msg, command=command, exit_code=self.process.returncode, stderr=err_str, stdout=out_str
                        )
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
                self._terminate_process_group(timeout)
        except Exception as e:
            console.print(f"[red]Failed to stop Vite process: {e!s}[/]")
            msg = f"Failed to stop Vite process: {e!s}"
            raise ViteProcessError(msg) from e

    def _terminate_process_group(self, timeout: float) -> None:
        """Terminate the process group, waiting and killing if needed.

        When available, uses process group termination to ensure all child processes are stopped
        (e.g., Vite spawning Node/SSR framework processes). The process is started with
        ``start_new_session=True`` so the process id is the group id.
        """
        if not self.process or self.process.poll() is not None:
            return
        pid = self.process.pid
        try:
            os.killpg(pid, signal.SIGTERM)
        except AttributeError:
            self.process.terminate()
        except ProcessLookupError:
            pass
        try:
            self.process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            self._force_kill_process_group()
            self.process.wait(timeout=1.0)
        finally:
            self.process = None

    def _force_kill_process_group(self) -> None:
        """Force kill the process group if still alive."""
        if not self.process:
            return
        pid = self.process.pid
        try:
            os.killpg(pid, signal.SIGKILL)
        except AttributeError:
            self.process.kill()
        except ProcessLookupError:
            pass

    def _atexit_stop(self) -> None:
        """Best-effort stop on interpreter exit."""
        with suppress(Exception):
            self.stop()
