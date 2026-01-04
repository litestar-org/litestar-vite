"""Process manager for example applications.

This module manages the lifecycle of example applications for E2E testing.
All commands use the Litestar CLI (`litestar assets`) to ensure we test
the real developer experience, not just that npm works directly.

Key design decisions:
- Each example has a fixed Vite port configured in app.py (RuntimeConfig.port)
- This eliminates port detection from output (stdout buffering in CI is unreliable)
- Litestar ports are dynamically assigned using find_free_port()
- HTTP polling verifies server readiness instead of output parsing

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

# SSR examples that run their own Node server in BOTH dev AND production
# These need `litestar assets serve --production` to start the Node production server
SSR_EXAMPLES: set[str] = {"nuxt", "sveltekit"}

# SSG (Static Site Generation) examples that run their own dev server but NOT in production
# In production, they build static files served directly by Litestar (no Node server needed)
SSG_EXAMPLES: set[str] = {"astro"}

# CLI examples use their own build tools (Angular CLI)
EXTERNAL_EXAMPLES: set[str] = {"angular-cli"}

# Fixed Vite ports configured in each example's app.py RuntimeConfig.port
# These must match the ports in examples/*/app.py
# This avoids output parsing which is unreliable in CI due to stdout buffering
EXAMPLE_PORTS: dict[str, int] = {
    "react": 5001,
    "react-inertia": 5002,
    "react-inertia-jinja": 5003,
    "vue": 5011,
    "vue-inertia": 5012,
    "vue-inertia-jinja": 5013,
    "svelte": 5021,
    "sveltekit": 5022,
    "angular": 5031,
    "angular-cli": 5032,
    "nuxt": 5041,
    "astro": 5051,
    "jinja-htmx": 5061,
}

# External dev server target ports for CLI examples
# These are the ports where external dev servers (not Vite) actually listen
# For angular-cli: Angular CLI uses port 4200 by default, not the Litestar proxy port
EXTERNAL_TARGET_PORTS: dict[str, int] = {
    "angular-cli": 4200  # Angular CLI always uses port 4200
}

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
                    "Waiting for port... %.0fs elapsed, %d lines captured, no new output", elapsed, current_lines
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
    def _ensure_port_free(self) -> None:
        """Ensure the configured Vite port is free before starting.

        Kills any remaining processes using the port.
        """
        ports_to_free: list[int] = []

        vite_port = EXAMPLE_PORTS.get(self.example_name)
        if vite_port is not None:
            ports_to_free.append(vite_port)

        # External examples proxy to a separate dev server port (e.g. Angular CLI 4200)
        external_target_port = EXTERNAL_TARGET_PORTS.get(self.example_name)
        if external_target_port is not None:
            ports_to_free.append(external_target_port)

        if not ports_to_free:
            return

        try:
            for port in ports_to_free:
                result = subprocess.run(["lsof", "-t", "-i", f":{port}"], capture_output=True, text=True, timeout=5)
                if result.stdout.strip():
                    for pid_str in result.stdout.strip().split("\n"):
                        try:
                            pid = int(pid_str.strip())
                            os.kill(pid, signal.SIGKILL)
                            logger.warning("Killed orphaned process %d using port %d", pid, port)
                        except (ValueError, ProcessLookupError, PermissionError):
                            pass
                    # Wait for port to be released
                    time.sleep(0.3)
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass

    def start_dev_mode(self) -> None:
        """Start dev servers using Litestar CLI.

        For ALL examples in dev mode: just `litestar run`
        The plugin auto-starts Vite via start_dev_server=True (default).
        """
        # Ensure the configured port is free before starting
        self._ensure_port_free()

        env = self._base_env(dev_mode=True)

        # Ensure plugin is built and deps installed once per example
        self._ensure_plugin_built(env)
        self._ensure_assets_installed(env)

        # Start Litestar backend on a free port
        # The plugin auto-starts Vite dev server via start_dev_server=True
        self.litestar_port = find_free_port()
        litestar_proc, litestar_capture = self._spawn_with_capture(
            self._litestar_run_command(self.litestar_port), env=env, patterns=[LITESTAR_PORT_PATTERN]
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
        3. For SSR only: `litestar assets serve --production` - Start Node production server

        Note: SSG examples (Astro) do NOT need a production Node server - Litestar
        serves the static files directly from the build output.

        Raises:
            ValueError: If example port configuration is missing.
        """
        # Ensure the configured port is free before starting (for SSR production server)
        if self._is_ssr_example():
            self._ensure_port_free()

        env = self._base_env(dev_mode=False)

        # Ensure plugin is built and deps installed once per example
        self._ensure_plugin_built(env)
        self._ensure_assets_installed(env)

        # Build assets via litestar assets build
        self._run(self._assets_build_command(), cwd=self.example_dir, env=env)

        # Start Litestar backend on a free port (serves static files in production)
        self.litestar_port = find_free_port()
        litestar_proc, litestar_capture = self._spawn_with_capture(
            self._litestar_run_command(self.litestar_port), env=env, patterns=[LITESTAR_PORT_PATTERN]
        )
        self._processes.append(litestar_proc)
        self._captures.append(litestar_capture)

        # For SSR examples, also start production Node server
        # SSG examples (Astro) do NOT need this - Litestar serves static files directly
        if self._is_ssr_example():
            # Verify build artifacts exist before attempting to serve
            self._verify_ssr_build()

            # Get the known Vite port for this example (needed before wait_until_ready sets it)
            self.vite_port = EXAMPLE_PORTS.get(self.example_name)
            if self.vite_port is None:
                raise ValueError(f"No port configured for SSR example: {self.example_name}")

            # Set VITE_PORT for SSR production server
            # The Litestar plugin will use this to configure the Nitro/SSR server port
            ssr_env = env.copy()
            ssr_env["VITE_PORT"] = str(self.vite_port)
            # Nitro specifically uses NITRO_PORT and NITRO_HOST
            ssr_env["NITRO_PORT"] = str(self.vite_port)
            ssr_env["NITRO_HOST"] = "127.0.0.1"
            # Some frameworks use PORT/HOST as fallback
            ssr_env["PORT"] = str(self.vite_port)
            ssr_env["HOST"] = "127.0.0.1"
            ssr_patterns = [VITE_PORT_PATTERN, NUXT_PORT_PATTERN, LISTENING_PORT_PATTERN]
            ssr_proc, ssr_capture = self._spawn_with_capture(
                self._assets_serve_production_command(), env=ssr_env, patterns=ssr_patterns
            )
            self._processes.append(ssr_proc)
            self._captures.append(ssr_capture)
        elif self._is_ssg_example():
            # SSG examples just need build verification - no production server needed
            self._verify_ssr_build()
            logger.info("SSG build verified for %s - Litestar will serve static files", self.example_name)

        self._dev_mode = False
        logger.info("Started production mode for %s", self.example_name)

    def wait_until_ready(self, timeout: float = 60.0) -> None:
        """Wait until servers are ready using HTTP polling.

        Uses fixed ports from EXAMPLE_PORTS instead of parsing process output.
        This avoids stdout buffering issues in CI environments.

        Args:
            timeout: Maximum seconds to wait for servers to be ready.

        Raises:
            ValueError: If example port configuration is missing.
        """
        # Get the known Vite port for this example
        self.vite_port = EXAMPLE_PORTS.get(self.example_name)
        if self.vite_port is None:
            raise ValueError(f"No port configured for example: {self.example_name}")

        logger.info("Waiting for servers: Vite port=%d, Litestar port=%d", self.vite_port, self.litestar_port)

        start = time.monotonic()

        # Wait for Litestar backend to be ready
        # For SSR/SSG examples, check /api/summary instead of / because:
        # - The homepage (/) is proxied to the SSR dev server
        # - The SSR dev server takes time to start and returns 500 initially
        # - API routes (/api/*) are handled directly by Litestar without proxy
        if self._dev_mode and (
            self.example_name in SSR_EXAMPLES
            or self.example_name in SSG_EXAMPLES
            or self.example_name in EXTERNAL_EXAMPLES
        ):
            self._verify_http_ready(port=self.litestar_port, timeout=timeout, health_path="/api/summary")
        else:
            self._verify_http_ready(port=self.litestar_port, timeout=timeout)
        logger.info("Litestar backend ready on port %d", self.litestar_port)

        # Calculate remaining timeout after Litestar check
        elapsed = time.monotonic() - start
        remaining_timeout = max(timeout - elapsed, 30.0)  # At least 30s for frontend
        logger.info("Remaining timeout for frontend: %.1fs", remaining_timeout)

        if self._dev_mode:
            # In dev mode, also verify the frontend dev server is responding
            if self.example_name in EXTERNAL_EXAMPLES:
                # CLI examples (angular-cli) use external dev servers that take time to build
                # We check via Litestar proxy (which returns 503 until external server is ready)
                # Don't check the external port directly - go through the Litestar proxy
                self._verify_proxy_ready(timeout=remaining_timeout)
                logger.info("External dev server ready (via Litestar proxy)")
            elif self.example_name in SSR_EXAMPLES or self.example_name in SSG_EXAMPLES:
                # SSR/SSG examples (nuxt, sveltekit, astro) use dynamic ports via hotfile
                # Verify via Litestar proxy - the proxy returns 503 until SSR server is ready
                self._verify_proxy_ready(timeout=remaining_timeout)
                logger.info("SSR/SSG dev server ready (via Litestar proxy)")
            else:
                # Standard Vite examples - check the configured port
                self._verify_http_ready(port=self.vite_port, timeout=timeout)
                logger.info("Vite dev server ready on port %d", self.vite_port)
        elif self._is_ssr_example():
            # In production SSR (not SSG!), verify the Node server is responding
            # SSG examples (astro) don't run a production server - Litestar serves static files
            self._verify_http_ready(port=self.vite_port, timeout=timeout)
            logger.info("SSR production server ready on port %d", self.vite_port)
        # Note: SSG examples in production don't need additional checks - Litestar serves static files

        self._check_processes_alive()

    def _verify_http_ready(self, timeout: float = 45.0, port: int | None = None, health_path: str = "/") -> None:
        """Verify servers respond to HTTP requests.

        Args:
            timeout: Maximum seconds to wait for HTTP response.
            port: Specific port to check (defaults to litestar_port).
            health_path: Path to check for health (default "/", use "/api/summary" for SSR/SSG).

        Raises:
            TimeoutError: If server doesn't respond within timeout.
        """
        import httpx

        if port is None:
            port = self.litestar_port

        start = time.monotonic()
        base_url = f"http://127.0.0.1:{port}"
        health_url = f"{base_url}{health_path}"

        last_status = None
        last_error = None
        while time.monotonic() - start < timeout:
            self._check_processes_alive()
            try:
                response = httpx.get(health_url, timeout=5.0)
                last_status = response.status_code
                # Accept any response that's not a connection error
                # SSR frameworks may return 500/503 while building, but that means server is up
                if response.status_code < 500:
                    logger.info("HTTP ready: %s returned %d", health_url, response.status_code)
                    return
                # 5xx means server is up but SSR framework is still building - keep waiting
                logger.debug("HTTP waiting: %s returned %d (SSR building)", health_url, response.status_code)
            except httpx.RequestError as e:
                last_error = str(e)
            time.sleep(0.5)

        msg = f"HTTP health check failed for {base_url}"
        if last_status:
            msg += f" (last status: {last_status})"
        if last_error:
            msg += f" (last error: {last_error})"

        # Include captured server output for debugging
        if self._captures:
            for i, capture in enumerate(self._captures):
                output = capture.get_output()
                if output:
                    # Show last 30 lines of output
                    lines = output.split("\n")[-30:]
                    msg += f"\n\n=== Server output (capture {i + 1}) ===\n{chr(10).join(lines)}"
        raise TimeoutError(msg)

    def _verify_proxy_ready(self, timeout: float = 60.0) -> None:
        """Verify external dev server is ready via Litestar proxy.

        For CLI examples (Angular CLI), the external server takes time to build.
        We check via Litestar's proxy which returns 503 while building, then 200 when ready.

        Args:
            timeout: Maximum seconds to wait for proxy to return 200.

        Raises:
            TimeoutError: If proxy doesn't return 200 within timeout.
        """
        import httpx

        # Leave a small buffer so we raise our own TimeoutError with captured logs
        # before pytest-timeout interrupts the test mid-sleep.
        timeout = max(timeout - 5.0, 1.0)

        start = time.monotonic()
        base_url = f"http://127.0.0.1:{self.litestar_port}"
        last_status = None
        last_error = None

        while time.monotonic() - start < timeout:
            self._check_processes_alive()
            try:
                # Check root path through Litestar proxy
                response = httpx.get(f"{base_url}/", timeout=5.0)
                last_status = response.status_code
                if response.status_code < 500:
                    # Any non-5xx status means the dev server is responding
                    logger.info("Proxy ready: %s returned %d", base_url, response.status_code)
                    return
                # 5xx status (500, 502, 503) means dev server is still building
                logger.debug("Proxy building: %s returned %d", base_url, response.status_code)
            except httpx.RequestError as e:
                last_error = str(e)
                logger.debug("Proxy request error: %s", e)
            time.sleep(0.5)

        msg = f"Proxy health check failed for {base_url}."
        if last_status is not None:
            msg += f" Last status: {last_status}."
        if last_error:
            msg += f" Last error: {last_error}."

        # Include captured server output for debugging
        if self._captures:
            for i, capture in enumerate(self._captures):
                output = capture.get_output()
                if output:
                    lines = output.split("\n")[-30:]
                    msg += f"\n\n=== Server output (capture {i + 1}) ===\n{chr(10).join(lines)}"

        raise TimeoutError(msg)

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
        return [sys.executable, "-m", "litestar", "--app-dir", str(self.example_dir), "assets", "serve"]

    def _assets_install_command(self) -> list[str]:
        """Command to install frontend deps: `litestar assets install`.

        Returns:
            Command arguments list for subprocess.
        """
        return [sys.executable, "-m", "litestar", "--app-dir", str(self.example_dir), "assets", "install"]

    def _assets_serve_production_command(self) -> list[str]:
        """Command to start production Node server: `litestar assets serve --production`.

        Returns:
            Command arguments list for subprocess.
        """
        return [sys.executable, "-m", "litestar", "--app-dir", str(self.example_dir), "assets", "serve", "--production"]

    def _assets_build_command(self) -> list[str]:
        """Command to build frontend assets: `litestar assets build`.

        Returns:
            Command arguments list for subprocess.
        """
        return [sys.executable, "-m", "litestar", "--app-dir", str(self.example_dir), "assets", "build"]

    def _litestar_run_command(self, port: int) -> list[str]:
        """Command to start Litestar backend: `litestar run --port <port>`.

        Args:
            port: The port number to bind the server to.

        Returns:
            Command arguments list for subprocess.
        """
        return [sys.executable, "-m", "litestar", "--app-dir", str(self.example_dir), "run", "--port", str(port)]

    # ---------------------------- helpers ---------------------------- #
    def _base_env(self, dev_mode: bool) -> dict[str, str]:
        """Build environment variables for subprocesses.

        Args:
            dev_mode: Whether to configure for development mode.

        Returns:
            Environment variables dict for subprocess.
        """
        env = os.environ.copy()

        # CRITICAL: Remove all Vite/Litestar-related env vars to ensure clean isolation.
        # The plugin's set_environment() uses setdefault() which does NOT override existing
        # values. If the parent process has stale VITE_PORT etc., subprocesses would inherit
        # the wrong ports. By removing these vars, we ensure RuntimeConfig.port from each
        # example's app.py is used correctly.
        for key in list(env.keys()):
            if key.startswith(("VITE_", "LITESTAR_", "NUXT_", "NITRO_")):
                del env[key]
        # Also remove PORT which some frameworks use as fallback
        env.pop("PORT", None)

        env.update({
            "VITE_DEV_MODE": "true" if dev_mode else "false",
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
        })
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
        dist_shared_constants = repo_root / "dist" / "js" / "shared" / "constants.js"
        dist_shared_network = repo_root / "dist" / "js" / "shared" / "network.js"

        # Install JS deps if missing
        node_modules = repo_root / "node_modules"
        if not node_modules.exists():
            install_cmd = ["npm", "ci"] if (repo_root / "package-lock.json").exists() else ["npm", "install"]
            logger.info("Installing root JS deps for plugin build (%s)", " ".join(install_cmd))
            self._run(install_cmd, cwd=repo_root, env=env)

        if not dist_js.exists() or not dist_shared_constants.exists() or not dist_shared_network.exists():
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
        self, cmd: list[str], env: dict[str, str], patterns: list[re.Pattern[str]]
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
        # NOTE: We intentionally do NOT use stdbuf here.
        # While stdbuf helps with line-buffered output, it can interfere with stdin
        # handling for Node.js/Nitro servers. Nitro detects stdin EOF and exits
        # gracefully to prevent zombie processes. When stdbuf wraps the command,
        # stdin handling can become unreliable in some CI environments.
        # The trade-off (potentially buffered output) is acceptable since we poll
        # for readiness via HTTP rather than parsing output.
        proc = subprocess.Popen(
            cmd,
            cwd=self.example_dir,
            env=env,
            start_new_session=True,
            stdin=subprocess.PIPE,  # Keep stdin open - prevents Nitro from exiting on stdin EOF
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
        """Check if this is an SSR example that needs a production Node server.

        SSR examples (Nuxt, SvelteKit) run a Node server in production.
        SSG examples (Astro) do NOT - they generate static files served by Litestar.

        Returns:
            True if the example needs a production Node server.
        """
        return self.example_name in SSR_EXAMPLES

    def _is_ssg_example(self) -> bool:
        """Check if this is an SSG (Static Site Generation) example.

        SSG examples (Astro) generate static files at build time.
        In dev mode, they run a dev server (like SSR).
        In production, Litestar serves the static files directly (no Node server).

        Returns:
            True if the example uses SSG.
        """
        return self.example_name in SSG_EXAMPLES

    def _is_cli_example(self) -> bool:
        """Check if this is a CLI-based example (Angular CLI).

        Returns:
            True if the example uses a CLI-based build tool.
        """
        return self.example_name in EXTERNAL_EXAMPLES

    def _verify_ssr_build(self) -> None:
        """Verify SSR/SSG build artifacts exist before serving.

        Raises:
            RuntimeError: If required build artifacts are missing.
        """
        # Map SSR/SSG examples to their expected build output directories
        build_dirs: dict[str, list[str]] = {
            "sveltekit": ["build"],
            "nuxt": [".output", ".nuxt"],
            "astro": ["dist"],  # SSG - static files
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
