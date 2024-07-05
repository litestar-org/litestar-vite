from __future__ import annotations

from typing import Any, Dict

import pytest
from litestar import Request, get
from litestar.testing import create_test_client  # pyright: ignore[reportUnknownVariableType]

from litestar_vite.inertia import InertiaHeaders, InertiaPlugin
from litestar_vite.plugin import VitePlugin

pytestmark = pytest.mark.anyio


async def test_component_enabled(inertia_plugin: InertiaPlugin, vite_plugin: VitePlugin) -> None:
    @get("/", component="Home")
    async def handler(request: Request[Any, Any, Any]) -> Dict[str, Any]:
        return {"thing": "value"}

    with create_test_client(
        route_handlers=[handler],
        plugins=[inertia_plugin, vite_plugin],
    ) as client:
        response = client.get("/")
        assert response.text.startswith("<!DOCTYPE html>")


async def test_component_inertia_header_enabled(inertia_plugin: InertiaPlugin, vite_plugin: VitePlugin) -> None:
    @get("/", component="Home")
    async def handler(request: Request[Any, Any, Any]) -> Dict[str, Any]:
        return {"thing": "value"}

    with create_test_client(
        route_handlers=[handler],
        plugins=[inertia_plugin, vite_plugin],
    ) as client:
        response = client.get("/", headers={InertiaHeaders.ENABLED.value: "true"})
        assert response.content == b'{"component":"Home","url":"","version":"","props":{"content":{"thing":"value"}}}'


async def test_default_route_response_no_component(inertia_plugin: InertiaPlugin, vite_plugin: VitePlugin) -> None:
    @get("/")
    async def handler(request: Request[Any, Any, Any]) -> Dict[str, Any]:
        return {"thing": "value"}

    with create_test_client(route_handlers=[handler], plugins=[inertia_plugin, vite_plugin]) as client:
        response = client.get("/")
        assert response.content == b'{"thing":"value"}'
