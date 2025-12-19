"""Unit tests for codegen module."""

from typing import Annotated, Any
from uuid import UUID

from litestar import Litestar, get, post
from litestar.params import Parameter

from litestar_vite.codegen import escape_ts_string, generate_routes_ts, is_type_required, ts_type_for_param
from litestar_vite.codegen._routes import extract_path_params, extract_route_metadata, make_unique_name
from litestar_vite.codegen._ts import (
    collect_ref_names,
    join_union,
    python_type_to_typescript,
    ts_literal,
    ts_type_from_openapi,
    wrap_for_array,
)


def testts_type_for_param_basic_types() -> None:
    """Test TypeScript type mapping for basic types."""
    assert ts_type_for_param("string") == "string"
    assert ts_type_for_param("integer") == "number"
    assert ts_type_for_param("number") == "number"
    assert ts_type_for_param("boolean") == "boolean"
    assert ts_type_for_param("int") == "number"
    assert ts_type_for_param("float") == "number"
    assert ts_type_for_param("str") == "string"
    assert ts_type_for_param("bool") == "boolean"


def testts_type_for_param_special_formats() -> None:
    """Test TypeScript type mapping for special formats."""
    assert ts_type_for_param("uuid") == "string"
    assert ts_type_for_param("date") == "string"
    assert ts_type_for_param("date-time") == "string"
    assert ts_type_for_param("email") == "string"
    assert ts_type_for_param("uri") == "string"
    assert ts_type_for_param("path") == "string"


def testts_type_for_param_optional_handling() -> None:
    """Test TypeScript type mapping handles optional markers."""
    assert ts_type_for_param("string | undefined") == "string | undefined"
    assert ts_type_for_param("integer?") == "number | undefined"
    assert ts_type_for_param("unknown") == "unknown"


def testis_type_required() -> None:
    """Test required type detection."""
    assert is_type_required("string") is True
    assert is_type_required("integer") is True
    assert is_type_required("string | undefined") is False
    assert is_type_required("integer?") is False


def testescape_ts_string() -> None:
    """Test TypeScript string escaping."""
    assert escape_ts_string("simple") == "simple"
    assert escape_ts_string("with'quote") == "with\\'quote"
    assert escape_ts_string('with"double') == 'with\\"double'
    assert escape_ts_string("with\\backslash") == "with\\\\backslash"


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
    assert "export const routeDefinitions = {" in ts_content


def test_generate_routes_ts_global_route_registers_window() -> None:
    @get("/users", name="list_users", sync_to_thread=False)
    def list_users() -> list[str]:
        return ["user1", "user2"]

    app = Litestar([list_users])
    ts_content = generate_routes_ts(app, global_route=True)

    assert "(window as any).route = route;" in ts_content


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

    # Check UUID format is preserved as a semantic alias in TypeScript.
    assert "export type UUID = string;" in ts_content
    assert "item_id: UUID" in ts_content


def test_generate_routes_ts_with_query_params() -> None:
    """Test TypeScript route generation with query parameters."""

    @get("/search", name="search", sync_to_thread=False)
    def search(q: str, limit: Annotated[int | None, Parameter(default=10)] = None) -> list[str]:
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
    assert "export const routeDefinitions = {" in ts_content
    # The RouteName type should be 'never' when no routes
    # Check that the file is syntactically complete
    # Note: We don't check brace balance because regex literals like /\{([^}]+)\}/
    # contain unbalanced braces in the source code (this is valid JS/TS)
    assert "export function route<" in ts_content


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
    assert ts_content.startswith("// AUTO-GENERATED")  # Starts with generated marker
    assert "export type RouteName" in ts_content
    assert "export interface RoutePathParams" in ts_content
    assert "export interface RouteQueryParams" in ts_content
    assert "export const routeDefinitions = {" in ts_content
    assert "export function route<" in ts_content

    # Note: We don't check brace balance because regex literals like /\{([^}]+)\}/
    # contain unbalanced braces in the source code (this is valid JS/TS).
    # The real validation is done by TypeScript compilation via npm run build.
    assert ts_content.count("(") == ts_content.count(")")
    assert ts_content.count("[") == ts_content.count("]")


# Tests for ts_type_from_openapi (OpenAPI 3.1 compatibility)
# Note: These tests use Litestar's typescript_converter which sorts union types alphabetically


def testts_type_from_openapi_single_types() -> None:
    """Test basic single type mapping."""
    assert ts_type_from_openapi({"type": "string"}) == "string"
    assert ts_type_from_openapi({"type": "integer"}) == "number"
    assert ts_type_from_openapi({"type": "number"}) == "number"
    assert ts_type_from_openapi({"type": "boolean"}) == "boolean"
    assert ts_type_from_openapi({"type": "null"}) == "null"
    # Object without properties returns empty interface
    result = ts_type_from_openapi({"type": "object"})
    assert "{" in result  # Empty interface


def testts_type_from_openapi_ref() -> None:
    """Test schema $ref resolution emits the component name."""
    assert ts_type_from_openapi({"$ref": "#/components/schemas/User"}) == "User"


def testts_type_from_openapi_list_types() -> None:
    """Test OpenAPI 3.1 list types (nullable)."""
    # Litestar sorts union types alphabetically
    assert ts_type_from_openapi({"type": ["integer", "null"]}) == "null | number"
    assert ts_type_from_openapi({"type": ["string", "null"]}) == "null | string"
    assert ts_type_from_openapi({"type": ["null", "boolean"]}) == "boolean | null"
    assert ts_type_from_openapi({"type": ["number", "null"]}) == "null | number"


def testts_type_from_openapi_one_of() -> None:
    """Test oneOf compositions (Litestar's nullable pattern)."""
    schema = {"oneOf": [{"type": "integer"}, {"type": "null"}]}
    assert ts_type_from_openapi(schema) == "null | number"

    schema = {"oneOf": [{"type": "string"}, {"type": "integer"}]}
    assert ts_type_from_openapi(schema) == "number | string"


def testts_type_from_openapi_any_of() -> None:
    """Test anyOf compositions."""
    schema = {"anyOf": [{"type": "string"}, {"type": "integer"}]}
    assert ts_type_from_openapi(schema) == "number | string"


def testts_type_from_openapi_all_of() -> None:
    """Test allOf compositions (intersection)."""
    schema = {"allOf": [{"type": "object"}, {"type": "object"}]}
    result = ts_type_from_openapi(schema)
    assert "&" in result  # Intersection type


def testts_type_from_openapi_all_of_wraps_union_parts() -> None:
    """Test allOf wraps unions so TS precedence is correct."""
    schema = {"allOf": [{"anyOf": [{"type": "string"}, {"type": "integer"}]}, {"type": "string"}]}
    assert ts_type_from_openapi(schema) == "(number | string) & string"


def testts_type_from_openapi_enum() -> None:
    """Test enum as literal union."""
    assert ts_type_from_openapi({"enum": ["a", "b", "c"]}) == '"a" | "b" | "c"'
    assert ts_type_from_openapi({"enum": [1, 2, 3]}) == "1 | 2 | 3"
    assert ts_type_from_openapi({"enum": ["active", "inactive"]}) == '"active" | "inactive"'


def testts_type_from_openapi_const() -> None:
    """Test const as literal."""
    assert ts_type_from_openapi({"const": "active"}) == '"active"'
    assert ts_type_from_openapi({"const": 42}) == "42"
    assert ts_type_from_openapi({"const": True}) == "true"
    # Note: const=False returns "any" due to Litestar's falsy check bug
    # See: litestar/_openapi/typescript_converter/schema_parsing.py line ~117
    assert ts_type_from_openapi({"const": False}) == "any"


def testts_literal_helper() -> None:
    """Test literal helper covers common primitives and fallbacks."""
    assert ts_literal(None) == "null"
    assert ts_literal(True) == "true"
    assert ts_literal(False) == "false"
    assert ts_literal(1) == "1"
    assert ts_literal(1.5) == "1.5"
    assert ts_literal("x") == '"x"'
    assert ts_literal({"a": 1}) == "any"


def testts_type_from_openapi_array() -> None:
    """Test array types."""
    assert ts_type_from_openapi({"type": "array", "items": {"type": "string"}}) == "string[]"
    assert ts_type_from_openapi({"type": "array", "items": {"type": "integer"}}) == "number[]"
    assert ts_type_from_openapi({"type": "array"}) == "unknown[]"  # No items = unknown[]
    # Nested arrays
    schema = {"type": "array", "items": {"type": "array", "items": {"type": "number"}}}
    assert ts_type_from_openapi(schema) == "number[][]"
    # Arrays of unions must be parenthesized
    schema = {"type": "array", "items": {"anyOf": [{"type": "string"}, {"type": "integer"}]}}
    assert ts_type_from_openapi(schema) == "(number | string)[]"


def testts_type_from_openapi_format_only() -> None:
    """Test format-only schemas return 'any' (no type info)."""
    # Format without type returns 'any' per Litestar's behavior
    assert ts_type_from_openapi({"format": "uuid"}) == "any"
    assert ts_type_from_openapi({"format": "date-time"}) == "any"


def testts_type_from_openapi_string_formats() -> None:
    """Test OpenAPI string formats map to semantic aliases."""
    assert ts_type_from_openapi({"type": "string", "format": "uuid"}) == "UUID"
    assert ts_type_from_openapi({"type": "string", "format": "date-time"}) == "DateTime"
    assert ts_type_from_openapi({"type": "string", "format": "date"}) == "DateOnly"
    assert ts_type_from_openapi({"type": "string", "format": "time"}) == "TimeOnly"
    assert ts_type_from_openapi({"type": "string", "format": "duration"}) == "Duration"
    assert ts_type_from_openapi({"type": "string", "format": "email"}) == "Email"
    assert ts_type_from_openapi({"type": "string", "format": "uri"}) == "URI"
    assert ts_type_from_openapi({"type": "string", "format": "url"}) == "URI"
    assert ts_type_from_openapi({"type": "string", "format": "ipv4"}) == "IPv4"
    assert ts_type_from_openapi({"type": "string", "format": "ipv6"}) == "IPv6"
    assert ts_type_from_openapi({"type": "string", "format": "unknown-format"}) == "string"


def test_generate_routes_ts_query_params_do_not_emit_null() -> None:
    """Test generated URL param types never include `null`."""

    @get("/search-null", name="search_null", sync_to_thread=False)
    def search_null(q: str | None = None) -> list[str]:
        return []

    app = Litestar([search_null])
    ts_content = generate_routes_ts(app, openapi_schema=app.openapi_schema.to_schema())

    assert "q?: string" in ts_content
    assert "q?: string | null" not in ts_content
    assert "q?: null" not in ts_content


def testts_type_from_openapi_edge_cases() -> None:
    """Test edge cases."""
    assert ts_type_from_openapi({}) == "any"  # Empty schema = any
    assert ts_type_from_openapi({"type": []}) == "any"  # Empty type list = any
    assert ts_type_from_openapi({"type": ["null"]}) == "null"
    assert ts_type_from_openapi({"unknown_field": "value"}) == "any"


def testts_type_from_openapi_nullable_array() -> None:
    """Test nullable array in OpenAPI 3.1 style."""
    # oneOf with array and null (sorted alphabetically)
    schema: dict[str, Any] = {"oneOf": [{"type": "array", "items": {"type": "string"}}, {"type": "null"}]}
    assert ts_type_from_openapi(schema) == "null | string[]"


def testts_type_from_openapi_object_properties_required() -> None:
    """Test object properties generate correct optional markers."""
    schema: dict[str, Any] = {
        "type": "object",
        "properties": {"a": {"type": "string"}, "b": {"type": "integer"}},
        "required": ["a"],
    }
    result = ts_type_from_openapi(schema)
    assert "a: string;" in result
    assert "b?: number;" in result


def test_python_type_to_typescript_basic_mappings() -> None:
    """Test conversion of Python type strings to TypeScript."""
    assert python_type_to_typescript("", fallback="unknown") == ("unknown", False)
    assert python_type_to_typescript("str") == ("string", False)
    assert python_type_to_typescript("int") == ("number", False)
    ts_type, optional = python_type_to_typescript("typing.Optional[int]")
    assert optional is True
    assert ts_type == "Optional[int]"
    assert python_type_to_typescript("None") == ("null", True)
    assert python_type_to_typescript("Dict") == ("Record<string, unknown>", False)
    assert python_type_to_typescript("List", fallback="Foo") == ("Foo[]", False)


def test_collect_ref_names_nested() -> None:
    """Test collection of referenced schema names."""
    schema: dict[str, Any] = {
        "type": "object",
        "properties": {
            "user": {"$ref": "#/components/schemas/User"},
            "tags": {"type": "array", "items": {"$ref": "#/components/schemas/Tag"}},
        },
        "anyOf": [{"$ref": "#/components/schemas/A"}, {"type": "null"}],
    }
    assert collect_ref_names(schema) == {"User", "Tag", "A"}


def test_ts_helpers_union_and_array_wrapping() -> None:
    """Test union join and array wrap helpers."""
    assert join_union(set()) == "any"
    assert join_union({"string"}) == "string"
    assert wrap_for_array("") == "unknown"
    assert wrap_for_array("number | string") == "(number | string)"


def test_routes_helpersmake_unique_name_andextract_path_params() -> None:
    """Test helper behaviors for route name collisions and path param extraction."""
    used = {"users"}
    assert make_unique_name("users", used, "/users/{id:int}", ["GET"]).startswith("users_users_id:int")
    assert extract_path_params("/users/{id:int}/posts/{slug:path}") == {"id": "string", "slug": "string"}


def test_extract_route_metadata_falls_back_when_openapi_disabled() -> None:
    """Test route metadata extraction uses path parsing when OpenAPI is disabled."""

    @get("/users/{id:int}", name="user_detail", sync_to_thread=False)
    def user_detail(id: int) -> dict[str, int]:
        return {"id": id}

    app = Litestar([user_detail], openapi_config=None)
    routes = extract_route_metadata(app)
    route = next(r for r in routes if r.name == "user_detail")
    assert route.params == {"id": "string"}


def test_generate_routes_ts_no_semantic_alias_block_when_unused() -> None:
    """Test generated routes.ts does not include alias preamble when no formats are used."""

    @get("/users/{id:int}", name="user_by_id", sync_to_thread=False)
    def user_by_id(id: int) -> dict[str, int]:
        return {"id": id}

    app = Litestar([user_by_id])
    ts_content = generate_routes_ts(app, openapi_schema=app.openapi_schema.to_schema())
    assert "Semantic string aliases derived from OpenAPI `format`." not in ts_content


# ============================================================================
# Body Parameter Detection Tests
# ============================================================================


def test_post_body_param_not_in_query_params() -> None:
    """POST with body param should NOT show body in queryParameters."""
    from dataclasses import dataclass

    from litestar_vite.codegen import generate_routes_json

    @dataclass
    class TeamCreate:
        name: str

    @post("/teams", name="teams.add", sync_to_thread=False)
    def add_team(data: TeamCreate) -> dict[str, str]:
        return {}

    app = Litestar([add_team])
    routes = generate_routes_json(app, openapi_schema=app.openapi_schema.to_schema())

    route_data = routes["routes"]["teams.add"]
    assert "queryParameters" not in route_data, f"Body param should not appear in queryParameters: {route_data}"


def test_post_body_and_query_params_separated() -> None:
    """POST with both body and query params - only query params in queryParameters."""
    from dataclasses import dataclass

    from litestar_vite.codegen import generate_routes_json

    @dataclass
    class TeamCreate:
        name: str

    @post("/teams", name="teams.add", sync_to_thread=False)
    def add_team(data: TeamCreate, notify: bool = False) -> dict[str, str]:
        return {}

    app = Litestar([add_team])
    routes = generate_routes_json(app, openapi_schema=app.openapi_schema.to_schema())

    route_data = routes["routes"]["teams.add"]
    assert "queryParameters" in route_data, "Should have queryParameters"
    assert "data" not in route_data["queryParameters"], "Body param 'data' should be excluded"
    assert "notify" in route_data["queryParameters"], "Query param 'notify' should be included"
    assert route_data["queryParameters"]["notify"] == "boolean | undefined"


def test_put_body_param_excluded() -> None:
    """PUT with body param handled correctly."""
    from litestar import put
    from msgspec import Struct

    from litestar_vite.codegen import generate_routes_json

    class TeamUpdate(Struct):
        name: str

    @put("/teams/{team_id:int}", name="teams.update", sync_to_thread=False)
    def update_team(team_id: int, data: TeamUpdate) -> dict[str, str]:
        return {}

    app = Litestar([update_team])
    routes = generate_routes_json(app, openapi_schema=app.openapi_schema.to_schema())

    route_data = routes["routes"]["teams.update"]
    assert "queryParameters" not in route_data, f"Body param should be excluded: {route_data}"
    assert "parameters" in route_data
    assert "team_id" in route_data["parameters"]


def test_patch_body_param_excluded() -> None:
    """PATCH with body param handled correctly."""
    from litestar import patch
    from msgspec import Struct

    from litestar_vite.codegen import generate_routes_json

    class TeamPatch(Struct):
        name: str | None = None

    @patch("/teams/{team_id:int}", name="teams.patch", sync_to_thread=False)
    def patch_team(team_id: int, data: TeamPatch) -> dict[str, str]:
        return {}

    app = Litestar([patch_team])
    routes = generate_routes_json(app, openapi_schema=app.openapi_schema.to_schema())

    route_data = routes["routes"]["teams.patch"]
    assert "queryParameters" not in route_data, f"Body param should be excluded: {route_data}"


def test_get_no_body_params_possible() -> None:
    """GET request - all non-path params are query params."""
    from litestar_vite.codegen import generate_routes_json

    @get("/teams", name="teams.list", sync_to_thread=False)
    def list_teams(limit: int = 10, offset: int = 0) -> list[dict[str, str]]:
        return []

    app = Litestar([list_teams])
    routes = generate_routes_json(app, openapi_schema=app.openapi_schema.to_schema())

    route_data = routes["routes"]["teams.list"]
    assert "queryParameters" in route_data
    assert "limit" in route_data["queryParameters"]
    assert "offset" in route_data["queryParameters"]
    assert route_data["queryParameters"]["limit"] == "number | undefined"
    assert route_data["queryParameters"]["offset"] == "number | undefined"


def test_schema_excluded_endpoint_body_detection() -> None:
    """Endpoint with include_in_schema=False uses heuristics to exclude body."""
    from msgspec import Struct

    from litestar_vite.codegen import generate_routes_json

    class TeamCreate(Struct):
        name: str

    @post("/internal/teams", name="internal.teams.add", include_in_schema=False, sync_to_thread=False)
    def add_internal_team(data: TeamCreate, notify: bool = False) -> dict[str, str]:
        return {}

    app = Litestar([add_internal_team])
    routes = generate_routes_json(app, openapi_schema=app.openapi_schema.to_schema())

    route_data = routes["routes"]["internal.teams.add"]
    assert "queryParameters" in route_data, "Should have queryParameters with notify"
    assert "data" not in route_data["queryParameters"], "Body param 'data' should be excluded via heuristics"
    assert "notify" in route_data["queryParameters"], "Query param 'notify' should be included"
    # Heuristic path should still produce proper types
    assert route_data["queryParameters"]["notify"] == "boolean | undefined"


def test_body_param_uses_data_convention() -> None:
    """Litestar treats 'data' named params as body params.

    Note: Litestar's OpenAPI generation only automatically detects body params
    when the parameter is named 'data'. Custom names like 'payload' are treated
    as query params unless explicitly annotated. This test verifies the 'data'
    convention works correctly.
    """
    from msgspec import Struct

    from litestar_vite.codegen import generate_routes_json

    class TeamPayload(Struct):
        name: str

    @post("/teams", name="teams.add", sync_to_thread=False)
    def add_team(data: TeamPayload, active: bool = True) -> dict[str, str]:
        return {}

    app = Litestar([add_team])
    routes = generate_routes_json(app, openapi_schema=app.openapi_schema.to_schema())

    route_data = routes["routes"]["teams.add"]
    assert "queryParameters" in route_data
    assert "data" not in route_data["queryParameters"], "Body param 'data' should be excluded"
    assert "active" in route_data["queryParameters"]


def test_list_body_type() -> None:
    """list[Model] as body param handled correctly."""
    from msgspec import Struct

    from litestar_vite.codegen import generate_routes_json

    class TeamCreate(Struct):
        name: str

    @post("/teams/bulk", name="teams.bulk_add", sync_to_thread=False)
    def bulk_add_teams(data: list[TeamCreate]) -> dict[str, str]:
        return {}

    app = Litestar([bulk_add_teams])
    routes = generate_routes_json(app, openapi_schema=app.openapi_schema.to_schema())

    route_data = routes["routes"]["teams.bulk_add"]
    assert "queryParameters" not in route_data, f"list[Model] body should be excluded: {route_data}"


def test_options_routes_excluded() -> None:
    """OPTIONS-only routes should be excluded from generated routes."""
    from litestar_vite.codegen import generate_routes_json

    @get("/teams", name="teams.list", sync_to_thread=False)
    def list_teams() -> list[dict[str, str]]:
        return []

    app = Litestar([list_teams])
    routes = generate_routes_json(app, openapi_schema=app.openapi_schema.to_schema())

    # Check that no OPTIONS-only routes are in the output
    for name, route_data in routes["routes"].items():
        methods = route_data.get("methods", [])
        assert methods != ["OPTIONS"], f"OPTIONS-only route '{name}' should be excluded"


def test_head_routes_excluded() -> None:
    """HEAD-only routes should be excluded from generated routes."""
    from litestar_vite.codegen import generate_routes_json

    @get("/teams", name="teams.list", sync_to_thread=False)
    def list_teams() -> list[dict[str, str]]:
        return []

    app = Litestar([list_teams])
    routes = generate_routes_json(app, openapi_schema=app.openapi_schema.to_schema())

    # Check that no HEAD-only routes are in the output
    for name, route_data in routes["routes"].items():
        methods = route_data.get("methods", [])
        assert methods != ["HEAD"], f"HEAD-only route '{name}' should be excluded"


def test_schema_ui_routes_excluded() -> None:
    """Schema/Swagger UI routes like /schema/scalar should be excluded."""
    from litestar_vite.codegen import generate_routes_json

    @get("/teams", name="teams.list", sync_to_thread=False)
    def list_teams() -> list[dict[str, str]]:
        return []

    app = Litestar([list_teams])
    routes = generate_routes_json(app, openapi_schema=app.openapi_schema.to_schema())

    # Check that schema UI routes are excluded (but openapi.json/yaml may exist)
    for name, route_data in routes["routes"].items():
        uri = route_data.get("uri", "")
        if uri.startswith("/schema"):
            # Only openapi.json and openapi.yaml routes should remain
            assert "openapi.json" in uri or "openapi.yaml" in uri or "openapi.yml" in uri, (
                f"Schema UI route '{name}' with uri '{uri}' should be excluded"
            )


def test_openapi_routes_use_simple_names() -> None:
    """OpenAPI routes should use simple names like 'openapi.json' not hashed names."""
    from litestar_vite.codegen import generate_routes_json

    @get("/teams", name="teams.list", sync_to_thread=False)
    def list_teams() -> list[dict[str, str]]:
        return []

    app = Litestar([list_teams])
    routes = generate_routes_json(app, openapi_schema=app.openapi_schema.to_schema())

    # Check for simple openapi.json name (not hashed like 1d39ee870e3e4b73a83c764025bd27d9_litestar_openapi_json)
    for name in routes["routes"]:
        if "openapi" in name.lower():
            # Should be simple like "openapi.json" not a long hash
            assert len(name) < 20, f"OpenAPI route name '{name}' should be simple, not hashed"
