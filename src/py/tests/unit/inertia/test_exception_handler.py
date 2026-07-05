"""Regression tests for Inertia exception handling."""

from typing import Any

from litestar import get
from litestar.middleware.session.server_side import ServerSideSessionConfig
from litestar.stores.memory import MemoryStore
from litestar.template.config import TemplateConfig
from litestar.testing import create_test_client

from litestar_vite.inertia import InertiaHeaders, InertiaPlugin
from litestar_vite.plugin import VitePlugin


async def test_production_500_body_omits_exception_detail(
    inertia_plugin: InertiaPlugin, vite_plugin: VitePlugin, template_config: TemplateConfig[Any]
) -> None:
    @get("/boom")
    async def handler() -> None:
        raise RuntimeError("secret db dsn leaked")

    with create_test_client(
        route_handlers=[handler],
        debug=False,
        plugins=[inertia_plugin, vite_plugin],
        template_config=template_config,
        middleware=[ServerSideSessionConfig().middleware],
        stores={"sessions": MemoryStore()},
        raise_server_exceptions=False,
    ) as client:
        response = client.get("/boom")

    assert response.status_code == 500
    assert "secret db dsn leaked" not in response.text
    assert "Internal Server Error" in response.text


async def test_inertia_500_flash_and_body_omit_detail_in_production(
    inertia_plugin: InertiaPlugin, vite_plugin: VitePlugin, template_config: TemplateConfig[Any]
) -> None:
    @get("/boom", component="Boom")
    async def handler() -> dict[str, str]:
        raise RuntimeError("secret db dsn leaked")

    with create_test_client(
        route_handlers=[handler],
        debug=False,
        plugins=[inertia_plugin, vite_plugin],
        template_config=template_config,
        middleware=[ServerSideSessionConfig().middleware],
        stores={"sessions": MemoryStore()},
        raise_server_exceptions=False,
    ) as client:
        response = client.get("/boom", headers={InertiaHeaders.ENABLED.value: "true"})

    assert response.status_code == 500
    body = response.json()
    assert body["props"]["message"] == "Internal Server Error"
    assert "secret db dsn leaked" not in response.text


async def test_debug_500_still_includes_detail(
    inertia_plugin: InertiaPlugin, vite_plugin: VitePlugin, template_config: TemplateConfig[Any]
) -> None:
    @get("/boom")
    async def handler() -> None:
        raise RuntimeError("debug detail visible")

    with create_test_client(
        route_handlers=[handler],
        debug=True,
        plugins=[inertia_plugin, vite_plugin],
        template_config=template_config,
        middleware=[ServerSideSessionConfig().middleware],
        stores={"sessions": MemoryStore()},
        raise_server_exceptions=False,
    ) as client:
        response = client.get("/boom")

    assert response.status_code == 500
    assert "debug detail visible" in response.text


async def test_inertia_error_without_route_component_avoids_null_component(
    inertia_plugin: InertiaPlugin, vite_plugin: VitePlugin, template_config: TemplateConfig[Any]
) -> None:
    @get("/api/data")
    async def handler() -> dict[str, str]:
        raise RuntimeError("api exploded")

    with create_test_client(
        route_handlers=[handler],
        debug=False,
        plugins=[inertia_plugin, vite_plugin],
        template_config=template_config,
        middleware=[ServerSideSessionConfig().middleware],
        stores={"sessions": MemoryStore()},
        raise_server_exceptions=False,
    ) as client:
        response = client.get("/api/data", headers={InertiaHeaders.ENABLED.value: "true"})

    assert response.status_code >= 500
    body = response.json()
    assert body.get("component", "MISSING") is not None
    assert "component" not in body
    assert body["message"] == "Internal Server Error"


async def test_inertia_error_with_component_still_renders_page(
    inertia_plugin: InertiaPlugin, vite_plugin: VitePlugin, template_config: TemplateConfig[Any]
) -> None:
    @get("/page", component="Page")
    async def handler() -> dict[str, str]:
        raise RuntimeError("page exploded")

    with create_test_client(
        route_handlers=[handler],
        debug=False,
        plugins=[inertia_plugin, vite_plugin],
        template_config=template_config,
        middleware=[ServerSideSessionConfig().middleware],
        stores={"sessions": MemoryStore()},
        raise_server_exceptions=False,
    ) as client:
        response = client.get("/page", headers={InertiaHeaders.ENABLED.value: "true"})

    assert response.status_code == 500
    body = response.json()
    assert body["component"] == "Page"
    assert body["props"]["message"] == "Internal Server Error"
