"""Code generation utilities for type-safe route definitions.

This module provides utilities for extracting route metadata from a Litestar application
and generating TypeScript type definitions and route helpers.

Example usage:
    ```python
    from litestar import Litestar
    from litestar_vite.codegen import extract_route_metadata, generate_routes_json

    app = Litestar([...])

    # Extract metadata
    routes = extract_route_metadata(app)

    # Generate JSON
    json_output = generate_routes_json(app, include_components=True)
    ```
"""

from __future__ import annotations

import inspect
import re
import types
from dataclasses import dataclass, field
from pathlib import PurePosixPath
from typing import TYPE_CHECKING, Any, Union, get_args, get_origin

if TYPE_CHECKING:
    from litestar import Litestar
    from litestar.handlers import HTTPRouteHandler
    from litestar.routes import HTTPRoute


__all__ = ("RouteMetadata", "extract_route_metadata", "generate_routes_json")

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
    params: dict[str, str] = field(default_factory=dict)
    query_params: dict[str, str] = field(default_factory=dict)
    component: str | None = None


def _python_type_to_typescript(python_type: str | type | Any) -> str:
    """Convert Python type annotation to TypeScript type.

    Args:
        python_type: Python type as a string or actual type object.

    Returns:
        TypeScript type equivalent.
    """
    # String-based type mapping (for path parameter types from URL)
    string_type_map = {
        "int": "number",
        "float": "number",
        "str": "string",
        "bool": "boolean",
        "uuid.UUID": "string",
        "UUID": "string",
        "datetime.datetime": "string",
        "datetime.date": "string",
        "datetime.time": "string",
        "pathlib.Path": "string",
        "Path": "string",
    }

    # Handle string types (from path parameters)
    if isinstance(python_type, str):
        return string_type_map.get(python_type, "string")

    # Handle None type
    if python_type is type(None):
        return "null"

    # Handle Union types (Optional[T] is Union[T, None], and PEP 604 X | Y)
    origin = get_origin(python_type)
    if origin is Union or origin is types.UnionType:
        args = get_args(python_type)
        # Filter out NoneType and convert remaining types
        non_none_types = [_python_type_to_typescript(arg) for arg in args if arg is not type(None)]
        if non_none_types:
            return " | ".join(non_none_types)
        return "any"

    # Handle list/List types
    if origin is list:
        args = get_args(python_type)
        if args:
            inner_type = _python_type_to_typescript(args[0])
            return f"{inner_type}[]"
        return "any[]"

    # Handle actual type objects
    if isinstance(python_type, type):
        type_name = python_type.__name__
        type_obj_map = {
            "int": "number",
            "float": "number",
            "str": "string",
            "bool": "boolean",
            "UUID": "string",
            "datetime": "string",
            "date": "string",
            "time": "string",
            "Path": "string",
            "Decimal": "number",
        }
        return type_obj_map.get(type_name, "any")

    # Fallback for unknown types
    return "any"


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
        param_type = match.group(2) or "str"

        # Convert to TypeScript type
        ts_type = _python_type_to_typescript(param_type)
        params[param_name] = ts_type

    return params


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
    from litestar.params import ParameterKwarg

    query_params: dict[str, str] = {}

    # Get parsed signature - contains all handler parameters
    parsed_sig = getattr(handler, "parsed_fn_signature", None)
    if parsed_sig is None:
        return query_params

    # Get the body parameter name (if any) - this is the "data" parameter
    body_param_name = getattr(parsed_sig, "data", None)
    if hasattr(body_param_name, "name"):
        body_param_name = body_param_name.name

    # Get dependency names to exclude
    dependency_names: set[str] = set()
    try:
        resolved_deps = handler.resolve_dependencies()
        dependency_names = set(resolved_deps.keys())
    except Exception:  # noqa: BLE001
        # Dependencies may not be resolvable in all contexts
        pass

    # Iterate through all parameters (FieldDefinition objects)
    parameters = getattr(parsed_sig, "parameters", {})
    for param_name, field_def in parameters.items():
        # Skip 'self' and 'cls'
        if param_name in ("self", "cls"):
            continue

        # Skip path parameters
        if param_name in path_param_names:
            continue

        # Skip body parameter
        if param_name == body_param_name:
            continue

        # Skip dependencies
        if param_name in dependency_names:
            continue

        # Skip return annotation
        if param_name == "return":
            continue

        # Get the annotation from FieldDefinition
        annotation = getattr(field_def, "annotation", None)
        if annotation is None:
            continue

        # Skip system types (Request, State, Scope, etc.)
        if _is_system_type(annotation):
            continue

        # Convert to TypeScript type
        ts_type = _python_type_to_typescript(annotation)

        # Check if optional (has default value)
        # Litestar uses _EmptyEnum.EMPTY as sentinel for no default
        default = getattr(field_def, "default", None)
        # Check if it's the EMPTY sentinel by checking its type/name
        is_empty = (
            default is None
            or (hasattr(default, "name") and default.name == "EMPTY")
            or str(default) == "<_EmptyEnum.EMPTY: 0>"
        )
        is_optional = not is_empty

        # Handle ParameterKwarg metadata for aliasing (from Parameter() calls)
        # In Litestar, Parameter() metadata is stored in kwarg_definition, not default
        final_name = param_name
        kwarg_def = getattr(field_def, "kwarg_definition", None)
        if isinstance(kwarg_def, ParameterKwarg):
            # Check for query name alias
            query_alias = getattr(kwarg_def, "query", None)
            if query_alias:
                final_name = query_alias

        # Add undefined to type if optional
        if is_optional and "undefined" not in ts_type:
            ts_type = f"{ts_type} | undefined"

        query_params[final_name] = ts_type

    return query_params


def extract_route_metadata(
    app: Litestar,
    *,
    only: list[str] | None = None,
    exclude: list[str] | None = None,
) -> list[RouteMetadata]:
    """Extract route metadata from a Litestar application.

    Args:
        app: Litestar application instance.
        only: Whitelist patterns (route names or paths to include).
        exclude: Blacklist patterns (route names or paths to exclude).

    Returns:
        List of route metadata objects.
    """
    routes_metadata: list[RouteMetadata] = []

    for route in app.routes:
        if not isinstance(route, type(route)) or not hasattr(route, "route_handler_map"):
            continue

        # Get the HTTP route
        http_route: HTTPRoute = route  # type: ignore[assignment]

        for route_handler in http_route.route_handlers:
            # Get route name
            route_name = route_handler.name or route_handler.handler_name or str(route_handler)

            # Get full path (including mount paths)
            full_path = str(http_route.path)

            # Apply filters
            if only and not any(pattern in route_name or pattern in full_path for pattern in only):
                continue
            if exclude and any(pattern in route_name or pattern in full_path for pattern in exclude):
                continue

            # Extract methods
            methods = [method.upper() for method in route_handler.http_methods]

            # Extract path parameters
            params = _extract_path_params(full_path)
            path_param_names = set(params.keys())

            # Extract query parameters (excludes path params, body, deps, system types)
            query_params = _extract_query_params(route_handler, path_param_names)

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
    only: list[str] | None = None,
    exclude: list[str] | None = None,
    include_components: bool = False,
) -> dict[str, Any]:
    """Generate Ziggy-compatible routes JSON.

    Args:
        app: Litestar application instance.
        only: Whitelist patterns (route names or paths to include).
        exclude: Blacklist patterns (route names or paths to exclude).
        include_components: Include Inertia component names in output.

    Returns:
        Dictionary with routes in Ziggy-compatible format.
    """
    routes_metadata = extract_route_metadata(app, only=only, exclude=exclude)

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
