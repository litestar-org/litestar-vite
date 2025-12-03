"""Pytest fixtures for example E2E suite."""

from collections.abc import Generator

import pytest

from .server_manager import EXAMPLES_DIR, RUNNING_PROCS, ExampleServer

# Default timeout for E2E tests (60 seconds per test)
# Can be overridden with @pytest.mark.timeout(X) on individual tests
E2E_TEST_TIMEOUT = 60

# =============================================================================
# TODO(SSR-E2E): Re-enable SSR examples once port detection is stabilized
# =============================================================================
# The following SSR examples are temporarily disabled due to flaky port detection:
# - astro, nuxt, sveltekit: These SSR frameworks have complex Node server lifecycles
#   with varying output formats that make reliable port detection challenging.
#
# To re-enable: Remove from SKIP_EXAMPLES and improve OutputCapture patterns in
# server_manager.py to handle all SSR framework output variations.
#
# Tracked issue: https://github.com/litestar-org/litestar-vite/issues/XXX
# =============================================================================

# Examples that require special handling and should be skipped in the standard E2E suite
SKIP_EXAMPLES: set[str] = {
    # TODO(SSR-E2E): Re-enable once port detection is stabilized
    "astro",
    "nuxt",
    "sveltekit",
}


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
    yield
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


@pytest.fixture
def dev_mode_server(example_server: ExampleServer) -> Generator[ExampleServer, None, None]:
    """Start example in dev mode and wait until ready.

    Uses `litestar assets serve` + `litestar run`.
    Ports are auto-selected and parsed from output.

    Yields:
        ExampleServer: Running server in development mode.
    """
    example_server.start_dev_mode()
    example_server.wait_until_ready()
    yield example_server
    example_server.stop()


@pytest.fixture
def production_server(example_server: ExampleServer) -> Generator[ExampleServer, None, None]:
    """Start example in production mode and wait until ready.

    Uses `litestar assets build` + `litestar run`.
    For SSR: also uses `litestar assets serve --production`.
    Ports are auto-selected and parsed from output.

    Yields:
        ExampleServer: Running server in production mode.
    """
    example_server.start_production_mode()
    example_server.wait_until_ready()
    yield example_server
    example_server.stop()
