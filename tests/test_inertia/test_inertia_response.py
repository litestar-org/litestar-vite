from typing import Any

import pytest
from litestar import MediaType, get
from litestar.status_codes import HTTP_200_OK
from litestar.testing import create_test_client  # pyright: ignore[reportUnknownVariableType]

from litestar_vite.inertia import InertiaHeaders, InertiaPlugin, InertiaRequest

pytestmark = pytest.mark.anyio


def test_health_check(inertia_plugin: InertiaPlugin) -> None:
    @get("/health-check", media_type=MediaType.TEXT)
    async def health_check() -> str:
        return "healthy"

    with create_test_client(route_handlers=health_check, plugins=[inertia_plugin]) as client:
        response = client.get("/health-check")
        assert response.status_code == HTTP_200_OK
        assert response.text == "healthy"


async def test_is_inertia_default(inertia_plugin: InertiaPlugin) -> None:
    @get("/")
    def handler(request: InertiaRequest[Any, Any, Any]) -> bool:
        return bool(request.is_inertia)

    with create_test_client(route_handlers=[handler], request_class=InertiaRequest, plugins=[inertia_plugin]) as client:
        response = client.get("/")
        assert response.text == "false"


async def test_is_inertia_false(inertia_plugin: InertiaPlugin) -> None:
    @get("/")
    async def handler(request: InertiaRequest[Any, Any, Any]) -> bool:
        return bool(request.is_inertia)

    with create_test_client(route_handlers=[handler], request_class=InertiaRequest, plugins=[inertia_plugin]) as client:
        response = client.get("/", headers={InertiaHeaders.ENABLED.value: "false"})
        assert response.text == "false"


async def test_is_inertia_true(inertia_plugin: InertiaPlugin) -> None:
    @get("/")
    async def handler(request: InertiaRequest[Any, Any, Any]) -> bool:
        return bool(request.is_inertia)

    with create_test_client(route_handlers=[handler], request_class=InertiaRequest, plugins=[inertia_plugin]) as client:
        response = client.get("/", headers={InertiaHeaders.ENABLED.value: "true"})
        assert response.text == "true"


async def test_component_prop_default(inertia_plugin: InertiaPlugin) -> None:
    @get("/")
    async def handler(request: InertiaRequest[Any, Any, Any]) -> bool:
        return request.inertia_enabled

    with create_test_client(route_handlers=[handler], request_class=InertiaRequest, plugins=[inertia_plugin]) as client:
        response = client.get("/")
        assert response.text == "false"


async def test_component_enabled(inertia_plugin: InertiaPlugin) -> None:
    @get("/", component="Home")
    async def handler(request: InertiaRequest[Any, Any, Any]) -> bool:
        return request.inertia_enabled

    with create_test_client(route_handlers=[handler], request_class=InertiaRequest, plugins=[inertia_plugin]) as client:
        response = client.get("/")
        assert response.text == "true"
