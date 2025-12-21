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


# =====================================================
# flash() Helper Tests (GitHub #164)
# =====================================================


async def test_flash_returns_true_with_session(
    inertia_plugin: InertiaPlugin,
    vite_plugin: VitePlugin,
    template_config: TemplateConfig,  # pyright: ignore[reportUnknownParameterType,reportMissingTypeArgument]
) -> None:
    """Test flash() returns True when session is available."""
    from litestar_vite.inertia.helpers import flash

    @get("/", component="Home")
    async def handler(request: Request[Any, Any, Any]) -> dict[str, Any]:
        result = flash(request, "Test message", "success")
        return {"flash_result": result}

    with create_test_client(
        route_handlers=[handler],
        template_config=template_config,
        plugins=[inertia_plugin, vite_plugin],
        middleware=[ServerSideSessionConfig().middleware],
        stores={"sessions": MemoryStore()},
    ) as client:
        response = client.get("/", headers={InertiaHeaders.ENABLED.value: "true"})
        data = response.json()
        # flash should have succeeded
        assert data["props"]["flash_result"] is True
        # Message should be in flash
        assert data["flash"] == {"success": ["Test message"]}


def test_flash_returns_false_when_session_access_fails() -> None:
    """Test flash() returns False when session access fails (GitHub #164).

    This simulates the scenario where session middleware is configured but
    the session itself is not accessible (e.g., for unauthenticated users
    on their first request before a session is created).
    """
    from unittest.mock import MagicMock

    from litestar.exceptions import ImproperlyConfiguredException

    from litestar_vite.inertia.helpers import flash

    # Create a mock connection where session access raises an exception
    mock_connection = MagicMock()
    mock_connection.session.setdefault.side_effect = ImproperlyConfiguredException("No session")
    mock_connection.logger = MagicMock()

    result = flash(mock_connection, "Test message", "error")

    # flash should have failed and returned False
    assert result is False
    # Should log at debug level (not warning)
    mock_connection.logger.debug.assert_called_once()


def test_flash_returns_false_when_session_setdefault_raises_attribute_error() -> None:
    """Test flash() returns False when session.setdefault raises AttributeError."""
    from unittest.mock import MagicMock

    from litestar_vite.inertia.helpers import flash

    # Create a mock connection where session.setdefault raises AttributeError
    mock_connection = MagicMock()
    mock_connection.session.setdefault.side_effect = AttributeError("session attribute error")
    mock_connection.logger = MagicMock()

    result = flash(mock_connection, "Test message", "error")

    # flash should have failed and returned False
    assert result is False
    # Should log at debug level
    mock_connection.logger.debug.assert_called_once()


# =====================================================
# share() Helper Tests (GitHub #164)
# =====================================================


async def test_share_returns_true_with_session(
    inertia_plugin: InertiaPlugin,
    vite_plugin: VitePlugin,
    template_config: TemplateConfig,  # pyright: ignore[reportUnknownParameterType,reportMissingTypeArgument]
) -> None:
    """Test share() returns True when session is available."""
    from litestar_vite.inertia.helpers import share

    @get("/", component="Home")
    async def handler(request: Request[Any, Any, Any]) -> dict[str, Any]:
        result = share(request, "user", {"name": "Alice"})
        return {"share_result": result}

    with create_test_client(
        route_handlers=[handler],
        template_config=template_config,
        plugins=[inertia_plugin, vite_plugin],
        middleware=[ServerSideSessionConfig().middleware],
        stores={"sessions": MemoryStore()},
    ) as client:
        response = client.get("/", headers={InertiaHeaders.ENABLED.value: "true"})
        data = response.json()
        # share should have succeeded
        assert data["props"]["share_result"] is True
        # Shared value should be in props
        assert data["props"]["user"] == {"name": "Alice"}


def test_share_returns_false_when_session_fails() -> None:
    """Test share() returns False when session access fails."""
    from unittest.mock import MagicMock

    from litestar.exceptions import ImproperlyConfiguredException

    from litestar_vite.inertia.helpers import share

    mock_connection = MagicMock()
    mock_connection.session.setdefault.side_effect = ImproperlyConfiguredException("No session")
    mock_connection.logger = MagicMock()

    result = share(mock_connection, "key", "value")

    assert result is False
    mock_connection.logger.debug.assert_called_once()


# =====================================================
# error() Helper Tests (GitHub #164)
# =====================================================


async def test_error_returns_true_with_session(
    inertia_plugin: InertiaPlugin,
    vite_plugin: VitePlugin,
    template_config: TemplateConfig,  # pyright: ignore[reportUnknownParameterType,reportMissingTypeArgument]
) -> None:
    """Test error() returns True when session is available."""
    from litestar_vite.inertia.helpers import error

    @get("/", component="Home")
    async def handler(request: Request[Any, Any, Any]) -> dict[str, Any]:
        result = error(request, "email", "Invalid email format")
        return {"error_result": result}

    with create_test_client(
        route_handlers=[handler],
        template_config=template_config,
        plugins=[inertia_plugin, vite_plugin],
        middleware=[ServerSideSessionConfig().middleware],
        stores={"sessions": MemoryStore()},
    ) as client:
        response = client.get("/", headers={InertiaHeaders.ENABLED.value: "true"})
        data = response.json()
        # error should have succeeded
        assert data["props"]["error_result"] is True
        # Error should be in props.errors
        assert data["props"]["errors"]["email"] == "Invalid email format"


def test_error_returns_false_when_session_fails() -> None:
    """Test error() returns False when session access fails."""
    from unittest.mock import MagicMock

    from litestar.exceptions import ImproperlyConfiguredException

    from litestar_vite.inertia.helpers import error

    mock_connection = MagicMock()
    mock_connection.session.setdefault.side_effect = ImproperlyConfiguredException("No session")
    mock_connection.logger = MagicMock()

    result = error(mock_connection, "field", "Error message")

    assert result is False
    mock_connection.logger.debug.assert_called_once()


# =====================================================
# once() Helper Tests (v2.2.20+)
# =====================================================


def test_once_with_static_value() -> None:
    """Test once() helper with a static value."""
    from litestar_vite.inertia.helpers import once

    prop = once("settings", {"theme": "dark"})

    assert prop.key == "settings"
    result = prop.render()
    assert result == {"theme": "dark"}


def test_once_with_callable() -> None:
    """Test once() helper with a callable."""
    from litestar_vite.inertia.helpers import OnceProp, once

    call_count = 0

    def get_settings() -> dict[str, str]:
        nonlocal call_count
        call_count += 1
        return {"theme": "light"}

    prop: OnceProp[str, dict[str, str]] = once("settings", get_settings)

    assert prop.key == "settings"
    # First render
    result1 = prop.render()
    assert result1 == {"theme": "light"}
    assert call_count == 1

    # Second render should return cached value
    result2 = prop.render()
    assert result2 == {"theme": "light"}
    assert call_count == 1  # Should not call again


def test_once_is_recognized_by_type_guard() -> None:
    """Test is_once_prop type guard recognizes OnceProp."""
    from litestar_vite.inertia.helpers import is_once_prop, once

    prop = once("key", "value")
    assert is_once_prop(prop) is True
    assert is_once_prop("value") is False
    assert is_once_prop(None) is False


def test_once_should_render_always_true() -> None:
    """Test once props are always rendered (client handles caching)."""
    from litestar_vite.inertia.helpers import once, should_render

    prop = once("settings", {"value": 1})

    # Always render without partial filters
    assert should_render(prop) is True

    # Always render even with partial_data (once props don't filter by default)
    assert should_render(prop, partial_data={"other"}) is True

    # Respect partial_except
    assert should_render(prop, partial_except={"settings"}) is False


# =====================================================
# optional() Helper Tests (v2 WhenVisible)
# =====================================================


def test_optional_only_included_when_requested() -> None:
    """Test optional() props only render when explicitly requested."""
    from litestar_vite.inertia.helpers import optional, should_render

    call_count = 0

    def get_comments() -> list[str]:
        nonlocal call_count
        call_count += 1
        return ["comment1", "comment2"]

    prop = optional("comments", get_comments)

    # Never render on initial load (no partial_data)
    assert should_render(prop) is False

    # Never render when other props requested
    assert should_render(prop, partial_data={"posts"}) is False

    # Only render when explicitly requested
    assert should_render(prop, partial_data={"comments"}) is True


def test_optional_callback_only_called_when_needed() -> None:
    """Test optional() callback only evaluated when prop is requested."""
    from litestar_vite.inertia.helpers import optional

    call_count = 0

    def expensive_query() -> list[int]:
        nonlocal call_count
        call_count += 1
        return [1, 2, 3]

    prop = optional("data", expensive_query)

    assert call_count == 0  # Not called yet

    # Render the prop
    result = prop.render()
    assert result == [1, 2, 3]
    assert call_count == 1

    # Cached on second render
    result2 = prop.render()
    assert result2 == [1, 2, 3]
    assert call_count == 1


def test_optional_is_recognized_by_type_guard() -> None:
    """Test is_optional_prop type guard recognizes OptionalProp."""
    from litestar_vite.inertia.helpers import is_optional_prop, optional

    prop = optional("key", lambda: "value")
    assert is_optional_prop(prop) is True
    assert is_optional_prop("value") is False
    assert is_optional_prop(None) is False


# =====================================================
# always() Helper Tests (v2)
# =====================================================


def test_always_included_in_every_response() -> None:
    """Test always() props bypass all filtering."""
    from litestar_vite.inertia.helpers import always, should_render

    prop = always("auth", {"user": "Alice", "role": "admin"})

    # Always render without filters
    assert should_render(prop) is True

    # Always render even with partial_data
    assert should_render(prop, partial_data={"posts"}) is True

    # Always render even with partial_except (bypasses filtering)
    assert should_render(prop, partial_except={"auth"}) is True


def test_always_value_accessible() -> None:
    """Test always() prop value is directly accessible."""
    from litestar_vite.inertia.helpers import always

    prop = always("permissions", ["read", "write"])

    assert prop.key == "permissions"
    assert prop.value == ["read", "write"]
    assert prop.render() == ["read", "write"]


def test_always_is_recognized_by_type_guard() -> None:
    """Test is_always_prop type guard recognizes AlwaysProp."""
    from litestar_vite.inertia.helpers import always, is_always_prop

    prop = always("key", "value")
    assert is_always_prop(prop) is True
    assert is_always_prop("value") is False
    assert is_always_prop(None) is False


# =====================================================
# defer().once() Chaining Tests (v2.2.20+)
# =====================================================


def test_defer_once_chaining() -> None:
    """Test defer().once() creates a deferred prop with once behavior."""
    from litestar_vite.inertia.helpers import defer, is_deferred_prop

    prop = defer("stats", lambda: {"views": 100}).once()

    assert is_deferred_prop(prop) is True
    assert prop.is_once is True
    assert prop.key == "stats"


def test_defer_once_not_in_deferred_props_extraction() -> None:
    """Test defer().once() props are excluded from deferred_props metadata."""
    from litestar_vite.inertia.helpers import defer, extract_deferred_props

    props = {
        "regular_deferred": defer("regular_deferred", lambda: "value"),
        "once_deferred": defer("once_deferred", lambda: "cached").once(),
    }

    deferred = extract_deferred_props(props)

    # Regular deferred should be in metadata
    assert "regular_deferred" in deferred.get("default", [])
    # Once deferred should NOT be in metadata
    assert "once_deferred" not in deferred.get("default", [])


def test_defer_once_in_once_props_extraction() -> None:
    """Test defer().once() props are included in once_props extraction."""
    from litestar_vite.inertia.helpers import defer, extract_once_props, once

    props = {
        "regular": "value",
        "once_value": once("once_value", {"data": 1}),
        "deferred_once": defer("deferred_once", lambda: "cached").once(),
    }

    once_keys = extract_once_props(props)

    assert "once_value" in once_keys
    assert "deferred_once" in once_keys
    assert "regular" not in once_keys


# =====================================================
# extract_once_props() Tests
# =====================================================


def test_extract_once_props_empty() -> None:
    """Test extract_once_props with no once props."""
    from litestar_vite.inertia.helpers import extract_once_props

    props = {"user": "Alice", "posts": [1, 2, 3]}
    result = extract_once_props(props)

    assert result == []


def test_extract_once_props_mixed() -> None:
    """Test extract_once_props with mixed prop types."""
    from litestar_vite.inertia.helpers import defer, extract_once_props, lazy, once

    props = {
        "user": "Alice",
        "settings": once("settings", {"theme": "dark"}),
        "lazy_data": lazy("lazy_data", "value"),
        "cached_stats": defer("cached_stats", lambda: {}).once(),
    }

    result = extract_once_props(props)

    assert "settings" in result
    assert "cached_stats" in result
    assert "user" not in result
    assert "lazy_data" not in result


# =====================================================
# is_special_prop() and is_or_contains_special_prop() Tests
# =====================================================


def test_is_special_prop_recognizes_all_types() -> None:
    """Test is_special_prop recognizes all special prop types."""
    from litestar_vite.inertia.helpers import always, defer, is_special_prop, lazy, once, optional

    assert is_special_prop(lazy("k", "v")) is True
    assert is_special_prop(defer("k", lambda: "v")) is True
    assert is_special_prop(once("k", "v")) is True
    assert is_special_prop(optional("k", lambda: "v")) is True
    assert is_special_prop(always("k", "v")) is True
    assert is_special_prop("regular") is False
    assert is_special_prop(123) is False


def test_is_or_contains_special_prop_nested() -> None:
    """Test is_or_contains_special_prop finds nested special props."""
    from litestar_vite.inertia.helpers import always, is_or_contains_special_prop, once

    # Direct special prop
    assert is_or_contains_special_prop(once("k", "v")) is True

    # Nested in dict
    nested_dict = {"data": {"inner": once("inner", "value")}}
    assert is_or_contains_special_prop(nested_dict) is True

    # Nested in list
    nested_list = [always("auth", {"user": "Alice"})]
    assert is_or_contains_special_prop(nested_list) is True

    # No special props
    assert is_or_contains_special_prop({"a": 1, "b": [2, 3]}) is False
    assert is_or_contains_special_prop("string") is False


# =====================================================
# Integration Tests for New Prop Types
# =====================================================


async def test_once_prop_in_response(
    inertia_plugin: InertiaPlugin,
    vite_plugin: VitePlugin,
    template_config: TemplateConfig,  # pyright: ignore[reportUnknownParameterType,reportMissingTypeArgument]
) -> None:
    """Test once props are included in response with once_props metadata."""
    from litestar_vite.inertia.helpers import once, share

    @get("/", component="Home")
    async def handler(request: Request[Any, Any, Any]) -> dict[str, Any]:
        share(request, "settings", once("settings", {"theme": "dark"}))
        return {"message": "Hello"}

    with create_test_client(
        route_handlers=[handler],
        template_config=template_config,
        plugins=[inertia_plugin, vite_plugin],
        middleware=[ServerSideSessionConfig().middleware],
        stores={"sessions": MemoryStore()},
    ) as client:
        response = client.get("/", headers={InertiaHeaders.ENABLED.value: "true"})
        data = response.json()

        # Props should include the rendered once prop
        assert data["props"]["settings"] == {"theme": "dark"}
        # once_props metadata should include the key
        assert "settings" in (data.get("onceProps") or [])


async def test_optional_prop_excluded_from_initial(
    inertia_plugin: InertiaPlugin,
    vite_plugin: VitePlugin,
    template_config: TemplateConfig,  # pyright: ignore[reportUnknownParameterType,reportMissingTypeArgument]
) -> None:
    """Test optional props are excluded from initial page load."""
    from litestar_vite.inertia.helpers import optional, share

    @get("/", component="Home")
    async def handler(request: Request[Any, Any, Any]) -> dict[str, Any]:
        share(request, "comments", optional("comments", lambda: ["c1", "c2"]))
        return {"post": "Hello World"}

    with create_test_client(
        route_handlers=[handler],
        template_config=template_config,
        plugins=[inertia_plugin, vite_plugin],
        middleware=[ServerSideSessionConfig().middleware],
        stores={"sessions": MemoryStore()},
    ) as client:
        # Initial request - optional props should be excluded
        response = client.get("/", headers={InertiaHeaders.ENABLED.value: "true"})
        data = response.json()

        assert "post" in data["props"]
        assert "comments" not in data["props"]


async def test_optional_prop_included_when_requested(
    inertia_plugin: InertiaPlugin,
    vite_plugin: VitePlugin,
    template_config: TemplateConfig,  # pyright: ignore[reportUnknownParameterType,reportMissingTypeArgument]
) -> None:
    """Test optional props are included when explicitly requested via partial reload."""
    from litestar_vite.inertia.helpers import optional, share

    @get("/", component="Home")
    async def handler(request: Request[Any, Any, Any]) -> dict[str, Any]:
        share(request, "comments", optional("comments", lambda: ["c1", "c2"]))
        return {"post": "Hello World"}

    with create_test_client(
        route_handlers=[handler],
        template_config=template_config,
        plugins=[inertia_plugin, vite_plugin],
        middleware=[ServerSideSessionConfig().middleware],
        stores={"sessions": MemoryStore()},
    ) as client:
        # Partial request specifically requesting comments
        response = client.get(
            "/",
            headers={
                InertiaHeaders.ENABLED.value: "true",
                InertiaHeaders.PARTIAL_DATA.value: "comments",
                InertiaHeaders.PARTIAL_COMPONENT.value: "Home",
            },
        )
        data = response.json()

        # Comments should be included when requested
        assert data["props"]["comments"] == ["c1", "c2"]


async def test_always_prop_included_in_partial(
    inertia_plugin: InertiaPlugin,
    vite_plugin: VitePlugin,
    template_config: TemplateConfig,  # pyright: ignore[reportUnknownParameterType,reportMissingTypeArgument]
) -> None:
    """Test always props are included even during partial reloads for other props."""
    from litestar_vite.inertia.helpers import always, lazy, share

    @get("/", component="Home")
    async def handler(request: Request[Any, Any, Any]) -> dict[str, Any]:
        share(request, "auth", always("auth", {"user": "Alice"}))
        share(request, "analytics", lazy("analytics", {"views": 100}))
        return {"data": "content"}

    with create_test_client(
        route_handlers=[handler],
        template_config=template_config,
        plugins=[inertia_plugin, vite_plugin],
        middleware=[ServerSideSessionConfig().middleware],
        stores={"sessions": MemoryStore()},
    ) as client:
        # Partial request for analytics only
        response = client.get(
            "/",
            headers={
                InertiaHeaders.ENABLED.value: "true",
                InertiaHeaders.PARTIAL_DATA.value: "analytics",
                InertiaHeaders.PARTIAL_COMPONENT.value: "Home",
            },
        )
        data = response.json()

        # Always prop should be included even though not requested
        assert data["props"]["auth"] == {"user": "Alice"}
        # Lazy prop should be included (was requested)
        assert data["props"]["analytics"] == {"views": 100}
