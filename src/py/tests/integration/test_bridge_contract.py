"""End-to-end regression for the bridge-as-source-of-truth contract.

Litestar-vite-c1t: ``ViteAssetLoader`` (loader) and ``ViteProxyMiddleware``
(proxy) intentionally use different source-of-truth files:

- Loader anchors emitted asset URLs at ``appUrl`` (the bridge URL), keeping
  asset references on the single ASGI port when ``dev_mode_direct_urls=False``.
- Proxy targets the hotfile's actual resolved Vite URL, so when the
  loader-emitted URL hits Litestar's ``/static/...`` prefix it gets forwarded
  to the actual Vite dev server (not back to Litestar).

This test asserts both halves end-to-end with a stub upstream so the regression
cannot reappear silently.
"""

import json
from pathlib import Path
from unittest.mock import patch

import pytest
from litestar import Litestar
from litestar.testing import TestClient
from litestar.types import Send

from litestar_vite import PathConfig, RuntimeConfig, ViteConfig, VitePlugin


@pytest.mark.anyio
async def test_proxy_loader_dual_consumer_no_self_loop(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Loader anchors on bridge appUrl AND proxy hits the hotfile upstream."""
    from litestar_vite.utils import read_bridge_config

    read_bridge_config.cache_clear()

    bridge_payload = {"appUrl": "http://testserver", "host": "127.0.0.1", "port": 65431}
    bridge_path = tmp_path / ".litestar.json"
    bridge_path.write_text(json.dumps(bridge_payload))
    monkeypatch.setenv("LITESTAR_VITE_CONFIG_PATH", str(bridge_path))

    bundle_dir = tmp_path / "public"
    bundle_dir.mkdir()
    (bundle_dir / "hot").write_text("http://127.0.0.1:65431")

    upstream_calls: list[str] = []

    async def fake_proxy(url: str, *, send: Send, **_kwargs: object) -> None:
        upstream_calls.append(url)
        await send({"type": "http.response.start", "status": 200, "headers": [(b"content-type", b"text/javascript")]})
        await send({"type": "http.response.body", "body": b"// real-vite-stub", "more_body": False})

    config = ViteConfig(
        mode="template",
        paths=PathConfig(
            root=tmp_path, resource_dir=tmp_path / "resources", bundle_dir=bundle_dir, asset_url="/static/"
        ),
        runtime=RuntimeConfig(
            dev_mode=True, host="127.0.0.1", port=65431, set_environment=False, dev_mode_direct_urls=False
        ),
    )
    plugin = VitePlugin(config=config)
    app = Litestar(plugins=[plugin])

    loader = plugin.asset_loader
    asset_url = loader._vite_server_url("@vite/client")
    assert asset_url.startswith("http://testserver/"), asset_url
    assert "127.0.0.1:65431" not in asset_url

    with (
        patch("litestar_vite.plugin._proxy._anyio_proxy_http_request", side_effect=fake_proxy),
        TestClient(app=app) as client,
    ):
        response = client.get("/static/@vite/client")

    assert response.status_code == 200, response.text
    assert response.text == "// real-vite-stub"
    assert len(upstream_calls) == 1, upstream_calls
    target_url = upstream_calls[0]
    assert target_url.startswith("http://127.0.0.1:65431"), target_url
    assert "testserver" not in target_url

    read_bridge_config.cache_clear()
