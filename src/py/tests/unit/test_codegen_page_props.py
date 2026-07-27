"""Unit tests for Inertia page props extraction in codegen module."""

from dataclasses import dataclass
from typing import Any, TypedDict

import pytest
from litestar import Litestar, get
from litestar.params import FromPath

from litestar_vite.codegen import InertiaPageMetadata, extract_inertia_pages, generate_inertia_pages_json
from litestar_vite.codegen._inertia import get_openapi_schema_ref, get_return_type_name
from litestar_vite.config import InertiaConfig, TypeGenConfig

# =============================================================================
# Test Models
# =============================================================================


class BookProps(TypedDict):
    """TypedDict for book props."""

    title: str
    author: str


@dataclass
class UserProps:
    """Dataclass for user props."""

    name: str
    email: str


@dataclass
class SharedUser:
    """Nested model shared through a guard, also returned by a route."""

    id: str
    email: str
    is_verified: bool = False


@dataclass
class AuthProps:
    """Shape pushed by an authentication guard via share()."""

    is_authenticated: bool
    user: "SharedUser | None" = None


# =============================================================================
# Tests for get_return_type_name
# =============================================================================


def testget_return_type_name_with_typed_dict() -> None:
    """Test return type extraction for TypedDict."""

    @get("/books", sync_to_thread=False)
    def get_books() -> BookProps:
        return BookProps(title="Test", author="Author")

    app = Litestar([get_books])
    handler = app.routes[0].route_handlers[0]  # type: ignore[union-attr]
    result = get_return_type_name(handler)
    assert result == "BookProps"


def testget_return_type_name_with_dataclass() -> None:
    """Test return type extraction for dataclass."""

    @get("/users", sync_to_thread=False)
    def get_users() -> UserProps:
        return UserProps(name="Test", email="test@example.com")

    app = Litestar([get_users])
    handler = app.routes[0].route_handlers[0]  # type: ignore[union-attr]
    result = get_return_type_name(handler)
    assert result == "UserProps"


def testget_return_type_name_with_dict() -> None:
    """Test return type extraction for dict type."""

    @get("/data", sync_to_thread=False)
    def get_data() -> dict[str, Any]:
        return {}

    app = Litestar([get_data])
    handler = app.routes[0].route_handlers[0]  # type: ignore[union-attr]
    result = get_return_type_name(handler)
    assert result == "dict"


def testget_return_type_name_with_list() -> None:
    """Test return type extraction for list type."""

    @get("/items", sync_to_thread=False)
    def get_items() -> list[str]:
        return []

    app = Litestar([get_items])
    handler = app.routes[0].route_handlers[0]  # type: ignore[union-attr]
    result = get_return_type_name(handler)
    assert result == "list"


def testget_return_type_name_none_return() -> None:
    """Test return type extraction for None return type returns None."""

    @get("/none", sync_to_thread=False)
    def none_handler() -> None:
        pass

    app = Litestar([none_handler])
    handler = app.routes[0].route_handlers[0]  # type: ignore[union-attr]
    result = get_return_type_name(handler)
    # None has no __name__ attribute, so returns None
    assert result is None


def testget_return_type_name_with_string_annotation() -> None:
    """Test return type extraction for forward reference string annotation."""

    @get("/forward", sync_to_thread=False)
    def forward_ref() -> "dict[str, str]":
        return {}

    app = Litestar([forward_ref])
    handler = app.routes[0].route_handlers[0]  # type: ignore[union-attr]
    result = get_return_type_name(handler)
    assert result == "dict[str, str]"


# =============================================================================
# Tests for get_openapi_schema_ref
# =============================================================================


def testget_openapi_schema_ref_with_valid_ref() -> None:
    """Test schema ref extraction when ref exists."""

    @get("/books", sync_to_thread=False)
    def get_books() -> BookProps:
        return BookProps(title="Test", author="Author")

    app = Litestar([get_books])
    openapi = app.openapi_schema.to_schema()

    handler = app.routes[0].route_handlers[0]  # type: ignore[union-attr]
    result = get_openapi_schema_ref(handler, openapi, "/books", "GET")

    # Should return a schema ref if one exists (depends on Litestar's OpenAPI generation)
    # The ref may or may not exist depending on how Litestar generates the schema
    assert result is None or result.startswith("#/components/schemas/")


def testget_openapi_schema_ref_no_schema() -> None:
    """Test schema ref extraction with no OpenAPI schema."""

    @get("/test", sync_to_thread=False)
    def test_handler() -> dict[str, str]:
        return {}

    app = Litestar([test_handler])
    handler = app.routes[0].route_handlers[0]  # type: ignore[union-attr]
    result = get_openapi_schema_ref(handler, None, "/test", "GET")
    assert result is None


def testget_openapi_schema_ref_missing_path() -> None:
    """Test schema ref extraction when path doesn't exist."""

    @get("/test", sync_to_thread=False)
    def test_handler() -> dict[str, str]:
        return {}

    app = Litestar([test_handler])
    openapi = app.openapi_schema.to_schema()

    handler = app.routes[0].route_handlers[0]  # type: ignore[union-attr]
    result = get_openapi_schema_ref(handler, openapi, "/nonexistent", "GET")
    assert result is None


# =============================================================================
# Tests for extract_inertia_pages
# =============================================================================


def test_extract_inertia_pages_with_component() -> None:
    """Test page extraction for routes with component annotation."""

    @get("/dashboard", opt={"component": "Dashboard/Index"}, sync_to_thread=False)
    def dashboard() -> dict[str, str]:
        return {}

    app = Litestar([dashboard])
    pages = extract_inertia_pages(app)

    assert len(pages) == 1
    assert pages[0].component == "Dashboard/Index"
    assert pages[0].route_path == "/dashboard"


def test_extract_inertia_pages_with_page_opt() -> None:
    """Test page extraction using 'page' opt key (alternative to 'component')."""

    @get("/home", opt={"page": "Home"}, sync_to_thread=False)
    def home() -> dict[str, str]:
        return {}

    app = Litestar([home])
    pages = extract_inertia_pages(app)

    assert len(pages) == 1
    assert pages[0].component == "Home"


def test_extract_inertia_pages_without_component_skipped() -> None:
    """Test routes without component annotation are skipped."""

    @get("/api/data", sync_to_thread=False)
    def api_data() -> dict[str, str]:
        return {}

    @get("/dashboard", opt={"component": "Dashboard"}, sync_to_thread=False)
    def dashboard() -> dict[str, str]:
        return {}

    app = Litestar([api_data, dashboard])
    pages = extract_inertia_pages(app)

    # Only dashboard should be included
    assert len(pages) == 1
    assert pages[0].component == "Dashboard"


def test_extract_inertia_pages_multiple_components() -> None:
    """Test extraction of multiple page components."""

    @get("/", opt={"component": "Home"}, sync_to_thread=False)
    def home() -> dict[str, str]:
        return {}

    @get("/about", opt={"component": "About"}, sync_to_thread=False)
    def about() -> dict[str, str]:
        return {}

    @get("/contact", opt={"component": "Contact"}, sync_to_thread=False)
    def contact() -> dict[str, str]:
        return {}

    app = Litestar([home, about, contact])
    pages = extract_inertia_pages(app)

    assert len(pages) == 3
    components = {p.component for p in pages}
    assert components == {"Home", "About", "Contact"}


def test_extract_inertia_pages_with_path_params() -> None:
    """Test page extraction normalizes path parameters."""

    @get("/users/{user_id:int}", opt={"component": "Users/Show"}, sync_to_thread=False)
    def show_user(user_id: FromPath[int]) -> dict[str, int]:
        return {"id": user_id}

    app = Litestar([show_user])
    pages = extract_inertia_pages(app)

    assert len(pages) == 1
    # Path should be normalized
    assert "{user_id}" in pages[0].route_path


def test_extract_inertia_pages_captures_return_type() -> None:
    """Test that return type is captured from handler."""

    @get("/books", opt={"component": "Books/Index"}, sync_to_thread=False)
    def books() -> BookProps:
        return BookProps(title="Test", author="Author")

    app = Litestar([books])
    pages = extract_inertia_pages(app)

    assert len(pages) == 1
    assert pages[0].props_type == "BookProps"
    assert pages[0].ts_type == "BookProps"
    assert pages[0].custom_types == ["BookProps"]


def test_extract_inertia_pages_marks_non_mapping_payloads_for_content_wrapping() -> None:
    """Dataclass payloads should keep runtime-compatible nested content metadata."""

    @get("/users", opt={"component": "Users/Show"}, sync_to_thread=False)
    def users() -> UserProps:
        return UserProps(name="Test", email="test@example.com")

    app = Litestar([users])
    pages = extract_inertia_pages(app)

    assert len(pages) == 1
    assert pages[0].props_type == "UserProps"
    assert pages[0].ts_type == "UserProps"
    assert pages[0].wrap_with_content is True


def test_extract_inertia_pages_union_type_with_any() -> None:
    """Test that union types with Any preserve the specific type."""

    @get("/reset", opt={"component": "auth/reset-password"}, sync_to_thread=False)
    def reset_password() -> "Any | BookProps":
        return BookProps(title="Test", author="Author")

    app = Litestar([reset_password])
    pages = extract_inertia_pages(app)

    assert len(pages) == 1
    # The union type should preserve the BookProps type
    # Either as "any | BookProps" or with BookProps in custom_types
    page = pages[0]
    # Check that BookProps is preserved somewhere in the type info
    has_book_props = (
        (page.props_type and "BookProps" in page.props_type)
        or (page.ts_type and "BookProps" in page.ts_type)
        or "BookProps" in page.custom_types
    )
    assert has_book_props, (
        f"BookProps should be preserved in union type. Got: props_type={page.props_type}, ts_type={page.ts_type}, custom_types={page.custom_types}"
    )


def test_extract_inertia_pages_filters_redirect_from_union() -> None:
    """Test that response types (like Redirect) are filtered from union types."""
    from litestar.response import Redirect

    @get("/login", opt={"component": "auth/login"}, sync_to_thread=False)
    def show_login() -> Redirect | BookProps:
        return BookProps(title="Test", author="Author")

    app = Litestar([show_login])
    pages = extract_inertia_pages(app)

    assert len(pages) == 1
    page = pages[0]
    # The Redirect type should be filtered out, leaving only BookProps
    # The type should NOT contain "any" from the redirect being converted
    assert page.ts_type == "BookProps" or (page.props_type and "BookProps" in page.props_type)
    # Ensure "any" is not in the type (would indicate Redirect wasn't filtered)
    if page.ts_type:
        assert "any" not in page.ts_type.lower(), (
            f"Redirect should be filtered, not converted to any. Got: {page.ts_type}"
        )


def test_extract_inertia_pages_captures_handler_name() -> None:
    """Test that handler name is captured (uses function name, not route name)."""

    @get("/test", name="test_route", opt={"component": "Test"}, sync_to_thread=False)
    def my_handler() -> dict[str, str]:
        return {}

    app = Litestar([my_handler])
    pages = extract_inertia_pages(app)

    assert len(pages) == 1
    # handler_name uses handler_name or name attribute, which is function name
    assert pages[0].handler_name == "my_handler"


def test_extract_inertia_pages_empty_app() -> None:
    """Test extraction from app with no routes."""
    app = Litestar([])
    pages = extract_inertia_pages(app)
    assert pages == []


# =============================================================================
# Tests for generate_inertia_pages_json
# =============================================================================


def test_generate_inertia_pages_json_basic() -> None:
    """Test basic JSON generation structure."""

    @get("/", opt={"component": "Home"}, sync_to_thread=False)
    def home() -> dict[str, str]:
        return {}

    app = Litestar([home])
    result = generate_inertia_pages_json(app)

    assert "pages" in result
    assert "sharedProps" in result
    assert "typeGenConfig" in result
    # Note: generatedAt was removed for deterministic builds (PR #162 follow-up)


def test_generate_inertia_pages_json_pages_structure() -> None:
    """Test pages dict structure in generated JSON."""

    @get("/dashboard", opt={"component": "Dashboard"}, sync_to_thread=False)
    def dashboard() -> dict[str, str]:
        return {}

    app = Litestar([dashboard])
    result = generate_inertia_pages_json(app)

    assert "Dashboard" in result["pages"]
    page = result["pages"]["Dashboard"]
    assert page["route"] == "/dashboard"


def test_generate_inertia_pages_json_with_props_type() -> None:
    """Test that props type is included when available."""

    @get("/books", opt={"component": "Books"}, sync_to_thread=False)
    def books() -> BookProps:
        return BookProps(title="Test", author="Author")

    app = Litestar([books])
    result = generate_inertia_pages_json(app)

    page = result["pages"]["Books"]
    assert page.get("propsType") == "BookProps"
    assert page.get("tsType") == "BookProps"
    assert page.get("customTypes") == ["BookProps"]
    assert "wrapWithContent" not in page


def test_generate_inertia_pages_json_marks_non_mapping_payloads_for_content_wrapping() -> None:
    """Dataclass payload metadata should tell the TS emitter to keep nested content."""

    @get("/users", opt={"component": "Users/Show"}, sync_to_thread=False)
    def users() -> UserProps:
        return UserProps(name="Test", email="test@example.com")

    app = Litestar([users])
    result = generate_inertia_pages_json(app)

    page = result["pages"]["Users/Show"]
    assert page["propsType"] == "UserProps"
    assert page["tsType"] == "UserProps"
    assert page["wrapWithContent"] is True


def test_generate_inertia_pages_json_includes_types_config_hints() -> None:
    """Test that TypeGenConfig hints are included when provided."""

    @get("/books", opt={"component": "Books"}, sync_to_thread=False)
    def books() -> BookProps:
        return BookProps(title="Test", author="Author")

    app = Litestar([books])
    types_config = TypeGenConfig(type_import_paths={"OffsetPagination": "@/types/pagination"}, fallback_type="any")
    result = generate_inertia_pages_json(app, types_config=types_config)

    assert result.get("typeImportPaths") == {"OffsetPagination": "@/types/pagination"}
    assert result.get("fallbackType") == "any"


def test_generate_inertia_pages_json_shared_props() -> None:
    """Test shared props structure."""

    @get("/", opt={"component": "Home"}, sync_to_thread=False)
    def home() -> dict[str, str]:
        return {}

    app = Litestar([home])
    result = generate_inertia_pages_json(app)

    shared = result["sharedProps"]
    assert "csrf_token" in shared
    assert shared["csrf_token"]["type"] == "string"
    assert shared["csrf_token"]["optional"] is True
    # flash and errors belong to the page object, not props - see the
    # page-object props tests below.
    assert "errors" not in shared
    assert "flash" not in shared


def test_generate_inertia_pages_json_type_gen_config_defaults() -> None:
    """Test type gen config with default values."""

    @get("/", opt={"component": "Home"}, sync_to_thread=False)
    def home() -> dict[str, str]:
        return {}

    app = Litestar([home])
    result = generate_inertia_pages_json(app)

    config = result["typeGenConfig"]
    assert config["includeDefaultAuth"] is True
    assert config["includeDefaultFlash"] is True


def test_generate_inertia_pages_json_type_gen_config_custom() -> None:
    """Test type gen config with custom values."""

    @get("/", opt={"component": "Home"}, sync_to_thread=False)
    def home() -> dict[str, str]:
        return {}

    app = Litestar([home])
    result = generate_inertia_pages_json(app, include_default_auth=False, include_default_flash=False)

    config = result["typeGenConfig"]
    assert config["includeDefaultAuth"] is False
    assert config["includeDefaultFlash"] is False


def test_generate_inertia_pages_json_includes_handler_name() -> None:
    """Test that handler name is included in output (uses function name)."""

    @get("/test", name="test_route", opt={"component": "Test"}, sync_to_thread=False)
    def my_handler() -> dict[str, str]:
        return {}

    app = Litestar([my_handler])
    result = generate_inertia_pages_json(app)

    page = result["pages"]["Test"]
    # Uses function name, not route name
    assert page.get("handler") == "my_handler"


def test_generate_inertia_pages_json_empty_app() -> None:
    """Test JSON generation for empty app."""
    app = Litestar([])
    result = generate_inertia_pages_json(app)

    assert result["pages"] == {}
    assert "sharedProps" in result
    assert "typeGenConfig" in result


# Note: test_generate_inertia_pages_json_generated_at_is_iso was removed
# because generatedAt timestamp was removed for deterministic builds.


# =============================================================================
# Tests for page-object props (flash / errors)
# =============================================================================


def test_generate_inertia_pages_json_omits_flash_from_shared_props() -> None:
    """Inertia sends flash at the page top level, so it is not a prop.

    The runtime pops flash out of props (inertia/response.py) to match
    ``Page.flash`` in @inertiajs/core. Generating it as a prop promises a value
    that is never there.
    """
    app = Litestar([])
    result = generate_inertia_pages_json(app, include_default_flash=True)

    assert "flash" not in result["sharedProps"]


def test_generate_inertia_pages_json_omits_errors_from_shared_props() -> None:
    """Inertia declares ``Page.props.errors`` itself, typed from its own config."""
    app = Litestar([])
    result = generate_inertia_pages_json(app)

    assert "errors" not in result["sharedProps"]


def test_generate_inertia_pages_json_auth_does_not_depend_on_flash_flag() -> None:
    """include_default_flash must not conjure an auth prop."""
    app = Litestar([])
    result = generate_inertia_pages_json(app, include_default_auth=False, include_default_flash=True)

    assert "auth" not in result["sharedProps"]


def test_generate_inertia_pages_json_auth_follows_its_own_flag() -> None:
    """include_default_auth alone controls the generated auth prop."""
    app = Litestar([])
    result = generate_inertia_pages_json(app, include_default_auth=True, include_default_flash=False)

    assert result["sharedProps"]["auth"]["type"] == "AuthData"


def test_generate_inertia_pages_json_keeps_csrf_token_prop() -> None:
    """csrf_token is a real prop and stays."""
    app = Litestar([])
    result = generate_inertia_pages_json(app)

    assert result["sharedProps"]["csrf_token"]["type"] == "string"


# =============================================================================
# Tests for shared_page_prop_types
# =============================================================================


def _shared_prop_types_app() -> Litestar:
    """Build an app whose OpenAPI schema already carries SharedUser via a route.

    Returns:
        An app with one plain Inertia page and one route returning ``SharedUser``.
    """

    @get("/", opt={"component": "Home"}, sync_to_thread=False)
    def home() -> dict[str, str]:
        return {}

    @get("/me", opt={"component": "Me"}, sync_to_thread=False)
    def me() -> SharedUser:
        return SharedUser(id="1", email="a@b.c")

    return Litestar([home, me])


def test_generate_inertia_pages_json_shared_page_prop_types_resolves_annotation() -> None:
    """A declared share() prop resolves to its Python annotation instead of a synthesized type."""
    app = _shared_prop_types_app()
    result = generate_inertia_pages_json(
        app,
        openapi_schema=app.openapi_schema.to_schema(),
        inertia_config=InertiaConfig(shared_page_prop_types={"auth": AuthProps}),
    )

    auth = result["sharedProps"]["auth"]
    assert auth["type"] == "AuthProps"
    assert auth["optional"] is True


def test_generate_inertia_pages_json_shared_page_prop_types_reuses_route_schema() -> None:
    """A nested model already registered by a route is reused, not duplicated."""
    app = _shared_prop_types_app()
    openapi_schema = app.openapi_schema.to_schema()
    generate_inertia_pages_json(
        app, openapi_schema=openapi_schema, inertia_config=InertiaConfig(shared_page_prop_types={"auth": AuthProps})
    )

    schemas = openapi_schema["components"]["schemas"]
    shared_user_names = [name for name in schemas if name.endswith("SharedUser")]
    assert len(shared_user_names) == 1, f"SharedUser registered more than once: {shared_user_names}"
    assert any(name.endswith("AuthProps") for name in schemas)


def test_generate_inertia_pages_json_shared_page_prop_types_overrides_default_auth() -> None:
    """An explicit declaration wins over the synthesized AuthData convention."""
    app = _shared_prop_types_app()
    result = generate_inertia_pages_json(
        app,
        openapi_schema=app.openapi_schema.to_schema(),
        include_default_auth=True,
        inertia_config=InertiaConfig(shared_page_prop_types={"auth": AuthProps}),
    )

    assert result["sharedProps"]["auth"]["type"] == "AuthProps"


@pytest.mark.parametrize("include_default_auth", [True, False])
@pytest.mark.parametrize("include_default_flash", [True, False])
def test_generate_inertia_pages_json_shared_page_prop_types_unset_is_unchanged(
    include_default_auth: bool, include_default_flash: bool
) -> None:
    """Leaving the field unset produces byte-identical output for every boolean combination."""
    baseline_app = _shared_prop_types_app()
    baseline = generate_inertia_pages_json(
        baseline_app,
        openapi_schema=baseline_app.openapi_schema.to_schema(),
        include_default_auth=include_default_auth,
        include_default_flash=include_default_flash,
        inertia_config=InertiaConfig(),
    )

    declared_app = _shared_prop_types_app()
    with_field = generate_inertia_pages_json(
        declared_app,
        openapi_schema=declared_app.openapi_schema.to_schema(),
        include_default_auth=include_default_auth,
        include_default_flash=include_default_flash,
        inertia_config=InertiaConfig(shared_page_prop_types=None),
    )

    assert with_field == baseline


def test_generate_inertia_pages_json_shared_page_prop_types_resolves_generic_container() -> None:
    """A container annotation resolves to a TypeScript array, not the bare origin name."""
    app = _shared_prop_types_app()
    openapi_schema = app.openapi_schema.to_schema()
    result = generate_inertia_pages_json(
        app,
        openapi_schema=openapi_schema,
        inertia_config=InertiaConfig(shared_page_prop_types={"recent": list[SharedUser]}),
    )

    recent = result["sharedProps"]["recent"]
    assert recent["type"] == "SharedUser[]", f"expected an array type, got {recent['type']!r}"
    assert any(name.endswith("SharedUser") for name in openapi_schema["components"]["schemas"])


def test_generate_inertia_pages_json_shared_page_prop_types_ignores_empty_key() -> None:
    """Empty keys are skipped, matching existing static/session prop behavior."""
    app = _shared_prop_types_app()
    result = generate_inertia_pages_json(
        app,
        openapi_schema=app.openapi_schema.to_schema(),
        inertia_config=InertiaConfig(shared_page_prop_types={"": AuthProps}),
    )

    assert "" not in result["sharedProps"]


# =============================================================================
# Tests for InertiaPageMetadata dataclass
# =============================================================================


def test_inertia_page_metadata_defaults() -> None:
    """Test InertiaPageMetadata default values."""
    page = InertiaPageMetadata(component="Test", route_path="/test")

    assert page.component == "Test"
    assert page.route_path == "/test"
    assert page.props_type is None
    assert page.ts_type is None
    assert page.custom_types == []
    assert page.wrap_with_content is False
    assert page.schema_ref is None
    assert page.handler_name is None


def test_inertia_page_metadata_full() -> None:
    """Test InertiaPageMetadata with all fields."""
    page = InertiaPageMetadata(
        component="Dashboard/Index",
        route_path="/dashboard",
        props_type="DashboardProps",
        ts_type="DashboardProps",
        custom_types=["DashboardProps"],
        wrap_with_content=True,
        schema_ref="#/components/schemas/DashboardProps",
        handler_name="dashboard_index",
    )

    assert page.component == "Dashboard/Index"
    assert page.route_path == "/dashboard"
    assert page.props_type == "DashboardProps"
    assert page.ts_type == "DashboardProps"
    assert page.custom_types == ["DashboardProps"]
    assert page.wrap_with_content is True
    assert page.schema_ref == "#/components/schemas/DashboardProps"
    assert page.handler_name == "dashboard_index"
