"""Tests for Inertia helper functions (scroll_props, clear_history, should_render)."""

from typing import Any

from litestar import Request, get
from litestar.middleware.session.server_side import ServerSideSessionConfig
from litestar.stores.memory import MemoryStore
from litestar.template.config import TemplateConfig
from litestar.testing import create_test_client

from litestar_vite.inertia import InertiaHeaders, InertiaPlugin
from litestar_vite.inertia.helpers import clear_history, lazy, scroll_props, should_render
from litestar_vite.inertia.response import InertiaResponse
from litestar_vite.plugin import VitePlugin

# =====================================================
# scroll_props() Helper Tests
# =====================================================


def test_scroll_props_helper_creates_config() -> None:
    """Test scroll_props() helper creates correct ScrollPropsConfig."""
    config = scroll_props(page_name="page", current_page=2, previous_page=1, next_page=3)

    assert config.page_name == "page"
    assert config.current_page == 2
    assert config.previous_page == 1
    assert config.next_page == 3


def test_scroll_props_helper_defaults() -> None:
    """Test scroll_props() helper with default values."""
    config = scroll_props()

    assert config.page_name == "page"
    assert config.current_page == 1
    assert config.previous_page is None
    assert config.next_page is None


def test_scroll_props_helper_custom_page_name() -> None:
    """Test scroll_props() with custom page parameter name."""
    config = scroll_props(page_name="offset", current_page=10, previous_page=9, next_page=11)

    assert config.page_name == "offset"
    assert config.current_page == 10


def test_scroll_props_helper_first_page() -> None:
    """Test scroll_props() for first page (no previous)."""
    config = scroll_props(current_page=1, previous_page=None, next_page=2)

    assert config.current_page == 1
    assert config.previous_page is None
    assert config.next_page == 2


def test_scroll_props_helper_last_page() -> None:
    """Test scroll_props() for last page (no next)."""
    config = scroll_props(current_page=10, previous_page=9, next_page=None)

    assert config.current_page == 10
    assert config.previous_page == 9
    assert config.next_page is None


# =====================================================
# clear_history() Helper Tests
# =====================================================


async def test_clear_history_helper_sets_session_flag(
    inertia_plugin: InertiaPlugin,
    vite_plugin: VitePlugin,
    template_config: TemplateConfig,  # pyright: ignore[reportUnknownParameterType,reportMissingTypeArgument]
) -> None:
    """Test clear_history() helper sets session flag for next response."""

    @get("/logout", component="Logout")
    async def handler(request: Request[Any, Any, Any]) -> dict[str, str]:
        # Set flag that will be consumed by next InertiaResponse
        clear_history(request)
        return {"message": "Logged out"}

    with create_test_client(
        route_handlers=[handler],
        template_config=template_config,
        plugins=[inertia_plugin, vite_plugin],
        middleware=[ServerSideSessionConfig().middleware],
        stores={"sessions": MemoryStore()},
    ) as client:
        response = client.get("/logout", headers={InertiaHeaders.ENABLED.value: "true"})
        data = response.json()
        # clearHistory should be true from session flag
        assert data["clearHistory"] is True


async def test_clear_history_helper_consumed_once(
    inertia_plugin: InertiaPlugin,
    vite_plugin: VitePlugin,
    template_config: TemplateConfig,  # pyright: ignore[reportUnknownParameterType,reportMissingTypeArgument]
) -> None:
    """Test clear_history() flag is consumed after first use."""

    @get("/logout", component="Logout")
    async def logout_handler(request: Request[Any, Any, Any]) -> dict[str, str]:
        clear_history(request)
        return {"message": "Logged out"}

    @get("/home", component="Home")
    async def home_handler(request: Request[Any, Any, Any]) -> dict[str, str]:
        return {"message": "Home"}

    with create_test_client(
        route_handlers=[logout_handler, home_handler],
        template_config=template_config,
        plugins=[inertia_plugin, vite_plugin],
        middleware=[ServerSideSessionConfig().middleware],
        stores={"sessions": MemoryStore()},
    ) as client:
        # First request - clear_history flag is set
        logout_response = client.get("/logout", headers={InertiaHeaders.ENABLED.value: "true"})
        assert logout_response.json()["clearHistory"] is True

        # Second request - flag should be consumed (popped)
        home_response = client.get("/home", headers={InertiaHeaders.ENABLED.value: "true"})
        assert home_response.json()["clearHistory"] is False


async def test_clear_history_helper_response_param_takes_precedence(
    inertia_plugin: InertiaPlugin,
    vite_plugin: VitePlugin,
    template_config: TemplateConfig,  # pyright: ignore[reportUnknownParameterType,reportMissingTypeArgument]
) -> None:
    """Test that InertiaResponse clear_history=True parameter works alongside session flag."""

    @get("/logout", component="Logout")
    async def handler(request: Request[Any, Any, Any]) -> InertiaResponse[dict[str, str]]:
        # Both set the flag AND use response parameter explicitly True
        clear_history(request)
        # Response parameter explicitly True should work
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
        # Both flags set to True
        assert data["clearHistory"] is True


# =====================================================
# should_render() with key Parameter Tests (v2)
# =====================================================


def test_should_render_with_key_partial_data() -> None:
    """Test should_render() with key parameter for partial_data filtering."""
    # Without key - regular value always renders
    assert should_render("value") is True

    # With key and partial_data - only render if key is in set
    assert should_render("value", partial_data={"field1", "field2"}, key="field1") is True
    assert should_render("value", partial_data={"field1", "field2"}, key="field3") is False


def test_should_render_with_key_partial_except() -> None:
    """Test should_render() with key parameter for partial_except filtering (v2)."""
    # With key and partial_except - exclude if key is in set
    assert should_render("value", partial_except={"field1"}, key="field1") is False
    assert should_render("value", partial_except={"field1"}, key="field2") is True


def test_should_render_with_key_partial_except_precedence() -> None:
    """Test that partial_except takes precedence over partial_data with key."""
    # partial_except takes precedence - exclude even if in partial_data
    assert should_render("value", partial_data={"field1"}, partial_except={"field1"}, key="field1") is False


def test_should_render_lazy_prop_with_key() -> None:
    """Test should_render() for lazy props uses prop.key, not external key parameter."""
    prop = lazy("lazy_field", "value")

    # Lazy props use their own key for filtering
    assert should_render(prop, partial_data={"lazy_field"}) is True
    assert should_render(prop, partial_data={"other_field"}) is False

    # partial_except with lazy props
    assert should_render(prop, partial_except={"lazy_field"}) is False
    assert should_render(prop, partial_except={"other_field"}) is True


def test_should_render_filters_all_props_with_partial_data() -> None:
    """Test should_render() filters all props (not just lazy) when key is provided."""
    # Regular value with key and partial_data
    regular_value = {"data": "value"}

    # Without key - always render
    assert should_render(regular_value) is True

    # With key - filter based on partial_data
    assert should_render(regular_value, partial_data={"config"}, key="config") is True
    assert should_render(regular_value, partial_data={"config"}, key="other") is False


def test_should_render_filters_all_props_with_partial_except() -> None:
    """Test should_render() filters all props with partial_except when key is provided."""
    regular_value = {"data": "value"}

    # With key and partial_except - exclude if key matches
    assert should_render(regular_value, partial_except={"config"}, key="config") is False
    assert should_render(regular_value, partial_except={"config"}, key="other") is True


async def test_partial_reload_filters_shared_props(
    inertia_plugin: InertiaPlugin,
    vite_plugin: VitePlugin,
    template_config: TemplateConfig,  # pyright: ignore[reportUnknownParameterType,reportMissingTypeArgument]
) -> None:
    """Test that partial reload filters shared props with partial_data."""
    from litestar_vite.inertia.helpers import share

    @get("/", component="Home")
    async def handler(request: Request[Any, Any, Any]) -> dict[str, Any]:
        # Share some props
        share(request, "user", {"name": "Alice"})
        share(request, "settings", {"theme": "dark"})
        share(request, "notifications", ["msg1", "msg2"])
        # Route handler props are always included
        return {"posts": [1, 2, 3], "comments": [4, 5, 6]}

    with create_test_client(
        route_handlers=[handler],
        template_config=template_config,
        plugins=[inertia_plugin, vite_plugin],
        middleware=[ServerSideSessionConfig().middleware],
        stores={"sessions": MemoryStore()},
    ) as client:
        # Full request - all props present
        full_response = client.get("/", headers={InertiaHeaders.ENABLED.value: "true"})
        full_props = full_response.json()["props"]
        assert "user" in full_props
        assert "settings" in full_props
        assert "notifications" in full_props
        assert "posts" in full_props
        assert "comments" in full_props

        # Partial request with partial_data - filters shared props
        partial_response = client.get(
            "/",
            headers={
                InertiaHeaders.ENABLED.value: "true",
                InertiaHeaders.PARTIAL_DATA.value: "user,posts",
                InertiaHeaders.PARTIAL_COMPONENT.value: "Home",
            },
        )
        partial_props = partial_response.json()["props"]
        # user is requested and present in shared props
        assert "user" in partial_props
        # Route handler props are always included (posts, comments)
        assert "posts" in partial_props
        assert "comments" in partial_props
        # Shared props not requested are filtered out
        assert "settings" not in partial_props
        assert "notifications" not in partial_props


async def test_partial_reload_with_partial_except(
    inertia_plugin: InertiaPlugin,
    vite_plugin: VitePlugin,
    template_config: TemplateConfig,  # pyright: ignore[reportUnknownParameterType,reportMissingTypeArgument]
) -> None:
    """Test partial reload with partial_except (v2) excludes specified props."""
    from litestar_vite.inertia.helpers import share

    @get("/", component="Home")
    async def handler(request: Request[Any, Any, Any]) -> dict[str, Any]:
        share(request, "user", {"name": "Bob"})
        share(request, "settings", {"theme": "light"})
        share(request, "cache", {"data": "sensitive"})
        return {"posts": [1, 2, 3]}

    with create_test_client(
        route_handlers=[handler],
        template_config=template_config,
        plugins=[inertia_plugin, vite_plugin],
        middleware=[ServerSideSessionConfig().middleware],
        stores={"sessions": MemoryStore()},
    ) as client:
        # Partial request with partial_except - all props EXCEPT specified ones
        response = client.get(
            "/",
            headers={
                InertiaHeaders.ENABLED.value: "true",
                InertiaHeaders.PARTIAL_EXCEPT.value: "cache,settings",
                InertiaHeaders.PARTIAL_COMPONENT.value: "Home",
            },
        )
        props = response.json()["props"]
        # These should be present
        assert "user" in props
        assert "posts" in props
        # These should be excluded
        assert "cache" not in props
        assert "settings" not in props


# =====================================================
# pagination_to_dict() Helper Tests
# =====================================================


def test_pagination_to_dict_offset_pagination() -> None:
    """Test pagination_to_dict with OffsetPagination-style data."""
    from dataclasses import dataclass

    from litestar_vite.inertia.helpers import pagination_to_dict

    @dataclass
    class MockOffsetPagination:
        items: list[str]
        limit: int
        offset: int
        total: int

    pagination = MockOffsetPagination(items=["a", "b", "c"], limit=10, offset=20, total=100)
    result = pagination_to_dict(pagination)

    assert result["items"] == ["a", "b", "c"]
    assert result["total"] == 100
    assert result["limit"] == 10
    assert result["offset"] == 20


def test_pagination_to_dict_classic_pagination() -> None:
    """Test pagination_to_dict with ClassicPagination-style data."""
    from dataclasses import dataclass

    from litestar_vite.inertia.helpers import pagination_to_dict

    @dataclass
    class MockClassicPagination:
        items: list[str]
        page_size: int
        current_page: int
        total_pages: int

    pagination = MockClassicPagination(items=["x", "y"], page_size=15, current_page=2, total_pages=10)
    result = pagination_to_dict(pagination)

    assert result["items"] == ["x", "y"]
    # camelCase conversion
    assert result["pageSize"] == 15
    assert result["currentPage"] == 2
    assert result["totalPages"] == 10


def test_pagination_to_dict_custom_pagination() -> None:
    """Test pagination_to_dict with custom pagination class having extra attributes."""
    from dataclasses import dataclass

    from litestar_vite.inertia.helpers import pagination_to_dict

    @dataclass
    class CustomPagination:
        items: list[int]
        total: int
        has_more: bool
        next_cursor: str | None

    pagination = CustomPagination(items=[1, 2, 3], total=50, has_more=True, next_cursor="abc123")
    result = pagination_to_dict(pagination)

    assert result["items"] == [1, 2, 3]
    assert result["total"] == 50
    assert result["hasMore"] is True
    assert result["nextCursor"] == "abc123"


def test_pagination_to_dict_empty_items() -> None:
    """Test pagination_to_dict with empty items list."""
    from dataclasses import dataclass

    from litestar_vite.inertia.helpers import pagination_to_dict

    @dataclass
    class MockPagination:
        items: list[str]
        limit: int
        offset: int
        total: int

    pagination = MockPagination(items=[], limit=10, offset=0, total=0)
    result = pagination_to_dict(pagination)

    assert result["items"] == []
    assert result["total"] == 0
    assert result["limit"] == 10
    assert result["offset"] == 0


def test_pagination_to_dict_mixed_attributes() -> None:
    """Test pagination_to_dict with mix of known pagination attributes."""
    from dataclasses import dataclass

    from litestar_vite.inertia.helpers import pagination_to_dict

    @dataclass
    class MixedPagination:
        items: list[str]
        total: int
        limit: int
        offset: int
        page_size: int  # Both offset and classic style
        current_page: int

    # Has both offset and classic pagination attributes
    pagination = MixedPagination(items=["item1"], total=100, limit=10, offset=0, page_size=10, current_page=1)
    result = pagination_to_dict(pagination)

    # All found attributes should be included
    assert result["items"] == ["item1"]
    assert result["total"] == 100
    assert result["limit"] == 10
    assert result["offset"] == 0
    assert result["pageSize"] == 10
    assert result["currentPage"] == 1
