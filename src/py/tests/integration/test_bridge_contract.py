"""End-to-end regression for the bridge-as-source-of-truth contract.

Litestar-vite-c1t: ``ViteAssetLoader`` (loader) and ``ViteProxyMiddleware``
(proxy) read the bridge config (``.litestar.json``) for different fields:

- Loader anchors emitted asset URLs at ``appUrl`` (the bridge URL), keeping
  asset references on the single ASGI port.
- Proxy targets the real Vite ``host``/``port``, so when the loader-emitted
  URL hits Litestar's ``/static/...`` prefix it gets forwarded to the actual
  Vite dev server (not back to Litestar — that self-loop produced 10s
  timeouts before this fix).

This test asserts both halves end-to-end with a stub upstream so the regression
cannot reappear silently.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING

import httpx
import pytest
from litestar import Litestar
from litestar.testing import TestClient

from litestar_vite import PathConfig, RuntimeConfig, ViteConfig, VitePlugin

if TYPE_CHECKING:
    pass


@pytest.mark.anyio
async def test_proxy_loader_dual_consumer_no_self_loop(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Loader anchors on bridge appUrl AND proxy hits real Vite host:port.

    Failure mode without the fix: with proxyMode='vite' the JS plugin writes
    the bridge URL into the hotfile. Both consumers read the hotfile, both end
    up pointing at the bridge URL, and the proxy self-loops to Litestar.
    """
    from litestar_vite.utils import read_bridge_config

    read_bridge_config.cache_clear()

    # ----- Bridge: real Vite host/port + bridge appUrl -----
    bridge_payload = {
        "appUrl": "http://testserver",
        "host": "127.0.0.1",
        "port": 65431,
    }
    bridge_path = tmp_path / ".litestar.json"
    bridge_path.write_text(json.dumps(bridge_payload))
    monkeypatch.setenv("LITESTAR_VITE_CONFIG_PATH", str(bridge_path))

    # ----- Hotfile: present (readiness signal) but pointing at the bridge URL,
    # mirroring the JS plugin's C4 behavior in proxyMode='vite' -----
    bundle_dir = tmp_path / "public"
    bundle_dir.mkdir()
    (bundle_dir / "hot").write_text("http://testserver")

    # ----- Stub upstream: returns a sentinel body for the @vite/client request,
    # records the absolute URL it was called against so we can assert no self-loop.
    upstream_calls: list[str] = []

    def _upstream_handler(request: httpx.Request) -> httpx.Response:
        upstream_calls.append(str(request.url))
        return httpx.Response(200, headers={"content-type": "text/javascript"}, text="// real-vite-stub")

    transport = httpx.MockTransport(_upstream_handler)

    # ----- Build app -----
    config = ViteConfig(
        mode="template",
        paths=PathConfig(
            root=tmp_path,
            resource_dir=tmp_path / "resources",
            bundle_dir=bundle_dir,
            asset_url="/static/",
        ),
        runtime=RuntimeConfig(
            dev_mode=True, host="127.0.0.1", port=65431, set_environment=False
        ),
    )
    plugin = VitePlugin(config=config)
    app = Litestar(plugins=[plugin])

    # ----- Loader half: bridge appUrl wins, asset emission anchored on testserver -----
    loader = plugin.asset_loader
    asset_url = loader._vite_server_url("@vite/client")
    assert asset_url.startswith("http://testserver/"), asset_url
    assert "127.0.0.1:65431" not in asset_url

    # ----- Proxy half: drive a request through the middleware, swap in the
    # stub-transport client so we can intercept the upstream call.
    with TestClient(app=app) as client:
        # Inject the mock transport into the plugin's shared proxy client.
        # The lifespan has just initialized self._proxy_client; replace it.
        if plugin._proxy_client is not None:
            await plugin._proxy_client.aclose()
        plugin._proxy_client = httpx.AsyncClient(transport=transport)

        response = client.get("/static/@vite/client")

    assert response.status_code == 200, response.text
    assert response.text == "// real-vite-stub"
    assert len(upstream_calls) == 1, upstream_calls
    target_url = upstream_calls[0]
    # The upstream MUST be the real Vite host:port from the bridge — not the
    # bridge appUrl (testserver). Otherwise the proxy is self-looping.
    assert target_url.startswith("http://127.0.0.1:65431"), target_url
    assert "testserver" not in target_url

    read_bridge_config.cache_clear()
