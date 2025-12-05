"""Code generation utilities for route metadata export.

This module extracts route metadata from a Litestar application and emits a
`routes.json` file consumed by the Vite plugin. Detailed type generation is
delegated to @hey-api/openapi-ts; we keep only lightweight metadata here.
"""

import inspect
import re
from dataclasses import dataclass, field
from pathlib import PurePosixPath
from typing import TYPE_CHECKING, Any

from litestar import Litestar
from litestar.handlers import HTTPRouteHandler

if TYPE_CHECKING:
    from litestar.routes import HTTPRoute


__all__ = ("RouteMetadata", "extract_route_metadata", "generate_routes_json", "generate_routes_ts")

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

# OpenAPI to TypeScript type map
# Mirrors Litestar's typescript_converter: litestar/_openapi/typescript_converter/schema_parsing.py
_OPENAPI_TS_TYPE_MAP: dict[str, str] = {
    "array": "unknown[]",
    "boolean": "boolean",
    "integer": "number",
    "null": "null",
    "number": "number",
    "object": "Record<string, unknown>",
    "string": "string",
}


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

    # Replace {param:type} with {param} using compiled pattern
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

    # Add undefined to type if optional
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

    # Iterate through all parameters
    parameters = getattr(parsed_sig, "parameters", {})
    for param_name, field_def in parameters.items():
        if _should_skip_param(param_name, path_param_names, body_param_name, dependency_names):
            continue

        result = _process_field_definition(field_def, param_name)
        if result is not None:
            final_name, ts_type = result
            query_params[final_name] = ts_type

    return query_params


def _join_types(types: list[str], separator: str = " | ") -> str:
    """Join type strings, filtering duplicates and 'unknown'.

    Returns:
        Joined type string.
    """
    unique = list(dict.fromkeys(t for t in types if t != "unknown"))
    return separator.join(unique) if unique else "unknown"


def _ts_type_from_openapi(schema: dict[str, Any]) -> str:  # noqa: PLR0911
    """Map OpenAPI schema to TypeScript type string.

    Mirrors Litestar's typescript_converter patterns to handle OpenAPI 3.1 schemas.
    See: litestar/_openapi/typescript_converter/schema_parsing.py

    Args:
        schema: OpenAPI schema dictionary.

    Returns:
        TypeScript type string.
    """
    if not schema:
        return "unknown"

    # Handle oneOf/anyOf compositions (nullable types in OpenAPI 3.1)
    # Litestar uses one_of for optional fields: Schema(one_of=[type_schema, null_schema])
    if one_of := schema.get("oneOf"):
        sub_schemas: list[dict[str, Any]] = [s for s in one_of if isinstance(s, dict)]
        types = [_ts_type_from_openapi(s) for s in sub_schemas]
        return _join_types(types)

    if any_of := schema.get("anyOf"):
        sub_schemas = [s for s in any_of if isinstance(s, dict)]
        types = [_ts_type_from_openapi(s) for s in sub_schemas]
        return _join_types(types)

    # Handle allOf (intersection types)
    if all_of := schema.get("allOf"):
        sub_schemas = [s for s in all_of if isinstance(s, dict)]
        types = [_ts_type_from_openapi(s) for s in sub_schemas]
        return _join_types(types, " & ")

    # Handle enum (literal union)
    if enum := schema.get("enum"):
        literals: list[str] = []
        for v in enum:
            if isinstance(v, str):
                literals.append(f'"{v}"')
            elif isinstance(v, bool):
                literals.append("true" if v else "false")
            else:
                literals.append(str(v))
        return " | ".join(literals) if literals else "unknown"

    # Handle const (single literal)
    if (const := schema.get("const")) is not None:
        if isinstance(const, str):
            return f'"{const}"'
        if isinstance(const, bool):
            return "true" if const else "false"
        return str(const)

    # Get the type field
    t = schema.get("type")

    # Handle list types: ["integer", "null"] -> "number | null"
    # This is the key fix for OpenAPI 3.1
    if isinstance(t, list):
        type_list: list[Any] = t  # pyright: ignore[reportUnknownVariableType]
        type_names: list[str] = [str(item) for item in type_list if isinstance(item, str)]
        types = [_OPENAPI_TS_TYPE_MAP.get(name, "unknown") for name in type_names]
        unique = list(dict.fromkeys(types))  # Preserve order, remove duplicates
        return " | ".join(unique) if unique else "unknown"

    # Handle single type
    if isinstance(t, str):
        # Special case: array with items
        if t == "array":
            items: Any = schema.get("items", {})  # pyright: ignore[reportUnknownVariableType]
            item_schema: dict[str, Any] = items if isinstance(items, dict) else {}  # pyright: ignore[reportUnknownVariableType]
            item_type = _ts_type_from_openapi(item_schema)
            return f"{item_type}[]"

        return _OPENAPI_TS_TYPE_MAP.get(t, "unknown")

    # Handle format-only schemas (no type but has format like uuid, date-time)
    fmt = schema.get("format")
    if fmt in {"uuid", "date-time", "date", "time", "email", "uri", "url"}:
        return "string"

    # No type specified - could be any JSON value
    return "unknown"


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
        only: Whitelist patterns (route names or paths to include).
        exclude: Blacklist patterns (route names or paths to exclude).
        openapi_schema: Optional OpenAPI schema used to enrich parameter and query types.

    Returns:
        List of route metadata objects.
    """
    routes_metadata: list[RouteMetadata] = []
    used_names: set[str] = set()
    op_lookup = _openapi_lookup(openapi_schema)

    for route in app.routes:
        if not isinstance(route, type(route)) or not hasattr(route, "route_handler_map"):
            continue

        # Get the HTTP route
        http_route: HTTPRoute = route  # type: ignore[assignment]

        for route_handler in http_route.route_handlers:
            # Get base route name
            base_name = route_handler.name or route_handler.handler_name or str(route_handler)

            # Extract methods first (needed for unique name generation)
            methods = [method.upper() for method in route_handler.http_methods]

            # Get full path
            full_path = str(http_route.path)

            # Make name unique
            route_name = _make_unique_name(base_name, used_names, full_path, methods)
            used_names.add(route_name)

            # Apply filters
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
        only: Whitelist patterns (route names or paths to include).
        exclude: Blacklist patterns (route names or paths to exclude).
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
        only: Whitelist patterns (route names or paths to include).
        exclude: Blacklist patterns (route names or paths to exclude).
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
