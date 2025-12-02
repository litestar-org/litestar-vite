"""Dev mode E2E tests for all examples."""

import re
from collections.abc import Iterable

import httpx
import pytest

from .assertions import assert_asset_fetchable, assert_html_contains_assets
from .health_check import check_api_response, check_html_response
from .port_allocator import EXAMPLE_NAMES
from .server_manager import ExampleServer

pytestmark = [pytest.mark.e2e]


def _extract_asset_urls(html: str, base_url: str) -> list[str]:
    patterns: Iterable[re.Pattern[str]] = (
        re.compile(r'src="(?P<src>/[\\w/\\-\\.]+)"'),
        re.compile(r'href="(?P<href>/[\\w/\\-\\.]+\\.css)"'),
    )
    urls: set[str] = set()
    for pattern in patterns:
        for match in pattern.finditer(html):
            value = match.groupdict().get("src") or match.groupdict().get("href")
            if value:
                urls.add(f"{base_url}{value}")
    return list(urls)


@pytest.mark.parametrize("example_name", EXAMPLE_NAMES)
def test_dev_mode_homepage(dev_mode_server: ExampleServer, example_name: str) -> None:
    base_url = f"http://127.0.0.1:{dev_mode_server.litestar_port}"
    response = httpx.get(f"{base_url}/", timeout=10.0)
    check_html_response(response)
    assert_html_contains_assets(response)

    asset_urls = _extract_asset_urls(response.text, base_url)
    if asset_urls:
        assert_asset_fetchable(asset_urls[:3])


@pytest.mark.parametrize("example_name", EXAMPLE_NAMES)
def test_dev_mode_api_summary(dev_mode_server: ExampleServer, example_name: str) -> None:
    base_url = f"http://127.0.0.1:{dev_mode_server.litestar_port}"
    response = httpx.get(f"{base_url}/api/summary", timeout=10.0)
    check_api_response(response)
