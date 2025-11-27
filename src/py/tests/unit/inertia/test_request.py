from __future__ import annotations

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
    import json

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
        data = json.loads(response.text)
        assert data["component"] is None
        assert data["url"] == "/"
        assert "version" in data  # version is a hash, not a fixed value
        assert data["props"]["flash"] == {}
        assert data["props"]["errors"] == {}
        assert data["props"]["content"] is True


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


# =====================================================
# Inertia.js v2 Types Tests
# =====================================================


def test_to_camel_case() -> None:
    """Test snake_case to camelCase conversion."""
    from litestar_vite.inertia.types import to_camel_case

    assert to_camel_case("encrypt_history") == "encryptHistory"
    assert to_camel_case("deep_merge_props") == "deepMergeProps"
    assert to_camel_case("match_props_on") == "matchPropsOn"
    assert to_camel_case("simple") == "simple"
    assert to_camel_case("a_b_c") == "aBC"


def test_to_inertia_dict() -> None:
    """Test dataclass to camelCase dict conversion."""
    from dataclasses import dataclass

    from litestar_vite.inertia.types import to_inertia_dict

    @dataclass
    class TestProps:
        snake_case: str
        another_field: int
        optional_field: str | None = None

    obj = TestProps(snake_case="value", another_field=42)
    result = to_inertia_dict(obj)

    assert result == {"snakeCase": "value", "anotherField": 42}
    assert "optionalField" not in result  # None values excluded


def test_to_inertia_dict_with_required_fields() -> None:
    """Test required_fields parameter keeps None values."""
    from dataclasses import dataclass

    from litestar_vite.inertia.types import to_inertia_dict

    @dataclass
    class TestProps:
        required_field: str | None
        optional_field: str | None = None

    obj = TestProps(required_field=None)
    result = to_inertia_dict(obj, required_fields={"required_field"})

    assert result == {"requiredField": None}
    assert "optionalField" not in result


def test_page_props_to_dict() -> None:
    """Test PageProps.to_dict() produces correct camelCase output."""
    from litestar_vite.inertia.types import PageProps

    page = PageProps(
        component="Home",
        url="/dashboard",
        version="abc123",
        props={"user": "test"},
        encrypt_history=True,
        merge_props=["posts"],
        deferred_props={"default": ["permissions"]},
    )

    result = page.to_dict()

    # Required fields present with camelCase
    assert result["component"] == "Home"
    assert result["url"] == "/dashboard"
    assert result["version"] == "abc123"
    assert result["props"] == {"user": "test"}

    # v2 fields with camelCase
    assert result["encryptHistory"] is True
    assert result["mergeProps"] == ["posts"]
    assert result["deferredProps"] == {"default": ["permissions"]}

    # None values excluded (except required)
    assert "prependProps" not in result
    assert "deepMergeProps" not in result
    assert "matchPropsOn" not in result
