"""Pytest fixtures for example E2E suite."""

import os
from collections.abc import Generator

import pytest

from .server_manager import EXAMPLES_DIR, RUNNING_PROCS, ExampleServer

# Default timeout for E2E tests (seconds per test)
# Can be overridden with E2E_TEST_TIMEOUT env var or @pytest.mark.timeout(X)
E2E_TEST_TIMEOUT = int(os.environ.get("E2E_TEST_TIMEOUT", "60"))

# Examples that require special handling and should be skipped in the standard E2E suite
SKIP_EXAMPLES: set[str] = set()


def pytest_configure(config: pytest.Config) -> None:
    """Register custom markers."""
    config.addinivalue_line("markers", "e2e: end-to-end example tests")
    config.addinivalue_line("markers", "spa: SPA examples")
    config.addinivalue_line("markers", "template: Template examples")
    config.addinivalue_line("markers", "inertia: Inertia examples")
    config.addinivalue_line("markers", "ssr: SSR examples")
    config.addinivalue_line("markers", "cli: CLI-based examples")
    config.addinivalue_line("markers", "timeout: set test timeout in seconds")


def _get_available_examples() -> list[str]:
    """Discover available example names.

    Returns:
        list[str]: Names of examples available for E2E testing.
    """
    examples: list[str] = []
    if EXAMPLES_DIR.exists():
        examples.extend(
            child.name
            for child in sorted(EXAMPLES_DIR.iterdir())
            if child.is_dir() and (child / "app.py").exists() and child.name not in SKIP_EXAMPLES
        )
    return examples


# Dynamically discover available examples
EXAMPLE_NAMES = _get_available_examples()
EXAMPLE_PARAMS = [pytest.param(name, marks=pytest.mark.xdist_group(name)) for name in EXAMPLE_NAMES]


@pytest.fixture(scope="session", autouse=True)
def _cleanup_processes_after_session() -> Generator[None, None, None]:
    """Ensure all processes are cleaned up after the test session.

    Yields:
        None: Allows pytest to run session-scoped cleanup after tests complete.
    """
    yield

    # Stop all cached servers
    from .conftest import _dev_servers, _prod_servers

    for server in list(_dev_servers.values()):
        try:
            server.stop()
        except Exception:
            pass
    _dev_servers.clear()

    for server in list(_prod_servers.values()):
        try:
            server.stop()
        except Exception:
            pass
    _prod_servers.clear()

    # Clean up any remaining processes
    for proc in list(RUNNING_PROCS):
        try:
            if proc.poll() is None:
                proc.terminate()
                proc.wait(timeout=5)
        except Exception:
            try:
                proc.kill()
            except Exception:
                pass


@pytest.fixture(autouse=True)
def _cleanup_processes_after_test() -> Generator[None, None, None]:
    """Ensure all processes are cleaned up after each test.

    Yields:
        None: Allows pytest to run test-scoped cleanup after each test.
    """
    import signal
    import subprocess
    import time

    from .server_manager import EXAMPLE_PORTS

    yield

    # First, terminate processes we spawned
    for proc in list(RUNNING_PROCS):
        try:
            if proc.poll() is None:
                # Kill the entire process group to ensure child processes (npm, node, vite) are killed
                try:
                    os.killpg(proc.pid, signal.SIGTERM)
                except (ProcessLookupError, PermissionError):
                    proc.terminate()
                proc.wait(timeout=5)
        except Exception:
            try:
                # Force kill if graceful termination fails
                try:
                    os.killpg(proc.pid, signal.SIGKILL)
                except (ProcessLookupError, PermissionError):
                    proc.kill()
            except Exception:
                pass
        finally:
            if proc in RUNNING_PROCS:
                RUNNING_PROCS.remove(proc)

    # Wait a moment for ports to be released
    time.sleep(0.5)

    # Kill any remaining processes on our fixed ports (handles orphaned node/vite processes)
    for port in EXAMPLE_PORTS.values():
        try:
            # Use lsof to find PIDs using the port and kill them
            result = subprocess.run(
                ["lsof", "-t", "-i", f":{port}"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.stdout.strip():
                for pid_str in result.stdout.strip().split("\n"):
                    try:
                        pid = int(pid_str.strip())
                        os.kill(pid, signal.SIGKILL)
                    except (ValueError, ProcessLookupError, PermissionError):
                        pass
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass


@pytest.fixture(params=EXAMPLE_PARAMS)
def example_name(request: pytest.FixtureRequest) -> str:
    """Provide example name from parametrized list.

    Returns:
        str: Example name for the current test parameter.
    """
    return str(request.param)


@pytest.fixture
def example_server(example_name: str) -> Generator[ExampleServer, None, None]:
    """Create an ExampleServer for the given example.

    Yields:
        ExampleServer: Server instance for the requested example.
    """
    server = ExampleServer(example_name)
    yield server
    server.stop()


# Cache running servers to avoid TIME_WAIT port conflicts between tests
_dev_servers: dict[str, ExampleServer] = {}
_prod_servers: dict[str, ExampleServer] = {}


@pytest.fixture
def dev_mode_server(example_name: str) -> Generator[ExampleServer, None, None]:
    """Start example in dev mode and wait until ready.

    Uses `litestar assets serve` + `litestar run`.
    Server is cached per example to avoid port conflicts between tests.

    Yields:
        ExampleServer: Running server in development mode.
    """
    # Reuse existing server if already running for this example
    if example_name in _dev_servers:
        server = _dev_servers[example_name]
        # Verify server is still healthy
        try:
            server._check_processes_alive()
            yield server
            return
        except RuntimeError:
            # Server died, remove from cache and create new one
            del _dev_servers[example_name]

    server = ExampleServer(example_name)
    server.start_dev_mode()
    server.wait_until_ready(timeout=float(E2E_TEST_TIMEOUT))
    _dev_servers[example_name] = server
    yield server
    # Don't stop - server cleanup happens in session fixture


@pytest.fixture
def production_server(example_name: str) -> Generator[ExampleServer, None, None]:
    """Start example in production mode and wait until ready.

    Uses `litestar assets build` + `litestar run`.
    For SSR: also uses `litestar assets serve --production`.
    Server is cached per example to avoid port conflicts between tests.

    Yields:
        ExampleServer: Running server in production mode.
    """
    # Reuse existing server if already running for this example
    if example_name in _prod_servers:
        server = _prod_servers[example_name]
        # Verify server is still healthy
        try:
            server._check_processes_alive()
            yield server
            return
        except RuntimeError:
            # Server died, remove from cache and create new one
            del _prod_servers[example_name]

    server = ExampleServer(example_name)
    server.start_production_mode()
    server.wait_until_ready(timeout=float(E2E_TEST_TIMEOUT))
    _prod_servers[example_name] = server
    yield server
    # Don't stop - server cleanup happens in session fixture
