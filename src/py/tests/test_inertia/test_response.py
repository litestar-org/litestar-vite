from __future__ import annotations

import asyncio
from time import sleep
from typing import Any, Dict

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
from litestar_vite.inertia.helpers import (
    DeferredProp,
    StaticProp,
    is_lazy_prop,
    is_or_contains_lazy_prop,
    lazy,
    lazy_render,
    share,
    should_render,
)
from litestar_vite.inertia.response import (
    InertiaBack,
    InertiaExternalRedirect,
)
from litestar_vite.plugin import VitePlugin


async def test_component_enabled(
    inertia_plugin: InertiaPlugin,
    vite_plugin: VitePlugin,
    template_config: TemplateConfig,  # pyright: ignore[reportUnknownParameterType,reportMissingTypeArgument]
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
    inertia_plugin: InertiaPlugin,
    vite_plugin: VitePlugin,
    template_config: TemplateConfig,  # pyright: ignore[reportUnknownParameterType,reportMissingTypeArgument]
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
    inertia_plugin: InertiaPlugin,
    vite_plugin: VitePlugin,
    template_config: TemplateConfig,  # pyright: ignore[reportUnknownParameterType,reportMissingTypeArgument]
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
    template_config: TemplateConfig,  # pyright: ignore[reportUnknownParameterType,reportMissingTypeArgument]
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
    inertia_plugin: InertiaPlugin,
    vite_plugin: VitePlugin,
    template_config: TemplateConfig,  # pyright: ignore[reportUnknownParameterType,reportMissingTypeArgument]
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


async def test_component_inertia_invalid_version(
    inertia_plugin: InertiaPlugin,
    vite_plugin: VitePlugin,
    template_config: TemplateConfig,  # pyright: ignore[reportUnknownParameterType,reportMissingTypeArgument]
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
        assert response.status_code == 200
        assert (
            response.content
            == b'{"component":"Home","url":"/","version":"1.0","props":{"flash":{},"errors":{},"csrf_token":"","content":{"thing":"value"}}}'
        )


async def test_unauthenticated_redirect(
    inertia_plugin: InertiaPlugin,
    vite_plugin: VitePlugin,
    template_config: TemplateConfig,  # pyright: ignore[reportUnknownParameterType,reportMissingTypeArgument]
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
    inertia_plugin: InertiaPlugin,
    vite_plugin: VitePlugin,
    template_config: TemplateConfig,  # pyright: ignore[reportUnknownParameterType,reportMissingTypeArgument]
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


async def test_inertia_external_redirect(
    inertia_plugin: InertiaPlugin,
    vite_plugin: VitePlugin,
    template_config: TemplateConfig,  # pyright: ignore[reportUnknownParameterType,reportMissingTypeArgument]
) -> None:
    @get("/external", component="External")
    async def handler(request: Request[Any, Any, Any]) -> InertiaExternalRedirect:
        return InertiaExternalRedirect(request, "/external")

    with create_test_client(
        route_handlers=[handler],
        template_config=template_config,
        plugins=[inertia_plugin, vite_plugin],
        middleware=[ServerSideSessionConfig().middleware],
        stores={"sessions": MemoryStore()},
    ) as client:
        response = client.get(
            "/external",
            headers={InertiaHeaders.ENABLED.value: "true"},
            follow_redirects=False,
        )
        assert response.status_code == 409
        assert response.headers.get("X-Inertia-Location") == "/external"


async def test_inertia_back(
    inertia_plugin: InertiaPlugin,
    vite_plugin: VitePlugin,
    template_config: TemplateConfig,  # pyright: ignore[reportUnknownParameterType,reportMissingTypeArgument]
) -> None:
    @get("/back", component="Back")
    async def handler(request: Request[Any, Any, Any]) -> InertiaBack:
        return InertiaBack(request)

    with create_test_client(
        route_handlers=[handler],
        template_config=template_config,
        plugins=[inertia_plugin, vite_plugin],
        middleware=[ServerSideSessionConfig().middleware],
        stores={"sessions": MemoryStore()},
    ) as client:
        response = client.get(
            "/back",
            headers={InertiaHeaders.ENABLED.value: "true", "Referer": "/previous"},
            follow_redirects=False,
        )
        assert response.status_code == 307
        assert response.headers.get("location") == "/previous"


def test_deferred_prop_render() -> None:
    # Test rendering a callable

    def simulated_expensive_sync_function() -> str:
        sleep(0.5)
        return "callable_result"

    async def simulated_expensive_async_function() -> str:
        await asyncio.sleep(0.5)
        return "async_result"

    test_prop_1 = lazy("test_prop_1", simulated_expensive_sync_function)
    assert test_prop_1.render() == "callable_result"
    test_prop_2 = lazy("test_prop_2", simulated_expensive_async_function)
    assert test_prop_2.render() == "async_result"

    # Test rendering an async callable
    async def async_callable_func() -> str:
        return "async_result"

    prop_async_callable = DeferredProp[str, str](key="async_callable", value=async_callable_func)
    assert prop_async_callable.render() == "async_result"


async def test_static_prop_render() -> None:
    # Test rendering a static value
    prop_static_1 = StaticProp(key="static", value="static_value")
    assert prop_static_1.render() == "static_value"

    prop_static_2 = StaticProp(key="static", value=1)
    assert prop_static_2.render() == 1

    class TestClass:
        def __str__(self) -> str:
            return "test_class_result"

    prop_static_3 = StaticProp(key="static", value=TestClass())
    assert isinstance(prop_static_3.render(), TestClass)

    prop_static_4 = lazy("static", None)
    assert prop_static_4.render() is None

    vals: list[int] = []
    prop_static_5 = StaticProp(key="static", value=vals)
    assert prop_static_5.render() == []

    vals2: dict[str, int] = {}
    prop_static_6 = StaticProp(key="static", value=vals2)
    assert prop_static_6.render() == {}

    vals3: tuple[int] = (1,)
    prop_static_7 = StaticProp(key="static", value=vals3)
    assert prop_static_7.render() == (1,)


async def test_is_deferred_prop() -> None:
    async def simulated_expensive_async_function() -> str:
        await asyncio.sleep(0.5)
        return "async_result"

    assert is_lazy_prop(DeferredProp(key="test", value=simulated_expensive_async_function)) is True
    assert is_lazy_prop(StaticProp(key="static", value="static_value")) is True

    assert is_lazy_prop("string") is False
    assert is_lazy_prop(123) is False
    assert is_lazy_prop(None) is False


async def test_should_render() -> None:
    prop = lazy("test", "value")
    assert should_render(prop) is False
    assert should_render(prop, partial_data={"test"}) is True
    assert should_render(prop, partial_data={"other"}) is False
    assert should_render("string") is True


async def test_is_or_contains_lazy_prop() -> None:
    assert is_or_contains_lazy_prop(lazy("test", "value")) is True
    assert is_or_contains_lazy_prop({"key": lazy("key", "value")}) is True
    assert is_or_contains_lazy_prop(["string", lazy("string", "value")]) is True
    assert is_or_contains_lazy_prop("string") is False
    assert is_or_contains_lazy_prop({"key": "value"}) is False


async def test_filter_deferred_props() -> None:
    data = {
        "static": "value",
        "deferred": lazy("deferred", "deferred_value"),
        "nested": {
            "nested_deferred": lazy("nested_deferred", "nested_deferred_value"),
        },
        "list": [lazy("list_deferred", "list_deferred_value")],
    }

    # No partial data, all deferred props should not be rendered
    standard_response = lazy_render(data)
    assert standard_response == {
        "static": "value",
        "nested": {},
        "list": [],
    }

    # Partial data, only specified deferred props should be rendered
    partial_response_deferred = lazy_render(data, partial_data={"deferred"})
    assert partial_response_deferred == {
        "static": "value",
        "deferred": "deferred_value",
        "nested": {},
        "list": [],
    }

    partial_response_list = lazy_render(data, partial_data={"list_deferred"})
    assert partial_response_list == {
        "static": "value",
        "nested": {},
        "list": ["list_deferred_value"],
    }

    partial_response_multiple = lazy_render(data, partial_data={"nested_deferred", "list_deferred"})
    assert partial_response_multiple == {
        "static": "value",
        "nested": {"nested_deferred": "nested_deferred_value"},
        "list": ["list_deferred_value"],
    }

    partial_response_nested_deferred = lazy_render(data, partial_data={"nested_deferred"})
    assert partial_response_nested_deferred == {
        "static": "value",
        "nested": {"nested_deferred": "nested_deferred_value"},
        "list": [],
    }


async def test_lazy_helper() -> None:
    prop = lazy("test", "value")
    assert isinstance(prop, StaticProp)
    assert prop.key == "test"
    assert prop.render() == "value"

    def test_func() -> str:
        return "value"

    prop2 = lazy("test", test_func)
    assert isinstance(prop2, DeferredProp)
    assert prop2.key == "test"
    assert prop2.render() == "value"


async def test_component_inertia_deferred_props(
    inertia_plugin: InertiaPlugin,
    vite_plugin: VitePlugin,
    template_config: TemplateConfig,  # pyright: ignore[reportUnknownParameterType,reportMissingTypeArgument]
) -> None:
    async def simulated_expensive_async_function() -> str:
        await asyncio.sleep(0.5)
        return "async_result"

    def simulated_expensive_sync_function() -> str:
        return "sync_result"

    @get("/", component="Home")
    async def handler(request: Request[Any, Any, Any]) -> Dict[str, Any]:
        return {
            "static": "value",
            "deferred": lazy("deferred", "deferred_value"),
            "optional": lazy("optional", simulated_expensive_async_function),
            "sync": lazy("sync", simulated_expensive_sync_function),
            "list_deferred": lazy("list_deferred", ["list_deferred_value"]),
        }

    with create_test_client(
        route_handlers=[handler],
        template_config=template_config,
        plugins=[inertia_plugin, vite_plugin],
        middleware=[ServerSideSessionConfig().middleware],
        stores={"sessions": MemoryStore()},
    ) as client:
        # No partial data, all deferred props should be rendered
        response = client.get("/", headers={InertiaHeaders.ENABLED.value: "true"})
        assert response.json()["props"]["content"] == {
            "static": "value",
        }

        # Partial data, only specified deferred props should be rendered
        response_partial = client.get(
            "/",
            headers={
                InertiaHeaders.ENABLED.value: "true",
                InertiaHeaders.PARTIAL_DATA.value: "deferred,list_deferred",
                InertiaHeaders.PARTIAL_COMPONENT.value: "Home",
            },
        )
        assert response_partial.json()["props"]["content"] == {
            "static": "value",
            "deferred": "deferred_value",
            "list_deferred": ["list_deferred_value"],
        }
        # Partial data, only specified deferred props should be rendered
        response_partial2 = client.get(
            "/",
            headers={
                InertiaHeaders.ENABLED.value: "true",
                InertiaHeaders.PARTIAL_DATA.value: "deferred,list_deferred",
                InertiaHeaders.PARTIAL_COMPONENT.value: "Home",
            },
        )
        assert response_partial2.json()["props"]["content"] == {
            "static": "value",
            "deferred": "deferred_value",
            "list_deferred": ["list_deferred_value"],
        }
        response_partial3 = client.get(
            "/",
            headers={
                InertiaHeaders.ENABLED.value: "true",
                InertiaHeaders.PARTIAL_DATA.value: "deferred,optional,list_deferred,sync",
                InertiaHeaders.PARTIAL_COMPONENT.value: "Home",
            },
        )
        assert response_partial3.json()["props"]["content"] == {
            "static": "value",
            "deferred": "deferred_value",
            "optional": "async_result",
            "list_deferred": ["list_deferred_value"],
            "sync": "sync_result",
        }
