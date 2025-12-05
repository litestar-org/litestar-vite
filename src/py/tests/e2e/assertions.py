"""Assertion helpers for example E2E tests."""

from collections.abc import Iterable

import httpx


def assert_html_contains_assets(
    response: httpx.Response,
    asset_keywords: Iterable[str] = ("assets", "static"),
    shell_markers: Iterable[str] = ("<app-root", '<div id="app"', "<body"),
) -> None:
    """Ensure the HTML references assets or contains an app shell marker."""
    body = response.text.lower()
    if any(marker.lower() in body for marker in shell_markers):
        return
    if not any(keyword in body for keyword in asset_keywords):
        raise AssertionError("HTML response did not reference assets or recognizable app shell markers")


def assert_asset_fetchable(urls: list[str]) -> None:
    """Fetch assets and ensure at least one returns 200."""
    for url in urls:
        try:
            response = httpx.get(url, timeout=5.0)
        except httpx.RequestError:
            continue
        if response.status_code == 200:
            return
    raise AssertionError(f"No assets were reachable from {urls}")
