"""Route metadata extraction and Ziggy-compatible generation."""

import contextlib
import re
from collections.abc import Generator
from dataclasses import dataclass, field
from typing import Any, cast

from litestar import Litestar
from litestar._openapi.datastructures import OpenAPIContext  # pyright: ignore[reportPrivateUsage]
from litestar._openapi.parameters import (  # pyright: ignore[reportPrivateUsage,reportPrivateImportUsage]
    create_parameters_for_handler,
)
from litestar.handlers import HTTPRouteHandler
from litestar.routes import HTTPRoute

from litestar_vite._codegen.ts import normalize_path, ts_type_from_openapi

_PATH_PARAM_EXTRACT_PATTERN = re.compile(r"\{([^:}]+)(?::([^}]+))?\}")

_TS_SEMANTIC_ALIASES: dict[str, tuple[str, str]] = {
    "UUID": ("UUID v4 string", "string"),
    "DateTime": ("RFC 3339 date-time string", "string"),
    "DateOnly": ("ISO 8601 date string (YYYY-MM-DD)", "string"),
    "TimeOnly": ("ISO 8601 time string", "string"),
    "Duration": ("ISO 8601 duration string", "string"),
    "Email": ("Email address string", "string"),
    "URI": ("URI/URL string", "string"),
    "IPv4": ("IPv4 address string", "string"),
    "IPv6": ("IPv6 address string", "string"),
}


def _str_dict_factory() -> dict[str, str]:
    """Return an empty ``dict[str, str]`` (typed for pyright).

    Returns:
        An empty dictionary.
    """
    return {}


@dataclass
class RouteMetadata:
    """Metadata for a single route."""

    name: str
    path: str
    methods: list[str]
    params: dict[str, str] = field(default_factory=_str_dict_factory)
    query_params: dict[str, str] = field(default_factory=_str_dict_factory)
    component: "str | None" = None


def _extract_path_params(path: str) -> dict[str, str]:
    """Extract path parameters and their types from a route.

    Args:
        path: The route path template.

    Returns:
        Mapping of parameter name to TypeScript type.
    """
    return {match.group(1): "string" for match in _PATH_PARAM_EXTRACT_PATTERN.finditer(path)}


def _iter_route_handlers(app: Litestar) -> Generator[tuple["HTTPRoute", HTTPRouteHandler], None, None]:
    """Iterate over HTTP route handlers in an app.

    Args:
        app: The Litestar application.

    Yields:
        Tuples of (HTTPRoute, HTTPRouteHandler).
    """
    for route in app.routes:
        if isinstance(route, HTTPRoute):
            for route_handler in route.route_handlers:
                yield route, route_handler


def _extract_params_from_litestar(
    handler: HTTPRouteHandler, http_route: "HTTPRoute", openapi_context: OpenAPIContext | None
) -> tuple[dict[str, str], dict[str, str]]:
    """Extract path and query parameters using Litestar's native OpenAPI generation.

    Args:
        handler: The route handler.
        http_route: The HTTP route.
        openapi_context: The OpenAPI context, if available.

    Returns:
        A tuple of (path_params, query_params) maps.
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
            ts_type = ts_type_from_openapi(schema_dict or {}) if schema_dict else "any"
            # For URL generation, `null` is not a meaningful value (it would stringify to "null").
            # Treat `null` as "missing" rather than emitting `| null` into route parameter types.
            ts_type = ts_type.replace(" | null", "").replace("null | ", "")

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


def _make_unique_name(base_name: str, used_names: set[str], path: str, methods: list[str]) -> str:
    """Generate a unique route name, avoiding collisions.

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

    Note:
        ``openapi_schema`` is accepted for API compatibility and future enrichment,
        but parameter typing is currently derived from Litestar's OpenAPI parameter
        generation, not the exported schema document.

    Returns:
        A list of RouteMetadata objects.
    """
    routes_metadata: list[RouteMetadata] = []
    used_names: set[str] = set()

    openapi_context: OpenAPIContext | None = None
    if app.openapi_config is not None:
        with contextlib.suppress(AttributeError, TypeError, ValueError):
            openapi_context = OpenAPIContext(openapi_config=app.openapi_config, plugins=app.plugins.openapi)

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

        normalized_path = normalize_path(full_path)

        opt: dict[str, Any] = route_handler.opt or {}
        component = opt.get("component")

        routes_metadata.append(
            RouteMetadata(
                name=route_name,
                path=normalized_path,
                methods=methods,
                params=params,
                query_params=query_params,
                component=cast("str | None", component),
            )
        )

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

    Returns:
        A Ziggy-compatible routes payload as a dictionary.
    """
    routes_metadata = extract_route_metadata(app, only=only, exclude=exclude, openapi_schema=openapi_schema)

    routes_dict: dict[str, Any] = {}

    for route in routes_metadata:
        route_data: dict[str, Any] = {"uri": route.path, "methods": route.methods}

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

    Returns:
        The TypeScript type for the parameter.
    """
    is_optional = "undefined" in param_type or param_type.endswith("?")
    clean_type = param_type.replace(" | undefined", "").replace("?", "").strip()

    ts_type = _TS_TYPE_MAP.get(clean_type) or clean_type or "string"

    if is_optional and "undefined" not in ts_type:
        return f"{ts_type} | undefined"
    return ts_type


def _is_type_required(param_type: str) -> bool:
    """Check if a parameter type indicates a required field.

    Returns:
        True if the parameter is required, otherwise False.
    """
    return "undefined" not in param_type and not param_type.endswith("?")


def _escape_ts_string(s: str) -> str:
    """Escape a string for use in TypeScript string literals.

    Returns:
        The escaped string.
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

    Returns:
        The generated TypeScript source.
    """
    routes_metadata = extract_route_metadata(app, only=only, exclude=exclude, openapi_schema=openapi_schema)

    route_names: list[str] = []
    path_params_entries: list[str] = []
    query_params_entries: list[str] = []
    routes_entries: list[str] = []
    used_aliases: set[str] = set()

    for route in routes_metadata:
        route_name = route.name
        route_names.append(route_name)

        if route.params:
            param_fields: list[str] = []
            for param_name, param_type in route.params.items():
                ts_type = _ts_type_for_param(param_type)
                ts_type_clean = ts_type.replace(" | undefined", "")
                used_aliases.update(_collect_semantic_aliases(ts_type_clean))
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
                used_aliases.update(_collect_semantic_aliases(ts_type_clean))
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

    alias_block = _render_semantic_aliases(used_aliases)
    alias_preamble = f"{alias_block}\n\n" if alias_block else ""

    return f"""// AUTO-GENERATED by litestar-vite. Do not edit.
/* eslint-disable */

// API base URL - only needed for separate dev servers
// Set VITE_API_URL=http://localhost:8000 when running Vite separately
const API_URL = (typeof import.meta !== 'undefined' && (import.meta as any).env?.VITE_API_URL) ?? '';

{alias_preamble}
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


def _collect_semantic_aliases(type_expr: str) -> set[str]:
    return {alias for alias in _TS_SEMANTIC_ALIASES if alias in type_expr}


def _render_semantic_aliases(aliases: set[str]) -> str:
    if not aliases:
        return ""

    lines: list[str] = ["/** Semantic string aliases derived from OpenAPI `format`. */"]
    for alias in sorted(aliases):
        doc, base = _TS_SEMANTIC_ALIASES[alias]
        lines.append(f"/** {doc} */")
        lines.append(f"export type {alias} = {base};")
        lines.append("")
    return "\n".join(lines).rstrip()
