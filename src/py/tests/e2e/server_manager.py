"""Process manager for example applications.

This module manages the lifecycle of example applications for E2E testing.
All commands use the Litestar CLI (`litestar assets`) to ensure we test
the real developer experience, not just that npm works directly.

Key design decisions:
- Let Vite auto-select available ports (parsed from output)
- Find free ports for Litestar (uvicorn doesn't auto-select)
- Parse actual ports from process output
- This avoids port collisions and race conditions

Critical: NEVER use npm/node commands directly - always use litestar CLI!
"""

import logging
import os
import re
import signal
import socket
import subprocess
import sys
import time
from pathlib import Path
from threading import Thread
from typing import IO

logger = logging.getLogger(__name__)


def find_free_port() -> int:
    """Find a free port by letting the OS assign one.

    Returns:
        An available port number assigned by the OS.
    """
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        s.listen(1)
        return s.getsockname()[1]


EXAMPLES_DIR = Path(__file__).resolve().parent.parent.parent.parent.parent / "examples"

# SSR examples that run their own dev server (proxy to Node in dev, serve static in prod)
# Astro example uses static SSG output, so treat it as non-SSR here
SSR_EXAMPLES: set[str] = {"nuxt", "sveltekit"}

# CLI examples use their own build tools (Angular CLI)
CLI_EXAMPLES: set[str] = {"angular-cli"}

# Track all spawned processes to enable global cleanup in fixtures
RUNNING_PROCS: list[subprocess.Popen[bytes]] = []

# Patterns to extract ports from output
# Vite standard output: "Local:   http://localhost:5173/"
VITE_PORT_PATTERN = re.compile(r"Local:\s+https?://(?:localhost|127\.0\.0\.1):(\d+)")
# Uvicorn output: "Uvicorn running on http://127.0.0.1:8000"
LITESTAR_PORT_PATTERN = re.compile(r"Uvicorn running on https?://[\d.]+:(\d+)")
# Astro output: "┃ Local    http://localhost:55327/" (may include box chars + ANSI)
# Accept any ANSI prefix and host variants
ASTRO_PORT_PATTERN = re.compile(r"(?:\x1b\[[0-9;]*m)?Local\s+https?://(?:localhost|127\.0\.0\.1):(\d+)")
# Generic fallback to catch stray host prints
GENERIC_HOST_PATTERN = re.compile(r"https?://(?:localhost|127\.0\.0\.1):(\d+)")
# Nuxt dev output: "➜ Local:    http://127.0.0.1:60411/" (ANSI arrow, host may be 127 or localhost)
NUXT_PORT_PATTERN = re.compile(r"Local:\s+https?://(?:localhost|127\.0\.0\.1):(\d+)")
# Nitro/Nuxt production: "Listening on http://127.0.0.1:5173"
# SvelteKit production: "Listening on http://0.0.0.0:3000"
LISTENING_PORT_PATTERN = re.compile(r"Listening on https?://[\d.]+:(\d+)")
# Angular CLI dev output: "\u2714 Local:   http://localhost:4200/" or "listening on localhost:4200"
ANGULAR_CLI_PORT_PATTERN = re.compile(r"localhost:(\d+)")


class OutputCapture:
    """Captures process output and extracts port information."""

    def __init__(self, stream: "IO[bytes] | None", patterns: list[re.Pattern[str]]) -> None:
        self.stream = stream
        self.patterns = patterns
        self.port: int | None = None
        self.output_lines: list[str] = []
        self._thread: Thread | None = None

    def start(self) -> None:
        """Start capturing output in a background thread."""
        if self.stream is None:
            return
        self._thread = Thread(target=self._capture, daemon=True)
        self._thread.start()

    def _capture(self) -> None:
        """Read lines and extract port."""
        if self.stream is None:
            return
        for line_bytes in self.stream:
            line = line_bytes.decode(errors="replace").strip()
            self.output_lines.append(line)
            logger.debug("Output: %s", line)

            if self.port is None:
                for pattern in self.patterns:
                    match = pattern.search(line)
                    if match:
                        self.port = int(match.group(1))
                        logger.info("Detected port: %d from line: %s", self.port, line)
                        break

    def wait_for_port(self, timeout: float = 60.0) -> int:
        """Wait until port is detected or timeout.

        Args:
            timeout: Maximum seconds to wait for port detection.

        Returns:
            The detected port number.

        Raises:
            TimeoutError: If port is not detected within the timeout period.
        """
        start = time.monotonic()
        while time.monotonic() - start < timeout:
            if self.port is not None:
                return self.port
            time.sleep(0.1)
        output = "\n".join(self.output_lines[-20:])
        raise TimeoutError(f"Could not detect port within {timeout}s. Last output:\n{output}")

    def get_output(self) -> str:
        """Get captured output.

        Returns:
            All captured output lines joined with newlines.
        """
        return "\n".join(self.output_lines)


class ExampleServer:
    """Manage lifecycle of a single example app for tests.

    Uses Litestar CLI commands exclusively to test the real developer experience:
    - Dev mode: `litestar assets serve` + `litestar run`
    - Production: `litestar assets build` + `litestar run` (+ `litestar assets serve --production` for SSR)

    Ports are auto-selected by Vite/Litestar and parsed from output.
    """

    def __init__(self, example_name: str) -> None:
        self.example_name = example_name
        self.example_dir = EXAMPLES_DIR / example_name
        if not self.example_dir.exists():
            raise ValueError(f"Example directory not found: {self.example_dir}")

        self.vite_port: int | None = None
        self.litestar_port: int | None = None
        self._processes: list[subprocess.Popen[bytes]] = []
        self._captures: list[OutputCapture] = []
        self._dev_mode = False

    # ---------------------------- lifecycle ---------------------------- #
    def start_dev_mode(self) -> None:
        """Start dev servers using Litestar CLI.

        For dev mode:
        1. `litestar assets serve` - Starts Vite dev server (auto-selects port)
        2. `litestar run` - Starts Litestar backend (auto-selects port)

        Ports are parsed from process output.
        """
        env = self._base_env(dev_mode=True)

        # Start frontend dev server via litestar assets serve
        vite_patterns = [VITE_PORT_PATTERN, ASTRO_PORT_PATTERN, NUXT_PORT_PATTERN, LISTENING_PORT_PATTERN, GENERIC_HOST_PATTERN]
        if self._is_cli_example():
            vite_patterns.append(ANGULAR_CLI_PORT_PATTERN)
        vite_proc, vite_capture = self._spawn_with_capture(
            self._assets_serve_command(),
            env=env,
            patterns=vite_patterns,
        )
        self._processes.append(vite_proc)
        self._captures.append(vite_capture)

        # Start Litestar backend on a free port
        # Note: uvicorn doesn't auto-select ports like Vite, so we find one first
        self.litestar_port = find_free_port()
        litestar_proc, litestar_capture = self._spawn_with_capture(
            self._litestar_run_command(self.litestar_port),
            env=env,
            patterns=[LITESTAR_PORT_PATTERN],
        )
        self._processes.append(litestar_proc)
        self._captures.append(litestar_capture)

        self._dev_mode = True
        logger.info("Started dev mode for %s (litestar port: %d)", self.example_name, self.litestar_port)

    def start_production_mode(self) -> None:
        """Build and start production servers using Litestar CLI.

        For production mode:
        1. `litestar assets build` - Build frontend assets
        2. `litestar run` - Serve built assets via Litestar (auto-selects port)
        3. For SSR: `litestar assets serve --production` - Start Node production server
        """
        env = self._base_env(dev_mode=False)

        # Build assets via litestar assets build
        self._run(self._assets_build_command(), cwd=self.example_dir, env=env)

        # Start Litestar backend on a free port (serves static files in production)
        self.litestar_port = find_free_port()
        litestar_proc, litestar_capture = self._spawn_with_capture(
            self._litestar_run_command(self.litestar_port),
            env=env,
            patterns=[LITESTAR_PORT_PATTERN],
        )
        self._processes.append(litestar_proc)
        self._captures.append(litestar_capture)

        # For SSR examples, also start production Node server
        if self._is_ssr_example():
            ssr_patterns = [VITE_PORT_PATTERN, ASTRO_PORT_PATTERN, NUXT_PORT_PATTERN, LISTENING_PORT_PATTERN]
            ssr_proc, ssr_capture = self._spawn_with_capture(
                self._assets_serve_production_command(),
                env=env,
                patterns=ssr_patterns,
            )
            self._processes.append(ssr_proc)
            self._captures.append(ssr_capture)

        self._dev_mode = False
        logger.info("Started production mode for %s", self.example_name)

    def wait_until_ready(self, timeout: float = 120.0) -> None:
        """Wait until servers are ready.

        Process layout differs by mode:
        - Dev mode: _captures[0] = Vite dev server, _captures[1] = Litestar
        - Prod non-SSR: _captures[0] = Litestar only
        - Prod SSR: _captures[0] = Litestar, _captures[1] = Node production server

        Args:
            timeout: Maximum seconds to wait for servers to be ready.

        Raises:
            TimeoutError: If servers don't become ready within timeout.
            RuntimeError: If any process exits unexpectedly.
        """
        if self._dev_mode:
            # Dev mode: Vite is first, Litestar is second
            vite_capture = self._captures[0]
            litestar_capture = self._captures[1]
            try:
                self.vite_port = vite_capture.wait_for_port(timeout=timeout)
                logger.info("Vite dev server ready on port %d", self.vite_port)
            except TimeoutError:
                self._check_processes_alive()
                raise

            # Also wait for Litestar to finish startup (ensure port is serving)
            try:
                litestar_capture.wait_for_port(timeout=timeout)
            except TimeoutError:
                self._check_processes_alive()
                raise
        elif self._is_ssr_example():
            # Production SSR: Litestar is first, Node server is second
            ssr_capture = self._captures[1]  # SSR server is second in production
            try:
                self.vite_port = ssr_capture.wait_for_port(timeout=timeout)
                logger.info("SSR production server ready on port %d", self.vite_port)
            except TimeoutError:
                self._check_processes_alive()
                raise

            # Ensure SSR server responds before proceeding
            self._verify_http_ready(port=self.vite_port, timeout=30.0)

        self._check_processes_alive()

        # Final health check - verify Litestar responds to HTTP
        self._verify_http_ready(timeout=30.0)

    def _verify_http_ready(self, timeout: float = 30.0, port: int | None = None) -> None:
        """Verify servers respond to HTTP requests.

        Args:
            timeout: Maximum seconds to wait for HTTP response.
            port: Specific port to check (defaults to litestar_port).

        Raises:
            TimeoutError: If server doesn't respond within timeout.
        """
        import httpx

        if port is None:
            port = self.litestar_port

        start = time.monotonic()
        base_url = f"http://127.0.0.1:{port}"

        while time.monotonic() - start < timeout:
            self._check_processes_alive()
            try:
                response = httpx.get(f"{base_url}/", timeout=5.0)
                if response.status_code in (200, 301, 302, 404):
                    logger.info("HTTP ready: %s returned %d", base_url, response.status_code)
                    return
            except httpx.RequestError:
                pass
            time.sleep(0.5)

        raise TimeoutError(f"HTTP health check failed for {base_url}")

    def stop(self) -> None:
        """Terminate all child processes."""
        for proc in self._processes:
            if proc.poll() is None:
                self._terminate_process(proc)
                logger.info("Stopped process pid=%s for %s", proc.pid, self.example_name)
        self._processes.clear()
        self._captures.clear()

    # ---------------------------- Litestar CLI commands ---------------------------- #
    def _assets_serve_command(self) -> list[str]:
        """Command to start frontend dev server: `litestar assets serve`.

        Returns:
            Command arguments list for subprocess.
        """
        return [
            sys.executable,
            "-m",
            "litestar",
            "--app-dir",
            str(self.example_dir),
            "assets",
            "serve",
        ]

    def _assets_serve_production_command(self) -> list[str]:
        """Command to start production Node server: `litestar assets serve --production`.

        Returns:
            Command arguments list for subprocess.
        """
        return [
            sys.executable,
            "-m",
            "litestar",
            "--app-dir",
            str(self.example_dir),
            "assets",
            "serve",
            "--production",
        ]

    def _assets_build_command(self) -> list[str]:
        """Command to build frontend assets: `litestar assets build`.

        Returns:
            Command arguments list for subprocess.
        """
        return [
            sys.executable,
            "-m",
            "litestar",
            "--app-dir",
            str(self.example_dir),
            "assets",
            "build",
        ]

    def _litestar_run_command(self, port: int) -> list[str]:
        """Command to start Litestar backend: `litestar run --port <port>`.

        Args:
            port: The port number to bind the server to.

        Returns:
            Command arguments list for subprocess.
        """
        return [
            sys.executable,
            "-m",
            "litestar",
            "--app-dir",
            str(self.example_dir),
            "run",
            "--port",
            str(port),
        ]

    # ---------------------------- helpers ---------------------------- #
    def _base_env(self, dev_mode: bool) -> dict[str, str]:
        """Build environment variables for subprocesses.

        Args:
            dev_mode: Whether to configure for development mode.

        Returns:
            Environment variables dict for subprocess.
        """
        env = os.environ.copy()
        env.update(
            {
                "VITE_DEV_MODE": "true" if dev_mode else "false",
                # Let Vite/Litestar auto-select ports
                # Don't set VITE_PORT or LITESTAR_PORT
                "HOST": "127.0.0.1",
                # npm cache to avoid permission issues
                "npm_config_cache": str(Path.home() / ".cache" / "npm"),
            }
        )
        # Remove any port env vars that might interfere
        for key in ["VITE_PORT", "LITESTAR_PORT", "PORT", "NITRO_PORT"]:
            env.pop(key, None)
        return env

    def _run(self, cmd: list[str], cwd: Path, env: dict[str, str]) -> None:
        """Run a command synchronously and check for errors.

        Args:
            cmd: Command and arguments to execute.
            cwd: Working directory for the command.
            env: Environment variables for the subprocess.

        Raises:
            RuntimeError: If the command exits with non-zero status.
        """
        logger.info("Running: %s", " ".join(cmd))
        result = subprocess.run(cmd, cwd=cwd, env=env, capture_output=True)
        if result.returncode != 0:
            stdout = result.stdout.decode() if result.stdout else ""
            stderr = result.stderr.decode() if result.stderr else ""
            raise RuntimeError(f"Command failed: {' '.join(cmd)}\nstdout:\n{stdout}\nstderr:\n{stderr}")
        logger.info("Command succeeded: %s", " ".join(cmd))

    def _spawn_with_capture(
        self,
        cmd: list[str],
        env: dict[str, str],
        patterns: list[re.Pattern[str]],
    ) -> tuple[subprocess.Popen[bytes], OutputCapture]:
        """Spawn a process and capture its output to extract port.

        Args:
            cmd: Command and arguments to execute.
            env: Environment variables for the subprocess.
            patterns: Regex patterns to detect port from output.

        Returns:
            Tuple of (subprocess handle, output capture instance).
        """
        logger.info("Spawning: %s", " ".join(cmd))
        proc = subprocess.Popen(
            cmd,
            cwd=self.example_dir,
            env=env,
            start_new_session=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        RUNNING_PROCS.append(proc)

        capture = OutputCapture(proc.stdout, patterns)
        capture.start()

        return proc, capture

    def _terminate_process(self, proc: subprocess.Popen[bytes]) -> None:
        """Terminate a process and its children."""
        try:
            if proc.poll() is None:
                # POSIX: send SIGTERM to process group to kill child processes too
                if sys.platform != "win32":
                    os.killpg(proc.pid, signal.SIGTERM)
                else:
                    proc.terminate()
                proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            # Force kill if graceful termination fails
            if sys.platform != "win32":
                os.killpg(proc.pid, signal.SIGKILL)
            else:
                proc.kill()
        finally:
            if proc.poll() is None:
                proc.kill()
            if proc in RUNNING_PROCS:
                RUNNING_PROCS.remove(proc)

    def _check_processes_alive(self) -> None:
        """Check that all spawned processes are still running.

        Raises:
            RuntimeError: If any process has exited unexpectedly.
        """
        for i, proc in enumerate(self._processes):
            if proc.poll() is not None:
                output = self._captures[i].get_output() if i < len(self._captures) else ""
                raise RuntimeError(
                    f"Process for {self.example_name} exited early with code {proc.returncode}\nOutput:\n{output}"
                )

    def _is_ssr_example(self) -> bool:
        """Check if this is an SSR example (Nuxt, SvelteKit, Astro).

        Returns:
            True if the example uses SSR framework.
        """
        return self.example_name in SSR_EXAMPLES

    def _is_cli_example(self) -> bool:
        """Check if this is a CLI-based example (Angular CLI).

        Returns:
            True if the example uses a CLI-based build tool.
        """
        return self.example_name in CLI_EXAMPLES
