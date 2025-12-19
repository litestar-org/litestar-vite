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
    from litestar.serialization import decode_json

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
        data = decode_json(response.text)
        assert data["component"] is None
        assert data["url"] == "/"
        assert "version" in data  # version is a hash, not a fixed value
        # v2.3+ protocol: flash is at top-level, not in props
        assert "flash" not in data["props"]
        assert data.get("flash") == {}  # Empty flash is {} to support router.flash()
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
    class Props:
        snake_case: str
        another_field: int
        optional_field: str | None = None

    obj = Props(snake_case="value", another_field=42)
    result = to_inertia_dict(obj)

    assert result == {"snakeCase": "value", "anotherField": 42}
    assert "optionalField" not in result  # None values excluded


def test_to_inertia_dict_with_required_fields() -> None:
    """Test required_fields parameter keeps None values."""
    from dataclasses import dataclass

    from litestar_vite.inertia.types import to_inertia_dict

    @dataclass
    class PropsWithRequiredField:
        required_field: str | None
        optional_field: str | None = None

    obj = PropsWithRequiredField(required_field=None)
    result = to_inertia_dict(obj, required_fields={"required_field"})

    assert result == {"requiredField": None}
    assert "optionalField" not in result


def test_page_props_to_dict() -> None:
    """Test PageProps.to_dict() produces correct camelCase output."""
    from litestar_vite.inertia.types import PageProps

    page: PageProps[dict[str, str]] = PageProps(
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


# =====================================================
# Page Component Alias Tests (component_opt_keys)
# =====================================================


async def test_page_kwarg_enables_inertia(
    inertia_plugin: InertiaPlugin,
    vite_plugin: VitePlugin,
    template_config: "TemplateConfig[Any]",  # pyright: ignore[reportMissingTypeArgument,reportUnknownParameterType]
) -> None:
    """Test that @get("/", page="Home") enables inertia.

    The 'page' kwarg should work exactly like 'component' to enable
    Inertia rendering for a route.
    """

    @get("/", page="Home")
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
        # Should return HTML template, not "true"
        assert response.text.startswith("<!DOCTYPE html>")


async def test_page_kwarg_returns_correct_component(
    inertia_plugin: InertiaPlugin,
    vite_plugin: VitePlugin,
    template_config: "TemplateConfig[Any]",  # pyright: ignore[reportMissingTypeArgument,reportUnknownParameterType]
) -> None:
    """Test that page kwarg returns correct component name.

    The component name set via 'page' should be retrievable via
    request.inertia.route_component.
    """
    from litestar.serialization import decode_json

    @get("/dashboard", page="Dashboard")
    async def handler(request: InertiaRequest[Any, Any, Any]) -> str:
        return request.inertia.route_component or ""

    with create_test_client(
        route_handlers=[handler],
        plugins=[inertia_plugin, vite_plugin],
        template_config=template_config,
        middleware=[ServerSideSessionConfig().middleware],
        stores={"sessions": MemoryStore()},
    ) as client:
        # When Inertia header is sent, it returns JSON with component
        response = client.get("/dashboard", headers={InertiaHeaders.ENABLED.value: "true"})
        data = decode_json(response.text)
        assert data["component"] == "Dashboard"


async def test_page_opt_dict_works(
    inertia_plugin: InertiaPlugin,
    vite_plugin: VitePlugin,
    template_config: "TemplateConfig[Any]",  # pyright: ignore[reportMissingTypeArgument,reportUnknownParameterType]
) -> None:
    """Test that opt={"page": "Home"} works.

    Using the opt dictionary directly should also work with 'page' key.
    """
    from litestar.serialization import decode_json

    @get("/profile", opt={"page": "UserProfile"})
    async def handler(request: InertiaRequest[Any, Any, Any]) -> str:
        return request.inertia.route_component or ""

    with create_test_client(
        route_handlers=[handler],
        plugins=[inertia_plugin, vite_plugin],
        template_config=template_config,
        middleware=[ServerSideSessionConfig().middleware],
        stores={"sessions": MemoryStore()},
    ) as client:
        # When Inertia header is sent, it returns JSON with component
        response = client.get("/profile", headers={InertiaHeaders.ENABLED.value: "true"})
        data = decode_json(response.text)
        assert data["component"] == "UserProfile"


async def test_component_kwarg_still_works(
    inertia_plugin: InertiaPlugin,
    vite_plugin: VitePlugin,
    template_config: "TemplateConfig[Any]",  # pyright: ignore[reportMissingTypeArgument,reportUnknownParameterType]
) -> None:
    """Test backward compatibility with component kwarg.

    The original 'component' kwarg must continue to work to ensure
    backward compatibility with existing code.
    """
    from litestar.serialization import decode_json

    @get("/about", component="About")
    async def handler(request: InertiaRequest[Any, Any, Any]) -> str:
        return request.inertia.route_component or ""

    with create_test_client(
        route_handlers=[handler],
        plugins=[inertia_plugin, vite_plugin],
        template_config=template_config,
        middleware=[ServerSideSessionConfig().middleware],
        stores={"sessions": MemoryStore()},
    ) as client:
        # When Inertia header is sent, it returns JSON with component
        response = client.get("/about", headers={InertiaHeaders.ENABLED.value: "true"})
        data = decode_json(response.text)
        assert data["component"] == "About"


async def test_component_takes_precedence(
    inertia_plugin: InertiaPlugin,
    vite_plugin: VitePlugin,
    template_config: "TemplateConfig[Any]",  # pyright: ignore[reportMissingTypeArgument,reportUnknownParameterType]
) -> None:
    """Test that component takes precedence over page.

    When both 'component' and 'page' are specified, 'component' should win
    because it appears first in the default component_opt_keys tuple.
    """
    from litestar.serialization import decode_json

    @get("/conflict", component="ComponentWins", page="PageLoses")
    async def handler(request: InertiaRequest[Any, Any, Any]) -> str:
        return request.inertia.route_component or ""

    with create_test_client(
        route_handlers=[handler],
        plugins=[inertia_plugin, vite_plugin],
        template_config=template_config,
        middleware=[ServerSideSessionConfig().middleware],
        stores={"sessions": MemoryStore()},
    ) as client:
        # When Inertia header is sent, it returns JSON with component
        response = client.get("/conflict", headers={InertiaHeaders.ENABLED.value: "true"})
        data = decode_json(response.text)
        assert data["component"] == "ComponentWins"


async def test_page_kwarg_with_inertia_header(
    inertia_plugin: InertiaPlugin,
    vite_plugin: VitePlugin,
    template_config: "TemplateConfig[Any]",  # pyright: ignore[reportMissingTypeArgument,reportUnknownParameterType]
) -> None:
    """Test page kwarg with Inertia header returns JSON.

    When the X-Inertia header is present, the response should be JSON
    with the page component, not HTML.
    """
    from litestar.serialization import decode_json

    @get("/", page="Home")
    async def handler(request: InertiaRequest[Any, Any, Any]) -> dict[str, str]:
        return {"message": "Hello"}

    with create_test_client(
        route_handlers=[handler],
        plugins=[inertia_plugin, vite_plugin],
        template_config=template_config,
        middleware=[ServerSideSessionConfig().middleware],
        stores={"sessions": MemoryStore()},
    ) as client:
        response = client.get("/", headers={InertiaHeaders.ENABLED.value: "true"})
        data = decode_json(response.text)
        assert data["component"] == "Home"
        assert data["url"] == "/"
        assert data["props"]["message"] == "Hello"
        assert "content" not in data["props"]


async def test_no_component_or_page_returns_none(
    inertia_plugin: InertiaPlugin,
    vite_plugin: VitePlugin,
    template_config: "TemplateConfig[Any]",  # pyright: ignore[reportMissingTypeArgument,reportUnknownParameterType]
) -> None:
    """Test that route without component or page returns None.

    When neither 'component' nor 'page' is set, route_component should be None.
    """

    @get("/no-inertia")
    async def handler(request: Request[Any, Any, Any]) -> str:
        component = request.inertia.route_component  # pyright: ignore
        return component if component else "none"

    with create_test_client(
        route_handlers=[handler],
        plugins=[inertia_plugin, vite_plugin],
        template_config=template_config,
        middleware=[ServerSideSessionConfig().middleware],
        stores={"sessions": MemoryStore()},
    ) as client:
        response = client.get("/no-inertia")
        assert response.text == "none"


async def test_page_with_empty_string_value(
    inertia_plugin: InertiaPlugin,
    vite_plugin: VitePlugin,
    template_config: "TemplateConfig[Any]",  # pyright: ignore[reportMissingTypeArgument,reportUnknownParameterType]
) -> None:
    """Test that page="" (empty string) is treated as None.

    Empty string values should be ignored and treated as if not set.
    """

    @get("/empty", page="", component="Fallback")
    async def handler(request: InertiaRequest[Any, Any, Any]) -> str:
        return request.inertia.route_component or "none"

    with create_test_client(
        route_handlers=[handler],
        plugins=[inertia_plugin, vite_plugin],
        template_config=template_config,
        middleware=[ServerSideSessionConfig().middleware],
        stores={"sessions": MemoryStore()},
    ) as client:
        # With Inertia header, should return JSON
        from litestar.serialization import decode_json

        response = client.get("/empty", headers={InertiaHeaders.ENABLED.value: "true"})
        data = decode_json(response.text)
        # Empty page should fallback to component
        assert data["component"] == "Fallback"


async def test_inertia_enabled_check_with_page(
    inertia_plugin: InertiaPlugin,
    vite_plugin: VitePlugin,
    template_config: "TemplateConfig[Any]",  # pyright: ignore[reportMissingTypeArgument,reportUnknownParameterType]
) -> None:
    """Test that inertia_enabled is True when page is set.

    The inertia_enabled property should return True when 'page' kwarg is used.
    """

    @get("/dashboard", page="Dashboard")
    async def handler(request: InertiaRequest[Any, Any, Any]) -> str:
        return "enabled" if request.inertia_enabled else "disabled"

    with create_test_client(
        route_handlers=[handler],
        plugins=[inertia_plugin, vite_plugin],
        template_config=template_config,
        middleware=[ServerSideSessionConfig().middleware],
        stores={"sessions": MemoryStore()},
    ) as client:
        # Should render HTML since inertia is enabled
        response = client.get("/dashboard")
        assert response.text.startswith("<!DOCTYPE html>")


async def test_page_with_special_characters(
    inertia_plugin: InertiaPlugin,
    vite_plugin: VitePlugin,
    template_config: "TemplateConfig[Any]",  # pyright: ignore[reportMissingTypeArgument,reportUnknownParameterType]
) -> None:
    """Test page kwarg with special characters.

    Component names with special characters should be handled correctly.
    """
    from litestar.serialization import decode_json

    @get("/special", page="Admin/Users/Index")
    async def handler(request: InertiaRequest[Any, Any, Any]) -> dict[str, str]:
        return {"data": "test"}

    with create_test_client(
        route_handlers=[handler],
        plugins=[inertia_plugin, vite_plugin],
        template_config=template_config,
        middleware=[ServerSideSessionConfig().middleware],
        stores={"sessions": MemoryStore()},
    ) as client:
        response = client.get("/special", headers={InertiaHeaders.ENABLED.value: "true"})
        data = decode_json(response.text)
        assert data["component"] == "Admin/Users/Index"
