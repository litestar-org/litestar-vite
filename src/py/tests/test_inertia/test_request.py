from typing import Any

import pytest
from litestar import MediaType, Request, get
from litestar.middleware.session.server_side import ServerSideSessionConfig
from litestar.status_codes import HTTP_200_OK
from litestar.stores.memory import MemoryStore
from litestar.template.config import TemplateConfig
from litestar.testing import create_test_client  # pyright: ignore[reportUnknownVariableType]

from litestar_vite.inertia import InertiaHeaders, InertiaPlugin, InertiaRequest
from litestar_vite.plugin import VitePlugin

pytestmark = pytest.mark.anyio


def test_health_check(inertia_plugin: InertiaPlugin, vite_plugin: VitePlugin, template_config: TemplateConfig) -> None:  # pyright: ignore[reportMissingTypeArgument,reportUnknownParameterType]
    @get("/health-check", media_type=MediaType.TEXT)
    async def health_check() -> str:
        return "healthy"

    with create_test_client(
        route_handlers=health_check,
        plugins=[inertia_plugin, vite_plugin],
        template_config=template_config,
        middleware=[ServerSideSessionConfig().middleware],
        stores={"sessions": MemoryStore()},
    ) as client:
        response = client.get("/health-check")
        assert response.status_code == HTTP_200_OK
        assert response.text == "healthy"


async def test_is_inertia_default(
    inertia_plugin: InertiaPlugin,
    vite_plugin: VitePlugin,
    template_config: TemplateConfig,  # pyright: ignore[reportMissingTypeArgument,reportUnknownParameterType]
) -> None:
    @get("/")
    async def handler(request: InertiaRequest[Any, Any, Any]) -> bool:
        return bool(request.is_inertia)

    with create_test_client(
        route_handlers=[handler],
        plugins=[inertia_plugin, vite_plugin],
        template_config=template_config,
        middleware=[ServerSideSessionConfig().middleware],
        stores={"sessions": MemoryStore()},
    ) as client:
        response = client.get("/")
        assert response.text == "false"


async def test_is_inertia_false(
    inertia_plugin: InertiaPlugin,
    vite_plugin: VitePlugin,
    template_config: TemplateConfig,  # pyright: ignore[reportMissingTypeArgument,reportUnknownParameterType]
) -> None:
    @get("/")
    async def handler(request: InertiaRequest[Any, Any, Any]) -> bool:
        return bool(request.is_inertia)

    with create_test_client(
        route_handlers=[handler],
        plugins=[inertia_plugin, vite_plugin],
        template_config=template_config,
        middleware=[ServerSideSessionConfig().middleware],
        stores={"sessions": MemoryStore()},
    ) as client:
        response = client.get("/", headers={InertiaHeaders.ENABLED.value: "false"})
        assert response.text == "false"


async def test_is_inertia_true(
    inertia_plugin: InertiaPlugin,
    vite_plugin: VitePlugin,
    template_config: TemplateConfig,  # pyright: ignore[reportMissingTypeArgument,reportUnknownParameterType]
) -> None:
    @get("/")
    async def handler(request: InertiaRequest[Any, Any, Any]) -> bool:
        return bool(request.is_inertia)

    with create_test_client(
        route_handlers=[handler],
        plugins=[inertia_plugin, vite_plugin],
        middleware=[ServerSideSessionConfig().middleware],
        template_config=template_config,
        stores={"sessions": MemoryStore()},
    ) as client:
        response = client.get("/", headers={InertiaHeaders.ENABLED.value: "true"})
        assert (
            response.text
            == '{"component":null,"url":"/","version":"1.0","props":{"flash":{},"errors":{},"csrf_token":"","content":true}}'
        )


async def test_component_prop_default(
    inertia_plugin: InertiaPlugin,
    vite_plugin: VitePlugin,
    template_config: TemplateConfig,  # pyright: ignore[reportMissingTypeArgument,reportUnknownParameterType]
) -> None:
    @get("/")
    async def handler(request: InertiaRequest[Any, Any, Any]) -> bool:
        return request.inertia_enabled

    with create_test_client(
        route_handlers=[handler],
        plugins=[inertia_plugin, vite_plugin],
        template_config=template_config,
        middleware=[ServerSideSessionConfig().middleware],
        stores={"sessions": MemoryStore()},
    ) as client:
        response = client.get("/")
        assert response.text == "false"


async def test_component_enabled(
    inertia_plugin: InertiaPlugin,
    vite_plugin: VitePlugin,
    template_config: TemplateConfig,  # pyright: ignore[reportMissingTypeArgument,reportUnknownParameterType]
) -> None:
    @get("/", component="Home")
    async def handler(request: InertiaRequest[Any, Any, Any]) -> bool:
        return request.inertia_enabled

    with create_test_client(
        route_handlers=[handler],
        plugins=[inertia_plugin, vite_plugin],
        template_config=template_config,
        middleware=[ServerSideSessionConfig().middleware],
        stores={"sessions": MemoryStore()},
    ) as client:
        response = client.get("/")
        assert response.text.startswith("<!DOCTYPE html>")


async def test_default_route_no_component(
    inertia_plugin: InertiaPlugin,
    vite_plugin: VitePlugin,
    template_config: TemplateConfig,  # pyright: ignore[reportMissingTypeArgument,reportUnknownParameterType]
) -> None:
    @get("/")
    async def handler(request: Request[Any, Any, Any]) -> str:
        return request.inertia.route_component or ""  # pyright: ignore

    with create_test_client(
        route_handlers=[handler],
        plugins=[inertia_plugin, vite_plugin],
        template_config=template_config,
        middleware=[ServerSideSessionConfig().middleware],
        stores={"sessions": MemoryStore()},
    ) as client:
        response = client.get("/")
        assert response.text == ""
