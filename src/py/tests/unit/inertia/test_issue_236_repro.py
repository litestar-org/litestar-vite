"""Reproduction test for Issue #236: Inertia deferred props metadata is lost."""

from typing import Any

from litestar import get
from litestar.middleware.session.server_side import ServerSideSessionConfig
from litestar.status_codes import HTTP_200_OK
from litestar.stores.memory import MemoryStore
from litestar.testing import create_test_client

from litestar_vite.config import InertiaConfig
from litestar_vite.inertia import InertiaHeaders, InertiaPlugin, defer
from litestar_vite.plugin import VitePlugin


def test_issue_236_metadata_loss() -> None:
    """Verify that deferred props metadata is present in the initial response.

    In Issue #236, the 'deferredProps' key is missing from the initial JSON
    response because 'lazy_render' strips the metadata during value extraction.
    """

    @get("/", component="TestComponent")
    async def handler() -> dict[str, Any]:
        return {
            "eager_data": "loads immediately",
            "slow_data": defer("slow_data", lambda: {"items": [1, 2, 3]}),
        }

    with create_test_client(
        route_handlers=[handler],
        plugins=[InertiaPlugin(config=InertiaConfig()), VitePlugin()],
        middleware=[ServerSideSessionConfig().middleware],
        stores={"sessions": MemoryStore()},
    ) as client:
        # Initial load (not a partial reload)
        response = client.get("/", headers={InertiaHeaders.ENABLED.value: "true"})
        assert response.status_code == HTTP_200_OK
        
        data = response.json()
        
        # 1. Eager data should be present
        assert data["props"]["eager_data"] == "loads immediately"
        
        # 2. Slow data value should NOT be present (it's deferred)
        assert "slow_data" not in data["props"]
        
        # 3. METADATA should be present (This is what fails in #236)
        assert "deferredProps" in data, "deferredProps metadata missing from response"
        assert "default" in data["deferredProps"]
        assert "slow_data" in data["deferredProps"]["default"]
