"""Inertia page-props metadata extraction and export."""

import datetime
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

from litestar_vite._codegen.openapi import (
    OpenAPISupport,
    build_schema_name_map,
    merge_generated_components_into_openapi,
    openapi_components_schemas,
    resolve_page_props_field_definition,
    schema_name_from_ref,
)
from litestar_vite._codegen.ts import collect_ref_names, normalize_path, python_type_to_typescript, ts_type_from_openapi

if TYPE_CHECKING:
    from litestar import Litestar

    from litestar_vite.config import InertiaConfig, TypeGenConfig


def _str_list_factory() -> list[str]:
    """Return an empty ``list[str]`` (typed for pyright).

    Returns:
        An empty list.
    """
    return []


@dataclass
class InertiaPageMetadata:
    """Metadata for a single Inertia page component."""

    component: str
    route_path: str
    props_type: str | None = None
    schema_ref: str | None = None
    handler_name: str | None = None
    ts_type: str | None = None
    custom_types: list[str] = field(default_factory=_str_list_factory)


def _get_return_type_name(handler: HTTPRouteHandler) -> "str | None":
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


def _get_openapi_schema_ref(
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


def _extract_inertia_component(handler: HTTPRouteHandler) -> str | None:
    opt = handler.opt or {}
    component = opt.get("component") or opt.get("page")
    return component if isinstance(component, str) and component else None


def _infer_inertia_props_type(
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

    raw_type = _get_return_type_name(handler)
    if not raw_type:
        return None
    props_type, _ = python_type_to_typescript(raw_type, fallback=fallback_type)
    return props_type


def _finalize_inertia_pages(
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
            page.ts_type = schema_name
            page.props_type = schema_name

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

        page.custom_types = sorted(custom_types)


def extract_inertia_pages(
    app: "Litestar", *, openapi_schema: dict[str, Any] | None = None, fallback_type: "str" = "unknown"
) -> list[InertiaPageMetadata]:
    pages: list[InertiaPageMetadata] = []

    openapi_support = OpenAPISupport.from_app(app, openapi_schema)

    page_schema_keys: dict[str, tuple[str, ...]] = {}
    page_schema_dicts: dict[str, dict[str, Any]] = {}

    for http_route, route_handler in _iter_route_handlers(app):
        component = _extract_inertia_component(route_handler)
        if not component:
            continue

        normalized_path = normalize_path(str(http_route.path))
        handler_name = route_handler.handler_name or route_handler.name

        props_type = _infer_inertia_props_type(
            component,
            route_handler,
            openapi_support.schema_creator,
            page_schema_keys,
            page_schema_dicts,
            fallback_type=fallback_type,
        )

        method = next(iter(route_handler.http_methods), "GET") if route_handler.http_methods else "GET"
        schema_ref = _get_openapi_schema_ref(route_handler, openapi_schema, normalized_path, method=str(method))

        pages.append(
            InertiaPageMetadata(
                component=component,
                route_path=normalized_path,
                props_type=props_type,
                schema_ref=schema_ref,
                handler_name=handler_name,
            )
        )

    if openapi_support.enabled:
        _finalize_inertia_pages(
            pages,
            openapi_support=openapi_support,
            page_schema_keys=page_schema_keys,
            page_schema_dicts=page_schema_dicts,
        )

    return pages


def _iter_route_handlers(app: "Litestar") -> "list[tuple[HTTPRoute, HTTPRouteHandler]]":
    """Iterate over HTTP route handlers in an app.

    Returns:
        A list of (http_route, route_handler) tuples.
    """
    handlers: list[tuple[HTTPRoute, HTTPRouteHandler]] = []
    for route in app.routes:
        if isinstance(route, HTTPRoute):
            handlers.extend((route, route_handler) for route_handler in route.route_handlers)
    return handlers


def _fallback_ts_type(types_config: "TypeGenConfig | None") -> str:
    fallback_type = types_config.fallback_type if types_config is not None else "unknown"
    return "any" if fallback_type == "any" else "unknown"


def _ts_type_from_value(value: Any, *, fallback_ts_type: str) -> str:
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


def _should_register_value_schema(value: Any) -> bool:
    if value is None:
        return False
    return not isinstance(value, (bool, str, int, float, bytes, bytearray, Path, list, tuple, set, frozenset, dict))


def _build_inertia_shared_props(
    app: "Litestar",
    *,
    openapi_schema: dict[str, Any] | None,
    include_default_auth: bool,
    include_default_flash: bool,
    inertia_config: "InertiaConfig | None",
    types_config: "TypeGenConfig | None",
) -> dict[str, dict[str, Any]]:
    """Build shared props metadata (built-ins + configured props).

    Returns:
        Mapping of shared prop name to metadata payload.
    """
    fallback_ts_type = _fallback_ts_type(types_config)

    shared_props: dict[str, dict[str, Any]] = {
        "errors": {"type": "Record<string, string[]>", "optional": True},
        "csrf_token": {"type": "string", "optional": True},
    }

    if include_default_auth or include_default_flash:
        shared_props["auth"] = {"type": "AuthData", "optional": True}
        shared_props["flash"] = {"type": "FlashMessages", "optional": True}

    if inertia_config is None:
        return shared_props

    openapi_support = OpenAPISupport.from_app(app, openapi_schema)
    shared_schema_keys: dict[str, tuple[str, ...]] = {}

    for key, value in inertia_config.extra_static_page_props.items():
        if not key:
            continue

        shared_props[key] = {"type": _ts_type_from_value(value, fallback_ts_type=fallback_ts_type), "optional": True}

        if openapi_support.enabled and isinstance(openapi_schema, dict) and _should_register_value_schema(value):
            try:
                field_def = FieldDefinition.from_annotation(value.__class__)
                schema_result = openapi_support.schema_creator.for_field_definition(field_def)  # type: ignore[union-attr]
                if isinstance(schema_result, Reference):
                    shared_schema_keys[key] = _get_normalized_schema_key(field_def)
            except (AttributeError, TypeError, ValueError):  # pragma: no cover - defensive
                pass

    for key in inertia_config.extra_session_page_props:
        if not key:
            continue
        shared_props.setdefault(key, {"type": fallback_ts_type, "optional": True})

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

    Returns:
        An Inertia pages metadata payload as a dictionary.
    """
    pages_metadata = extract_inertia_pages(
        app,
        openapi_schema=openapi_schema,
        fallback_type=types_config.fallback_type if types_config is not None else "unknown",
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

    shared_props = _build_inertia_shared_props(
        app,
        openapi_schema=openapi_schema,
        include_default_auth=include_default_auth,
        include_default_flash=include_default_flash,
        inertia_config=inertia_config,
        types_config=types_config,
    )

    root: dict[str, Any] = {
        "pages": pages_dict,
        "sharedProps": shared_props,
        "typeGenConfig": {"includeDefaultAuth": include_default_auth, "includeDefaultFlash": include_default_flash},
        "generatedAt": datetime.datetime.now(tz=datetime.timezone.utc).isoformat(),
    }

    if types_config is not None:
        root["typeImportPaths"] = types_config.type_import_paths
        root["fallbackType"] = types_config.fallback_type

    return root
