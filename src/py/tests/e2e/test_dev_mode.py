"""Dev mode E2E tests for all examples.

Tests use `litestar assets serve` + `litestar run` to start the dev environment.
This ensures we test the real developer experience via the Litestar CLI.
"""

import httpx
import pytest

from .assertions import assert_html_contains_assets
from .conftest import E2E_TEST_TIMEOUT
from .health_check import check_api_response, check_html_response
from .server_manager import SSG_EXAMPLES, SSR_EXAMPLES, ExampleServer

pytestmark = [pytest.mark.e2e, pytest.mark.timeout(E2E_TEST_TIMEOUT)]

# SSR/SSG examples that take too long to compile in CI dev mode
# Homepage test is skipped because the SSR dev server takes minutes to compile
# The API test still validates that Litestar and the dev server process are running
SSR_SSG_SLOW_COMPILE = SSR_EXAMPLES | SSG_EXAMPLES


@pytest.mark.timeout(E2E_TEST_TIMEOUT)
def test_dev_mode_homepage(dev_mode_server: ExampleServer) -> None:
    """Test that the homepage renders correctly in dev mode.

    Uses litestar assets serve + litestar run to start the dev environment.
    Validates:
    - HTML response with DOCTYPE
    - Contains asset references or app shell markers

    Note: SSR/SSG examples (nuxt, sveltekit, astro) are skipped because
    their dev servers take too long to compile in CI environments.
    """
    if dev_mode_server.example_name in SSR_SSG_SLOW_COMPILE:
        pytest.skip(
            f"Skipping homepage test for {dev_mode_server.example_name}: "
            "SSR/SSG dev servers take too long to compile in CI"
        )

    base_url = f"http://127.0.0.1:{dev_mode_server.litestar_port}"
    response = httpx.get(f"{base_url}/", timeout=10.0)
    check_html_response(response)
    assert_html_contains_assets(response)


@pytest.mark.timeout(E2E_TEST_TIMEOUT)
def test_dev_mode_api_summary(dev_mode_server: ExampleServer) -> None:
    """Test that the API endpoint works correctly in dev mode.

    Uses litestar assets serve + litestar run to start the dev environment.
    """
    base_url = f"http://127.0.0.1:{dev_mode_server.litestar_port}"
    response = httpx.get(f"{base_url}/api/summary", timeout=10.0)
    check_api_response(response)
