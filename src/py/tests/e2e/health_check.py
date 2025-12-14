"""HTTP health checks for example E2E tests."""

import time
from collections.abc import Iterable
from typing import Protocol, runtime_checkable

import httpx


@runtime_checkable
class _Pollable(Protocol):
    def poll(self) -> int | None: ...


def wait_for_http(
    url: str,
    timeout: float = 60.0,
    interval: float = 0.5,
    expected_statuses: Iterable[int] = (200, 301, 302, 404),
    processes: list[object] | None = None,
) -> httpx.Response:
    """Poll an endpoint until it responds with an expected status or timeout.

    Args:
        url: URL to poll.
        timeout: Maximum seconds to wait.
        interval: Delay between attempts in seconds.
        expected_statuses: HTTP status codes that are considered successful.

    Returns:
        The final :class:`httpx.Response` that matched the expectation.

    Raises:
        TimeoutError: If the endpoint does not respond with an expected status.
    """
    start = time.monotonic()
    last_error: str | None = None
    while time.monotonic() - start < timeout:
        if processes:
            for proc in processes:
                if isinstance(proc, _Pollable):
                    exit_code = proc.poll()
                    if exit_code is not None:
                        raise RuntimeError(f"Process exited with code {exit_code} before {url} became ready")
        try:
            response = httpx.get(url, timeout=5.0)
            if response.status_code in expected_statuses:
                return response
            if response.status_code == 503:
                last_error = "503 Service Unavailable (upstream not ready)"
            else:
                last_error = f"Status {response.status_code}"
        except httpx.RequestError as exc:
            last_error = str(exc)
        time.sleep(interval)
    raise TimeoutError(f"Health check failed for {url}: {last_error or 'no response'} after {timeout}s")


def check_html_response(response: httpx.Response) -> None:
    """Validate a basic HTML response."""
    assert response.status_code == 200, f"Expected 200 but got {response.status_code}"
    text = response.text.lower()
    assert "<!doctype html>" in text or "<!DOCTYPE html>" in response.text, "Missing DOCTYPE in HTML response"


def check_api_response(response: httpx.Response) -> None:
    """Validate a minimal API response structure."""
    assert response.status_code == 200, f"Expected 200 but got {response.status_code}"
    data = response.json()
    assert isinstance(data, dict), "API response should be a JSON object"
    assert "app" in data or "headline" in data, "API response missing expected keys"
