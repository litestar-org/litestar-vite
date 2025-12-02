"""Production mode E2E tests for all examples.

Tests use `litestar assets build` + `litestar run` to build and serve production assets.
For SSR examples, also uses `litestar assets serve --production` to start the Node server.
This ensures we test the real production workflow via the Litestar CLI.
"""

import httpx
import pytest

from .conftest import E2E_TEST_TIMEOUT
from .health_check import check_api_response, check_html_response
from .server_manager import SSR_EXAMPLES, ExampleServer

# Production tests get extra time for asset building
PRODUCTION_TIMEOUT = E2E_TEST_TIMEOUT * 2  # 120 seconds

pytestmark = [pytest.mark.e2e, pytest.mark.timeout(PRODUCTION_TIMEOUT)]


@pytest.mark.timeout(PRODUCTION_TIMEOUT)
def test_production_homepage(production_server: ExampleServer) -> None:
    """Test that the homepage renders correctly in production mode.

    Uses litestar assets build + litestar run to serve production assets.
    For SSR examples, HTML comes from the Node server via litestar assets serve --production.
    """
    # For SSR examples, get HTML from the Node server port
    html_port = (
        production_server.vite_port
        if production_server.example_name in SSR_EXAMPLES
        else production_server.litestar_port
    )
    base_url = f"http://127.0.0.1:{html_port}"
    response = httpx.get(f"{base_url}/", timeout=20.0)
    check_html_response(response)


@pytest.mark.timeout(PRODUCTION_TIMEOUT)
def test_production_api_summary(production_server: ExampleServer) -> None:
    """Test that the API endpoint works correctly in production mode.

    Uses litestar assets build + litestar run to serve production assets.
    """
    base_url = f"http://127.0.0.1:{production_server.litestar_port}"
    response = httpx.get(f"{base_url}/api/summary", timeout=20.0)
    check_api_response(response)
