"""Production mode E2E tests for examples."""

import httpx
import pytest

from .health_check import check_api_response, check_html_response
from .port_allocator import EXAMPLE_NAMES
from .server_manager import SSR_EXAMPLES, STATIC_SSR_EXAMPLES, ExampleServer

pytestmark = [pytest.mark.e2e]


@pytest.mark.parametrize("example_name", EXAMPLE_NAMES)
def test_production_homepage(production_server: ExampleServer, example_name: str) -> None:
    html_port = (
        production_server.vite_port
        if example_name in SSR_EXAMPLES | STATIC_SSR_EXAMPLES
        else production_server.litestar_port
    )
    base_url = f"http://127.0.0.1:{html_port}"
    response = httpx.get(f"{base_url}/", timeout=20.0)
    check_html_response(response)


@pytest.mark.parametrize("example_name", EXAMPLE_NAMES)
def test_production_api_summary(production_server: ExampleServer, example_name: str) -> None:
    base_url = f"http://127.0.0.1:{production_server.litestar_port}"
    response = httpx.get(f"{base_url}/api/summary", timeout=20.0)
    check_api_response(response)
