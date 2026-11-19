"""Unit tests for codegen module."""

import json
from pathlib import Path
from typing import Annotated, Any
from unittest.mock import patch
from uuid import UUID

import pytest
from litestar import Litestar, Router, WebSocket, get, post, websocket
from litestar.channels import ChannelsPlugin
from litestar.channels.backends.memory import MemoryChannelsBackend
from litestar.config.csrf import CSRFConfig
from litestar.handlers import websocket_listener
from litestar.params import FromPath, FromQuery, QueryParameter

from litestar_vite.codegen import export_integration_assets, generate_routes_json, generate_routes_ts
from litestar_vite.codegen._routes import (
    collect_semantic_aliases,
    escape_ts_string,
    extract_path_params,
    extract_route_metadata,
    is_type_required,
    make_unique_name,
    ts_type_for_param,
)
from litestar_vite.codegen._ts import (
    collect_ref_names,
    is_valid_ts_identifier,
    join_union,
    python_type_to_typescript,
    ts_literal,
    ts_type_from_openapi,
    wrap_for_array,
)
from litestar_vite.config import PathConfig, TypeGenConfig, ViteConfig


def test_typegen_outputs_requested_signature_has_no_dead_config_param() -> None:
    import inspect

    from litestar_vite.codegen._export import typegen_outputs_requested

    params = list(inspect.signature(typegen_outputs_requested).parameters)
    assert params == ["types_config"], params


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


def test_export_integration_assets_extracts_route_metadata_once(tmp_path: Path) -> None:
    from litestar_vite.codegen import _routes as routes_module
    from litestar_vite.codegen import export_integration_assets

    @get("/users/{user_id:int}")
    async def handler(user_id: FromPath[int]) -> dict[str, int]:
        return {"user_id": user_id}

    app = Litestar(route_handlers=[handler])
    config = ViteConfig(
        paths=PathConfig(root=tmp_path), types=TypeGenConfig(output=tmp_path / "generated", generate_routes=True)
    )
    real_extract = routes_module.extract_route_metadata

    with patch("litestar_vite.codegen._routes.extract_route_metadata", wraps=real_extract) as extract:
        export_integration_assets(app, config)

    extract.assert_called_once()


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
    assert escape_ts_string("a\nb\u2028c\u2029d") == r"a\nb\u2028c\u2029d"


def test_generate_routes_ts_basic_route() -> None:
    """Test TypeScript route generation for a basic route."""

    @get("/users", name="list_users", sync_to_thread=False)
    def list_users() -> list[str]:
        return ["user1", "user2"]

    app = Litestar([list_users])
    ts_content = generate_routes_ts(app)

    # Check that the route name is in the output
    assert '"list_users"' in ts_content
    # Check the path
    assert 'path: "/users"' in ts_content
    # Check method
    assert '"GET"' in ts_content
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
    def get_user(user_id: FromPath[int]) -> dict[str, int]:
        return {"id": user_id}

    app = Litestar([get_user])
    # Use OpenAPI schema to get proper type inference for path params
    ts_content = generate_routes_ts(app, openapi_schema=app.openapi_schema.to_schema())

    # Check route name
    assert '"get_user"' in ts_content
    # Check path with parameter
    assert "/users/{user_id}" in ts_content
    # Check parameter type mapping (int -> number)
    assert "user_id: number" in ts_content
    # Check pathParams array
    assert '"user_id"' in ts_content
    assert "pathParams:" in ts_content


def test_generate_routes_ts_with_uuid_param() -> None:
    """Test TypeScript route generation with UUID path parameter."""

    @get("/items/{item_id:uuid}", name="get_item", sync_to_thread=False)
    def get_item(item_id: FromPath[UUID]) -> dict[str, str]:
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
    def search(q: FromQuery[str], limit: FromQuery[int | None] = 10) -> list[str]:
        return []

    app = Litestar([search])
    ts_content = generate_routes_ts(app, openapi_schema=app.openapi_schema.to_schema())

    # Check route name
    assert '"search"' in ts_content
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
    def get_resource(id: FromPath[int]) -> dict[str, int]:
        return {"id": id}

    @post("/resources/{id:int}", name="update_resource", sync_to_thread=False)
    def update_resource(id: FromPath[int], data: dict[str, str]) -> dict[str, int]:
        return {"id": id}

    app = Litestar([get_resource, update_resource])
    ts_content = generate_routes_ts(app)

    # Check both routes exist
    assert '"get_resource"' in ts_content
    assert '"update_resource"' in ts_content
    # Check both methods appear
    assert '"GET"' in ts_content
    assert '"POST"' in ts_content


def test_generate_routes_ts_with_component() -> None:
    """Test TypeScript generation includes component metadata."""

    @get("/dashboard", name="dashboard", opt={"component": "Dashboard/Index"}, sync_to_thread=False)
    def dashboard() -> dict[str, str]:
        return {}

    app = Litestar([dashboard])
    ts_content = generate_routes_ts(app)

    # Check component is included
    assert 'component: "Dashboard/Index"' in ts_content


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


def test_generate_routes_ts_default_csrf_constants() -> None:
    """Test that generated TypeScript includes default CSRF cookie and header names."""

    @get("/test", name="test", sync_to_thread=False)
    def test_route() -> str:
        return "test"

    app = Litestar([test_route])
    ts_content = generate_routes_ts(app)

    assert 'export const CSRF_COOKIE_NAME = "csrftoken";' in ts_content
    assert 'export const CSRF_HEADER_NAME = "x-csrftoken";' in ts_content


def test_generate_routes_ts_custom_csrf_constants() -> None:
    """Test that generated TypeScript includes configured CSRF cookie and header names."""
    from litestar.config.csrf import CSRFConfig

    @get("/test", name="test", sync_to_thread=False)
    def test_route() -> str:
        return "test"

    csrf_config = CSRFConfig(
        secret="test-secret-key-12345", cookie_name="my_custom_csrf_cookie", header_name="X-My-CSRF-Header"
    )
    app = Litestar([test_route], csrf_config=csrf_config)
    ts_content = generate_routes_ts(app)

    assert 'export const CSRF_COOKIE_NAME = "my_custom_csrf_cookie";' in ts_content
    assert 'export const CSRF_HEADER_NAME = "X-My-CSRF-Header";' in ts_content


def test_generate_routes_ts_type_overloads() -> None:
    """Test that route function has proper TypeScript overloads."""

    @get("/simple", name="simple", sync_to_thread=False)
    def simple_route() -> str:
        return "simple"

    @get("/with-param/{id:int}", name="with_param", sync_to_thread=False)
    def param_route(id: FromPath[int]) -> dict[str, int]:
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
    assert '"list_users"' in ts_content
    assert '"list_posts"' not in ts_content
    assert '"admin_settings"' not in ts_content

    # Test with 'exclude' filter
    ts_content = generate_routes_ts(app, exclude=["admin"])
    assert '"list_users"' in ts_content
    assert '"list_posts"' in ts_content
    assert '"admin_settings"' not in ts_content


def test_generate_routes_ts_escapes_special_chars() -> None:
    """Test that special characters in paths are safely serialized."""

    @get("/api/v1/user's-data", name="user_data", sync_to_thread=False)
    def user_data() -> dict[str, str]:
        return {}

    app = Litestar([user_data])
    ts_content = generate_routes_ts(app)

    assert 'path: "/api/v1/user\'s-data"' in ts_content


def test_generate_routes_ts_is_valid_typescript() -> None:
    """Test that generated content is syntactically valid TypeScript."""

    @get("/users", name="list_users", sync_to_thread=False)
    def list_users() -> list[str]:
        return []

    @get("/users/{user_id:int}", name="get_user", sync_to_thread=False)
    def get_user(user_id: FromPath[int]) -> dict[str, int]:
        return {"id": user_id}

    @get("/search", name="search", sync_to_thread=False)
    def search(q: FromQuery[str]) -> list[str]:
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
    assert ts_type_from_openapi({"const": False}) == "false"
    assert ts_type_from_openapi({"const": None}) == "null"


def testts_literal_helper() -> None:
    """Test literal helper covers common primitives and fallbacks."""
    assert ts_literal(None) == "null"
    assert ts_literal(True) == "true"
    assert ts_literal(False) == "false"
    assert ts_literal(1) == "1"
    assert ts_literal(1.5) == "1.5"
    assert ts_literal("x") == '"x"'
    assert ts_literal("x\\y") == '"x\\\\y"'
    assert ts_literal("x\ny") == '"x\\ny"'
    assert ts_literal("a\u2028b\u2029c") == r'"a\u2028b\u2029c"'
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
    def search_null(q: FromQuery[str | None] = None) -> list[str]:
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


def test_python_type_to_typescript_preserves_none_substrings() -> None:
    """Ensure identifiers containing 'None' are not mangled into 'null'."""
    assert python_type_to_typescript("NoneOption") == ("NoneOption", False)
    assert python_type_to_typescript("NoneableConfig") == ("NoneableConfig", False)
    assert python_type_to_typescript("Noneable[str]") == ("Noneable[str]", False)


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


def test_collect_semantic_aliases_matches_whole_identifiers() -> None:
    """Semantic alias collection should not match substrings of larger identifiers."""
    assert collect_semantic_aliases("UUID | DateTime | NotUUID | DateTimeRange") == {"UUID", "DateTime"}


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
    def user_detail(id: FromPath[int]) -> dict[str, int]:
        return {"id": id}

    app = Litestar([user_detail], openapi_config=None)
    routes = extract_route_metadata(app)
    route = next(r for r in routes if r.name == "user_detail")
    assert route.params == {"id": "string"}


def test_generate_routes_ts_no_semantic_alias_block_when_unused() -> None:
    """Test generated routes.ts does not include alias preamble when no formats are used."""

    @get("/users/{id:int}", name="user_by_id", sync_to_thread=False)
    def user_by_id(id: FromPath[int]) -> dict[str, int]:
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
    def add_team(data: TeamCreate, notify: FromQuery[bool] = False) -> dict[str, str]:
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
    def update_team(team_id: FromPath[int], data: TeamUpdate) -> dict[str, str]:
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
    def patch_team(team_id: FromPath[int], data: TeamPatch) -> dict[str, str]:
        return {}

    app = Litestar([patch_team])
    routes = generate_routes_json(app, openapi_schema=app.openapi_schema.to_schema())

    route_data = routes["routes"]["teams.patch"]
    assert "queryParameters" not in route_data, f"Body param should be excluded: {route_data}"


def test_get_no_body_params_possible() -> None:
    """GET request - all non-path params are query params."""
    from litestar_vite.codegen import generate_routes_json

    @get("/teams", name="teams.list", sync_to_thread=False)
    def list_teams(limit: FromQuery[int] = 10, offset: FromQuery[int] = 0) -> list[dict[str, str]]:
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
    """Endpoint with include_in_schema=False is omitted from extracted route metadata."""
    from msgspec import Struct

    from litestar_vite.codegen import generate_routes_json

    class TeamCreate(Struct):
        name: str

    @post("/internal/teams", name="internal.teams.add", include_in_schema=False, sync_to_thread=False)
    def add_internal_team(data: TeamCreate, notify: FromQuery[bool] = False) -> dict[str, str]:
        return {}

    @get("/teams", name="teams.list", sync_to_thread=False)
    def list_teams() -> list[dict[str, str]]:
        return []

    app = Litestar([add_internal_team, list_teams])
    routes = generate_routes_json(app, openapi_schema=app.openapi_schema.to_schema())

    assert "internal.teams.add" not in routes["routes"]
    assert "teams.list" in routes["routes"]


def test_endpoint_body_detection_without_openapi_path_entry() -> None:
    """Body parameter 'data' is excluded from queryParameters when OpenAPI path lookup is empty."""
    from msgspec import Struct

    from litestar_vite.codegen import generate_routes_json

    class TeamCreate(Struct):
        name: str

    @post("/teams", name="teams.add", sync_to_thread=False)
    def add_team(data: TeamCreate, notify: FromQuery[bool] = False) -> dict[str, str]:
        return {}

    app = Litestar([add_team])
    routes = generate_routes_json(app, openapi_schema={})

    route_data = routes["routes"]["teams.add"]
    assert "queryParameters" in route_data
    assert "data" not in route_data["queryParameters"]
    assert "notify" in route_data["queryParameters"]
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
    def add_team(data: TeamPayload, active: FromQuery[bool] = True) -> dict[str, str]:
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


# ===== C8: Module-prefixed enum ref resolution =====


def testts_type_from_openapi_ref_enum_resolves_to_literal_union() -> None:
    """Test enum refs resolve to literal unions when component schemas are provided."""
    schema = {"$ref": "#/components/schemas/__main___Granularity"}
    components_schemas: dict[str, Any] = {"Granularity": {"type": "string", "enum": ["hour", "day", "month"]}}
    assert ts_type_from_openapi(schema, components_schemas=components_schemas) == '"hour" | "day" | "month"'


def testts_type_from_openapi_any_of_ref_enum_resolves_to_literal_union() -> None:
    """Test anyOf containing enum refs resolves correctly with nullability."""
    schema = {
        "anyOf": [{"$ref": "#/components/schemas/app_domain_insight_schemas__base_Granularity"}, {"type": "null"}]
    }
    components_schemas: dict[str, Any] = {"Granularity": {"type": "string", "enum": ["hour", "day", "month"]}}
    assert ts_type_from_openapi(schema, components_schemas=components_schemas) == '"hour" | "day" | "month" | null'


def test_generate_routes_ts_str_enum_query_params_emit_literal_unions() -> None:
    """StrEnum query params should emit literal unions, not mangled type names."""
    from enum import Enum

    from litestar_vite.codegen import generate_routes_json

    class Granularity(str, Enum):
        HOUR = "hour"
        DAY = "day"
        MONTH = "month"

    @get("/trends", name="trends.list", sync_to_thread=False)
    def trends(granularity: FromQuery[Granularity] = Granularity.DAY) -> list[str]:
        return []

    app = Litestar([trends])
    schema = app.openapi_schema.to_schema()

    routes_json = generate_routes_json(app, openapi_schema=schema)
    query_type = routes_json["routes"]["trends.list"]["queryParameters"]["granularity"]
    assert query_type == '"hour" | "day" | "month" | undefined'

    ts_content = generate_routes_ts(app, openapi_schema=schema)
    assert 'granularity?: "hour" | "day" | "month";' in ts_content
    assert "__main___Granularity" not in ts_content


def test_generate_routes_ts_path_param_non_enum_ref_degrades_to_string() -> None:
    """Non-enum schema refs are not valid URL parameter value types."""

    @get("/widgets/{widget_id:str}", name="widget.detail", sync_to_thread=False)
    def widget_detail(widget_id: FromPath[str]) -> str:
        return widget_id

    app = Litestar([widget_detail])
    schema: dict[str, Any] = {
        "components": {"schemas": {"WidgetIdentifier": {"type": "object", "properties": {"id": {"type": "string"}}}}},
        "paths": {
            "/widgets/{widget_id}": {
                "get": {
                    "parameters": [
                        {
                            "name": "widget_id",
                            "in": "path",
                            "required": True,
                            "schema": {"$ref": "#/components/schemas/WidgetIdentifier"},
                        }
                    ]
                }
            }
        },
    }

    content = generate_routes_ts(app, openapi_schema=schema)

    assert "widget_id: string;" in content
    assert "widget_id: WidgetIdentifier;" not in content


def test_websocket_route_metadata_and_codegen() -> None:
    """WebSocket and websocket_listener handlers are extracted with protocol='websocket' and channel_key."""

    @get("/api/ping", name="ping", sync_to_thread=False)
    def ping() -> dict[str, str]:
        return {"ok": "1"}

    @websocket("/ws/notifications", name="notifications_ws")
    async def notifications_ws(socket: WebSocket) -> None:
        await socket.accept()

    @websocket_listener("/ws/chat/{room_id:str}")
    def chat_room(data: str, room_id: FromPath[str]) -> str:
        return f"{room_id}:{data}"

    channels_plugin = ChannelsPlugin(
        backend=MemoryChannelsBackend(),
        channels=["alerts"],
        create_ws_route_handlers=True,
        ws_handler_base_path="/channels",
    )

    app = Litestar([ping, notifications_ws, chat_room], plugins=[channels_plugin])
    metadata = extract_route_metadata(app)
    by_name = {r.name: r for r in metadata}

    assert "ping" in by_name
    assert by_name["ping"].protocol == "http"
    assert by_name["ping"].channel_key is None

    assert "notifications_ws" in by_name
    assert by_name["notifications_ws"].protocol == "websocket"
    assert by_name["notifications_ws"].methods == ["WS"]
    assert by_name["notifications_ws"].channel_key == "ws__notifications"

    assert "chat_room" in by_name
    assert by_name["chat_room"].protocol == "websocket"
    assert by_name["chat_room"].params == {"room_id": "string"}
    assert by_name["chat_room"].channel_key == "ws__chat__p_room_id"

    for route_meta in metadata:
        assert not route_meta.path.startswith("/channels"), (
            f"Internal ChannelsPlugin handler leaked into routes: {route_meta}"
        )

    routes_json = generate_routes_json(
        app,
        openapi_schema=app.openapi_schema.to_schema(),
        asyncapi_schema={"servers": {"dev": {"host": "localhost:8000", "protocol": "ws"}}},
    )
    assert routes_json["servers"] == {"dev": {"host": "localhost:8000", "protocol": "ws"}}
    assert routes_json["routes"]["notifications_ws"]["protocol"] == "websocket"
    assert routes_json["routes"]["notifications_ws"]["channel_key"] == "ws__notifications"
    assert routes_json["routes"]["chat_room"]["protocol"] == "websocket"
    assert routes_json["routes"]["chat_room"]["channel_key"] == "ws__chat__p_room_id"
    assert "protocol" not in routes_json["routes"]["ping"]

    ts_content = generate_routes_ts(
        app,
        openapi_schema=app.openapi_schema.to_schema(),
        asyncapi_schema={"servers": {"dev": {"host": "localhost:8000", "protocol": "ws"}}},
    )
    assert "export const WS_SERVER_URL =" in ts_content
    assert '|| "ws://localhost:8000";' in ts_content
    assert "export type WebSocketRouteName =" in ts_content
    assert '"notifications_ws"' in ts_content
    assert '"chat_room"' in ts_content
    assert "export function wsRoute<" in ts_content
    assert "route.ws = wsRoute;" in ts_content
    assert 'protocol: "websocket" as const,' in ts_content
    assert 'channelKey: "ws__chat__p_room_id",' in ts_content


@pytest.mark.parametrize(
    ("route_path", "route_name", "expected_wildcards"),
    [
        ("/files/{file_path:path}", "files", ("file_path",)),
        ("/items/{item_id:str}", "item", ()),
        ("/archive/{bucket:str}/{rest_path:path}", "archive", ("rest_path",)),
        ("/users/{user_id:int}", "user_int", ()),
        ("/static", "static_page", ()),
    ],
)
def test_extract_route_metadata_wildcard_params(
    route_path: str, route_name: str, expected_wildcards: tuple[str, ...]
) -> None:
    """Verify `:path` parameters are captured in RouteMetadata.wildcard_params."""

    @get(route_path, name=route_name, sync_to_thread=False)
    def handler() -> dict[str, str]:
        return {"ok": "1"}

    app = Litestar([handler])
    metadata = extract_route_metadata(app)
    by_name = {route.name: route for route in metadata}

    assert by_name[route_name].wildcard_params == expected_wildcards


def test_generate_routes_ts_wildcard_metadata_and_encoding() -> None:
    """Verify generated routes.ts emits wildcardParams metadata and path encoding logic."""

    @get("/files/{file_path:path}", name="files", sync_to_thread=False)
    def serve_file(file_path: FromPath[str]) -> dict[str, str]:
        return {"path": file_path}

    @get("/items/{item_id:str}", name="item", sync_to_thread=False)
    def get_item(item_id: FromPath[str]) -> dict[str, str]:
        return {"id": item_id}

    app = Litestar([serve_file, get_item])
    ts_content = generate_routes_ts(app, openapi_schema=app.openapi_schema.to_schema())

    assert 'wildcardParams: ["file_path"] as const,' in ts_content
    assert ts_content.count("wildcardParams:") == 1
    assert "function encodePathParam(value: unknown, isWildcard: boolean): string" in ts_content
    assert "encodeURIComponent(" in ts_content
    assert 'const segments = isWildcard ? str.split("/") : [str];' in ts_content
    assert 'const invalidSegment = segments.find((segment) => segment === "." || segment === "..");' in ts_content
    assert 'throw new Error(`Invalid path segment "${invalidSegment}" in route parameter`);' in ts_content
    assert '"wildcardParams" in def && (def.wildcardParams as readonly string[]).includes(param)' in ts_content
    assert 'if (url.startsWith("//"))' in ts_content
    assert 'url = "/" + url.replace(/^\\/+/, "");' in ts_content
    assert ts_content.count("(") == ts_content.count(")")
    assert ts_content.count("[") == ts_content.count("]")


@pytest.mark.parametrize("exclusion_mode", ["handler", "router", "opt"])
def test_http_routes_include_in_schema_false_excluded(exclusion_mode: str) -> None:
    """HTTP routes excluded from schema via handler, router, or opt are omitted from route exports."""

    @get("/public", name="public", sync_to_thread=False)
    def public_handler() -> dict[str, str]:
        return {}

    if exclusion_mode == "handler":

        @get("/internal", name="hidden", include_in_schema=False, sync_to_thread=False)
        def hidden_handler() -> dict[str, str]:
            return {}

        app = Litestar([public_handler, hidden_handler])
    elif exclusion_mode == "router":

        @get("/status", name="hidden", sync_to_thread=False)
        def router_hidden_handler() -> dict[str, str]:
            return {}

        ops_router = Router(path="/ops", route_handlers=[router_hidden_handler], include_in_schema=False)
        app = Litestar([public_handler, ops_router])
    else:

        @get("/hidden", name="hidden", opt={"include_in_schema": False}, sync_to_thread=False)
        def opt_hidden_handler() -> dict[str, str]:
            return {}

        app = Litestar([public_handler, opt_hidden_handler])

    metadata = extract_route_metadata(app)
    routes_json = generate_routes_json(app)
    routes_ts = generate_routes_ts(app)

    assert [route.name for route in metadata] == ["public"]
    assert list(routes_json["routes"]) == ["public"]
    assert '"public"' in routes_ts
    assert '"hidden"' not in routes_ts


@pytest.mark.parametrize(
    ("only_routes", "exclude_routes", "expected_names"),
    [
        (("api",), ("internal",), ["api_public"]),
        ((), ("internal",), ["api_public", "web_home"]),
        (("api",), (), ["api_internal", "api_public"]),
        ((), (), ["api_internal", "api_public", "web_home"]),
    ],
)
def test_export_integration_assets_applies_typegen_route_filters(
    tmp_path: Path, only_routes: tuple[str, ...], exclude_routes: tuple[str, ...], expected_names: list[str]
) -> None:
    """export_integration_assets forwards TypeGenConfig only_routes and exclude_routes to routes.json and routes.ts."""

    @get("/api/public", name="api_public", sync_to_thread=False)
    def api_public() -> dict[str, str]:
        return {}

    @get("/api/internal", name="api_internal", sync_to_thread=False)
    def api_internal() -> dict[str, str]:
        return {}

    @get("/web/home", name="web_home", sync_to_thread=False)
    def web_home() -> dict[str, str]:
        return {}

    app = Litestar([api_public, api_internal, web_home])
    out_dir = tmp_path / "generated"
    config = ViteConfig(
        paths=PathConfig(root=tmp_path),
        types=TypeGenConfig(
            output=out_dir,
            generate_sdk=False,
            generate_zod=False,
            generate_schemas=False,
            generate_page_props=False,
            generate_channels=False,
            generate_routes=True,
            only_routes=only_routes,
            exclude_routes=exclude_routes,
        ),
    )

    export_integration_assets(app, config)

    routes_payload = json.loads((out_dir / "routes.json").read_text(encoding="utf-8"))
    routes_ts = (out_dir / "routes.ts").read_text(encoding="utf-8")

    assert sorted(routes_payload["routes"].keys()) == sorted(expected_names)
    for name in ["api_internal", "api_public", "web_home"]:
        if name in expected_names:
            assert f'"{name}"' in routes_ts
        else:
            assert f'"{name}"' not in routes_ts


@pytest.mark.parametrize(
    ("identifier", "expected"),
    [
        ("validName", True),
        ("_private_1", True),
        ("$special", True),
        ("validName\n", False),
        ("validName\r\n", False),
        ("\nvalidName", False),
        ("123bad", False),
        ("bad-key", False),
        ("", False),
    ],
)
def test_is_valid_ts_identifier_rejects_trailing_newlines_and_invalid_names(identifier: str, expected: bool) -> None:
    """Verify is_valid_ts_identifier anchors start and end strictly without accepting trailing newlines."""
    assert is_valid_ts_identifier(identifier) is expected


@pytest.mark.parametrize(
    ("prop_name", "expected_line"),
    [
        ("x-api-key", '"x-api-key"?: string;'),
        ("content-type", '"content-type"?: string;'),
        ("123bad", '"123bad"?: string;'),
        ("bad_key\n", '"bad_key\\n"?: string;'),
        ("valid_key", "valid_key?: string;"),
    ],
)
def testts_type_from_openapi_quotes_non_identifier_property_keys(prop_name: str, expected_line: str) -> None:
    """OpenAPI object property keys that are not valid TS identifiers are JSON-quoted."""
    schema: dict[str, Any] = {"type": "object", "properties": {prop_name: {"type": "string"}}}
    result = ts_type_from_openapi(schema)
    assert expected_line in result


@pytest.mark.parametrize(
    "ref_value",
    [
        "#/components/schemas/123Bad",
        "#/components/schemas/Bad;Type",
        "#/components/schemas/ValidName\n",
        "#/definitions/Bad;Type",
        "external.json#/123Bad",
    ],
)
def testts_type_from_openapi_rejects_invalid_ref_identifiers(ref_value: str) -> None:
    """Invalid TypeScript identifiers extracted from $ref targets raise ValueError."""
    with pytest.raises(ValueError, match="Invalid TypeScript identifier"):
        ts_type_from_openapi({"$ref": ref_value})


@pytest.mark.parametrize("special_fragment", ["\n", "\r", "\u2028", "\u2029", "'", '"', "\\", "*/"])
def test_generate_routes_ts_escapes_control_chars_and_line_separators(special_fragment: str) -> None:
    """Route names, paths, components, and CSRF config values serialize safely without raw line terminators."""

    @get(
        "/items",
        name=f"route{special_fragment}name",
        opt={"component": f"Comp{special_fragment}Name"},
        sync_to_thread=False,
    )
    def item_handler() -> dict[str, str]:
        return {}

    csrf_config = CSRFConfig(
        secret="test-secret-key-12345",
        cookie_name=f"cookie{special_fragment}name",
        header_name=f"header{special_fragment}name",
    )
    app = Litestar([item_handler], csrf_config=csrf_config)
    ts_content = generate_routes_ts(app)

    assert "\u2028" not in ts_content
    assert "\u2029" not in ts_content
    assert "\r" not in ts_content
    assert f"component: {json.dumps(f'Comp{special_fragment}Name')}" in ts_content
    assert f"export const CSRF_COOKIE_NAME = {json.dumps(f'cookie{special_fragment}name')};" in ts_content
    assert f"export const CSRF_HEADER_NAME = {json.dumps(f'header{special_fragment}name')};" in ts_content


def test_generate_routes_ts_quotes_non_identifier_query_params() -> None:
    """Query parameter names that are not valid TS identifiers emit as quoted property keys."""

    @get("/filter", name="filter_items", sync_to_thread=False)
    def filter_items(filter_by: Annotated[str | None, QueryParameter(name="filter-by")] = None) -> list[str]:
        return []

    app = Litestar([filter_items])
    ts_content = generate_routes_ts(app, openapi_schema=app.openapi_schema.to_schema())

    assert '"filter-by"?: string;' in ts_content
