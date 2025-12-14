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
from litestar_vite.inertia.response import InertiaBack, InertiaExternalRedirect
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
        plugins=[inertia_plugin, vite_plugin, FlashPlugin(config=FlashConfig(template_config=template_config))],
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
        plugins=[inertia_plugin, vite_plugin, FlashPlugin(config=FlashConfig(template_config=template_config))],
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


async def test_component_inertia_version_mismatch_returns_409(
    inertia_plugin: InertiaPlugin,
    vite_plugin: VitePlugin,
    template_config: TemplateConfig,  # pyright: ignore[reportUnknownParameterType,reportMissingTypeArgument]
) -> None:
    """Test that version mismatch returns 409 with X-Inertia-Location header per protocol."""

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
            "/", headers={InertiaHeaders.ENABLED.value: "true", InertiaHeaders.VERSION.value: "wrong"}
        )
        # Per Inertia protocol: version mismatch returns 409 with X-Inertia-Location
        assert response.status_code == 409
        assert InertiaHeaders.LOCATION.value in response.headers
        assert response.headers[InertiaHeaders.LOCATION.value] == "http://testserver.local/"


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
        response = client.get("/external", headers={InertiaHeaders.ENABLED.value: "true"}, follow_redirects=False)
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
            "/back", headers={InertiaHeaders.ENABLED.value: "true", "Referer": "/previous"}, follow_redirects=False
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

    class RenderableObject:
        def __str__(self) -> str:
            return "test_class_result"

    prop_static_3 = StaticProp(key="static", value=RenderableObject())
    assert isinstance(prop_static_3.render(), RenderableObject)

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
        "nested": {"nested_deferred": lazy("nested_deferred", "nested_deferred_value")},
        "list": [lazy("list_deferred", "list_deferred_value")],
    }

    # No partial data, all deferred props should not be rendered
    standard_response = lazy_render(data)
    assert standard_response == {"static": "value", "nested": {}, "list": []}

    # Partial data, only specified deferred props should be rendered
    partial_response_deferred = lazy_render(data, partial_data={"deferred"})
    assert partial_response_deferred == {"static": "value", "deferred": "deferred_value", "nested": {}, "list": []}

    partial_response_list = lazy_render(data, partial_data={"list_deferred"})
    assert partial_response_list == {"static": "value", "nested": {}, "list": ["list_deferred_value"]}

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
    data = {"static": "value", "deferred1": lazy("deferred1", "val1"), "deferred2": lazy("deferred2", "val2")}

    # partial_except - render all except specified
    result = lazy_render(data, partial_except={"deferred1"})
    assert result == {"static": "value", "deferred2": "val2"}

    # Multiple exclusions
    result2 = lazy_render(data, partial_except={"deferred1", "deferred2"})
    assert result2 == {"static": "value"}


# =====================================================
# X-Inertia-Version Header Tests
# =====================================================


async def test_inertia_response_includes_version_header_json(
    inertia_plugin: InertiaPlugin,
    vite_plugin: VitePlugin,
    template_config: TemplateConfig,  # pyright: ignore[reportUnknownParameterType,reportMissingTypeArgument]
) -> None:
    """Test that X-Inertia-Version header is included in JSON responses."""

    @get("/", component="Home")
    async def handler(request: Request[Any, Any, Any]) -> dict[str, Any]:
        return {"data": "value"}

    with create_test_client(
        route_handlers=[handler],
        template_config=template_config,
        plugins=[inertia_plugin, vite_plugin],
        middleware=[ServerSideSessionConfig().middleware],
        stores={"sessions": MemoryStore()},
    ) as client:
        response = client.get("/", headers={InertiaHeaders.ENABLED.value: "true"})
        # X-Inertia-Version header must be present per protocol
        assert "X-Inertia-Version" in response.headers
        # Version should match the asset version
        assert response.headers["X-Inertia-Version"] == response.json()["version"]


async def test_inertia_response_includes_version_header_html(
    inertia_plugin: InertiaPlugin,
    vite_plugin: VitePlugin,
    template_config: TemplateConfig,  # pyright: ignore[reportUnknownParameterType,reportMissingTypeArgument]
) -> None:
    """Test that X-Inertia-Version header is included in HTML responses."""

    @get("/", component="Home")
    async def handler(request: Request[Any, Any, Any]) -> dict[str, Any]:
        return {"data": "value"}

    with create_test_client(
        route_handlers=[handler],
        template_config=template_config,
        plugins=[inertia_plugin, vite_plugin],
        middleware=[ServerSideSessionConfig().middleware],
        stores={"sessions": MemoryStore()},
    ) as client:
        # Request without X-Inertia header (initial page load)
        response = client.get("/")
        # X-Inertia-Version header should be present for HTML responses too
        assert "X-Inertia-Version" in response.headers
        # Should be a valid version string
        assert len(response.headers["X-Inertia-Version"]) > 0


# =====================================================
# History Encryption Tests (v2)
# =====================================================


async def test_encrypt_history_response_parameter(
    inertia_plugin: InertiaPlugin,
    vite_plugin: VitePlugin,
    template_config: TemplateConfig,  # pyright: ignore[reportUnknownParameterType,reportMissingTypeArgument]
) -> None:
    """Test that encrypt_history parameter sets encryptHistory in page props."""
    from litestar_vite.inertia.response import InertiaResponse

    @get("/secure", component="Secure")
    async def handler(request: Request[Any, Any, Any]) -> InertiaResponse[dict[str, str]]:
        return InertiaResponse({"secret": "data"}, encrypt_history=True)

    with create_test_client(
        route_handlers=[handler],
        template_config=template_config,
        plugins=[inertia_plugin, vite_plugin],
        middleware=[ServerSideSessionConfig().middleware],
        stores={"sessions": MemoryStore()},
    ) as client:
        response = client.get("/secure", headers={InertiaHeaders.ENABLED.value: "true"})
        data = response.json()
        # encryptHistory should be true (camelCase in JSON)
        assert data["encryptHistory"] is True


async def test_encrypt_history_defaults_to_false(
    inertia_plugin: InertiaPlugin,
    vite_plugin: VitePlugin,
    template_config: TemplateConfig,  # pyright: ignore[reportUnknownParameterType,reportMissingTypeArgument]
) -> None:
    """Test that encrypt_history defaults to false when not set."""

    @get("/", component="Home")
    async def handler(request: Request[Any, Any, Any]) -> dict[str, Any]:
        return {"data": "value"}

    with create_test_client(
        route_handlers=[handler],
        template_config=template_config,
        plugins=[inertia_plugin, vite_plugin],
        middleware=[ServerSideSessionConfig().middleware],
        stores={"sessions": MemoryStore()},
    ) as client:
        response = client.get("/", headers={InertiaHeaders.ENABLED.value: "true"})
        data = response.json()
        # encryptHistory should be false by default
        assert data["encryptHistory"] is False


async def test_encrypt_history_config_default(
    vite_plugin: VitePlugin,
    template_config: TemplateConfig,  # pyright: ignore[reportUnknownParameterType,reportMissingTypeArgument]
) -> None:
    """Test that InertiaConfig.encrypt_history sets the default."""
    from litestar_vite.config import InertiaConfig
    from litestar_vite.inertia.plugin import InertiaPlugin

    # Create plugin with encrypt_history enabled globally
    inertia_config = InertiaConfig(root_template="index.html.j2", encrypt_history=True)
    inertia_plugin_encrypted = InertiaPlugin(config=inertia_config)

    @get("/", component="Home")
    async def handler(request: Request[Any, Any, Any]) -> dict[str, Any]:
        return {"data": "value"}

    with create_test_client(
        route_handlers=[handler],
        template_config=template_config,
        plugins=[inertia_plugin_encrypted, vite_plugin],
        middleware=[ServerSideSessionConfig().middleware],
        stores={"sessions": MemoryStore()},
    ) as client:
        response = client.get("/", headers={InertiaHeaders.ENABLED.value: "true"})
        data = response.json()
        # Should inherit from config
        assert data["encryptHistory"] is True


async def test_encrypt_history_response_overrides_config(
    vite_plugin: VitePlugin,
    template_config: TemplateConfig,  # pyright: ignore[reportUnknownParameterType,reportMissingTypeArgument]
) -> None:
    """Test that response-level encrypt_history overrides config default."""
    from litestar_vite.config import InertiaConfig
    from litestar_vite.inertia.plugin import InertiaPlugin
    from litestar_vite.inertia.response import InertiaResponse

    # Create plugin with encrypt_history enabled globally
    inertia_config = InertiaConfig(root_template="index.html.j2", encrypt_history=True)
    inertia_plugin_encrypted = InertiaPlugin(config=inertia_config)

    @get("/public", component="Public")
    async def handler(request: Request[Any, Any, Any]) -> InertiaResponse[dict[str, str]]:
        # Explicitly disable for this response
        return InertiaResponse({"data": "value"}, encrypt_history=False)

    with create_test_client(
        route_handlers=[handler],
        template_config=template_config,
        plugins=[inertia_plugin_encrypted, vite_plugin],
        middleware=[ServerSideSessionConfig().middleware],
        stores={"sessions": MemoryStore()},
    ) as client:
        response = client.get("/public", headers={InertiaHeaders.ENABLED.value: "true"})
        data = response.json()
        # Response parameter should override config
        assert data["encryptHistory"] is False


async def test_clear_history_parameter(
    inertia_plugin: InertiaPlugin,
    vite_plugin: VitePlugin,
    template_config: TemplateConfig,  # pyright: ignore[reportUnknownParameterType,reportMissingTypeArgument]
) -> None:
    """Test that clear_history parameter sets clearHistory in page props."""
    from litestar_vite.inertia.response import InertiaResponse

    @get("/logout", component="Logout")
    async def handler(request: Request[Any, Any, Any]) -> InertiaResponse[dict[str, str]]:
        return InertiaResponse({"message": "Logged out"}, clear_history=True)

    with create_test_client(
        route_handlers=[handler],
        template_config=template_config,
        plugins=[inertia_plugin, vite_plugin],
        middleware=[ServerSideSessionConfig().middleware],
        stores={"sessions": MemoryStore()},
    ) as client:
        response = client.get("/logout", headers={InertiaHeaders.ENABLED.value: "true"})
        data = response.json()
        # clearHistory should be true (camelCase in JSON)
        assert data["clearHistory"] is True


async def test_clear_history_defaults_to_false(
    inertia_plugin: InertiaPlugin,
    vite_plugin: VitePlugin,
    template_config: TemplateConfig,  # pyright: ignore[reportUnknownParameterType,reportMissingTypeArgument]
) -> None:
    """Test that clear_history defaults to false."""

    @get("/", component="Home")
    async def handler(request: Request[Any, Any, Any]) -> dict[str, Any]:
        return {"data": "value"}

    with create_test_client(
        route_handlers=[handler],
        template_config=template_config,
        plugins=[inertia_plugin, vite_plugin],
        middleware=[ServerSideSessionConfig().middleware],
        stores={"sessions": MemoryStore()},
    ) as client:
        response = client.get("/", headers={InertiaHeaders.ENABLED.value: "true"})
        data = response.json()
        # clearHistory should be false by default
        assert data["clearHistory"] is False


# =====================================================
# Scroll Props Tests (v2)
# =====================================================


async def test_scroll_props_parameter(
    inertia_plugin: InertiaPlugin,
    vite_plugin: VitePlugin,
    template_config: TemplateConfig,  # pyright: ignore[reportUnknownParameterType,reportMissingTypeArgument]
) -> None:
    """Test that scroll_props parameter sets scroll config in page props."""
    from litestar_vite.inertia.helpers import scroll_props
    from litestar_vite.inertia.response import InertiaResponse

    @get("/posts", component="Posts")
    async def handler(request: Request[Any, Any, Any], page: int = 1) -> InertiaResponse[dict[str, Any]]:
        posts = [{"id": i, "title": f"Post {i}"} for i in range((page - 1) * 10, page * 10)]
        return InertiaResponse(
            {"posts": posts},
            scroll_props=scroll_props(
                current_page=page,
                previous_page=page - 1 if page > 1 else None,
                next_page=page + 1 if page < 5 else None,
            ),
        )

    with create_test_client(
        route_handlers=[handler],
        template_config=template_config,
        plugins=[inertia_plugin, vite_plugin],
        middleware=[ServerSideSessionConfig().middleware],
        stores={"sessions": MemoryStore()},
    ) as client:
        response = client.get("/posts?page=2", headers={InertiaHeaders.ENABLED.value: "true"})
        data = response.json()
        # scrollProps should be present with correct data (camelCase)
        assert "scrollProps" in data
        scroll_config = data["scrollProps"]
        assert scroll_config["pageName"] == "page"
        assert scroll_config["currentPage"] == 2
        assert scroll_config["previousPage"] == 1
        assert scroll_config["nextPage"] == 3


async def test_scroll_props_first_page(
    inertia_plugin: InertiaPlugin,
    vite_plugin: VitePlugin,
    template_config: TemplateConfig,  # pyright: ignore[reportUnknownParameterType,reportMissingTypeArgument]
) -> None:
    """Test scroll_props on first page (no previous)."""
    from litestar_vite.inertia.helpers import scroll_props
    from litestar_vite.inertia.response import InertiaResponse

    @get("/items", component="Items")
    async def handler(request: Request[Any, Any, Any]) -> InertiaResponse[dict[str, list[int]]]:
        return InertiaResponse(
            {"items": [1, 2, 3]}, scroll_props=scroll_props(current_page=1, previous_page=None, next_page=2)
        )

    with create_test_client(
        route_handlers=[handler],
        template_config=template_config,
        plugins=[inertia_plugin, vite_plugin],
        middleware=[ServerSideSessionConfig().middleware],
        stores={"sessions": MemoryStore()},
    ) as client:
        response = client.get("/items", headers={InertiaHeaders.ENABLED.value: "true"})
        data = response.json()
        scroll_config = data["scrollProps"]
        assert scroll_config["currentPage"] == 1
        # previousPage should not be in JSON when None (Inertia protocol)
        assert "previousPage" not in scroll_config
        assert scroll_config["nextPage"] == 2


async def test_scroll_props_last_page(
    inertia_plugin: InertiaPlugin,
    vite_plugin: VitePlugin,
    template_config: TemplateConfig,  # pyright: ignore[reportUnknownParameterType,reportMissingTypeArgument]
) -> None:
    """Test scroll_props on last page (no next)."""
    from litestar_vite.inertia.helpers import scroll_props
    from litestar_vite.inertia.response import InertiaResponse

    @get("/items", component="Items")
    async def handler(request: Request[Any, Any, Any]) -> InertiaResponse[dict[str, list[int]]]:
        return InertiaResponse(
            {"items": [91, 92, 93]}, scroll_props=scroll_props(current_page=10, previous_page=9, next_page=None)
        )

    with create_test_client(
        route_handlers=[handler],
        template_config=template_config,
        plugins=[inertia_plugin, vite_plugin],
        middleware=[ServerSideSessionConfig().middleware],
        stores={"sessions": MemoryStore()},
    ) as client:
        response = client.get("/items", headers={InertiaHeaders.ENABLED.value: "true"})
        data = response.json()
        scroll_config = data["scrollProps"]
        assert scroll_config["currentPage"] == 10
        assert scroll_config["previousPage"] == 9
        # nextPage should not be in JSON when None
        assert "nextPage" not in scroll_config


# =====================================================
# Exception Handler Tests (GitHub #122)
# =====================================================


async def test_http_exception_preserves_status_code_for_non_inertia_requests(
    inertia_plugin: InertiaPlugin,
    vite_plugin: VitePlugin,
    template_config: TemplateConfig,  # pyright: ignore[reportUnknownParameterType,reportMissingTypeArgument]
) -> None:
    """Test that HTTPExceptions preserve their status code for non-Inertia requests.

    GitHub #122: The exception handler was converting HTTPExceptions (like
    NotAuthorizedException with 401) to InternalServerException (500) for
    non-Inertia requests.
    """

    @get("/api/protected")
    async def handler(request: Request[Any, Any, Any]) -> dict[str, Any]:
        raise NotAuthorizedException(detail="User not authenticated")

    with create_test_client(
        route_handlers=[handler],
        template_config=template_config,
        plugins=[inertia_plugin, vite_plugin],
        middleware=[ServerSideSessionConfig().middleware],
        stores={"sessions": MemoryStore()},
    ) as client:
        # Non-Inertia request (no X-Inertia header)
        response = client.get("/api/protected")
        # Should return 401, NOT 500
        assert response.status_code == 401


async def test_http_exception_403_preserved_for_non_inertia_requests(
    inertia_plugin: InertiaPlugin,
    vite_plugin: VitePlugin,
    template_config: TemplateConfig,  # pyright: ignore[reportUnknownParameterType,reportMissingTypeArgument]
) -> None:
    """Test that PermissionDeniedException (403) is preserved for non-Inertia requests."""
    from litestar.exceptions import PermissionDeniedException

    @get("/api/admin")
    async def handler(request: Request[Any, Any, Any]) -> dict[str, Any]:
        raise PermissionDeniedException(detail="Admin access required")

    with create_test_client(
        route_handlers=[handler],
        template_config=template_config,
        plugins=[inertia_plugin, vite_plugin],
        middleware=[ServerSideSessionConfig().middleware],
        stores={"sessions": MemoryStore()},
    ) as client:
        response = client.get("/api/admin")
        # Should return 403, NOT 500
        assert response.status_code == 403


async def test_http_exception_404_preserved_for_non_inertia_requests(
    inertia_plugin: InertiaPlugin,
    vite_plugin: VitePlugin,
    template_config: TemplateConfig,  # pyright: ignore[reportUnknownParameterType,reportMissingTypeArgument]
) -> None:
    """Test that NotFoundException (404) is preserved for non-Inertia requests."""
    from litestar.exceptions import NotFoundException

    @get("/api/items/{item_id:int}")
    async def handler(request: Request[Any, Any, Any], item_id: int) -> dict[str, Any]:
        raise NotFoundException(detail=f"Item {item_id} not found")

    with create_test_client(
        route_handlers=[handler],
        template_config=template_config,
        plugins=[inertia_plugin, vite_plugin],
        middleware=[ServerSideSessionConfig().middleware],
        stores={"sessions": MemoryStore()},
    ) as client:
        response = client.get("/api/items/999")
        # Should return 404, NOT 500
        assert response.status_code == 404


# Pagination Container Tests


async def test_pagination_container_default_key(
    inertia_plugin: InertiaPlugin,
    vite_plugin: VitePlugin,
    template_config: TemplateConfig,  # pyright: ignore[reportUnknownParameterType,reportMissingTypeArgument]
) -> None:
    """Test that pagination containers flatten metadata as siblings with items under default key."""
    from dataclasses import dataclass

    @dataclass
    class MockPagination:
        items: list[str]
        limit: int
        offset: int
        total: int

    @get("/users", component="Users")
    async def handler(request: Request[Any, Any, Any]) -> MockPagination:
        return MockPagination(items=["user1", "user2"], limit=10, offset=0, total=2)

    with create_test_client(
        route_handlers=[handler],
        plugins=[inertia_plugin, vite_plugin],
        template_config=template_config,
        middleware=[ServerSideSessionConfig().middleware],
        stores={"sessions": MemoryStore()},
    ) as client:
        response = client.get("/users", headers={InertiaHeaders.ENABLED.value: "true"})
        data = response.json()
        # Items under default "items" key, metadata flattened as siblings
        assert data["props"]["items"] == ["user1", "user2"]
        assert data["props"]["total"] == 2
        assert data["props"]["limit"] == 10
        assert data["props"]["offset"] == 0


async def test_pagination_container_custom_key(
    inertia_plugin: InertiaPlugin,
    vite_plugin: VitePlugin,
    template_config: TemplateConfig,  # pyright: ignore[reportUnknownParameterType,reportMissingTypeArgument]
) -> None:
    """Test that pagination containers use route's 'key' opt with metadata flattened as siblings."""
    from dataclasses import dataclass

    @dataclass
    class MockPagination:
        items: list[str]
        limit: int
        offset: int
        total: int

    @get("/users", component="Users", key="users")
    async def handler(request: Request[Any, Any, Any]) -> MockPagination:
        return MockPagination(items=["user1", "user2"], limit=10, offset=0, total=2)

    with create_test_client(
        route_handlers=[handler],
        plugins=[inertia_plugin, vite_plugin],
        template_config=template_config,
        middleware=[ServerSideSessionConfig().middleware],
        stores={"sessions": MemoryStore()},
    ) as client:
        response = client.get("/users", headers={InertiaHeaders.ENABLED.value: "true"})
        data = response.json()
        # Items under custom "users" key, metadata flattened as siblings
        assert data["props"]["users"] == ["user1", "user2"]
        assert data["props"]["total"] == 2
        assert data["props"]["limit"] == 10
        assert data["props"]["offset"] == 0
        # Top-level "items" should not exist (custom key used)
        assert "items" not in data["props"]


async def test_pagination_in_dict_preserves_key(
    inertia_plugin: InertiaPlugin,
    vite_plugin: VitePlugin,
    template_config: TemplateConfig,  # pyright: ignore[reportUnknownParameterType,reportMissingTypeArgument]
) -> None:
    """Test that pagination in dict uses dict key with metadata flattened as siblings."""
    from dataclasses import dataclass

    @dataclass
    class MockPagination:
        items: list[str]
        limit: int
        offset: int
        total: int

    @get("/users", component="Users", key="ignored")
    async def handler(request: Request[Any, Any, Any]) -> dict[str, Any]:
        return {"members": MockPagination(items=["user1", "user2"], limit=10, offset=0, total=2)}

    with create_test_client(
        route_handlers=[handler],
        plugins=[inertia_plugin, vite_plugin],
        template_config=template_config,
        middleware=[ServerSideSessionConfig().middleware],
        stores={"sessions": MemoryStore()},
    ) as client:
        response = client.get("/users", headers={InertiaHeaders.ENABLED.value: "true"})
        data = response.json()
        # Items under dict key "members", metadata flattened as siblings
        assert data["props"]["members"] == ["user1", "user2"]
        assert data["props"]["total"] == 2
        assert data["props"]["limit"] == 10
        assert data["props"]["offset"] == 0
        assert "ignored" not in data["props"]


async def test_pagination_with_infinite_scroll_opt(
    inertia_plugin: InertiaPlugin,
    vite_plugin: VitePlugin,
    template_config: TemplateConfig,  # pyright: ignore[reportUnknownParameterType,reportMissingTypeArgument]
) -> None:
    """Test that infinite_scroll=True calculates scroll_props with metadata flattened as siblings."""
    from dataclasses import dataclass

    @dataclass
    class MockPagination:
        items: list[str]
        limit: int
        offset: int
        total: int

    @get("/posts", component="Posts", key="posts", infinite_scroll=True)
    async def handler(request: Request[Any, Any, Any]) -> MockPagination:
        # Page 2 of 5 (offset=10, limit=10, total=50)
        return MockPagination(items=["post1", "post2"], limit=10, offset=10, total=50)

    with create_test_client(
        route_handlers=[handler],
        plugins=[inertia_plugin, vite_plugin],
        template_config=template_config,
        middleware=[ServerSideSessionConfig().middleware],
        stores={"sessions": MemoryStore()},
    ) as client:
        response = client.get("/posts", headers={InertiaHeaders.ENABLED.value: "true"})
        data = response.json()
        # Items under custom key, metadata flattened as siblings
        assert data["props"]["posts"] == ["post1", "post2"]
        assert data["props"]["total"] == 50
        assert data["props"]["limit"] == 10
        assert data["props"]["offset"] == 10
        # scroll_props should be calculated from pagination metadata
        assert "scrollProps" in data
        assert data["scrollProps"]["currentPage"] == 2  # offset=10, limit=10 -> page 2
        assert data["scrollProps"]["previousPage"] == 1
        assert data["scrollProps"]["nextPage"] == 3


async def test_pagination_classic_style_metadata(
    inertia_plugin: InertiaPlugin,
    vite_plugin: VitePlugin,
    template_config: TemplateConfig,  # pyright: ignore[reportUnknownParameterType,reportMissingTypeArgument]
) -> None:
    """Test that ClassicPagination style metadata is flattened with camelCase keys."""
    from dataclasses import dataclass

    @dataclass
    class MockClassicPagination:
        items: list[str]
        page_size: int
        current_page: int
        total_pages: int

    @get("/articles", component="Articles", key="articles")
    async def handler(request: Request[Any, Any, Any]) -> MockClassicPagination:
        return MockClassicPagination(items=["article1", "article2"], page_size=20, current_page=1, total_pages=5)

    with create_test_client(
        route_handlers=[handler],
        plugins=[inertia_plugin, vite_plugin],
        template_config=template_config,
        middleware=[ServerSideSessionConfig().middleware],
        stores={"sessions": MemoryStore()},
    ) as client:
        response = client.get("/articles", headers={InertiaHeaders.ENABLED.value: "true"})
        data = response.json()
        # Items under custom key, classic pagination metadata flattened as siblings (camelCase)
        assert data["props"]["articles"] == ["article1", "article2"]
        assert data["props"]["pageSize"] == 20
        assert data["props"]["currentPage"] == 1
        assert data["props"]["totalPages"] == 5


# =====================================================
# Security Tests - Open Redirect Prevention (GitHub #123)
# =====================================================


async def test_inertia_back_rejects_cross_origin_referer(
    inertia_plugin: InertiaPlugin,
    vite_plugin: VitePlugin,
    template_config: TemplateConfig,  # pyright: ignore[reportUnknownParameterType,reportMissingTypeArgument]
) -> None:
    """Test that InertiaBack rejects cross-origin Referer headers (fixes #123)."""

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
        # Cross-origin Referer should be rejected
        response = client.get(
            "/back",
            headers={InertiaHeaders.ENABLED.value: "true", "Referer": "https://evil.com/malicious"},
            follow_redirects=False,
        )
        assert response.status_code == 307
        # Should redirect to base URL, not evil.com
        assert response.headers.get("location") == "http://testserver.local/"


async def test_inertia_back_allows_same_origin_referer(
    inertia_plugin: InertiaPlugin,
    vite_plugin: VitePlugin,
    template_config: TemplateConfig,  # pyright: ignore[reportUnknownParameterType,reportMissingTypeArgument]
) -> None:
    """Test that InertiaBack allows same-origin Referer headers."""

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
        # Same-origin Referer should be allowed
        response = client.get(
            "/back",
            headers={InertiaHeaders.ENABLED.value: "true", "Referer": "http://testserver.local/previous-page"},
            follow_redirects=False,
        )
        assert response.status_code == 307
        assert response.headers.get("location") == "http://testserver.local/previous-page"


async def test_inertia_back_allows_relative_referer(
    inertia_plugin: InertiaPlugin,
    vite_plugin: VitePlugin,
    template_config: TemplateConfig,  # pyright: ignore[reportUnknownParameterType,reportMissingTypeArgument]
) -> None:
    """Test that InertiaBack allows relative URL Referer headers."""

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
        # Relative URLs should be allowed (they're safe)
        response = client.get(
            "/back", headers={InertiaHeaders.ENABLED.value: "true", "Referer": "/previous-page"}, follow_redirects=False
        )
        assert response.status_code == 307
        assert response.headers.get("location") == "/previous-page"


async def test_inertia_back_rejects_javascript_scheme(
    inertia_plugin: InertiaPlugin,
    vite_plugin: VitePlugin,
    template_config: TemplateConfig,  # pyright: ignore[reportUnknownParameterType,reportMissingTypeArgument]
) -> None:
    """Test that InertiaBack rejects javascript: scheme in Referer."""

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
        # javascript: scheme should be rejected
        response = client.get(
            "/back",
            headers={InertiaHeaders.ENABLED.value: "true", "Referer": "javascript:alert(1)"},
            follow_redirects=False,
        )
        assert response.status_code == 307
        # Should redirect to base URL, not execute JS
        assert response.headers.get("location") == "http://testserver.local/"


async def test_inertia_back_rejects_protocol_relative_url(
    inertia_plugin: InertiaPlugin,
    vite_plugin: VitePlugin,
    template_config: TemplateConfig,  # pyright: ignore[reportUnknownParameterType,reportMissingTypeArgument]
) -> None:
    """Test that InertiaBack rejects protocol-relative URLs (//evil.com)."""

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
        # Protocol-relative URLs should be rejected (they redirect to external domain)
        response = client.get(
            "/back",
            headers={InertiaHeaders.ENABLED.value: "true", "Referer": "//evil.com/path"},
            follow_redirects=False,
        )
        assert response.status_code == 307
        # Should redirect to base URL, not evil.com
        assert response.headers.get("location") == "http://testserver.local/"


async def test_inertia_back_missing_referer_uses_base_url(
    inertia_plugin: InertiaPlugin,
    vite_plugin: VitePlugin,
    template_config: TemplateConfig,  # pyright: ignore[reportUnknownParameterType,reportMissingTypeArgument]
) -> None:
    """Test that InertiaBack uses base_url when Referer is missing."""

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
        # No Referer header - should use base URL
        response = client.get("/back", headers={InertiaHeaders.ENABLED.value: "true"}, follow_redirects=False)
        assert response.status_code == 307
        assert response.headers.get("location") == "http://testserver.local/"


async def test_inertia_redirect_rejects_cross_origin_url(
    inertia_plugin: InertiaPlugin,
    vite_plugin: VitePlugin,
    template_config: TemplateConfig,  # pyright: ignore[reportUnknownParameterType,reportMissingTypeArgument]
) -> None:
    """Test that InertiaRedirect rejects cross-origin redirect_to URLs."""
    from litestar_vite.inertia.response import InertiaRedirect

    @get("/redirect", component="Redirect")
    async def handler(request: Request[Any, Any, Any]) -> InertiaRedirect:
        # Attempt cross-origin redirect
        return InertiaRedirect(request, redirect_to="https://evil.com/malicious")

    with create_test_client(
        route_handlers=[handler],
        template_config=template_config,
        plugins=[inertia_plugin, vite_plugin],
        middleware=[ServerSideSessionConfig().middleware],
        stores={"sessions": MemoryStore()},
    ) as client:
        response = client.get("/redirect", headers={InertiaHeaders.ENABLED.value: "true"}, follow_redirects=False)
        assert response.status_code == 307
        # Should redirect to base URL, not evil.com
        assert response.headers.get("location") == "http://testserver.local/"


async def test_inertia_redirect_allows_relative_url(
    inertia_plugin: InertiaPlugin,
    vite_plugin: VitePlugin,
    template_config: TemplateConfig,  # pyright: ignore[reportUnknownParameterType,reportMissingTypeArgument]
) -> None:
    """Test that InertiaRedirect allows relative URLs."""
    from litestar_vite.inertia.response import InertiaRedirect

    @get("/redirect", component="Redirect")
    async def handler(request: Request[Any, Any, Any]) -> InertiaRedirect:
        return InertiaRedirect(request, redirect_to="/dashboard")

    with create_test_client(
        route_handlers=[handler],
        template_config=template_config,
        plugins=[inertia_plugin, vite_plugin],
        middleware=[ServerSideSessionConfig().middleware],
        stores={"sessions": MemoryStore()},
    ) as client:
        response = client.get("/redirect", headers={InertiaHeaders.ENABLED.value: "true"}, follow_redirects=False)
        assert response.status_code == 307
        assert response.headers.get("location") == "/dashboard"


# =====================================================
# Security Tests - Cookie Leak Prevention (GitHub #126)
# =====================================================


async def test_inertia_back_no_cookie_echo(
    inertia_plugin: InertiaPlugin,
    vite_plugin: VitePlugin,
    template_config: TemplateConfig,  # pyright: ignore[reportUnknownParameterType,reportMissingTypeArgument]
) -> None:
    """Test that InertiaBack does not echo request cookies (fixes #126)."""

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
        # Send request with a cookie (set on client to avoid deprecation warning)
        client.cookies.set("session_id", "secret_session_value")
        response = client.get(
            "/back", headers={InertiaHeaders.ENABLED.value: "true", "Referer": "/previous"}, follow_redirects=False
        )
        # The response should NOT have Set-Cookie header echoing the session_id
        set_cookie_headers = response.headers.get_list("set-cookie")
        session_cookie_echoed = any("session_id=secret_session_value" in c for c in set_cookie_headers)
        assert not session_cookie_echoed, "Request cookies should not be echoed in response"


async def test_inertia_external_redirect_no_cookie_echo(
    inertia_plugin: InertiaPlugin,
    vite_plugin: VitePlugin,
    template_config: TemplateConfig,  # pyright: ignore[reportUnknownParameterType,reportMissingTypeArgument]
) -> None:
    """Test that InertiaExternalRedirect does not echo request cookies (fixes #126)."""

    @get("/external", component="External")
    async def handler(request: Request[Any, Any, Any]) -> InertiaExternalRedirect:
        return InertiaExternalRedirect(request, redirect_to="https://external-site.com/callback")

    with create_test_client(
        route_handlers=[handler],
        template_config=template_config,
        plugins=[inertia_plugin, vite_plugin],
        middleware=[ServerSideSessionConfig().middleware],
        stores={"sessions": MemoryStore()},
    ) as client:
        # Set cookie on client to avoid deprecation warning
        client.cookies.set("auth_token", "secret_token")
        response = client.get("/external", headers={InertiaHeaders.ENABLED.value: "true"}, follow_redirects=False)
        assert response.status_code == 409
        # The response should NOT have Set-Cookie header echoing the auth_token
        set_cookie_headers = response.headers.get_list("set-cookie")
        token_cookie_echoed = any("auth_token=secret_token" in c for c in set_cookie_headers)
        assert not token_cookie_echoed, "Request cookies should not be echoed in response"
