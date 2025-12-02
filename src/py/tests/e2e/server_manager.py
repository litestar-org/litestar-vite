"""Process manager for example applications."""

import logging
import os
import signal
import subprocess
import sys
from pathlib import Path

from .health_check import wait_for_http
from .port_allocator import EXAMPLE_NAMES, get_ports_for_example

logger = logging.getLogger(__name__)

EXAMPLES_DIR = Path(__file__).resolve().parent.parent.parent.parent.parent / "examples"

SSR_EXAMPLES: set[str] = {"nuxt", "sveltekit"}
STATIC_SSR_EXAMPLES: set[str] = {"astro"}
CLI_EXAMPLES: set[str] = {"angular-cli"}

# Track all spawned processes to enable global cleanup in fixtures
RUNNING_PROCS: list[subprocess.Popen[bytes]] = []


class ExampleServer:
    """Manage lifecycle of a single example app for tests."""

    def __init__(self, example_name: str) -> None:
        if example_name not in EXAMPLE_NAMES:
            raise ValueError(f"Unknown example: {example_name}")
        self.example_name = example_name
        self.example_dir = EXAMPLES_DIR / example_name
        self.vite_port, self.litestar_port = get_ports_for_example(example_name)
        self._processes: list[subprocess.Popen[bytes]] = []
        self._dev_mode = False

    # ---------------------------- lifecycle ---------------------------- #
    def start_dev_mode(self) -> None:
        """Start dev servers (Vite/Angular CLI + Litestar)."""
        env = self._base_env(dev_mode=True)
        if not self._is_cli_example():
            self._processes.append(self._spawn(self._dev_command(), env=env, cwd=self.example_dir))
        self._processes.append(self._spawn(self._litestar_command(), env=env))
        logger.info("Started dev mode for %s (vite=%s, litestar=%s)", self.example_name, self.vite_port, self.litestar_port)
        self._dev_mode = True

    def start_production_mode(self) -> None:
        """Build and start production servers."""
        env = self._base_env(dev_mode=False, port_override=self.vite_port)
        self._run([sys.executable, "-m", "litestar", "--app-dir", str(self.example_dir), "assets", "build"], cwd=self.example_dir, env=env)
        self._processes.append(self._spawn(self._litestar_command(), env=env))
        if self.example_name in SSR_EXAMPLES | STATIC_SSR_EXAMPLES | CLI_EXAMPLES:
            self._processes.append(self._spawn(self._serve_command(), env=env, cwd=self.example_dir))
        logger.info("Started production mode for %s (litestar=%s)", self.example_name, self.litestar_port)
        self._dev_mode = False

    def wait_until_ready(self, timeout: float = 120.0) -> None:
        """Wait until Litestar responds to /api/summary or /."""
        # Ensure frontend or node server is up when applicable to avoid Litestar proxy 500s.
        if (self._dev_mode and not self._is_cli_example()) or self._is_ssr_example() or self._is_static_ssr_example():
            wait_for_http(f"http://127.0.0.1:{self.vite_port}/", timeout=timeout, processes=self._processes)

        base_url = f"http://127.0.0.1:{self.litestar_port}"
        try:
            wait_for_http(f"{base_url}/api/summary", timeout=timeout, processes=self._processes)
        except TimeoutError:
            wait_for_http(f"{base_url}/", timeout=timeout, processes=self._processes)
        # Ensure homepage returns successfully (helps Angular CLI where proxy can lag).
        wait_for_http(f"{base_url}/", timeout=timeout, processes=self._processes, expected_statuses=(200,))
        if self._is_ssr_example() or self._is_static_ssr_example():
            wait_for_http(f"http://127.0.0.1:{self.vite_port}/", timeout=timeout, processes=self._processes)
        self._assert_processes_alive()

    def stop(self) -> None:
        """Terminate all child processes."""
        for proc in self._processes:
            if proc.poll() is None:
                self._terminate_process(proc)
                logger.info("Stopped process pid=%s for %s", proc.pid, self.example_name)
        self._processes.clear()

    # ---------------------------- commands ---------------------------- #
    def _dev_command(self) -> list[str]:
        if self.example_name in CLI_EXAMPLES:
            return ["npm", "run", "start", "--", "--port", str(self.vite_port)]
        return ["npm", "run", "dev", "--", "--port", str(self.vite_port)]

    def _litestar_command(self) -> list[str]:
        return [
            sys.executable,
            "-m",
            "litestar",
            "--app-dir",
            str(self.example_dir),
            "run",
            "--port",
            str(self.litestar_port),
        ]

    def _serve_command(self) -> list[str]:
        if self.example_name in STATIC_SSR_EXAMPLES:
            return ["npm", "run", "preview", "--", "--host", "127.0.0.1", "--port", str(self.vite_port)]
        if self.example_name in SSR_EXAMPLES:
            return ["npm", "run", "serve"]
        if self.example_name in CLI_EXAMPLES:
            return ["npm", "run", "serve", "--", "--port", str(self.vite_port)]
        return ["npm", "run", "serve"]

    # ---------------------------- helpers ---------------------------- #
    def _base_env(self, dev_mode: bool, port_override: int | None = None) -> dict[str, str]:
        env = os.environ.copy()
        env.update(
            {
                "LITESTAR_PORT": str(self.litestar_port),
                "VITE_DEV_MODE": "true" if dev_mode else "false",
                "npm_config_cache": str(Path.home() / ".cache" / "npm"),
            }
        )
        if not self._is_cli_example():
            env["VITE_PORT"] = str(self.vite_port)
        if port_override is not None:
            env.setdefault("PORT", str(port_override))
            env.setdefault("NITRO_PORT", str(port_override))
            env.setdefault("HOST", "127.0.0.1")
        return env

    def _run(self, cmd: list[str], cwd: Path, env: dict[str, str]) -> None:
        result = subprocess.run(cmd, cwd=cwd, env=env, capture_output=True)
        if result.returncode != 0:
            stdout = result.stdout.decode() if result.stdout else ""
            stderr = result.stderr.decode() if result.stderr else ""
            raise RuntimeError(f"Command failed: {' '.join(cmd)}\nstdout:\n{stdout}\nstderr:\n{stderr}")
        logger.info("Command succeeded: %s", " ".join(cmd))

    def _spawn(self, cmd: list[str], env: dict[str, str], cwd: Path | None = None) -> subprocess.Popen[bytes]:
        proc = subprocess.Popen(
            cmd,
            cwd=cwd or self.example_dir,
            env=env,
            start_new_session=True,
            stdout=None,
            stderr=None,
        )
        RUNNING_PROCS.append(proc)
        return proc

    def _terminate_process(self, proc: subprocess.Popen[bytes]) -> None:
        try:
            if proc.poll() is None:
                # POSIX: send SIGTERM to process group
                if sys.platform != "win32":
                    os.killpg(proc.pid, signal.SIGTERM)
                else:
                    proc.terminate()
                proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            if sys.platform != "win32":
                os.killpg(proc.pid, signal.SIGKILL)
            else:
                proc.kill()
        finally:
            if proc.poll() is None:
                proc.kill()
            if proc in RUNNING_PROCS:
                RUNNING_PROCS.remove(proc)

    def _assert_processes_alive(self) -> None:
        for proc in list(self._processes):
            if proc.poll() is not None:
                raise RuntimeError(f"Process for {self.example_name} exited early with code {proc.returncode}")

    def _is_ssr_example(self) -> bool:
        return self.example_name in SSR_EXAMPLES

    def _is_static_ssr_example(self) -> bool:
        return self.example_name in STATIC_SSR_EXAMPLES

    def _is_cli_example(self) -> bool:
        return self.example_name in CLI_EXAMPLES
