"""Pytest fixtures for example E2E suite."""

from collections.abc import Generator

import pytest

from .port_allocator import EXAMPLE_NAMES, validate_unique_ports
from .server_manager import RUNNING_PROCS, ExampleServer


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line("markers", "e2e: end-to-end example tests")
    config.addinivalue_line("markers", "spa: SPA examples")
    config.addinivalue_line("markers", "template: Template examples")
    config.addinivalue_line("markers", "inertia: Inertia examples")
    config.addinivalue_line("markers", "ssr: SSR examples")
    config.addinivalue_line("markers", "cli: CLI-based examples")


@pytest.fixture(scope="session", autouse=True)
def _validate_port_allocation() -> None:
    validate_unique_ports()


@pytest.fixture(scope="session", autouse=True)
def _cleanup_processes_after_session() -> Generator[None, None, None]:
    yield
    for proc in list(RUNNING_PROCS):
        try:
            if proc.poll() is None:
                proc.terminate()
                proc.wait(timeout=5)
        except Exception:
            proc.kill()


EXAMPLE_PARAMS = [pytest.param(name, marks=pytest.mark.xdist_group(name)) for name in EXAMPLE_NAMES]


@pytest.fixture(params=EXAMPLE_PARAMS)
def example_name(request: pytest.FixtureRequest) -> str:
    return str(request.param)


@pytest.fixture
def example_server(example_name: str) -> Generator[ExampleServer, None, None]:
    server = ExampleServer(example_name)
    yield server
    server.stop()


@pytest.fixture
def dev_mode_server(example_server: ExampleServer) -> Generator[ExampleServer, None, None]:
    example_server.start_dev_mode()
    example_server.wait_until_ready()
    yield example_server
    example_server.stop()


@pytest.fixture
def production_server(example_server: ExampleServer) -> Generator[ExampleServer, None, None]:
    example_server.start_production_mode()
    example_server.wait_until_ready()
    yield example_server
    example_server.stop()
