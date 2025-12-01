import asyncio
from time import sleep
from typing import Any

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
    MergeProp,
    StaticProp,
    defer,
    extract_deferred_props,
    extract_merge_props,
    is_lazy_prop,
    is_merge_prop,
    is_or_contains_lazy_prop,
    lazy,
    lazy_render,
    merge,
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
    async def handler(request: Request[Any, Any, Any]) -> dict[str, Any]:
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
    async def handler(request: Request[Any, Any, Any]) -> dict[str, Any]:
        return {"thing": "value"}

    with create_test_client(
        route_handlers=[handler],
        plugins=[inertia_plugin, vite_plugin],
        template_config=template_config,
        middleware=[ServerSideSessionConfig().middleware],
        stores={"sessions": MemoryStore()},
    ) as client:
        response = client.get("/", headers={InertiaHeaders.ENABLED.value: "true"})
        data = response.json()
        assert data["component"] == "Home"
        assert data["url"] == "/"
        assert "version" in data  # version is a hash, not a fixed value
        assert data["props"]["flash"] == {}
        assert data["props"]["errors"] == {}
        assert data["props"]["csrf_token"] == ""
        assert data["props"]["thing"] == "value"
        assert "content" not in data["props"]


async def test_component_inertia_flash_header_enabled(
    inertia_plugin: InertiaPlugin,
    vite_plugin: VitePlugin,
    template_config: TemplateConfig,  # pyright: ignore[reportUnknownParameterType,reportMissingTypeArgument]
) -> None:
    @get("/", component="Home")
    async def handler(request: Request[Any, Any, Any]) -> dict[str, Any]:
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
        data = response.json()
        assert data["component"] == "Home"
        assert data["url"] == "/"
        assert "version" in data  # version is a hash, not a fixed value
        assert data["props"]["flash"] == {"info": ["a flash message"]}
        assert data["props"]["errors"] == {}
        assert data["props"]["csrf_token"] == ""
        assert data["props"]["thing"] == "value"
        assert "content" not in data["props"]


async def test_component_inertia_shared_flash_header_enabled(
    inertia_plugin: InertiaPlugin,
    vite_plugin: VitePlugin,
    template_config: TemplateConfig,  # pyright: ignore[reportUnknownParameterType,reportMissingTypeArgument]
) -> None:
    @get("/", component="Home")
    async def handler(request: Request[Any, Any, Any]) -> dict[str, Any]:
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
        data = response.json()
        assert data["component"] == "Home"
        assert data["url"] == "/"
        assert "version" in data  # version is a hash, not a fixed value
        assert data["props"]["auth"] == {"user": "nobody"}
        assert data["props"]["flash"] == {"info": ["a flash message"]}
        assert data["props"]["errors"] == {}
        assert data["props"]["csrf_token"] == ""
        assert data["props"]["thing"] == "value"
        assert "content" not in data["props"]


async def test_default_route_response_no_component(
    inertia_plugin: InertiaPlugin,
    vite_plugin: VitePlugin,
    template_config: TemplateConfig,  # pyright: ignore[reportUnknownParameterType,reportMissingTypeArgument]
) -> None:
    @get("/")
    async def handler(request: Request[Any, Any, Any]) -> dict[str, Any]:
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
    async def handler(request: Request[Any, Any, Any]) -> dict[str, Any]:
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
        data = response.json()
        assert data["component"] == "Home"
        assert data["url"] == "/"
        assert "version" in data  # version is a hash, not a fixed value
        assert data["props"]["flash"] == {}
        assert data["props"]["errors"] == {}
        assert data["props"]["csrf_token"] == ""
        assert data["props"]["thing"] == "value"
        assert "content" not in data["props"]


async def test_unauthenticated_redirect(
    inertia_plugin: InertiaPlugin,
    vite_plugin: VitePlugin,
    template_config: TemplateConfig,  # pyright: ignore[reportUnknownParameterType,reportMissingTypeArgument]
) -> None:
    @get("/", component="Home")
    async def handler(request: Request[Any, Any, Any]) -> dict[str, Any]:
        raise NotAuthorizedException(detail="User not authenticated")

    @get("/login", component="Login")
    async def login_handler(request: Request[Any, Any, Any]) -> dict[str, Any]:
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
    async def handler(request: Request[Any, Any, Any]) -> dict[str, Any]:
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


async def test_props_flattened_and_preserve_explicit_content(
    inertia_plugin: InertiaPlugin,
    vite_plugin: VitePlugin,
    template_config: TemplateConfig,  # pyright: ignore[reportUnknownParameterType,reportMissingTypeArgument]
) -> None:
    @get("/", component="Home")
    async def handler(request: Request[Any, Any, Any]) -> dict[str, Any]:
        share(request, "overlap", "shared")
        return {"overlap": "route", "content": {"keep": True}, "books": [1, 2]}

    with create_test_client(
        route_handlers=[handler],
        template_config=template_config,
        plugins=[inertia_plugin, vite_plugin],
        middleware=[ServerSideSessionConfig().middleware],
        stores={"sessions": MemoryStore()},
    ) as client:
        response = client.get("/", headers={InertiaHeaders.ENABLED.value: "true"})
        props = response.json()["props"]
        # route content overrides shared props for overlapping keys
        assert props["overlap"] == "route"
        # explicit content key is preserved alongside flattened keys
        assert props["content"] == {"keep": True}
        # other content entries are lifted to top level
        assert props["books"] == [1, 2]


async def test_non_mapping_content_remains_nested(
    inertia_plugin: InertiaPlugin,
    vite_plugin: VitePlugin,
    template_config: TemplateConfig,  # pyright: ignore[reportUnknownParameterType,reportMissingTypeArgument]
) -> None:
    @get("/", component="Home")
    async def handler(request: Request[Any, Any, Any]) -> list[int]:
        return [1, 2, 3]

    with create_test_client(
        route_handlers=[handler],
        template_config=template_config,
        plugins=[inertia_plugin, vite_plugin],
        middleware=[ServerSideSessionConfig().middleware],
        stores={"sessions": MemoryStore()},
    ) as client:
        response = client.get("/", headers={InertiaHeaders.ENABLED.value: "true"})
        props = response.json()["props"]
        assert props["content"] == [1, 2, 3]
        assert "0" not in props  # ensure list not spread


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
    async def handler(request: Request[Any, Any, Any]) -> dict[str, Any]:
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
        assert response.json()["props"]["static"] == "value"
        assert "content" not in response.json()["props"]

        # Partial data, only specified deferred props should be rendered
        response_partial = client.get(
            "/",
            headers={
                InertiaHeaders.ENABLED.value: "true",
                InertiaHeaders.PARTIAL_DATA.value: "deferred,list_deferred",
                InertiaHeaders.PARTIAL_COMPONENT.value: "Home",
            },
        )
        assert response_partial.json()["props"]["static"] == "value"
        assert response_partial.json()["props"]["deferred"] == "deferred_value"
        assert response_partial.json()["props"]["list_deferred"] == ["list_deferred_value"]
        assert "content" not in response_partial.json()["props"]
        # Partial data, only specified deferred props should be rendered
        response_partial2 = client.get(
            "/",
            headers={
                InertiaHeaders.ENABLED.value: "true",
                InertiaHeaders.PARTIAL_DATA.value: "deferred,list_deferred",
                InertiaHeaders.PARTIAL_COMPONENT.value: "Home",
            },
        )
        assert response_partial2.json()["props"]["static"] == "value"
        assert response_partial2.json()["props"]["deferred"] == "deferred_value"
        assert response_partial2.json()["props"]["list_deferred"] == ["list_deferred_value"]
        assert "content" not in response_partial2.json()["props"]
        response_partial3 = client.get(
            "/",
            headers={
                InertiaHeaders.ENABLED.value: "true",
                InertiaHeaders.PARTIAL_DATA.value: "deferred,optional,list_deferred,sync",
                InertiaHeaders.PARTIAL_COMPONENT.value: "Home",
            },
        )
        assert response_partial3.json()["props"]["static"] == "value"
        assert response_partial3.json()["props"]["deferred"] == "deferred_value"
        assert response_partial3.json()["props"]["optional"] == "async_result"
        assert response_partial3.json()["props"]["list_deferred"] == ["list_deferred_value"]
        assert response_partial3.json()["props"]["sync"] == "sync_result"
        assert "content" not in response_partial3.json()["props"]


# =====================================================
# Inertia.js v2 Protocol Tests
# =====================================================


async def test_defer_helper_with_groups() -> None:
    """Test defer() helper creates DeferredProp with group support."""

    def get_teams() -> list[str]:
        return ["team1", "team2"]

    def get_projects() -> list[str]:
        return ["project1", "project2"]

    # Default group
    prop1 = defer("permissions", lambda: ["read", "write"])
    assert isinstance(prop1, DeferredProp)
    assert prop1.key == "permissions"
    assert prop1.group == "default"
    assert prop1.render() == ["read", "write"]

    # Custom group
    prop2 = defer("teams", get_teams, group="attributes")
    assert prop2.key == "teams"
    assert prop2.group == "attributes"
    assert prop2.render() == ["team1", "team2"]

    prop3 = defer("projects", get_projects, group="attributes")
    assert prop3.key == "projects"
    assert prop3.group == "attributes"
    assert prop3.render() == ["project1", "project2"]


async def test_extract_deferred_props() -> None:
    """Test extract_deferred_props extracts group metadata."""
    props = {
        "users": ["user1", "user2"],  # regular prop
        "teams": defer("teams", lambda: [], group="attributes"),
        "projects": defer("projects", lambda: [], group="attributes"),
        "permissions": defer("permissions", lambda: []),  # default group
    }

    groups = extract_deferred_props(props)
    assert "default" in groups
    assert "attributes" in groups
    assert groups["default"] == ["permissions"]
    assert sorted(groups["attributes"]) == ["projects", "teams"]


async def test_merge_helper() -> None:
    """Test merge() helper creates MergeProp with strategies."""
    # Default append strategy
    prop1 = merge("posts", [{"id": 1}])
    assert isinstance(prop1, MergeProp)
    assert prop1.key == "posts"
    assert prop1.value == [{"id": 1}]
    assert prop1.strategy == "append"
    assert prop1.match_on is None

    # Prepend strategy
    prop2 = merge("messages", ["msg1"], strategy="prepend")
    assert prop2.strategy == "prepend"

    # Deep merge strategy
    prop3 = merge("user_data", {"name": "test"}, strategy="deep")
    assert prop3.strategy == "deep"

    # With match_on (string)
    prop4 = merge("items", [{"id": 1}], match_on="id")
    assert prop4.match_on == ["id"]

    # With match_on (list)
    prop5 = merge("items", [{"id": 1, "type": "x"}], match_on=["id", "type"])
    assert prop5.match_on == ["id", "type"]


async def test_is_merge_prop() -> None:
    """Test is_merge_prop type guard."""
    assert is_merge_prop(merge("test", [])) is True
    assert is_merge_prop(MergeProp("test", [])) is True
    assert is_merge_prop("string") is False
    assert is_merge_prop([]) is False
    assert is_merge_prop(lazy("test", "value")) is False


async def test_extract_merge_props() -> None:
    """Test extract_merge_props extracts strategy metadata."""
    props = {
        "users": ["user1"],  # regular prop
        "posts": merge("posts", [{"id": 1}]),  # append
        "messages": merge("messages", [], strategy="prepend"),
        "config": merge("config", {}, strategy="deep"),
        "items": merge("items", [], match_on="id"),
    }

    merge_list, prepend_list, deep_list, match_on = extract_merge_props(props)

    assert sorted(merge_list) == ["items", "posts"]
    assert prepend_list == ["messages"]
    assert deep_list == ["config"]
    assert match_on == {"items": ["id"]}


async def test_should_render_with_partial_except() -> None:
    """Test should_render with v2 partial_except parameter."""
    prop = lazy("test", "value")

    # No filtering - lazy props not rendered
    assert should_render(prop) is False

    # partial_data - include if in set
    assert should_render(prop, partial_data={"test"}) is True
    assert should_render(prop, partial_data={"other"}) is False

    # partial_except - exclude if in set (v2)
    assert should_render(prop, partial_except={"test"}) is False
    assert should_render(prop, partial_except={"other"}) is True

    # partial_except takes precedence
    assert should_render(prop, partial_data={"test"}, partial_except={"test"}) is False

    # Regular values always render
    assert should_render("regular") is True


async def test_lazy_render_with_partial_except() -> None:
    """Test lazy_render with v2 partial_except parameter."""
    data = {
        "static": "value",
        "deferred1": lazy("deferred1", "val1"),
        "deferred2": lazy("deferred2", "val2"),
    }

    # partial_except - render all except specified
    result = lazy_render(data, partial_except={"deferred1"})
    assert result == {
        "static": "value",
        "deferred2": "val2",
    }

    # Multiple exclusions
    result2 = lazy_render(data, partial_except={"deferred1", "deferred2"})
    assert result2 == {
        "static": "value",
    }
