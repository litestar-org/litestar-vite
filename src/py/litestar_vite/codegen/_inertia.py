"""Inertia page-props metadata extraction and export."""

import re
from contextlib import suppress
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

from litestar._openapi.datastructures import _get_normalized_schema_key  # pyright: ignore[reportPrivateUsage]
from litestar.handlers import HTTPRouteHandler
from litestar.openapi.spec import Reference, Schema
from litestar.response.base import ASGIResponse
from litestar.routes import HTTPRoute
from litestar.types.builtin_types import NoneType
from litestar.typing import FieldDefinition

from litestar_vite.codegen._openapi import (
    OpenAPISupport,
    build_schema_name_map,
    merge_generated_components_into_openapi,
    openapi_components_schemas,
    resolve_page_props_field_definition,
    schema_name_from_ref,
)
from litestar_vite.codegen._ts import collect_ref_names, normalize_path, python_type_to_typescript, ts_type_from_openapi

if TYPE_CHECKING:
    from litestar import Litestar

    from litestar_vite.config import InertiaConfig, TypeGenConfig

# Compiled regex for splitting TypeScript type strings on union/intersection operators
_TYPE_OPERATOR_RE = re.compile(r"(\s*[|&]\s*)")


def str_list_factory() -> list[str]:
    """Return an empty ``list[str]`` (typed for pyright).

    Returns:
        An empty list.
    """
    return []


def _pick_inertia_method(http_methods: "set[Any] | frozenset[Any] | None") -> str:
    """Pick a deterministic HTTP method for Inertia page props inference.

    Inertia pages are typically loaded via GET requests, so we prefer GET.
    For determinism, we sort remaining methods alphabetically.

    Args:
        http_methods: Set of HTTP methods from the route handler.

    Returns:
        The selected HTTP method string.
    """
    if not http_methods:
        return "GET"
    # Prefer GET for Inertia page loads
    if "GET" in http_methods:
        return "GET"
    # Fallback to alphabetically first method for determinism
    return sorted(http_methods)[0]


def normalize_type_name(type_name: str, openapi_schemas: set[str]) -> str:
    """Strip module prefix from mangled type names.

    Always converts 'app_lib_schema_NoProps' -> 'NoProps' because:
    1. If 'NoProps' exists in OpenAPI, it will be imported correctly
    2. If 'NoProps' doesn't exist, the error message is clearer for users
       (they can add it to OpenAPI or configure type_import_paths)

    The mangled name 'app_lib_schema_NoProps' will NEVER work - it doesn't
    exist anywhere. The short name is always preferable.

    Args:
        type_name: The potentially mangled type name.
        openapi_schemas: Set of available OpenAPI schema names.

    Returns:
        The normalized (unmangled) type name.
    """
    if type_name in openapi_schemas:
        return type_name

    # Check if this looks like a mangled module path (contains underscores)
    if "_" not in type_name:
        return type_name

    # Try progressively shorter suffixes to find the class name
    parts = type_name.split("_")
    for i in range(len(parts)):
        short_name = "_".join(parts[i:])
        # Prefer OpenAPI match, but if we get to the last part, use it anyway
        if short_name in openapi_schemas:
            return short_name

    # Use the last part as the class name (e.g., 'NoProps' from 'app_lib_schema_NoProps')
    # This is always better than the mangled name for error messages
    return parts[-1] if parts else type_name


def normalize_type_string(type_string: str, openapi_schemas: set[str]) -> str:
    """Normalize all type names within a TypeScript type string.

    Handles union types like 'any | app_lib_schema_NoProps' by parsing the
    string and normalizing each type name individually.

    Args:
        type_string: A TypeScript type string (may contain unions, intersections).
        openapi_schemas: Set of available OpenAPI schema names.

    Returns:
        The type string with all type names normalized.
    """
    # Primitives and special types that should not be normalized
    skip_types = {"any", "unknown", "null", "undefined", "void", "never", "string", "number", "boolean", "object"}

    # Split on | and & while preserving whitespace
    tokens = _TYPE_OPERATOR_RE.split(type_string)
    result_parts: list[str] = []

    for token in tokens:
        stripped = token.strip()
        # Keep operators and whitespace as-is
        if stripped in {"|", "&", ""} or stripped in skip_types or stripped == "{}":
            result_parts.append(token)
        # Normalize type names
        else:
            normalized = normalize_type_name(stripped, openapi_schemas)
            # Preserve original whitespace around the type
            prefix = token[: len(token) - len(token.lstrip())]
            suffix = token[len(token.rstrip()) :]
            result_parts.append(prefix + normalized + suffix)

    return "".join(result_parts)


@dataclass
class InertiaPageMetadata:
    """Metadata for a single Inertia page component."""

    component: str
    route_path: str
    props_type: str | None = None
    schema_ref: str | None = None
    handler_name: str | None = None
    ts_type: str | None = None
    custom_types: list[str] = field(default_factory=str_list_factory)


def get_return_type_name(handler: HTTPRouteHandler) -> "str | None":
    field_definition = handler.parsed_fn_signature.return_type
    excluded_types: tuple[type[Any], ...] = (NoneType, ASGIResponse)
    if field_definition.is_subclass_of(excluded_types):
        return None

    fn = handler.fn
    with suppress(AttributeError):
        return_annotation = fn.__annotations__.get("return")
        if isinstance(return_annotation, str) and return_annotation:
            return return_annotation

    raw = field_definition.raw
    if isinstance(raw, str):
        return raw
    if isinstance(raw, type):
        return raw.__name__
    origin: Any = None
    with suppress(AttributeError):
        origin = field_definition.origin
    if isinstance(origin, type):
        return origin.__name__
    return str(raw)


def get_openapi_schema_ref(
    handler: HTTPRouteHandler, openapi_schema: dict[str, Any] | None, route_path: str, method: str = "GET"
) -> "str | None":
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
    return cast("str | None", ref) if ref else None


def extract_inertia_component(handler: HTTPRouteHandler) -> str | None:
    opt = handler.opt or {}
    component = opt.get("component") or opt.get("page")
    return component if isinstance(component, str) and component else None


def infer_inertia_props_type(
    component: str,
    handler: HTTPRouteHandler,
    schema_creator: Any,
    page_schema_keys: dict[str, tuple[str, ...]],
    page_schema_dicts: dict[str, dict[str, Any]],
    *,
    fallback_type: str,
) -> str | None:
    if schema_creator is not None:
        field_def, schema_result = resolve_page_props_field_definition(handler, schema_creator)
        if field_def is not None and isinstance(schema_result, Reference):
            page_schema_keys[component] = _get_normalized_schema_key(field_def)
            return None
        if isinstance(schema_result, Schema):
            schema_dict = schema_result.to_schema()
            page_schema_dicts[component] = schema_dict
            return ts_type_from_openapi(schema_dict)
        return None

    raw_type = get_return_type_name(handler)
    if not raw_type:
        return None
    props_type, _ = python_type_to_typescript(raw_type, fallback=fallback_type)
    return props_type


def finalize_inertia_pages(
    pages: list[InertiaPageMetadata],
    *,
    openapi_support: OpenAPISupport,
    page_schema_keys: dict[str, tuple[str, ...]],
    page_schema_dicts: dict[str, dict[str, Any]],
) -> None:
    context = openapi_support.context
    if context is None:
        return

    generated_components = context.schema_registry.generate_components_schemas()
    name_map = build_schema_name_map(context.schema_registry)
    openapi_components = openapi_components_schemas(openapi_support.openapi_schema)

    # Build set of available OpenAPI schema names for type normalization
    openapi_schema_names: set[str] = set(openapi_components.keys())
    openapi_schema_names.update(generated_components.keys())

    if openapi_support.openapi_schema is not None:
        merge_generated_components_into_openapi(openapi_support.openapi_schema, generated_components)

    for page in pages:
        schema_key = page_schema_keys.get(page.component)

        schema_name: str | None = None
        if page.schema_ref:
            schema_name = schema_name_from_ref(page.schema_ref)
        elif schema_key:
            schema_name = name_map.get(schema_key)

        if schema_name:
            # Normalize mangled type names (e.g., 'app_lib_schema_NoProps' -> 'NoProps')
            normalized_name = normalize_type_name(schema_name, openapi_schema_names)
            page.ts_type = normalized_name
            page.props_type = normalized_name
        elif page.props_type:
            # Normalize type names in union/intersection type strings
            # (e.g., 'any | app_lib_schema_NoProps' -> 'any | NoProps')
            page.props_type = normalize_type_string(page.props_type, openapi_schema_names)

        custom_types: set[str] = set()
        if page.ts_type:
            custom_types.add(page.ts_type)

        if page.schema_ref:
            openapi_schema_dict = openapi_components.get(page.ts_type or "")
            if isinstance(openapi_schema_dict, dict):
                custom_types.update(collect_ref_names(openapi_schema_dict))
        else:
            page_schema_dict = page_schema_dicts.get(page.component)
            if isinstance(page_schema_dict, dict):
                custom_types.update(collect_ref_names(page_schema_dict))
            elif schema_key:
                registered = context.schema_registry._schema_key_map.get(  # pyright: ignore[reportPrivateUsage]
                    schema_key
                )
                if registered:
                    custom_types.update(collect_ref_names(registered.schema.to_schema()))

        # Normalize all custom type names
        page.custom_types = sorted(normalize_type_name(t, openapi_schema_names) for t in custom_types)


def extract_inertia_pages(
    app: "Litestar",
    *,
    openapi_schema: dict[str, Any] | None = None,
    fallback_type: "str" = "unknown",
    openapi_support: OpenAPISupport | None = None,
) -> list[InertiaPageMetadata]:
    """Extract Inertia page metadata from an application.

    When multiple handlers map to the same component, GET handlers are preferred
    since Inertia pages are typically loaded via GET requests.

    Args:
        app: Litestar application instance.
        openapi_schema: Optional OpenAPI schema dict.
        fallback_type: TypeScript fallback type for unknown types.
        openapi_support: Optional shared OpenAPISupport instance. If not provided,
            a new one will be created. Sharing improves determinism and performance.

    Returns:
        List of InertiaPageMetadata for each discovered page.
    """
    # Track seen components: component -> (metadata, is_get_handler)
    # When multiple handlers map to the same component, prefer GET handlers
    seen_components: dict[str, tuple[InertiaPageMetadata, bool]] = {}

    if openapi_support is None:
        openapi_support = OpenAPISupport.from_app(app, openapi_schema)

    page_schema_keys: dict[str, tuple[str, ...]] = {}
    page_schema_dicts: dict[str, dict[str, Any]] = {}

    for http_route, route_handler in iter_route_handlers(app):
        component = extract_inertia_component(route_handler)
        if not component:
            continue

        normalized_path = normalize_path(str(http_route.path))
        handler_name = route_handler.handler_name or route_handler.name
        is_get_handler = "GET" in (route_handler.http_methods or set())

        props_type = infer_inertia_props_type(
            component,
            route_handler,
            openapi_support.schema_creator,
            page_schema_keys,
            page_schema_dicts,
            fallback_type=fallback_type,
        )

        method = _pick_inertia_method(route_handler.http_methods)
        schema_ref = get_openapi_schema_ref(route_handler, openapi_schema, normalized_path, method=str(method))

        page_metadata = InertiaPageMetadata(
            component=component,
            route_path=normalized_path,
            props_type=props_type,
            schema_ref=schema_ref,
            handler_name=handler_name,
        )

        # Prefer GET handlers when multiple handlers map to the same component
        existing = seen_components.get(component)
        if existing is None:
            seen_components[component] = (page_metadata, is_get_handler)
        elif is_get_handler and not existing[1]:
            # New handler is GET, existing is not - prefer the GET handler
            seen_components[component] = (page_metadata, is_get_handler)
        # Otherwise keep existing (it's either GET or we prefer first-seen for determinism)

    pages = [entry[0] for entry in seen_components.values()]

    if openapi_support.enabled:
        finalize_inertia_pages(
            pages,
            openapi_support=openapi_support,
            page_schema_keys=page_schema_keys,
            page_schema_dicts=page_schema_dicts,
        )

    return pages


def iter_route_handlers(app: "Litestar") -> "list[tuple[HTTPRoute, HTTPRouteHandler]]":
    """Iterate over HTTP route handlers in an app.

    Returns a deterministically sorted list to ensure consistent output
    across multiple runs. Handlers are sorted by (route_path, handler_name).

    Returns:
        A list of (http_route, route_handler) tuples, sorted for determinism.
    """
    handlers: list[tuple[HTTPRoute, HTTPRouteHandler]] = []
    for route in app.routes:
        if isinstance(route, HTTPRoute):
            handlers.extend((route, route_handler) for route_handler in route.route_handlers)
    # Sort by route path, then handler name for deterministic ordering
    return sorted(handlers, key=lambda x: (str(x[0].path), x[1].handler_name or x[1].name or ""))


def get_fallback_ts_type(types_config: "TypeGenConfig | None") -> str:
    fallback_type = types_config.fallback_type if types_config is not None else "unknown"
    return "any" if fallback_type == "any" else "unknown"


def ts_type_from_value(value: Any, *, fallback_ts_type: str) -> str:
    ts_type = fallback_ts_type
    if value is None:
        ts_type = "null"
    elif isinstance(value, bool):
        ts_type = "boolean"
    elif isinstance(value, str):
        ts_type = "string"
    elif isinstance(value, (int, float)):
        ts_type = "number"
    elif isinstance(value, (bytes, bytearray, Path)):
        ts_type = "string"
    elif isinstance(value, (list, tuple, set, frozenset)):
        ts_type = f"{fallback_ts_type}[]"
    elif isinstance(value, dict):
        ts_type = f"Record<string, {fallback_ts_type}>"
    return ts_type


def should_register_value_schema(value: Any) -> bool:
    if value is None:
        return False
    return not isinstance(value, (bool, str, int, float, bytes, bytearray, Path, list, tuple, set, frozenset, dict))


def process_session_props(
    session_props: "set[str] | dict[str, type]",
    shared_props: dict[str, dict[str, Any]],
    shared_schema_keys: dict[str, tuple[str, ...]],
    openapi_support: OpenAPISupport,
    fallback_ts_type: str,
) -> None:
    """Process session props and add them to shared_props.

    Handles both set[str] (legacy) and dict[str, type] (new typed) formats.
    """
    if isinstance(session_props, dict):
        # New behavior: dict maps prop names to Python types
        for key, prop_type_class in session_props.items():
            if not key:
                continue
            # Register the type with OpenAPI if possible
            if openapi_support.enabled and openapi_support.schema_creator:
                try:
                    field_def = FieldDefinition.from_annotation(prop_type_class)
                    schema_result = openapi_support.schema_creator.for_field_definition(field_def)
                    if isinstance(schema_result, Reference):
                        shared_schema_keys[key] = _get_normalized_schema_key(field_def)
                    type_name = prop_type_class.__name__ if hasattr(prop_type_class, "__name__") else fallback_ts_type
                    shared_props.setdefault(key, {"type": type_name, "optional": True})
                except (AttributeError, TypeError, ValueError):  # pragma: no cover - defensive
                    shared_props.setdefault(key, {"type": fallback_ts_type, "optional": True})
            else:
                type_name = prop_type_class.__name__ if hasattr(prop_type_class, "__name__") else fallback_ts_type
                shared_props.setdefault(key, {"type": type_name, "optional": True})
    else:
        # Legacy behavior: set of prop names (types are unknown)
        for key in session_props:
            if not key:
                continue
            shared_props.setdefault(key, {"type": fallback_ts_type, "optional": True})


def build_inertia_shared_props(
    app: "Litestar",
    *,
    openapi_schema: dict[str, Any] | None,
    include_default_auth: bool,
    include_default_flash: bool,
    inertia_config: "InertiaConfig | None",
    types_config: "TypeGenConfig | None",
    openapi_support: OpenAPISupport | None = None,
) -> dict[str, dict[str, Any]]:
    """Build shared props metadata (built-ins + configured props).

    Args:
        app: Litestar application instance.
        openapi_schema: Optional OpenAPI schema dict.
        include_default_auth: Include default auth shared prop.
        include_default_flash: Include default flash shared prop.
        inertia_config: Optional Inertia configuration.
        types_config: Optional type generation configuration.
        openapi_support: Optional shared OpenAPISupport instance. If not provided,
            a new one will be created. Sharing improves determinism and performance.

    Returns:
        Mapping of shared prop name to metadata payload.
    """
    fallback_ts_type = get_fallback_ts_type(types_config)

    shared_props: dict[str, dict[str, Any]] = {
        "errors": {"type": "Record<string, string[]>", "optional": True},
        "csrf_token": {"type": "string", "optional": True},
    }

    if include_default_auth or include_default_flash:
        shared_props["auth"] = {"type": "AuthData", "optional": True}
        shared_props["flash"] = {"type": "FlashMessages", "optional": True}

    if inertia_config is None:
        return shared_props

    if openapi_support is None:
        openapi_support = OpenAPISupport.from_app(app, openapi_schema)
    shared_schema_keys: dict[str, tuple[str, ...]] = {}

    for key, value in inertia_config.extra_static_page_props.items():
        if not key:
            continue

        shared_props[key] = {"type": ts_type_from_value(value, fallback_ts_type=fallback_ts_type), "optional": True}

        if openapi_support.enabled and isinstance(openapi_schema, dict) and should_register_value_schema(value):
            try:
                field_def = FieldDefinition.from_annotation(value.__class__)
                schema_result = openapi_support.schema_creator.for_field_definition(field_def)  # type: ignore[union-attr]
                if isinstance(schema_result, Reference):
                    shared_schema_keys[key] = _get_normalized_schema_key(field_def)
            except (AttributeError, TypeError, ValueError):  # pragma: no cover - defensive
                pass

    # Handle session props - can be set[str] or dict[str, type]
    process_session_props(
        inertia_config.extra_session_page_props, shared_props, shared_schema_keys, openapi_support, fallback_ts_type
    )

    if not (
        openapi_support.context
        and openapi_support.schema_creator
        and isinstance(openapi_schema, dict)
        and shared_schema_keys
    ):
        return shared_props

    generated_components = openapi_support.context.schema_registry.generate_components_schemas()
    name_map = build_schema_name_map(openapi_support.context.schema_registry)
    merge_generated_components_into_openapi(openapi_schema, generated_components)

    for prop_name, schema_key in shared_schema_keys.items():
        type_name = name_map.get(schema_key)
        if type_name:
            shared_props[prop_name]["type"] = type_name

    return shared_props


def generate_inertia_pages_json(
    app: "Litestar",
    *,
    openapi_schema: dict[str, Any] | None = None,
    include_default_auth: bool = True,
    include_default_flash: bool = True,
    inertia_config: "InertiaConfig | None" = None,
    types_config: "TypeGenConfig | None" = None,
) -> dict[str, Any]:
    """Generate Inertia pages metadata JSON.

    The output is deterministic: all dict keys are sorted alphabetically
    to produce byte-identical output for the same input data.

    A single OpenAPISupport instance is shared across both page extraction and
    shared props building to ensure consistent schema registration and naming.
    This eliminates non-determinism from split schema registries.

    Returns:
        An Inertia pages metadata payload as a dictionary with sorted keys.
    """
    # Create a single OpenAPISupport instance to share across the entire pipeline.
    # This ensures consistent schema registration and prevents "split-brain" issues
    # where separate registries could produce different schema names.
    openapi_support = OpenAPISupport.from_app(app, openapi_schema)

    pages_metadata = extract_inertia_pages(
        app,
        openapi_schema=openapi_schema,
        fallback_type=types_config.fallback_type if types_config is not None else "unknown",
        openapi_support=openapi_support,
    )

    pages_dict: dict[str, dict[str, Any]] = {}
    for page in pages_metadata:
        page_data: dict[str, Any] = {"route": page.route_path}
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

    shared_props = build_inertia_shared_props(
        app,
        openapi_schema=openapi_schema,
        include_default_auth=include_default_auth,
        include_default_flash=include_default_flash,
        inertia_config=inertia_config,
        types_config=types_config,
        openapi_support=openapi_support,
    )

    # Sort all dict keys for deterministic output
    # Pages sorted by component name, shared props sorted by prop name
    sorted_pages = dict(sorted(pages_dict.items()))
    sorted_shared_props = dict(sorted(shared_props.items()))

    root: dict[str, Any] = {
        "fallbackType": types_config.fallback_type if types_config is not None else None,
        "pages": sorted_pages,
        "sharedProps": sorted_shared_props,
        "typeGenConfig": {"includeDefaultAuth": include_default_auth, "includeDefaultFlash": include_default_flash},
        "typeImportPaths": types_config.type_import_paths if types_config is not None else None,
    }

    # Remove None values for cleaner output
    return {k: v for k, v in root.items() if v is not None}
