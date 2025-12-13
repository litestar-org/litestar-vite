"""Code generation utilities for route metadata export.

This module extracts route metadata from a Litestar application and emits a
`routes.json` file consumed by the Vite plugin. Detailed type generation is
delegated to @hey-api/openapi-ts; we keep only lightweight metadata here.
"""

import contextlib
import datetime
import re
from collections.abc import Callable, Generator
from dataclasses import dataclass, field
from pathlib import PurePosixPath
from typing import TYPE_CHECKING, Any, cast

from litestar import Litestar
from litestar._openapi.datastructures import (  # pyright: ignore[reportPrivateUsage]
    OpenAPIContext,
    _get_normalized_schema_key,  # pyright: ignore[reportPrivateUsage]
)
from litestar._openapi.parameters import (
    create_parameters_for_handler,  # pyright: ignore[reportPrivateUsage,reportPrivateImportUsage]
)
from litestar._openapi.schema_generation import SchemaCreator  # pyright: ignore[reportPrivateUsage]
from litestar._openapi.typescript_converter.schema_parsing import parse_schema  # pyright: ignore[reportPrivateUsage]
from litestar.handlers import HTTPRouteHandler
from litestar.openapi.spec import Reference, Schema
from litestar.openapi.spec.enums import OpenAPIType
from litestar.response import Response as LitestarResponse
from litestar.response import Template
from litestar.response.base import ASGIResponse
from litestar.types.builtin_types import NoneType
from litestar.typing import FieldDefinition

if TYPE_CHECKING:
    from litestar.dto import AbstractDTO
    from litestar.routes import HTTPRoute

    from litestar_vite.config import TypeGenConfig


__all__ = (
    "InertiaPageMetadata",
    "RouteMetadata",
    "extract_inertia_pages",
    "extract_route_metadata",
    "generate_inertia_pages_json",
    "generate_routes_json",
    "generate_routes_ts",
)

_PATH_PARAM_TYPE_PATTERN = re.compile(r"\{([^:}]+):[^}]+\}")
_PATH_PARAM_EXTRACT_PATTERN = re.compile(r"\{([^:}]+)(?::([^}]+))?\}")
_OPENAPI_TYPE_VALUES = frozenset(e.value for e in OpenAPIType)


def _str_dict_factory() -> dict[str, str]:
    """Return an empty ``dict[str, str]`` (typed for pyright)."""
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
    if not path or path == "/":
        return path

    return _PATH_PARAM_TYPE_PATTERN.sub(r"{\1}", str(PurePosixPath(path)))


def _extract_path_params(path: str) -> dict[str, str]:
    """Extract path parameters and their types from a route.

    Args:
        path: Route path.

    Returns:
        Dictionary mapping parameter names to TypeScript types.
    """
    return {match.group(1): "string" for match in _PATH_PARAM_EXTRACT_PATTERN.finditer(path)}


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
        if hasattr(route, "route_handler_map"):
            http_route: "HTTPRoute" = route  # type: ignore[assignment]
            for route_handler in http_route.route_handlers:
                yield http_route, route_handler


def _extract_params_from_litestar(
    handler: HTTPRouteHandler,
    http_route: "HTTPRoute",
    openapi_context: OpenAPIContext | None,
) -> tuple[dict[str, str], dict[str, str]]:
    """Extract path and query parameters using Litestar's native OpenAPI generation.

    Uses Litestar's `create_parameters_for_handler` which correctly handles:
    - Body parameter detection (DTOData, dataclass, Struct, etc.)
    - Filter dependencies expansion
    - Path vs query parameter classification

    Args:
        handler: The Litestar route handler.
        http_route: The HTTP route containing path parameter definitions.
        openapi_context: OpenAPI context for parameter generation.

    Returns:
        Tuple of (path_params, query_params) dictionaries mapping names to TypeScript types.
    """
    path_params: dict[str, str] = {}
    query_params: dict[str, str] = {}

    if openapi_context is None:
        return path_params, query_params

    try:
        route_path_params = http_route.path_parameters
        params = create_parameters_for_handler(openapi_context, handler, route_path_params)

        for param in params:
            schema_dict = param.schema.to_schema() if param.schema else None
            ts_type = _ts_type_from_openapi(schema_dict or {}) if schema_dict else "any"

            if not param.required and ts_type != "any" and "undefined" not in ts_type:
                ts_type = f"{ts_type} | undefined"

            match param.param_in:
                case "path":
                    path_params[param.name] = ts_type.replace(" | undefined", "")
                case "query":
                    query_params[param.name] = ts_type
                case _:
                    pass

    except (AttributeError, TypeError, ValueError, KeyError):
        pass

    return path_params, query_params


def _dict_to_schema(d: dict[str, Any]) -> Schema:
    """Convert an OpenAPI schema dict to a Litestar Schema object.

    Args:
        d: OpenAPI schema dictionary.

    Returns:
        Litestar Schema object.
    """
    if not d:
        return Schema()

    t = d.get("type")
    schema_type: "OpenAPIType | list[OpenAPIType] | None" = None
    if isinstance(t, str) and t in _OPENAPI_TYPE_VALUES:
        schema_type = OpenAPIType(t)
    elif isinstance(t, list):
        schema_type = [OpenAPIType(x) for x in t if isinstance(x, str) and x in _OPENAPI_TYPE_VALUES] or None  # pyright: ignore[reportUnknownVariableType, reportUnknownArgumentType]

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
        ts_element = parse_schema(_dict_to_schema(schema))
        return ts_element.write()
    except (TypeError, ValueError, KeyError):
        return "any"


_PYTHON_TO_TS_SIMPLE: dict[str, str] = {
    "str": "string",
    "int": "number",
    "float": "number",
    "bool": "boolean",
    "None": "null",
    "Any": "any",
}

_PYTHON_TO_TS_SIMPLE_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = tuple(
    (re.compile(rf"\b{re.escape(py)}\b"), ts) for py, ts in _PYTHON_TO_TS_SIMPLE.items()
)
_LIST_GENERIC_PATTERN = re.compile(r"\blist\[(.+?)\]")
_DICT_GENERIC_PATTERN = re.compile(r"\bdict\[(.+?),\s*(.+?)\]")
_DICT_PATTERN = re.compile(r"\bdict\b")
_GENERIC_BRACKETS_PATTERN = re.compile(r"\[([^\[\]]+)\]")
_TS_IDENTIFIER_PATTERN = re.compile(r"\b([A-Z][a-zA-Z0-9]*)\b")


def _python_type_to_typescript(py_type: str, *, fallback: str = "unknown") -> tuple[str, list[str]]:
    """Best-effort conversion of a Python type annotation string to TypeScript.

    This is used only as a last-resort fallback when Litestar's schema pipeline
    is unavailable (e.g., OpenAPI disabled) or the annotation is a forward-ref string.

    Args:
        py_type: Python type string (e.g., "dict[str, Team]", "list[User]").
        fallback: Value type for untyped containers ("unknown" or "any").

    Returns:
        Tuple of (typescript_type, list_of_custom_types_to_import).
    """
    if not py_type:
        return f"Record<string, {fallback}>", []

    ts_type = py_type.replace("List[", "list[").replace("Dict[", "dict[")

    # list[T] -> Array<T>
    ts_type = _LIST_GENERIC_PATTERN.sub(r"Array<\1>", ts_type)

    # dict[K, V] -> Record<K, V>; dict -> Record<string, fallback>
    ts_type = _DICT_GENERIC_PATTERN.sub(r"Record<\1, \2>", ts_type)
    ts_type = _DICT_PATTERN.sub(f"Record<string, {fallback}>", ts_type)

    # Map scalar builtins
    for pattern, ts in _PYTHON_TO_TS_SIMPLE_PATTERNS:
        ts_type = pattern.sub(ts, ts_type)

    # Convert remaining generic syntax: Type[T] -> Type<T>
    ts_type = _GENERIC_BRACKETS_PATTERN.sub(r"<\1>", ts_type)

    identifiers = _TS_IDENTIFIER_PATTERN.findall(ts_type)
    ts_builtins = {"Record", "Array", "string", "number", "boolean", "null", "unknown", "any", "never"}
    custom_types = sorted({t for t in identifiers if t not in ts_builtins})

    return ts_type, custom_types


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

    path_suffix = path.strip("/").replace("/", "_").replace("{", "").replace("}", "").replace("-", "_")
    method_suffix = methods[0].lower() if methods else ""

    candidate = f"{base_name}_{path_suffix}" if path_suffix else base_name
    if candidate not in used_names:
        return candidate

    candidate = f"{base_name}_{path_suffix}_{method_suffix}" if path_suffix else f"{base_name}_{method_suffix}"
    if candidate not in used_names:
        return candidate

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

    openapi_context: OpenAPIContext | None = None
    if app.openapi_config is not None:
        with contextlib.suppress(AttributeError, TypeError, ValueError):
            openapi_context = OpenAPIContext(
                openapi_config=app.openapi_config,
                plugins=app.plugins.openapi,
            )

    for http_route, route_handler in _iter_route_handlers(app):
        base_name = route_handler.name or route_handler.handler_name or str(route_handler)
        methods = [method.upper() for method in route_handler.http_methods]

        if methods in (["OPTIONS"], ["HEAD"]):
            continue

        full_path = str(http_route.path)

        if full_path.startswith("/schema"):
            if "openapi.json" in full_path:
                if "openapi.json" in used_names:
                    continue
                base_name = "openapi.json"
            elif "openapi.yaml" in full_path or "openapi.yml" in full_path:
                if "openapi.yaml" in used_names:
                    continue
                base_name = "openapi.yaml"
            else:
                continue

        route_name = _make_unique_name(base_name, used_names, full_path, methods)
        used_names.add(route_name)

        if only and not any(pattern in route_name or pattern in full_path for pattern in only):
            continue
        if exclude and any(pattern in route_name or pattern in full_path for pattern in exclude):
            continue

        params, query_params = _extract_params_from_litestar(route_handler, http_route, openapi_context)

        if not params:
            params = _extract_path_params(full_path)

        normalized_path = _normalize_path(full_path)

        opt: dict[str, Any] = getattr(route_handler, "opt", {}) or {}
        component = opt.get("component")

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


_TS_TYPE_MAP: dict[str, str] = {
    "string": "string",
    "integer": "number",
    "number": "number",
    "boolean": "boolean",
    "array": "unknown[]",
    "object": "Record<string, unknown>",
    "uuid": "string",
    "date": "string",
    "date-time": "string",
    "email": "string",
    "uri": "string",
    "url": "string",
    "int": "number",
    "float": "number",
    "str": "string",
    "bool": "boolean",
    "path": "string",
    "unknown": "unknown",
}


def _ts_type_for_param(param_type: str) -> str:
    """Map a parameter type string to TypeScript type.

    Args:
        param_type: Type string from OpenAPI schema or Litestar path param.

    Returns:
        TypeScript type string.
    """
    is_optional = "undefined" in param_type or param_type.endswith("?")
    clean_type = param_type.replace(" | undefined", "").replace("?", "").strip()

    ts_type = _TS_TYPE_MAP.get(clean_type) or clean_type or "string"

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

    route_names: list[str] = []
    path_params_entries: list[str] = []
    query_params_entries: list[str] = []
    routes_entries: list[str] = []

    for route in routes_metadata:
        route_name = route.name
        route_names.append(route_name)

        if route.params:
            param_fields: list[str] = []
            for param_name, param_type in route.params.items():
                ts_type = _ts_type_for_param(param_type)
                ts_type_clean = ts_type.replace(" | undefined", "")
                param_fields.append(f"    {param_name}: {ts_type_clean};")
            path_params_entries.append(f"  '{route_name}': {{\n" + "\n".join(param_fields) + "\n  };")
        else:
            path_params_entries.append(f"  '{route_name}': Record<string, never>;")

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

        methods_str = ", ".join(f"'{m}'" for m in route.methods)
        route_entry_lines = [
            f"  '{route_name}': {{",
            f"    path: '{_escape_ts_string(route.path)}',",
            f"    methods: [{methods_str}] as const,",
        ]
        param_names_str = ", ".join(f"'{p}'" for p in route.params) if route.params else ""
        route_entry_lines.append(f"    pathParams: [{param_names_str}] as const,")

        query_names_str = ", ".join(f"'{p}'" for p in route.query_params) if route.query_params else ""
        route_entry_lines.append(f"    queryParams: [{query_names_str}] as const,")
        if route.component:
            route_entry_lines.append(f"    component: '{_escape_ts_string(route.component)}',")
        route_entry_lines.append("  },")
        routes_entries.append("\n".join(route_entry_lines))

    route_names_union = "\n  | ".join(f"'{name}'" for name in route_names) if route_names else "never"

    return f"""// AUTO-GENERATED by litestar-vite. Do not edit.
/* eslint-disable */

// API base URL - only needed for separate dev servers
// Set VITE_API_URL=http://localhost:8000 when running Vite separately
const API_URL = (typeof import.meta !== 'undefined' && (import.meta as any).env?.VITE_API_URL) ?? '';

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

type EmptyParams = Record<string, never>
type MergeParams<A, B> =
  A extends EmptyParams ? (B extends EmptyParams ? EmptyParams : B) : B extends EmptyParams ? A : A & B

/** Combined parameters (path + query) */
export type RouteParams<T extends RouteName> = MergeParams<RoutePathParams[T], RouteQueryParams[T]>

/** Route metadata */
export const routeDefinitions = {{
{chr(10).join(routes_entries)}
}} as const

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
  const def = routeDefinitions[name];
  let url: string = def.path;

  // Replace path parameters
  if (params) {{
    for (const param of def.pathParams) {{
      const value = (params as Record<string, unknown>)[param];
      if (value !== undefined) {{
        url = url.replace("{{" + param + "}}", String(value));
      }}
    }}
  }}

  // Add query parameters
  if (params) {{
    const queryParts: string[] = [];
    for (const param of def.queryParams) {{
      const value = (params as Record<string, unknown>)[param];
      if (value !== undefined) {{
        queryParts.push(encodeURIComponent(param) + "=" + encodeURIComponent(String(value)));
      }}
    }}
    if (queryParts.length > 0) {{
      url += "?" + queryParts.join("&");
    }}
  }}

  // Apply API URL if set (for separate dev servers)
  return API_URL ? API_URL.replace(/\\/$/, '') + url : url;
}}

/** Check if a route exists */
export function hasRoute(name: string): name is RouteName {{
  return name in routeDefinitions;
}}

/** Get all route names */
export function getRouteNames(): RouteName[] {{
  return Object.keys(routeDefinitions) as RouteName[];
}}

/** Get route metadata */
export function getRoute<T extends RouteName>(name: T): (typeof routeDefinitions)[T] {{
  return routeDefinitions[name];
}}
"""


@dataclass
class InertiaPageMetadata:
    """Metadata for an Inertia page component.

    Attributes:
        component: Inertia component name (e.g., "Home", "Books/Index").
        route_path: Route path for this page.
        props_type: TypeScript type name for page props (from OpenAPI).
        ts_type: Canonical schema/type name for props derived from Litestar's schema pipeline.
        custom_types: Referenced schema/type names used within props that may need importing.
        schema_ref: OpenAPI schema $ref if available.
        handler_name: Python handler function name.
    """

    component: str
    route_path: str
    props_type: "str | None" = None
    ts_type: "str | None" = None
    custom_types: list[str] = field(default_factory=lambda: cast("list[str]", []))
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
    handler_fn = handler.fn
    fn = handler_fn.value if hasattr(handler_fn, "value") else handler_fn  # pyright: ignore
    annotations = getattr(fn, "__annotations__", {})
    return_type = annotations.get("return")

    if return_type is None:
        return None

    if isinstance(return_type, str):
        return return_type

    type_name = getattr(return_type, "__name__", None)
    if type_name:
        return type_name

    origin = getattr(return_type, "__origin__", None)
    if origin is not None:
        return getattr(origin, "__name__", str(origin))

    return str(return_type)


def _schema_name_from_ref(ref: str) -> str:
    """Extract schema component name from an OpenAPI $ref.

    Returns:
        Schema name string.
    """
    return ref.rsplit("/", maxsplit=1)[-1]


def _collect_ref_names(schema_dict: Any) -> set[str]:
    """Collect component schema names referenced by $ref within an OpenAPI schema dict.

    Returns:
        Set of schema names referenced.
    """
    names: set[str] = set()

    def _visit(obj: Any) -> None:
        if isinstance(obj, dict):
            mapping = cast("dict[str, Any]", obj)
            ref_value = mapping.get("$ref")
            if isinstance(ref_value, str) and ref_value.startswith("#/components/schemas/"):
                names.add(_schema_name_from_ref(ref_value))
            for v in mapping.values():
                _visit(v)
        elif isinstance(obj, list):
            for v in cast("list[Any]", obj):
                _visit(v)

    _visit(schema_dict)
    return names


def _resolve_page_props_field_definition(
    handler: HTTPRouteHandler,
    schema_creator: SchemaCreator,
) -> tuple[FieldDefinition | None, Schema | Reference | None]:
    """Resolve the FieldDefinition and schema result for a handler's Inertia props.

    Mirrors Litestar's response schema generation to ensure consistent schema registration.

    Returns:
        Tuple of (FieldDefinition or None, Schema or Reference or None).
    """
    field_definition = handler.parsed_fn_signature.return_type

    if field_definition.is_subclass_of((NoneType, ASGIResponse)):
        return None, None

    handler_any = cast("Any", handler)
    resolve_return_dto = cast("Callable[[], type[AbstractDTO[Any]] | None]", handler_any.resolve_return_dto)
    dto = resolve_return_dto()
    if dto is not None:
        result = dto.create_openapi_schema(
            field_definition=field_definition,
            handler_id=handler.handler_id,
            schema_creator=schema_creator,
        )
        return field_definition, result

    if field_definition.is_subclass_of(Template):
        resolved_field = FieldDefinition.from_annotation(str)
    elif field_definition.is_subclass_of(LitestarResponse):
        resolved_field = (
            field_definition.inner_types[0] if field_definition.inner_types else FieldDefinition.from_annotation(Any)
        )
    else:
        resolved_field = field_definition

    return resolved_field, schema_creator.for_field_definition(resolved_field)


def _build_schema_name_map(schema_registry: Any) -> dict[tuple[str, ...], str]:
    """Build a mapping of schema registry keys to final component names.

    Uses the same shortening and de-duplication logic as SchemaRegistry.generate_components_schemas().

    Returns:
        Mapping of schema keys to component names.
    """
    name_map: dict[tuple[str, ...], str] = {}
    model_name_groups = getattr(schema_registry, "_model_name_groups", {})

    for name, group in model_name_groups.items():
        if len(group) == 1:
            name_map[group[0].key] = name
            continue

        full_keys = [registered_schema.key for registered_schema in group]
        names = ["_".join(k) for k in schema_registry.remove_common_prefix(full_keys)]
        for name_, registered_schema in zip(names, group, strict=False):
            name_map[registered_schema.key] = name_

    return name_map


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

    responses = operation.get("responses", {})
    success_response = responses.get("200", responses.get("2XX", {}))
    content = success_response.get("content", {})

    json_content = content.get("application/json", {})
    schema = json_content.get("schema", {})

    ref = schema.get("$ref")
    if ref:
        return ref

    return None


def _try_create_openapi_context(app: "Litestar") -> tuple[OpenAPIContext | None, SchemaCreator | None]:
    """Create OpenAPIContext and SchemaCreator if available.

    This mirrors Litestar's internal OpenAPI setup but is tolerant of missing
    configuration or internal API changes.

    Returns:
        Tuple of (OpenAPIContext or None, SchemaCreator or None).
    """
    if app.openapi_config is None:
        return None, None

    with contextlib.suppress(AttributeError, TypeError, ValueError):
        openapi_context = OpenAPIContext(
            openapi_config=app.openapi_config,
            plugins=app.plugins.openapi,
        )
        return openapi_context, SchemaCreator.from_openapi_context(openapi_context)

    return None, None


def _extract_inertia_component(handler: HTTPRouteHandler) -> str | None:
    """Resolve the Inertia component name from handler options.

    Returns:
        Component name string or None if not set.
    """
    opt = handler.opt or {}
    component = opt.get("component") or opt.get("page")
    return component if isinstance(component, str) and component else None


def _infer_inertia_props_type(
    component: str,
    handler: HTTPRouteHandler,
    schema_creator: SchemaCreator | None,
    page_schema_keys: dict[str, tuple[str, ...]],
    page_schema_dicts: dict[str, dict[str, Any]],
    *,
    fallback_type: str,
) -> str | None:
    """Infer a page's props type and collect schema sources for later resolution.

    Returns:
        TypeScript type string or None if untyped.
    """
    if schema_creator is not None:
        field_def, schema_result = _resolve_page_props_field_definition(handler, schema_creator)
        if field_def is not None and isinstance(schema_result, Reference):
            page_schema_keys[component] = _get_normalized_schema_key(field_def)
            return None
        if isinstance(schema_result, Schema):
            schema_dict = schema_result.to_schema()
            page_schema_dicts[component] = schema_dict
            return _ts_type_from_openapi(schema_dict)
        return None

    raw_type = _get_return_type_name(handler)
    if not raw_type:
        return None
    props_type, _ = _python_type_to_typescript(raw_type, fallback=fallback_type)
    return props_type


def _openapi_components_schemas(openapi_schema: dict[str, Any] | None) -> dict[str, Any]:
    """Extract OpenAPI components.schemas dict as a concrete mapping."""
    if not isinstance(openapi_schema, dict):
        return {}
    schema_dict = openapi_schema
    components = schema_dict.get("components")
    if not isinstance(components, dict):
        return {}
    components_dict = cast("dict[str, Any]", components)
    schemas = components_dict.get("schemas")
    if not isinstance(schemas, dict):
        return {}
    return cast("dict[str, Any]", schemas)


def _finalize_inertia_pages(
    pages: list[InertiaPageMetadata],
    *,
    openapi_schema: dict[str, Any] | None,
    openapi_context: OpenAPIContext,
    page_schema_keys: dict[str, tuple[str, ...]],
    page_schema_dicts: dict[str, dict[str, Any]],
) -> None:
    """Finalize page type names and custom type references from the schema registry."""
    openapi_context.schema_registry.generate_components_schemas()
    name_map = _build_schema_name_map(openapi_context.schema_registry)
    openapi_components = _openapi_components_schemas(openapi_schema)

    for page in pages:
        schema_key = page_schema_keys.get(page.component)

        schema_name: str | None = None
        if page.schema_ref:
            schema_name = _schema_name_from_ref(page.schema_ref)
        elif schema_key:
            schema_name = name_map.get(schema_key)

        if schema_name:
            page.ts_type = schema_name
            page.props_type = schema_name

        custom_types: set[str] = set()
        if page.ts_type:
            custom_types.add(page.ts_type)

        if page.schema_ref:
            openapi_schema_dict = openapi_components.get(page.ts_type or "")
            if isinstance(openapi_schema_dict, dict):
                custom_types.update(_collect_ref_names(openapi_schema_dict))
        else:
            page_schema_dict = page_schema_dicts.get(page.component)
            if isinstance(page_schema_dict, dict):
                custom_types.update(_collect_ref_names(page_schema_dict))
            elif schema_key:
                registered = openapi_context.schema_registry._schema_key_map.get(schema_key)  # pyright: ignore[reportPrivateUsage]
                if registered:
                    custom_types.update(_collect_ref_names(registered.schema.to_schema()))

        page.custom_types = sorted(custom_types)


def extract_inertia_pages(
    app: "Litestar",
    *,
    openapi_schema: dict[str, Any] | None = None,
    fallback_type: "str" = "unknown",
) -> list[InertiaPageMetadata]:
    """Extract Inertia page metadata from a Litestar application.

    Finds all routes with Inertia component annotations and extracts
    their return type information for TypeScript type generation.

    Args:
        app: Litestar application instance.
        openapi_schema: Optional OpenAPI schema for enhanced type info.
        fallback_type: Fallback value type for untyped containers in props.
            Use "unknown" (default) for strictness or "any" for permissiveness.

    Returns:
        List of InertiaPageMetadata objects.
    """
    pages: list[InertiaPageMetadata] = []

    openapi_context, schema_creator = _try_create_openapi_context(app)

    page_schema_keys: dict[str, tuple[str, ...]] = {}
    page_schema_dicts: dict[str, dict[str, Any]] = {}

    for http_route, route_handler in _iter_route_handlers(app):
        component = _extract_inertia_component(route_handler)
        if not component:
            continue

        normalized_path = _normalize_path(str(http_route.path))
        handler_name = route_handler.handler_name or route_handler.name

        props_type = _infer_inertia_props_type(
            component,
            route_handler,
            schema_creator,
            page_schema_keys,
            page_schema_dicts,
            fallback_type=fallback_type,
        )

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

    if openapi_context is not None and schema_creator is not None:
        _finalize_inertia_pages(
            pages,
            openapi_schema=openapi_schema,
            openapi_context=openapi_context,
            page_schema_keys=page_schema_keys,
            page_schema_dicts=page_schema_dicts,
        )

    return pages


def generate_inertia_pages_json(
    app: "Litestar",
    *,
    openapi_schema: dict[str, Any] | None = None,
    include_default_auth: bool = True,
    include_default_flash: bool = True,
    types_config: "TypeGenConfig | None" = None,
) -> dict[str, Any]:
    """Generate Inertia pages metadata JSON.

    Creates a JSON structure consumed by the Vite plugin to generate
    page-props.ts with typed page props for each Inertia component.

    Args:
        app: Litestar application instance.
        openapi_schema: Optional OpenAPI schema for enhanced type info.
        include_default_auth: Include default User/AuthData types.
        include_default_flash: Include default FlashMessages type.
        types_config: Optional TypeGenConfig to include import and fallback hints.

    Returns:
        Dictionary with pages metadata for JSON export.
    """
    pages_metadata = extract_inertia_pages(
        app,
        openapi_schema=openapi_schema,
        fallback_type=types_config.fallback_type if types_config is not None else "unknown",
    )

    pages_dict: dict[str, dict[str, Any]] = {}

    for page in pages_metadata:
        page_data: dict[str, Any] = {
            "route": page.route_path,
        }

        if page.props_type:
            page_data["propsType"] = page.props_type
        if page.ts_type:
            page_data["tsType"] = page.ts_type
        if page.custom_types:
            page_data["customTypes"] = page.custom_types

        if page.schema_ref:
            page_data["schemaRef"] = page.schema_ref

        if page.handler_name:
            page_data["handler"] = page.handler_name

        pages_dict[page.component] = page_data

    shared_props: dict[str, dict[str, Any]] = {
        "errors": {"type": "Record<string, string[]>", "optional": True},
        "csrf_token": {"type": "string", "optional": True},
    }

    type_gen_config: dict[str, bool] = {
        "includeDefaultAuth": include_default_auth,
        "includeDefaultFlash": include_default_flash,
    }

    root: dict[str, Any] = {
        "pages": pages_dict,
        "sharedProps": shared_props,
        "typeGenConfig": type_gen_config,
        "generatedAt": datetime.datetime.now(tz=datetime.timezone.utc).isoformat(),
    }

    if types_config is not None:
        root["typeImportPaths"] = types_config.type_import_paths
        root["fallbackType"] = types_config.fallback_type

    return root
