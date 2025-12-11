"""Code generation utilities for route metadata export.

This module extracts route metadata from a Litestar application and emits a
`routes.json` file consumed by the Vite plugin. Detailed type generation is
delegated to @hey-api/openapi-ts; we keep only lightweight metadata here.
"""

import inspect
import re
from collections.abc import Generator
from dataclasses import dataclass, field
from pathlib import PurePosixPath
from typing import TYPE_CHECKING, Any

from litestar import Litestar
from litestar._openapi.typescript_converter.schema_parsing import parse_schema
from litestar.handlers import HTTPRouteHandler
from litestar.openapi.spec import Schema
from litestar.openapi.spec.enums import OpenAPIType

if TYPE_CHECKING:
    from litestar.routes import HTTPRoute


__all__ = (
    "InertiaPageMetadata",
    "RouteMetadata",
    "extract_inertia_pages",
    "extract_route_metadata",
    "generate_inertia_pages_json",
    "generate_routes_json",
    "generate_routes_ts",
)

# Compiled regex patterns for path parsing (compiled once at module load)
_PATH_PARAM_TYPE_PATTERN = re.compile(r"\{([^:}]+):[^}]+\}")
_PATH_PARAM_EXTRACT_PATTERN = re.compile(r"\{([^:}]+)(?::([^}]+))?\}")

# System types that should be excluded from query parameters
# These are injected by Litestar, not from the request query string
_SYSTEM_TYPE_NAMES = frozenset(
    {
        "Request",
        "WebSocket",
        "State",
        "ASGIConnection",
        "HTTPConnection",
        "Scope",
        "Receive",
        "Send",
    }
)

# Valid OpenAPI type values for validation
_OPENAPI_TYPE_VALUES = frozenset(e.value for e in OpenAPIType)


def _str_dict_factory() -> dict[str, str]:
    """Factory function for empty string dict (typed for pyright).

    Returns:
        An empty dictionary with str keys and str values.
    """
    return {}


@dataclass
class RouteMetadata:
    """Metadata for a single route.

    Attributes:
        name: Route name (handler name or explicit route name).
        path: Route path with normalized parameter placeholders ({param} syntax).
        methods: HTTP methods for this route.
        params: Path parameters with their types.
        query_params: Query parameters with their types.
        component: Inertia component name (if applicable).
    """

    name: str
    path: str
    methods: list[str]
    params: dict[str, str] = field(default_factory=_str_dict_factory)
    query_params: dict[str, str] = field(default_factory=_str_dict_factory)
    component: "str | None" = None


def _is_system_type(annotation: Any) -> bool:
    """Check if a type annotation is a Litestar system type.

    System types are injected by Litestar (Request, State, etc.) and should
    not be treated as query parameters.

    Args:
        annotation: Type annotation to check.

    Returns:
        True if it's a system type, False otherwise.
    """
    if annotation is None:
        return False

    # Check by class name (handles imports from different locations)
    if inspect.isclass(annotation) and annotation.__name__ in _SYSTEM_TYPE_NAMES:
        return True

    # Check string representation for generic types
    type_str = str(annotation)
    return any(system_type in type_str for system_type in _SYSTEM_TYPE_NAMES)


def _normalize_path(path: str) -> str:
    """Normalize route path to use {param} syntax.

    Handles Litestar path parameters with type annotations:
    - /users/{user_id:int} -> /users/{user_id}
    - /items/{uuid:uuid} -> /items/{uuid}
    - /posts/{slug:str} -> /posts/{slug}

    Args:
        path: Route path with Litestar parameter syntax.

    Returns:
        Path with normalized {param} syntax.
    """
    # Handle empty or root paths
    if not path or path == "/":
        return path

    # Use PurePosixPath for cross-platform compatibility
    path_obj = PurePosixPath(path)

    return _PATH_PARAM_TYPE_PATTERN.sub(r"{\1}", str(path_obj))


def _extract_path_params(path: str) -> dict[str, str]:
    """Extract path parameters and their types from a route.

    Args:
        path: Route path.

    Returns:
        Dictionary mapping parameter names to TypeScript types.
    """
    params: dict[str, str] = {}

    # Extract parameter names from path using compiled pattern
    for match in _PATH_PARAM_EXTRACT_PATTERN.finditer(path):
        param_name = match.group(1)
        # Keep type hinting minimal; detailed typing is handled by OpenAPI exports.
        params[param_name] = "string"

    return params


def _iter_route_handlers(app: Litestar) -> Generator[tuple["HTTPRoute", HTTPRouteHandler], None, None]:
    """Iterate over HTTP route handlers in an app.

    Yields tuples of (http_route, route_handler) for each HTTP route handler,
    filtering out non-HTTP routes (WebSocket, static, etc.).

    Args:
        app: The Litestar application.

    Yields:
        Tuples of (HTTPRoute, HTTPRouteHandler) for each route handler.
    """
    for route in app.routes:
        if not hasattr(route, "route_handler_map"):
            continue
        http_route: "HTTPRoute" = route  # type: ignore[assignment]
        for route_handler in http_route.route_handlers:
            yield http_route, route_handler


def _should_skip_param(
    param_name: str,
    path_param_names: set[str],
    body_param_name: Any,
    dependency_names: set[str],
) -> bool:
    """Check if a parameter should be skipped when extracting query params.

    Args:
        param_name: The name of the parameter.
        path_param_names: Set of path parameter names.
        body_param_name: The name of the body parameter (if any).
        dependency_names: Set of dependency parameter names.

    Returns:
        True if the parameter should be skipped.
    """
    if param_name in {"self", "cls", "return"}:
        return True
    if param_name in path_param_names:
        return True
    if param_name == body_param_name:
        return True
    return param_name in dependency_names


def _process_field_definition(field_def: Any, param_name: str) -> "tuple[str, str] | None":
    """Process a field definition and return the query param name and type.

    Args:
        field_def: The FieldDefinition object.
        param_name: The parameter name.

    Returns:
        Tuple of (final_name, ts_type) or None if field should be skipped.
    """
    from litestar.params import ParameterKwarg

    # Get the annotation from FieldDefinition
    annotation = getattr(field_def, "annotation", None)
    if annotation is None or _is_system_type(annotation):
        return None

    # Keep type inference minimal; OpenAPI handles detailed typing
    ts_type = "unknown"

    # Check if optional (has default value)
    default = getattr(field_def, "default", None)
    is_empty = (
        default is None
        or (hasattr(default, "name") and default.name == "EMPTY")
        or str(default) == "<_EmptyEnum.EMPTY: 0>"
    )
    is_optional = not is_empty

    # Handle ParameterKwarg metadata for aliasing
    final_name = param_name
    kwarg_def = getattr(field_def, "kwarg_definition", None)
    if isinstance(kwarg_def, ParameterKwarg):
        query_alias = getattr(kwarg_def, "query", None)
        if query_alias:
            final_name = query_alias

    if is_optional and "undefined" not in ts_type:
        ts_type = f"{ts_type} | undefined"

    return final_name, ts_type


def _extract_query_params(handler: HTTPRouteHandler, path_param_names: set[str]) -> dict[str, str]:
    """Extract query parameters and their types from a route handler.

    Uses the subtraction approach: all handler parameters that are NOT path params,
    body params, dependencies, or system types are considered query parameters.

    Args:
        handler: The Litestar route handler.
        path_param_names: Set of path parameter names (already extracted from path).

    Returns:
        Dictionary mapping query parameter names to TypeScript types.
    """
    query_params: dict[str, str] = {}

    # Get parsed signature - contains all handler parameters
    parsed_sig = getattr(handler, "parsed_fn_signature", None)
    if parsed_sig is None:
        return query_params

    # Get the body parameter name (if any)
    body_param_name = getattr(parsed_sig, "data", None)
    body_name_attr = getattr(body_param_name, "name", None) if body_param_name is not None else None
    if body_name_attr is not None:
        body_param_name = body_name_attr

    # Get dependency names to exclude
    dependency_names: set[str] = set()
    try:
        resolved_deps = handler.resolve_dependencies()
        dependency_names = set(resolved_deps.keys())
    except (AttributeError, KeyError, TypeError, ValueError):
        # Dependencies may not be resolvable in all contexts
        pass

    parameters = getattr(parsed_sig, "parameters", {})
    for param_name, field_def in parameters.items():
        if _should_skip_param(param_name, path_param_names, body_param_name, dependency_names):
            continue

        result = _process_field_definition(field_def, param_name)
        if result is not None:
            final_name, ts_type = result
            query_params[final_name] = ts_type

    return query_params


def _dict_to_schema(d: dict[str, Any]) -> Schema:
    """Convert an OpenAPI schema dict to a Litestar Schema object.

    Args:
        d: OpenAPI schema dictionary.

    Returns:
        Litestar Schema object.
    """
    if not d:
        return Schema()

    # Convert type string(s) to OpenAPIType enum(s)
    t = d.get("type")
    schema_type: "OpenAPIType | list[OpenAPIType] | None" = None
    if isinstance(t, str) and t in _OPENAPI_TYPE_VALUES:
        schema_type = OpenAPIType(t)
    elif isinstance(t, list):
        schema_type = [OpenAPIType(x) for x in t if isinstance(x, str) and x in _OPENAPI_TYPE_VALUES] or None  # pyright: ignore[reportUnknownVariableType, reportUnknownArgumentType]

    # Handle nested schemas recursively
    # pyright: ignore[reportUnknownArgumentType] - dict contents validated with isinstance
    one_of = [_dict_to_schema(s) for s in d.get("oneOf", []) if isinstance(s, dict)] or None  # pyright: ignore[reportUnknownArgumentType]
    any_of = [_dict_to_schema(s) for s in d.get("anyOf", []) if isinstance(s, dict)] or None  # pyright: ignore[reportUnknownArgumentType]
    all_of = [_dict_to_schema(s) for s in d.get("allOf", []) if isinstance(s, dict)] or None  # pyright: ignore[reportUnknownArgumentType]
    items_dict = d.get("items")
    items = _dict_to_schema(items_dict) if isinstance(items_dict, dict) else None  # pyright: ignore[reportUnknownArgumentType]

    return Schema(
        type=schema_type,
        one_of=one_of,
        any_of=any_of,
        all_of=all_of,
        items=items,
        enum=d.get("enum"),
        const=d.get("const"),
        format=d.get("format"),
    )


def _ts_type_from_openapi(schema: dict[str, Any]) -> str:
    """Map OpenAPI schema dict to TypeScript type string.

    Uses Litestar's typescript_converter for consistent type generation.
    See: litestar/_openapi/typescript_converter/schema_parsing.py

    Args:
        schema: OpenAPI schema dictionary.

    Returns:
        TypeScript type string.
    """
    try:
        litestar_schema = _dict_to_schema(schema)
        ts_element = parse_schema(litestar_schema)
        return ts_element.write()
    except (TypeError, ValueError, KeyError):
        # Fallback for schemas that can't be converted
        return "any"


def _openapi_lookup(openapi_schema: dict[str, Any] | None) -> dict[tuple[str, str], dict[str, Any]]:
    """Build a lookup of (path, method) -> operation object from OpenAPI schema."""

    if not openapi_schema:
        return {}

    paths = openapi_schema.get("paths", {})
    lookup: dict[tuple[str, str], dict[str, Any]] = {}
    for path, methods in paths.items():
        if not isinstance(methods, dict):
            continue
        for method_obj, operation_obj in methods.items():  # pyright: ignore
            if not isinstance(method_obj, str):
                continue
            method = method_obj
            operation: dict[str, Any] = operation_obj or {}  # pyright: ignore

            lower = method.lower()
            if lower not in {"get", "post", "put", "patch", "delete", "head", "options"}:
                continue

            lookup[path, method.upper()] = operation
    return lookup


def _apply_openapi_params(
    operation: dict[str, Any] | None,
    params: dict[str, str],
    query_params: dict[str, str],
) -> None:
    if not operation:
        return

    for param in operation.get("parameters", []):
        name = param.get("name")
        schema = param.get("schema", {})
        ts_type = _ts_type_from_openapi(schema)

        if param.get("in") == "path" and name:
            params[name] = ts_type or "string"
        elif param.get("in") == "query" and name:
            if not param.get("required", False) and ts_type != "unknown":
                ts_type = f"{ts_type} | undefined"
            query_params[name] = ts_type or "unknown"


def _make_unique_name(base_name: str, used_names: set[str], path: str, methods: list[str]) -> str:
    """Generate a unique route name, avoiding collisions.

    Args:
        base_name: The preferred route name.
        used_names: Set of already-used route names.
        path: Route path for generating fallback name.
        methods: HTTP methods for this route.

    Returns:
        A unique route name.
    """
    if base_name not in used_names:
        return base_name

    # Generate a path-based suffix for deduplication
    # /api/books/{book_id} -> api_books_book_id
    path_suffix = path.strip("/").replace("/", "_").replace("{", "").replace("}", "").replace("-", "_")
    method_suffix = methods[0].lower() if methods else ""

    # Try path-based name
    candidate = f"{base_name}_{path_suffix}" if path_suffix else base_name
    if candidate not in used_names:
        return candidate

    # Try with method suffix
    candidate = f"{base_name}_{path_suffix}_{method_suffix}" if path_suffix else f"{base_name}_{method_suffix}"
    if candidate not in used_names:
        return candidate

    # Fall back to counter
    counter = 2
    while f"{candidate}_{counter}" in used_names:
        counter += 1
    return f"{candidate}_{counter}"


def extract_route_metadata(
    app: Litestar,
    *,
    only: "list[str] | None" = None,
    exclude: "list[str] | None" = None,
    openapi_schema: dict[str, Any] | None = None,
) -> list[RouteMetadata]:
    """Extract route metadata from a Litestar application.

    Args:
        app: Litestar application instance.
        only: Include patterns (route names or paths to include).
        exclude: Exclude patterns (route names or paths to exclude).
        openapi_schema: Optional OpenAPI schema used to enrich parameter and query types.

    Returns:
        List of route metadata objects.
    """
    routes_metadata: list[RouteMetadata] = []
    used_names: set[str] = set()
    op_lookup = _openapi_lookup(openapi_schema)

    for http_route, route_handler in _iter_route_handlers(app):
        # Get base route name
        base_name = route_handler.name or route_handler.handler_name or str(route_handler)

        # Extract methods first (needed for unique name generation)
        methods = [method.upper() for method in route_handler.http_methods]

        # Get full path
        full_path = str(http_route.path)

        # Make name unique
        route_name = _make_unique_name(base_name, used_names, full_path, methods)
        used_names.add(route_name)

        if only and not any(pattern in route_name or pattern in full_path for pattern in only):
            continue
        if exclude and any(pattern in route_name or pattern in full_path for pattern in exclude):
            continue

        # Extract path parameters (override with OpenAPI if available)
        params = _extract_path_params(full_path)
        path_param_names = set(params.keys())

        # Extract query parameters (excludes path params, body, deps, system types)
        query_params = _extract_query_params(route_handler, path_param_names)

        # Enhance with OpenAPI types when available
        operation = op_lookup.get((_normalize_path(full_path), methods[0] if methods else ""))
        _apply_openapi_params(operation, params, query_params)

        # Extract Inertia component (if present)
        component = None
        if hasattr(route_handler, "opt") and route_handler.opt:
            component = route_handler.opt.get("component")

        # Normalize path
        normalized_path = _normalize_path(full_path)

        metadata = RouteMetadata(
            name=route_name,
            path=normalized_path,
            methods=methods,
            params=params,
            query_params=query_params,
            component=component,
        )

        routes_metadata.append(metadata)

    return routes_metadata


def generate_routes_json(
    app: Litestar,
    *,
    only: "list[str] | None" = None,
    exclude: "list[str] | None" = None,
    include_components: bool = False,
    openapi_schema: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Generate Ziggy-compatible routes JSON.

    Args:
        app: Litestar application instance.
        only: Include patterns (route names or paths to include).
        exclude: Exclude patterns (route names or paths to exclude).
        include_components: Include Inertia component names in output.
        openapi_schema: Optional OpenAPI schema used to enrich parameter and query types.

    Returns:
        Dictionary with routes in Ziggy-compatible format.
    """
    routes_metadata = extract_route_metadata(app, only=only, exclude=exclude, openapi_schema=openapi_schema)

    routes_dict: dict[str, Any] = {}

    for route in routes_metadata:
        route_data: dict[str, Any] = {
            "uri": route.path,
            "methods": route.methods,
        }

        if route.params:
            route_data["parameters"] = list(route.params.keys())
            route_data["parameterTypes"] = route.params

        if route.query_params:
            route_data["queryParameters"] = route.query_params

        if include_components and route.component:
            route_data["component"] = route.component

        routes_dict[route.name] = route_data

    return {"routes": routes_dict}


# TypeScript type mapping
_TS_TYPE_MAP: dict[str, str] = {
    # OpenAPI types
    "string": "string",
    "integer": "number",
    "number": "number",
    "boolean": "boolean",
    "array": "unknown[]",
    "object": "Record<string, unknown>",
    # Common formats
    "uuid": "string",
    "date": "string",
    "date-time": "string",
    "email": "string",
    "uri": "string",
    "url": "string",
    # Python/Litestar path parameter types
    "int": "number",
    "float": "number",
    "str": "string",
    "bool": "boolean",
    "path": "string",
    # Defaults
    "unknown": "unknown",
}


def _ts_type_for_param(param_type: str) -> str:
    """Map a parameter type string to TypeScript type.

    Args:
        param_type: Type string from OpenAPI schema or Litestar path param.

    Returns:
        TypeScript type string.
    """
    # Handle optional markers
    is_optional = "undefined" in param_type or param_type.endswith("?")
    clean_type = param_type.replace(" | undefined", "").replace("?", "").strip()

    ts_type = _TS_TYPE_MAP.get(clean_type, "unknown")

    if is_optional and "undefined" not in ts_type:
        return f"{ts_type} | undefined"
    return ts_type


def _is_type_required(param_type: str) -> bool:
    """Check if a parameter type indicates a required field.

    Args:
        param_type: Type string potentially containing '| undefined'.

    Returns:
        True if the parameter is required (no undefined marker).
    """
    return "undefined" not in param_type and not param_type.endswith("?")


def _escape_ts_string(s: str) -> str:
    """Escape a string for use in TypeScript string literals.

    Args:
        s: String to escape.

    Returns:
        Escaped string safe for TypeScript.
    """
    return s.replace("\\", "\\\\").replace("'", "\\'").replace('"', '\\"')


def generate_routes_ts(
    app: Litestar,
    *,
    only: "list[str] | None" = None,
    exclude: "list[str] | None" = None,
    openapi_schema: dict[str, Any] | None = None,
) -> str:
    """Generate typed routes TypeScript file (Ziggy-style).

    This function generates a routes.ts file with:
    - Type-safe route names as a union type
    - Type-safe path and query parameters per route
    - A `route()` function with proper overloads for compile-time safety
    - Helper functions: hasRoute(), getRouteNames(), getRoute()

    The generated file works with relative paths by default. For separate dev
    servers, set VITE_API_URL environment variable.

    Args:
        app: Litestar application instance.
        only: Include patterns (route names or paths to include).
        exclude: Exclude patterns (route names or paths to exclude).
        openapi_schema: Optional OpenAPI schema for enhanced type info.

    Returns:
        TypeScript source code as a string.

    Example:
        ts_content = generate_routes_ts(app)
        Path("src/generated/routes.ts").write_text(ts_content)
    """
    routes_metadata = extract_route_metadata(app, only=only, exclude=exclude, openapi_schema=openapi_schema)

    # Build route data structures
    route_names: list[str] = []
    path_params_entries: list[str] = []
    query_params_entries: list[str] = []
    routes_entries: list[str] = []

    for route in routes_metadata:
        route_name = route.name
        route_names.append(route_name)

        # Build path params interface entry
        if route.params:
            param_fields: list[str] = []
            for param_name, param_type in route.params.items():
                ts_type = _ts_type_for_param(param_type)
                # Path params are always required
                ts_type_clean = ts_type.replace(" | undefined", "")
                param_fields.append(f"    {param_name}: {ts_type_clean};")
            path_params_entries.append(f"  '{route_name}': {{\n" + "\n".join(param_fields) + "\n  };")
        else:
            path_params_entries.append(f"  '{route_name}': Record<string, never>;")

        # Build query params interface entry
        if route.query_params:
            query_param_fields: list[str] = []
            for param_name, param_type in route.query_params.items():
                ts_type = _ts_type_for_param(param_type)
                is_required = _is_type_required(param_type)
                ts_type_clean = ts_type.replace(" | undefined", "")
                if is_required:
                    query_param_fields.append(f"    {param_name}: {ts_type_clean};")
                else:
                    query_param_fields.append(f"    {param_name}?: {ts_type_clean};")
            query_params_entries.append(f"  '{route_name}': {{\n" + "\n".join(query_param_fields) + "\n  };")
        else:
            query_params_entries.append(f"  '{route_name}': Record<string, never>;")

        # Build routes object entry
        methods_str = ", ".join(f"'{m}'" for m in route.methods)
        route_entry_lines = [
            f"  '{route_name}': {{",
            f"    path: '{_escape_ts_string(route.path)}',",
            f"    methods: [{methods_str}] as const,",
        ]
        if route.params:
            param_names_str = ", ".join(f"'{p}'" for p in route.params)
            route_entry_lines.append(f"    pathParams: [{param_names_str}] as const,")
        if route.query_params:
            query_names_str = ", ".join(f"'{p}'" for p in route.query_params)
            route_entry_lines.append(f"    queryParams: [{query_names_str}] as const,")
        if route.component:
            route_entry_lines.append(f"    component: '{_escape_ts_string(route.component)}',")
        route_entry_lines.append("  },")
        routes_entries.append("\n".join(route_entry_lines))

    # Generate TypeScript content
    route_names_union = "\n  | ".join(f"'{name}'" for name in route_names) if route_names else "never"

    return f"""/**
 * Auto-generated route definitions for litestar-vite.
 * DO NOT EDIT - regenerated on server restart and file changes.
 *
 * @generated
 */

// API base URL - only needed for separate dev servers
// Set VITE_API_URL=http://localhost:8000 when running Vite separately
const API_URL = (typeof import.meta !== 'undefined' && import.meta.env?.VITE_API_URL) ?? '';

/** All available route names */
export type RouteName =
  | {route_names_union};

/** Path parameter definitions per route */
export interface RoutePathParams {{
{chr(10).join(path_params_entries)}
}}

/** Query parameter definitions per route */
export interface RouteQueryParams {{
{chr(10).join(query_params_entries)}
}}

/** Combined parameters (path + query) */
export type RouteParams<T extends RouteName> =
  RoutePathParams[T] & RouteQueryParams[T];

/** Route metadata */
export const routes = {{
{chr(10).join(routes_entries)}
}} as const;

/** Check if path params are required for a route */
type HasRequiredPathParams<T extends RouteName> =
  RoutePathParams[T] extends Record<string, never> ? false : true;

/** Check if query params have any required fields */
type HasRequiredQueryParams<T extends RouteName> =
  RouteQueryParams[T] extends Record<string, never>
    ? false
    : Partial<RouteQueryParams[T]> extends RouteQueryParams[T]
      ? false
      : true;

/** Routes that require parameters (path or query) */
type RoutesWithRequiredParams = {{
  [K in RouteName]: HasRequiredPathParams<K> extends true
    ? K
    : HasRequiredQueryParams<K> extends true
      ? K
      : never;
}}[RouteName];

/** Routes without any required parameters */
type RoutesWithoutRequiredParams = Exclude<RouteName, RoutesWithRequiredParams>;

/**
 * Generate a URL for a named route.
 *
 * @example
 * route('books')                              // '/api/books'
 * route('book_detail', {{ book_id: 123 }})      // '/api/books/123'
 * route('search', {{ q: 'test', limit: 5 }})    // '/api/search?q=test&limit=5'
 */
export function route<T extends RoutesWithoutRequiredParams>(name: T): string;
export function route<T extends RoutesWithoutRequiredParams>(
  name: T,
  params?: RouteParams<T>,
): string;
export function route<T extends RoutesWithRequiredParams>(
  name: T,
  params: RouteParams<T>,
): string;
export function route<T extends RouteName>(
  name: T,
  params?: RouteParams<T>,
): string {{
  const def = routes[name];
  let url = def.path;

  // Replace path parameters
  if (params && 'pathParams' in def) {{
    for (const param of def.pathParams) {{
      const value = (params as Record<string, unknown>)[param];
      if (value !== undefined) {{
        url = url.replace(`{{${{param}}}}`, String(value));
      }}
    }}
  }}

  // Add query parameters
  if (params && 'queryParams' in def) {{
    const queryParts: string[] = [];
    for (const param of def.queryParams) {{
      const value = (params as Record<string, unknown>)[param];
      if (value !== undefined) {{
        queryParts.push(`${{encodeURIComponent(param)}}=${{encodeURIComponent(String(value))}}`);
      }}
    }}
    if (queryParts.length > 0) {{
      url += '?' + queryParts.join('&');
    }}
  }}

  // Apply API URL if set (for separate dev servers)
  return API_URL ? API_URL.replace(/\\/$/, '') + url : url;
}}

/** Check if a route exists */
export function hasRoute(name: string): name is RouteName {{
  return name in routes;
}}

/** Get all route names */
export function getRouteNames(): RouteName[] {{
  return Object.keys(routes) as RouteName[];
}}

/** Get route metadata */
export function getRoute<T extends RouteName>(name: T): (typeof routes)[T] {{
  return routes[name];
}}
"""


# =============================================================================
# Inertia Page Props Generation
# =============================================================================


@dataclass
class InertiaPageMetadata:
    """Metadata for an Inertia page component.

    Attributes:
        component: Inertia component name (e.g., "Home", "Books/Index").
        route_path: Route path for this page.
        props_type: TypeScript type name for page props (from OpenAPI).
        schema_ref: OpenAPI schema $ref if available.
        handler_name: Python handler function name.
    """

    component: str
    route_path: str
    props_type: "str | None" = None
    schema_ref: "str | None" = None
    handler_name: "str | None" = None


def _get_return_type_name(handler: HTTPRouteHandler) -> "str | None":
    """Extract the return type name from a route handler.

    Looks for msgspec Struct, Pydantic BaseModel, TypedDict, or other
    typed return annotations and extracts a meaningful type name.

    Args:
        handler: The Litestar route handler.

    Returns:
        The type name string or None if untyped.
    """
    # Get the return annotation from the handler
    # handler.fn is a Ref that wraps the actual function
    handler_fn = handler.fn
    fn = handler_fn.value if hasattr(handler_fn, "value") else handler_fn  # pyright: ignore
    annotations = getattr(fn, "__annotations__", {})
    return_type = annotations.get("return")

    if return_type is None:
        return None

    # Handle string annotations
    if isinstance(return_type, str):
        return return_type

    # Get the type name
    type_name = getattr(return_type, "__name__", None)
    if type_name:
        return type_name

    # Handle generic types (e.g., dict[str, Any])
    origin = getattr(return_type, "__origin__", None)
    if origin is not None:
        return getattr(origin, "__name__", str(origin))

    return str(return_type)


def _get_openapi_schema_ref(
    handler: HTTPRouteHandler,
    openapi_schema: dict[str, Any] | None,
    route_path: str,
    method: str = "GET",
) -> "str | None":
    """Find the OpenAPI schema $ref for a handler's response type.

    Args:
        handler: The route handler.
        openapi_schema: The full OpenAPI schema dict.
        route_path: The normalized route path.
        method: HTTP method (default GET for page routes).

    Returns:
        Schema $ref string like "#/components/schemas/BooksPageProps" or None.
    """
    if not openapi_schema:
        return None

    paths = openapi_schema.get("paths", {})
    path_item = paths.get(route_path, {})
    operation = path_item.get(method.lower(), {})

    # Look for 200 response schema
    responses = operation.get("responses", {})
    success_response = responses.get("200", responses.get("2XX", {}))
    content = success_response.get("content", {})

    # Check JSON content type
    json_content = content.get("application/json", {})
    schema = json_content.get("schema", {})

    # Return $ref if it exists
    ref = schema.get("$ref")
    if ref:
        return ref

    return None


def extract_inertia_pages(
    app: "Litestar",
    *,
    openapi_schema: dict[str, Any] | None = None,
) -> list[InertiaPageMetadata]:
    """Extract Inertia page metadata from a Litestar application.

    Finds all routes with Inertia component annotations and extracts
    their return type information for TypeScript type generation.

    Args:
        app: Litestar application instance.
        openapi_schema: Optional OpenAPI schema for enhanced type info.

    Returns:
        List of InertiaPageMetadata objects.
    """
    pages: list[InertiaPageMetadata] = []

    for http_route, route_handler in _iter_route_handlers(app):
        # Look for Inertia component in handler opts
        component = None
        if hasattr(route_handler, "opt") and route_handler.opt:
            # Check common keys: "component", "page"
            component = route_handler.opt.get("component") or route_handler.opt.get("page")

        if not component:
            continue

        # Get route info
        full_path = str(http_route.path)
        normalized_path = _normalize_path(full_path)
        handler_name = route_handler.handler_name or route_handler.name

        # Get return type info
        props_type = _get_return_type_name(route_handler)

        # Get OpenAPI schema ref
        # http_methods is a set, so use next(iter(...)) to get the first method
        method = next(iter(route_handler.http_methods), "GET") if route_handler.http_methods else "GET"
        schema_ref = _get_openapi_schema_ref(
            route_handler,
            openapi_schema,
            normalized_path,
            method=str(method),
        )

        pages.append(
            InertiaPageMetadata(
                component=component,
                route_path=normalized_path,
                props_type=props_type,
                schema_ref=schema_ref,
                handler_name=handler_name,
            )
        )

    return pages


def generate_inertia_pages_json(
    app: "Litestar",
    *,
    openapi_schema: dict[str, Any] | None = None,
    include_default_auth: bool = True,
    include_default_flash: bool = True,
) -> dict[str, Any]:
    """Generate Inertia pages metadata JSON.

    Creates a JSON structure consumed by the Vite plugin to generate
    page-props.ts with typed page props for each Inertia component.

    Args:
        app: Litestar application instance.
        openapi_schema: Optional OpenAPI schema for enhanced type info.
        include_default_auth: Include default User/AuthData types.
        include_default_flash: Include default FlashMessages type.

    Returns:
        Dictionary with pages metadata for JSON export.
    """
    pages_metadata = extract_inertia_pages(app, openapi_schema=openapi_schema)

    pages_dict: dict[str, dict[str, Any]] = {}

    for page in pages_metadata:
        page_data: dict[str, Any] = {
            "route": page.route_path,
        }

        if page.props_type:
            page_data["propsType"] = page.props_type

        if page.schema_ref:
            page_data["schemaRef"] = page.schema_ref

        if page.handler_name:
            page_data["handler"] = page.handler_name

        pages_dict[page.component] = page_data

    # Shared props structure (built-in props always present)
    shared_props: dict[str, dict[str, Any]] = {
        "errors": {"type": "Record<string, string[]>", "optional": True},
        "csrf_token": {"type": "string", "optional": True},
    }

    # Type generation config
    type_gen_config: dict[str, bool] = {
        "includeDefaultAuth": include_default_auth,
        "includeDefaultFlash": include_default_flash,
    }

    return {
        "pages": pages_dict,
        "sharedProps": shared_props,
        "typeGenConfig": type_gen_config,
        "generatedAt": __import__("datetime").datetime.now(tz=__import__("datetime").timezone.utc).isoformat(),
    }
