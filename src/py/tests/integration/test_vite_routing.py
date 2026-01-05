from pathlib import Path

import pytest
from litestar import Litestar, get
from litestar.openapi.config import OpenAPIConfig
from litestar.status_codes import HTTP_200_OK, HTTP_503_SERVICE_UNAVAILABLE
from litestar.testing import TestClient

from litestar_vite import PathConfig, ViteConfig, VitePlugin


@pytest.fixture
def test_asset_root(tmp_path: Path) -> Path:
    return tmp_path


@pytest.mark.anyio
async def test_vite_proxy_respects_litestar_routes_with_root_asset_url(test_asset_root: Path) -> None:
    """
    Integration test to verify that when asset_url is set to "/",
    Litestar routes take precedence over the Vite proxy.
    """

    @get("/api/health")
    async def health_check() -> dict[str, str]:
        return {"status": "ok"}

    # Configure Vite with root asset_url
    vite_config = ViteConfig(mode="spa", dev_mode=True, paths=PathConfig(root=test_asset_root, asset_url="/"))

    plugin = VitePlugin(config=vite_config)

    # Configure OpenAPI with a path (defaults to /schema)
    openapi_config = OpenAPIConfig(title="Test API", version="1.0.0")

    app = Litestar(route_handlers=[health_check], plugins=[plugin], openapi_config=openapi_config)

    with TestClient(app) as client:
        # 1. Request the Litestar route
        # Should NOT be proxied. Should return 200 OK from health_check.
        response = client.get("/api/health")
        assert response.status_code == HTTP_200_OK
        assert response.json() == {"status": "ok"}

        # 2. Request OpenAPI schema endpoints
        # These should also be protected from proxying

        # /schema (HTML UI)
        response = client.get("/schema")
        assert response.status_code == HTTP_200_OK
        assert "text/html" in response.headers["content-type"]

        # /schema/openapi.json (JSON Spec)
        response = client.get("/schema/openapi.json")
        assert response.status_code == HTTP_200_OK
        assert "application/vnd.oai.openapi+json" in response.headers["content-type"]

        # 3. Request a non-existent route that should be proxied (because asset_url="/")
        response = client.get("/assets/main.js")
        assert response.status_code == HTTP_503_SERVICE_UNAVAILABLE
        assert "Vite server not running" in response.text
