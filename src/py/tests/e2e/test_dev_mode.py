"""Dev mode E2E tests for all examples.

Tests use `litestar assets serve` + `litestar run` to start the dev environment.
This ensures we test the real developer experience via the Litestar CLI.
"""

import re
from collections.abc import Generator

import httpx
import pytest

from .assertions import assert_html_contains_assets
from .conftest import E2E_TEST_TIMEOUT, _dev_servers
from .health_check import check_api_response, check_html_response
from .server_manager import EXAMPLE_PORTS, ExampleServer

pytestmark = [pytest.mark.e2e, pytest.mark.timeout(E2E_TEST_TIMEOUT)]


@pytest.mark.timeout(E2E_TEST_TIMEOUT)
def test_dev_mode_homepage(dev_mode_server: ExampleServer) -> None:
    """Test that the homepage renders correctly in dev mode.

    Uses litestar assets serve + litestar run to start the dev environment.
    Validates:
    - HTML response with DOCTYPE
    - Contains asset references or app shell markers
    """
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


# ===== Bridge-source-of-truth E2E (litestar-vite-c1t) =====
#
# These tests use a focused fixture rather than the parametrized `dev_mode_server`
# because the bridge contract is specific to template-mode (proxyMode='vite').
# We pin to `jinja-htmx` as a representative single-port template-mode example.


_BRIDGE_E2E_EXAMPLE = "jinja-htmx"


@pytest.fixture
def jinja_htmx_dev_server() -> Generator[ExampleServer, None, None]:
    """Start (or reuse) the jinja-htmx example in dev mode.

    Uses the same caching strategy as ``dev_mode_server`` so successive tests
    share the running server (avoids port conflicts from TIME_WAIT).
    """
    name = _BRIDGE_E2E_EXAMPLE
    if name in _dev_servers:
        server = _dev_servers[name]
        try:
            server._check_processes_alive()
            yield server
            return
        except RuntimeError:
            del _dev_servers[name]

    server = ExampleServer(name)
    server.start_dev_mode()
    server.wait_until_ready(timeout=float(E2E_TEST_TIMEOUT))
    _dev_servers[name] = server
    yield server


@pytest.mark.timeout(E2E_TEST_TIMEOUT)
def test_dev_mode_vite_client_proxies_within_1s(jinja_htmx_dev_server: ExampleServer) -> None:
    """``/static/@vite/client`` MUST proxy through to Vite within 1 second.

    Pre-fix the proxy self-looped to Litestar (hotfile pointed at the bridge
    URL post-JS-C4), exhausting the httpx 10s default. This SLA codifies the
    fix.
    """
    base_url = f"http://127.0.0.1:{jinja_htmx_dev_server.litestar_port}"
    response = httpx.get(f"{base_url}/static/@vite/client", timeout=2.0)

    assert response.status_code == 200, f"unexpected status {response.status_code}: {response.text[:200]}"
    elapsed = response.elapsed.total_seconds()
    assert elapsed < 1.0, f"@vite/client took {elapsed:.3f}s (SLA 1.0s — likely a self-loop regression)"


@pytest.mark.timeout(E2E_TEST_TIMEOUT)
def test_dev_mode_html_anchors_on_litestar_origin(jinja_htmx_dev_server: ExampleServer) -> None:
    """All HTML asset references must be relative or anchored on the Litestar origin.

    No script/link reference may leak the raw Vite port — that would mean the
    bridge config isn't being honored on the loader side.
    """
    base_url = f"http://127.0.0.1:{jinja_htmx_dev_server.litestar_port}"
    response = httpx.get(f"{base_url}/", timeout=10.0)
    response.raise_for_status()
    html = response.text

    refs: list[str] = []
    refs.extend(re.findall(r"""<script[^>]*\bsrc=["']([^"']+)["']""", html))
    refs.extend(re.findall(r"""<link[^>]*\bhref=["']([^"']+)["']""", html))
    assert refs, "page rendered no <script src> or <link href> references"

    vite_port = EXAMPLE_PORTS[_BRIDGE_E2E_EXAMPLE]
    litestar_origin = f"http://127.0.0.1:{jinja_htmx_dev_server.litestar_port}"

    for ref in refs:
        if ref.startswith("/"):
            continue
        # Reject any reference to the Vite port directly.
        assert f":{vite_port}" not in ref, f"asset reference leaks Vite port: {ref}"
        # Absolute URLs must anchor on the Litestar origin.
        if ref.startswith(("http://", "https://")):
            assert ref.startswith(litestar_origin), f"asset reference leaks non-Litestar origin: {ref}"
