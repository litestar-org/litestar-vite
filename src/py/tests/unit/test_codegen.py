"""Unit tests for codegen module."""

from typing import Annotated
from uuid import UUID

from litestar import Litestar, get, post
from litestar.params import Parameter

from litestar_vite.codegen import (
    _escape_ts_string,
    _is_type_required,
    _ts_type_for_param,
    generate_routes_ts,
)


def test_ts_type_for_param_basic_types() -> None:
    """Test TypeScript type mapping for basic types."""
    assert _ts_type_for_param("string") == "string"
    assert _ts_type_for_param("integer") == "number"
    assert _ts_type_for_param("number") == "number"
    assert _ts_type_for_param("boolean") == "boolean"
    assert _ts_type_for_param("int") == "number"
    assert _ts_type_for_param("float") == "number"
    assert _ts_type_for_param("str") == "string"
    assert _ts_type_for_param("bool") == "boolean"


def test_ts_type_for_param_special_formats() -> None:
    """Test TypeScript type mapping for special formats."""
    assert _ts_type_for_param("uuid") == "string"
    assert _ts_type_for_param("date") == "string"
    assert _ts_type_for_param("date-time") == "string"
    assert _ts_type_for_param("email") == "string"
    assert _ts_type_for_param("uri") == "string"
    assert _ts_type_for_param("path") == "string"


def test_ts_type_for_param_optional_handling() -> None:
    """Test TypeScript type mapping handles optional markers."""
    assert _ts_type_for_param("string | undefined") == "string | undefined"
    assert _ts_type_for_param("integer?") == "number | undefined"
    assert _ts_type_for_param("unknown") == "unknown"


def test_is_type_required() -> None:
    """Test required type detection."""
    assert _is_type_required("string") is True
    assert _is_type_required("integer") is True
    assert _is_type_required("string | undefined") is False
    assert _is_type_required("integer?") is False


def test_escape_ts_string() -> None:
    """Test TypeScript string escaping."""
    assert _escape_ts_string("simple") == "simple"
    assert _escape_ts_string("with'quote") == "with\\'quote"
    assert _escape_ts_string('with"double') == 'with\\"double'
    assert _escape_ts_string("with\\backslash") == "with\\\\backslash"


def test_generate_routes_ts_basic_route() -> None:
    """Test TypeScript route generation for a basic route."""

    @get("/users", name="list_users", sync_to_thread=False)
    def list_users() -> list[str]:
        return ["user1", "user2"]

    app = Litestar([list_users])
    ts_content = generate_routes_ts(app)

    # Check that the route name is in the output
    assert "'list_users'" in ts_content
    # Check the path
    assert "path: '/users'" in ts_content
    # Check method
    assert "'GET'" in ts_content
    # Check it's a valid TypeScript file structure
    assert "export type RouteName =" in ts_content
    assert "export function route<" in ts_content
    assert "export const routes = {" in ts_content


def test_generate_routes_ts_with_path_params() -> None:
    """Test TypeScript route generation with path parameters."""

    @get("/users/{user_id:int}", name="get_user", sync_to_thread=False)
    def get_user(user_id: int) -> dict[str, int]:
        return {"id": user_id}

    app = Litestar([get_user])
    # Use OpenAPI schema to get proper type inference for path params
    ts_content = generate_routes_ts(app, openapi_schema=app.openapi_schema.to_schema())

    # Check route name
    assert "'get_user'" in ts_content
    # Check path with parameter
    assert "/users/{user_id}" in ts_content
    # Check parameter type mapping (int -> number)
    assert "user_id: number" in ts_content
    # Check pathParams array
    assert "'user_id'" in ts_content
    assert "pathParams:" in ts_content


def test_generate_routes_ts_with_uuid_param() -> None:
    """Test TypeScript route generation with UUID path parameter."""

    @get("/items/{item_id:uuid}", name="get_item", sync_to_thread=False)
    def get_item(item_id: UUID) -> dict[str, str]:
        return {"id": str(item_id)}

    app = Litestar([get_item])
    # Use OpenAPI schema to get proper type inference
    ts_content = generate_routes_ts(app, openapi_schema=app.openapi_schema.to_schema())

    # Check UUID type maps to string (UUID format is represented as string in TypeScript)
    assert "item_id: string" in ts_content


def test_generate_routes_ts_with_query_params() -> None:
    """Test TypeScript route generation with query parameters."""

    @get("/search", name="search", sync_to_thread=False)
    def search(
        q: str,
        limit: Annotated[int | None, Parameter(default=10)] = None,
    ) -> list[str]:
        return []

    app = Litestar([search])
    ts_content = generate_routes_ts(app, openapi_schema=app.openapi_schema.to_schema())

    # Check route name
    assert "'search'" in ts_content
    # Check that query params interface has entries
    assert "RouteQueryParams" in ts_content


def test_generate_routes_ts_empty_routes() -> None:
    """Test TypeScript generation with no routes produces valid TS."""
    # No route handlers - the app will have no user routes
    app = Litestar([])
    ts_content = generate_routes_ts(app)

    # Should still produce valid TypeScript structure
    assert "export type RouteName =" in ts_content
    assert "export const routes = {" in ts_content
    # The RouteName type should be 'never' when no routes
    # Check that the file is syntactically complete
    assert ts_content.count("{") == ts_content.count("}")


def test_generate_routes_ts_multiple_methods() -> None:
    """Test TypeScript generation with routes having multiple methods."""

    @get("/resources/{id:int}", name="get_resource", sync_to_thread=False)
    def get_resource(id: int) -> dict[str, int]:
        return {"id": id}

    @post("/resources/{id:int}", name="update_resource", sync_to_thread=False)
    def update_resource(id: int, data: dict[str, str]) -> dict[str, int]:
        return {"id": id}

    app = Litestar([get_resource, update_resource])
    ts_content = generate_routes_ts(app)

    # Check both routes exist
    assert "'get_resource'" in ts_content
    assert "'update_resource'" in ts_content
    # Check both methods appear
    assert "'GET'" in ts_content
    assert "'POST'" in ts_content


def test_generate_routes_ts_with_component() -> None:
    """Test TypeScript generation includes component metadata."""

    @get("/dashboard", name="dashboard", opt={"component": "Dashboard/Index"}, sync_to_thread=False)
    def dashboard() -> dict[str, str]:
        return {}

    app = Litestar([dashboard])
    ts_content = generate_routes_ts(app)

    # Check component is included
    assert "component: 'Dashboard/Index'" in ts_content


def test_generate_routes_ts_has_helper_functions() -> None:
    """Test that generated TypeScript includes helper functions."""

    @get("/test", name="test", sync_to_thread=False)
    def test_route() -> str:
        return "test"

    app = Litestar([test_route])
    ts_content = generate_routes_ts(app)

    # Check helper functions are present
    assert "export function hasRoute(" in ts_content
    assert "export function getRouteNames(" in ts_content
    assert "export function getRoute<" in ts_content


def test_generate_routes_ts_has_api_url_config() -> None:
    """Test that generated TypeScript has API_URL configuration."""

    @get("/test", name="test", sync_to_thread=False)
    def test_route() -> str:
        return "test"

    app = Litestar([test_route])
    ts_content = generate_routes_ts(app)

    # Check API_URL config is present
    assert "VITE_API_URL" in ts_content
    assert "API_URL" in ts_content


def test_generate_routes_ts_type_overloads() -> None:
    """Test that route function has proper TypeScript overloads."""

    @get("/simple", name="simple", sync_to_thread=False)
    def simple_route() -> str:
        return "simple"

    @get("/with-param/{id:int}", name="with_param", sync_to_thread=False)
    def param_route(id: int) -> dict[str, int]:
        return {"id": id}

    app = Litestar([simple_route, param_route])
    ts_content = generate_routes_ts(app)

    # Check overloads for routes with/without required params
    assert "RoutesWithoutRequiredParams" in ts_content
    assert "RoutesWithRequiredParams" in ts_content


def test_generate_routes_ts_filters() -> None:
    """Test that route filters work with TypeScript generation."""

    @get("/users", name="list_users", sync_to_thread=False)
    def list_users() -> list[str]:
        return []

    @get("/posts", name="list_posts", sync_to_thread=False)
    def list_posts() -> list[str]:
        return []

    @get("/admin/settings", name="admin_settings", sync_to_thread=False)
    def admin_settings() -> dict[str, str]:
        return {}

    app = Litestar([list_users, list_posts, admin_settings])

    # Test with 'only' filter
    ts_content = generate_routes_ts(app, only=["users"])
    assert "'list_users'" in ts_content
    assert "'list_posts'" not in ts_content
    assert "'admin_settings'" not in ts_content

    # Test with 'exclude' filter
    ts_content = generate_routes_ts(app, exclude=["admin"])
    assert "'list_users'" in ts_content
    assert "'list_posts'" in ts_content
    assert "'admin_settings'" not in ts_content


def test_generate_routes_ts_escapes_special_chars() -> None:
    """Test that special characters in paths are escaped."""

    @get("/api/v1/user's-data", name="user_data", sync_to_thread=False)
    def user_data() -> dict[str, str]:
        return {}

    app = Litestar([user_data])
    ts_content = generate_routes_ts(app)

    # Check that the apostrophe is escaped
    assert "\\'" in ts_content


def test_generate_routes_ts_is_valid_typescript() -> None:
    """Test that generated content is syntactically valid TypeScript."""

    @get("/users", name="list_users", sync_to_thread=False)
    def list_users() -> list[str]:
        return []

    @get("/users/{user_id:int}", name="get_user", sync_to_thread=False)
    def get_user(user_id: int) -> dict[str, int]:
        return {"id": user_id}

    @get("/search", name="search", sync_to_thread=False)
    def search(q: str) -> list[str]:
        return []

    app = Litestar([list_users, get_user, search])
    ts_content = generate_routes_ts(app)

    # Basic structural checks
    assert ts_content.startswith("/**")  # Starts with doc comment
    assert "export type RouteName" in ts_content
    assert "export interface RoutePathParams" in ts_content
    assert "export interface RouteQueryParams" in ts_content
    assert "export const routes = {" in ts_content
    assert "export function route<" in ts_content

    # Balanced braces
    assert ts_content.count("{") == ts_content.count("}")
    assert ts_content.count("(") == ts_content.count(")")
    assert ts_content.count("[") == ts_content.count("]")
