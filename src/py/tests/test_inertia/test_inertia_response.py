from __future__ import annotations

from typing import Any, Dict

import pytest
from litestar import Request, get
from litestar.exceptions import NotAuthorizedException
from litestar.middleware.session.server_side import ServerSideSessionConfig
from litestar.plugins.flash import (  # pyright: ignore[reportUnknownVariableType]  # pyright: ignore[reportUnknownVariableType]
    FlashConfig,
    FlashPlugin,
    flash,
)
from litestar.stores.memory import MemoryStore
from litestar.template.config import TemplateConfig
from litestar.testing import create_test_client  # pyright: ignore[reportUnknownVariableType]

from litestar_vite.inertia import InertiaHeaders, InertiaPlugin
from litestar_vite.inertia.response import share
from litestar_vite.plugin import VitePlugin

pytestmark = pytest.mark.anyio


async def test_component_enabled(
    inertia_plugin: InertiaPlugin, vite_plugin: VitePlugin, template_config: TemplateConfig
) -> None:
    @get("/", component="Home")
    async def handler(request: Request[Any, Any, Any]) -> Dict[str, Any]:
        return {"thing": "value"}

    with create_test_client(
        route_handlers=[handler],
        plugins=[inertia_plugin, vite_plugin],
        template_config=template_config,
        middleware=[ServerSideSessionConfig().middleware],
        stores={"sessions": MemoryStore()},
    ) as client:
        response = client.get("/")
        assert response.text.startswith("<!DOCTYPE html>")


async def test_component_inertia_header_enabled(
    inertia_plugin: InertiaPlugin, vite_plugin: VitePlugin, template_config: TemplateConfig
) -> None:
    @get("/", component="Home")
    async def handler(request: Request[Any, Any, Any]) -> Dict[str, Any]:
        return {"thing": "value"}

    with create_test_client(
        route_handlers=[handler],
        plugins=[inertia_plugin, vite_plugin],
        template_config=template_config,
        middleware=[ServerSideSessionConfig().middleware],
        stores={"sessions": MemoryStore()},
    ) as client:
        response = client.get("/", headers={InertiaHeaders.ENABLED.value: "true"})
        assert (
            response.content
            == b'{"component":"Home","url":"/","version":"1.0","props":{"flash":{},"errors":{},"csrf_token":"","content":{"thing":"value"}}}'
        )


async def test_component_inertia_flash_header_enabled(
    inertia_plugin: InertiaPlugin, vite_plugin: VitePlugin, template_config: TemplateConfig
) -> None:
    @get("/", component="Home")
    async def handler(request: Request[Any, Any, Any]) -> Dict[str, Any]:
        flash(request, "a flash message", "info")
        return {"thing": "value"}

    with create_test_client(
        route_handlers=[handler],
        template_config=template_config,
        plugins=[
            inertia_plugin,
            vite_plugin,
            FlashPlugin(config=FlashConfig(template_config=template_config)),
        ],
        middleware=[ServerSideSessionConfig().middleware],
        stores={"sessions": MemoryStore()},
    ) as client:
        response = client.get("/", headers={InertiaHeaders.ENABLED.value: "true"})
        assert (
            response.content
            == b'{"component":"Home","url":"/","version":"1.0","props":{"flash":{"info":["a flash message"]},"errors":{},"csrf_token":"","content":{"thing":"value"}}}'
        )


async def test_component_inertia_shared_flash_header_enabled(
    inertia_plugin: InertiaPlugin,
    vite_plugin: VitePlugin,
    template_config: TemplateConfig,
) -> None:
    @get("/", component="Home")
    async def handler(request: Request[Any, Any, Any]) -> Dict[str, Any]:
        flash(request, "a flash message", "info")
        share(request, "auth", {"user": "nobody"})
        return {"thing": "value"}

    with create_test_client(
        route_handlers=[handler],
        template_config=template_config,
        plugins=[
            inertia_plugin,
            vite_plugin,
            FlashPlugin(config=FlashConfig(template_config=template_config)),
        ],
        middleware=[ServerSideSessionConfig().middleware],
        stores={"sessions": MemoryStore()},
    ) as client:
        response = client.get("/", headers={InertiaHeaders.ENABLED.value: "true"})
        assert (
            response.content
            == b'{"component":"Home","url":"/","version":"1.0","props":{"auth":{"user":"nobody"},"flash":{"info":["a flash message"]},"errors":{},"csrf_token":"","content":{"thing":"value"}}}'
        )


async def test_default_route_response_no_component(
    inertia_plugin: InertiaPlugin, vite_plugin: VitePlugin, template_config: TemplateConfig
) -> None:
    @get("/")
    async def handler(request: Request[Any, Any, Any]) -> Dict[str, Any]:
        return {"thing": "value"}

    with create_test_client(
        route_handlers=[handler],
        template_config=template_config,
        plugins=[inertia_plugin, vite_plugin],
        middleware=[ServerSideSessionConfig().middleware],
        stores={"sessions": MemoryStore()},
    ) as client:
        response = client.get("/")
        assert response.content == b'{"thing":"value"}'


async def test_component_inertia_version_redirect(
    inertia_plugin: InertiaPlugin, vite_plugin: VitePlugin, template_config: TemplateConfig
) -> None:
    @get("/", component="Home")
    async def handler(request: Request[Any, Any, Any]) -> Dict[str, Any]:
        return {"thing": "value"}

    with create_test_client(
        route_handlers=[handler],
        template_config=template_config,
        plugins=[inertia_plugin, vite_plugin],
        middleware=[ServerSideSessionConfig().middleware],
        stores={"sessions": MemoryStore()},
    ) as client:
        response = client.get(
            "/",
            headers={InertiaHeaders.ENABLED.value: "true", InertiaHeaders.VERSION.value: "wrong"},
        )
        assert (
            response.content
            == b'{"component":"Home","url":"/","version":"1.0","props":{"flash":{},"errors":{},"csrf_token":"","content":{"thing":"value"}}}'
        )


async def test_unauthenticated_redirect(
    inertia_plugin: InertiaPlugin, vite_plugin: VitePlugin, template_config: TemplateConfig
) -> None:
    @get("/", component="Home")
    async def handler(request: Request[Any, Any, Any]) -> Dict[str, Any]:
        raise NotAuthorizedException(detail="User not authenticated")

    @get("/login", component="Login")
    async def login_handler(request: Request[Any, Any, Any]) -> Dict[str, Any]:
        return {"thing": "value"}

    inertia_plugin.config.redirect_unauthorized_to = "/login"

    with create_test_client(
        route_handlers=[handler, login_handler],
        template_config=template_config,
        plugins=[inertia_plugin, vite_plugin],
        middleware=[ServerSideSessionConfig().middleware],
        stores={"sessions": MemoryStore()},
    ) as client:
        response = client.get("/", headers={InertiaHeaders.ENABLED.value: "true"})
        assert response.status_code == 200
        assert response.url.path == "/login"


async def test_404_redirect(
    inertia_plugin: InertiaPlugin, vite_plugin: VitePlugin, template_config: TemplateConfig
) -> None:
    @get("/", component="Home")
    async def handler(request: Request[Any, Any, Any]) -> Dict[str, Any]:
        return {"thing": "value"}

    inertia_plugin.config.redirect_404 = "/"

    with create_test_client(
        route_handlers=[handler],
        template_config=template_config,
        plugins=[inertia_plugin, vite_plugin],
        middleware=[ServerSideSessionConfig().middleware],
        stores={"sessions": MemoryStore()},
    ) as client:
        response = client.get("/not-found", headers={InertiaHeaders.ENABLED.value: "true"})
        assert response.status_code == 200
        assert response.url.path == "/"
