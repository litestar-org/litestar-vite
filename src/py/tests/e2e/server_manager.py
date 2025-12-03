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
import shutil
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

RUNNING_PROCS: list[subprocess.Popen[bytes]] = []
# Track examples that have already installed frontend deps to avoid repeated installs
INSTALLED_EXAMPLES: set[str] = set()
# Track plugin build to avoid repeated root builds
PLUGIN_BUILT: bool = False

# Patterns to extract ports from output
# Vite/SvelteKit output: "Local:   http://localhost:5173/" (may be prefixed by Unicode arrow)
VITE_PORT_PATTERN = re.compile(r"Local:\s+https?://(?:localhost|127\.0\.0\.1):(\d+)")
# SvelteKit dev output sometimes prints with ANSI + padding, capture any host:port mention
SVELTEKIT_PORT_PATTERN = re.compile(r"https?://(?:localhost|127\.0\.0\.1):(\d+)")
# Extremely permissive host:port fallback (handles 0.0.0.0 and ANSI noise)
ANY_HOST_PORT_PATTERN = re.compile(r"https?://[\w\.-]+:(\d+)")
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

    def __init__(
        self,
        stream: "IO[bytes] | None",
        patterns: list[re.Pattern[str]],
        process: "subprocess.Popen[bytes] | None" = None,
    ) -> None:
        self.stream = stream
        self.patterns = patterns
        self.process = process  # Reference to check if process is still alive
        self.port: int | None = None
        self.output_lines: list[str] = []
        self._thread: Thread | None = None
        self._stream_closed = False

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
        try:
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
        except Exception as e:
            logger.warning("Output capture error: %s", e)
        finally:
            self._stream_closed = True

    def wait_for_port(self, timeout: float = 60.0) -> int:
        """Wait until port is detected or timeout.

        Args:
            timeout: Maximum seconds to wait for port detection.

        Returns:
            The detected port number.

        Raises:
            TimeoutError: If port is not detected within the timeout period.
            RuntimeError: If the process exits before port is detected.
        """
        start = time.monotonic()
        last_line_count = 0

        while time.monotonic() - start < timeout:
            if self.port is not None:
                return self.port

            # Check if process has exited (fail fast)
            if self.process is not None and self.process.poll() is not None:
                output = "\n".join(self.output_lines[-30:])
                raise RuntimeError(
                    f"Server process exited with code {self.process.returncode} before port was detected.\n"
                    f"Output:\n{output}"
                )

            # Check if stream closed without port detection
            if self._stream_closed and self.port is None:
                output = "\n".join(self.output_lines[-30:])
                raise RuntimeError(f"Output stream closed without detecting port.\nOutput:\n{output}")

            # Log progress every 10 seconds if no new output
            current_lines = len(self.output_lines)
            elapsed = time.monotonic() - start
            if elapsed > 10 and current_lines == last_line_count and int(elapsed) % 10 == 0:
                logger.warning(
                    "Waiting for port... %.0fs elapsed, %d lines captured, no new output",
                    elapsed,
                    current_lines,
                )
            last_line_count = current_lines

            time.sleep(0.1)

        output = "\n".join(self.output_lines[-30:])
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

        # Ensure plugin is built and deps installed once per example
        self._ensure_plugin_built(env)
        self._ensure_assets_installed(env)

        # Start frontend dev server via litestar assets serve
        vite_patterns = [
            VITE_PORT_PATTERN,
            ASTRO_PORT_PATTERN,
            NUXT_PORT_PATTERN,
            LISTENING_PORT_PATTERN,
            GENERIC_HOST_PATTERN,
            SVELTEKIT_PORT_PATTERN,
            ANY_HOST_PORT_PATTERN,
        ]
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

        # Ensure plugin is built and deps installed once per example
        self._ensure_plugin_built(env)
        self._ensure_assets_installed(env)

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
            # Verify build artifacts exist before attempting to serve
            self._verify_ssr_build()

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

    def wait_until_ready(self, timeout: float = 60.0) -> None:
        """Wait until servers are ready.

        Process layout differs by mode:
        - Dev mode: _captures[0] = Vite dev server, _captures[1] = Litestar
        - Prod non-SSR: _captures[0] = Litestar only
        - Prod SSR: _captures[0] = Litestar, _captures[1] = Node production server

        Args:
            timeout: Maximum seconds to wait for servers to be ready.

        Raises:
            TimeoutError: If servers don't become ready within timeout.
        """
        if self._dev_mode:
            # Dev mode: Vite is first, Litestar is second
            vite_capture = self._captures[0]
            litestar_capture = self._captures[1]
            try:
                self.vite_port = vite_capture.wait_for_port(timeout=timeout)
                logger.info("Vite dev server ready on port %d", self.vite_port)
            except TimeoutError:
                # For SSR frameworks, proceed as long as Litestar comes up; port detection can be flaky with ANSI output
                self._check_processes_alive()
                logger.warning("Vite port not detected within timeout; continuing with proxy health check")
                self.vite_port = self._infer_vite_port(vite_capture)

            # Always wait for Litestar to finish startup (ensure port is serving)
            try:
                litestar_capture.wait_for_port(timeout=timeout)
            except TimeoutError:
                self._check_processes_alive()
                raise

            # If Vite port is still unknown (e.g., SvelteKit ANSI output), attempt to extract from stored lines
            if self.vite_port is None:
                self.vite_port = self._infer_vite_port(vite_capture)
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
            self._verify_http_ready(port=self.vite_port, timeout=timeout)

        self._check_processes_alive()

        # Final health check - verify Litestar responds to HTTP
        self._verify_http_ready(timeout=timeout)

    def _verify_http_ready(self, timeout: float = 45.0, port: int | None = None) -> None:
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

    def _assets_install_command(self) -> list[str]:
        """Command to install frontend deps: `litestar assets install`."""

        return [
            sys.executable,
            "-m",
            "litestar",
            "--app-dir",
            str(self.example_dir),
            "assets",
            "install",
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
                # Bypass CI environment check in Vite plugin for E2E tests
                # We intentionally test dev mode in CI to validate the full experience
                "LITESTAR_BYPASS_ENV_CHECK": "1",
                # Force unbuffered output for reliable port detection in CI
                "PYTHONUNBUFFERED": "1",
                # Disable interactive features that might buffer output
                "CI": "true",
                # Force color output to be consistent with expected patterns
                "FORCE_COLOR": "1",
                # Node.js: force immediate stdout flushing
                "NODE_OPTIONS": "--no-warnings",
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

    def _ensure_plugin_built(self, env: dict[str, str]) -> None:
        """Build root JS plugin once so examples can resolve file:../.. dependency."""

        global PLUGIN_BUILT
        if PLUGIN_BUILT:
            return

        repo_root = EXAMPLES_DIR.parent
        dist_js = repo_root / "dist" / "js" / "index.js"

        # Install JS deps if missing
        node_modules = repo_root / "node_modules"
        if not node_modules.exists():
            install_cmd = ["npm", "ci"] if (repo_root / "package-lock.json").exists() else ["npm", "install"]
            logger.info("Installing root JS deps for plugin build (%s)", " ".join(install_cmd))
            self._run(install_cmd, cwd=repo_root, env=env)

        if not dist_js.exists():
            logger.info("Building root plugin dist/js for examples")
            build_cmd = ["npm", "run", "build"]
            self._run(build_cmd, cwd=repo_root, env=env)

        PLUGIN_BUILT = True

    def _ensure_assets_installed(self, env: dict[str, str]) -> None:
        """Run `litestar assets install` once per example to fetch frontend deps."""

        if self.example_name in INSTALLED_EXAMPLES:
            return
        install_cmd = self._assets_install_command()
        logger.info("Installing frontend deps for %s", self.example_name)
        self._run(install_cmd, cwd=self.example_dir, env=env)
        INSTALLED_EXAMPLES.add(self.example_name)

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
        # Use stdbuf to force line-buffered output if available (Linux)
        # This helps ensure Vite/Node output is immediately available
        stdbuf_cmd = ["stdbuf", "-oL", "-eL", *cmd] if shutil.which("stdbuf") else cmd
        proc = subprocess.Popen(
            stdbuf_cmd,
            cwd=self.example_dir,
            env=env,
            start_new_session=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            bufsize=0,  # Unbuffered
        )
        RUNNING_PROCS.append(proc)

        # Pass process reference so OutputCapture can detect early exits
        capture = OutputCapture(proc.stdout, patterns, process=proc)
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

    def _verify_ssr_build(self) -> None:
        """Verify SSR build artifacts exist before serving.

        Raises:
            RuntimeError: If required build artifacts are missing.
        """
        # Map SSR examples to their expected build output directories
        build_dirs: dict[str, list[str]] = {
            "sveltekit": ["build"],
            "nuxt": [".output", ".nuxt"],
            "astro": ["dist"],
        }

        expected_dirs = build_dirs.get(self.example_name, [])
        if not expected_dirs:
            logger.warning("No build verification configured for SSR example: %s", self.example_name)
            return

        for dir_name in expected_dirs:
            build_path = self.example_dir / dir_name
            if build_path.exists():
                logger.info("Build artifact verified: %s", build_path)
                return

        # None of the expected directories exist
        raise RuntimeError(
            f"SSR build artifacts missing for {self.example_name}. "
            f"Expected one of: {expected_dirs} in {self.example_dir}. "
            "The 'litestar assets build' command may have failed silently."
        )

    def _infer_vite_port(self, capture: OutputCapture) -> int | None:
        """Infer Vite port from captured output, skipping backend ports."""

        backend_port = self.litestar_port
        for line in reversed(capture.output_lines):
            if "proxying /api" in line or "litestar" in line.lower():
                continue
            match = ANY_HOST_PORT_PATTERN.search(line)
            if match:
                port_val = int(match.group(1))
                if port_val != backend_port:
                    logger.info("Vite port inferred from output: %d", port_val)
                    return port_val
        return None
