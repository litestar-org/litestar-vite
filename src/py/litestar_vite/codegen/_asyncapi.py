"""AsyncAPI 3.0 document models and WebSocket route introspection for Litestar.

This module provides data models for AsyncAPI 3.0.0 specifications and utilities
to introspect Litestar WebSocket routes and listeners into structured channels
and operations.
"""

import contextlib
import re
import types
from dataclasses import asdict, dataclass, field
from types import UnionType
from typing import TYPE_CHECKING, Any, Union, cast, get_args, get_origin

from litestar.channels import ChannelsPlugin
from litestar.handlers import WebsocketListenerRouteHandler
from litestar.openapi.spec import Reference
from litestar.response import ServerSentEvent
from litestar.routes import HTTPRoute, WebSocketRoute
from litestar.types.builtin_types import NoneType
from litestar.typing import FieldDefinition

from litestar_vite.codegen._openapi import (
    OpenAPISupport,
    asyncapi_schema_from_result,
    build_schema_name_map,
    resolve_handler_field_schema,
)
from litestar_vite.codegen._routes import extract_path_params
from litestar_vite.codegen._ts import normalize_path

if not getattr(ServerSentEvent, "__parameters__", None):

    def _sse_class_getitem(cls: type[Any], item: Any) -> types.GenericAlias:
        return types.GenericAlias(cls, item)

    setattr(ServerSentEvent, "__class_getitem__", classmethod(_sse_class_getitem))

if TYPE_CHECKING:
    from litestar import Litestar


ASYNCAPI_PAYLOAD_OPT_KEY = "asyncapi_event_payload"
_PRESERVED_SUBTREE_KEYS = frozenset({"payload", "bindings", "schemas"})


def _clean_dict(d: dict[str, Any]) -> dict[str, Any]:
    """Recursively remove None values and empty collections from a dictionary.

    Metadata keys are pruned for compactness. Keys present in
    _PRESERVED_SUBTREE_KEYS (such as payload, bindings, and schemas) are
    spec-significant JSON Schema or protocol structures where empty dictionaries
    and lists carry semantic meaning and must round-trip byte-for-byte.

    Args:
        d: The dictionary to clean.

    Returns:
        A cleaned dictionary with non-empty values, preserving spec-significant
        subtrees verbatim when non-None.
    """
    cleaned: dict[str, Any] = {}
    for key, value in d.items():
        if value is None:
            continue
        if key in _PRESERVED_SUBTREE_KEYS:
            cleaned[key] = value
        elif isinstance(value, dict):
            typed_dict = cast("dict[str, Any]", value)
            sub_dict = _clean_dict(typed_dict)
            if sub_dict:
                cleaned[key] = sub_dict
        elif isinstance(value, list):
            sub_list: list[Any] = []
            typed_list = cast("list[Any]", value)
            for item in typed_list:
                if item is None:
                    continue
                if isinstance(item, dict):
                    typed_item = cast("dict[str, Any]", item)
                    sub_list.append(_clean_dict(typed_item))
                else:
                    sub_list.append(item)
            if sub_list:
                cleaned[key] = sub_list
        else:
            cleaned[key] = value
    return cleaned


@dataclass(slots=True)
class AsyncAPIInfo:
    """AsyncAPI 3.0 Info Object."""

    title: str
    version: str
    description: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert the info object to a dictionary.

        Returns:
            Dictionary representation of the info object.
        """
        return _clean_dict(asdict(self))


@dataclass(slots=True)
class AsyncAPIServer:
    """AsyncAPI 3.0 Server Object."""

    host: str
    protocol: str
    protocol_version: str | None = None
    description: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert the server object to a dictionary.

        Returns:
            Dictionary representation of the server object.
        """
        res = {
            "host": self.host,
            "protocol": self.protocol,
            "protocolVersion": self.protocol_version,
            "description": self.description,
        }
        return _clean_dict(res)


@dataclass(slots=True)
class AsyncAPIParameter:
    """AsyncAPI 3.0 Parameter Object."""

    description: str | None = None
    enum: list[str] = field(default_factory=list[str])
    default: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert the parameter object to a dictionary.

        Returns:
            Dictionary representation of the parameter object.
        """
        return _clean_dict(asdict(self))


@dataclass(slots=True)
class AsyncAPIMessage:
    """AsyncAPI 3.0 Message Object."""

    name: str
    title: str | None = None
    summary: str | None = None
    description: str | None = None
    content_type: str = "application/json"
    payload: dict[str, Any] = field(default_factory=dict[str, Any])

    def to_dict(self) -> dict[str, Any]:
        """Convert the message object to a dictionary.

        Returns:
            Dictionary representation of the message object.
        """
        res = {
            "name": self.name,
            "title": self.title,
            "summary": self.summary,
            "description": self.description,
            "contentType": self.content_type,
            "payload": self.payload,
        }
        return _clean_dict(res)


@dataclass(slots=True)
class AsyncAPIChannel:
    """AsyncAPI 3.0 Channel Object."""

    address: str
    title: str | None = None
    summary: str | None = None
    description: str | None = None
    parameters: dict[str, AsyncAPIParameter] = field(default_factory=dict[str, AsyncAPIParameter])
    messages: dict[str, AsyncAPIMessage] = field(default_factory=dict[str, AsyncAPIMessage])
    bindings: dict[str, Any] = field(default_factory=dict[str, Any])

    def to_dict(self) -> dict[str, Any]:
        """Convert the channel object to a dictionary.

        Returns:
            Dictionary representation of the channel object.
        """
        res: dict[str, Any] = {
            "address": self.address,
            "title": self.title,
            "summary": self.summary,
            "description": self.description,
            "parameters": {k: v.to_dict() for k, v in self.parameters.items()},
            "messages": {k: v.to_dict() for k, v in self.messages.items()},
            "bindings": self.bindings,
        }
        return _clean_dict(res)


@dataclass(slots=True)
class AsyncAPIOperation:
    """AsyncAPI 3.0 Operation Object."""

    action: str
    channel: dict[str, str]
    title: str | None = None
    summary: str | None = None
    description: str | None = None
    messages: list[dict[str, str]] = field(default_factory=list[dict[str, str]])

    def to_dict(self) -> dict[str, Any]:
        """Convert the operation object to a dictionary.

        Returns:
            Dictionary representation of the operation object.
        """
        return _clean_dict(asdict(self))


@dataclass(slots=True)
class AsyncAPIComponents:
    """AsyncAPI 3.0 Components Object."""

    messages: dict[str, AsyncAPIMessage] = field(default_factory=dict[str, AsyncAPIMessage])
    schemas: dict[str, Any] = field(default_factory=dict[str, Any])
    parameters: dict[str, AsyncAPIParameter] = field(default_factory=dict[str, AsyncAPIParameter])

    def to_dict(self) -> dict[str, Any]:
        """Convert the components object to a dictionary.

        Returns:
            Dictionary representation of the components object.
        """
        res: dict[str, Any] = {
            "messages": {k: v.to_dict() for k, v in self.messages.items()},
            "schemas": self.schemas,
            "parameters": {k: v.to_dict() for k, v in self.parameters.items()},
        }
        return _clean_dict(res)


@dataclass(slots=True)
class AsyncAPIDocument:
    """Root AsyncAPI 3.0 Document."""

    info: AsyncAPIInfo
    asyncapi: str = "3.0.0"
    id: str | None = None
    servers: dict[str, AsyncAPIServer] = field(default_factory=dict[str, AsyncAPIServer])
    channels: dict[str, AsyncAPIChannel] = field(default_factory=dict[str, AsyncAPIChannel])
    operations: dict[str, AsyncAPIOperation] = field(default_factory=dict[str, AsyncAPIOperation])
    components: AsyncAPIComponents | None = None

    def to_dict(self) -> dict[str, Any]:
        """Serialize the complete document to an AsyncAPI 3.0 specification dictionary.

        Returns:
            Deterministic dictionary representation of the AsyncAPI 3.0 specification.
        """
        data: dict[str, Any] = {"asyncapi": self.asyncapi, "info": self.info.to_dict()}
        if self.id is not None:
            data["id"] = self.id
        if self.servers:
            data["servers"] = {k: v.to_dict() for k, v in self.servers.items()}
        if self.channels:
            data["channels"] = {k: v.to_dict() for k, v in self.channels.items()}
        if self.operations:
            data["operations"] = {k: v.to_dict() for k, v in self.operations.items()}
        if self.components is not None:
            comp_dict = self.components.to_dict()
            if comp_dict:
                data["components"] = comp_dict
        return data


_SCALAR_SCHEMA_MAP: dict[Any, dict[str, Any]] = {
    str: {"type": "string"},
    "str": {"type": "string"},
    int: {"type": "integer"},
    "int": {"type": "integer"},
    float: {"type": "number"},
    "float": {"type": "number"},
    bool: {"type": "boolean"},
    "bool": {"type": "boolean"},
    bytes: {"type": "string", "contentMediaType": "application/octet-stream"},
    "bytes": {"type": "string", "contentMediaType": "application/octet-stream"},
    dict: {"type": "object", "additionalProperties": {}},
    "dict": {"type": "object", "additionalProperties": {}},
    list: {"type": "array", "items": {}},
    "list": {"type": "array", "items": {}},
}


def _rewrite_schema_refs(obj: Any) -> Any:
    """Rewrite schema reference paths from defs to AsyncAPI components.

    Args:
        obj: JSON Schema fragment or collection to rewrite.

    Returns:
        The rewritten JSON Schema structure.
    """
    defs_prefix = "#/$defs/"
    legacy_prefix = "#/definitions/"
    if isinstance(obj, dict):
        typed_dict = cast("dict[str, Any]", obj)
        result: dict[str, Any] = {}
        for key, value in typed_dict.items():
            if key == "$ref" and isinstance(value, str):
                if value.startswith(defs_prefix):
                    result[key] = f"#/components/schemas/{value[len(defs_prefix) :]}"
                elif value.startswith(legacy_prefix):
                    result[key] = f"#/components/schemas/{value[len(legacy_prefix) :]}"
                else:
                    result[key] = value
            else:
                result[key] = _rewrite_schema_refs(value)
        return result
    if isinstance(obj, list):
        typed_list = cast("list[Any]", obj)
        return [_rewrite_schema_refs(item) for item in typed_list]
    return obj


def _extract_union_schema(args: tuple[Any, ...], components_schemas: dict[str, Any] | None) -> dict[str, Any]:
    """Extract JSON Schema for Union or UnionType annotations.

    Args:
        args: Type arguments of the Union.
        components_schemas: Optional dictionary to collect named component schemas.

    Returns:
        JSON Schema representation of the union.
    """
    union_args = [arg for arg in args if arg not in (None, NoneType)]
    has_null = len(union_args) < len(args)
    if len(union_args) == 1:
        base_schema = extract_payload_schema(union_args[0], components_schemas)
        if has_null:
            return {"anyOf": [base_schema, {"type": "null"}]}
        return base_schema
    schemas = [extract_payload_schema(arg, components_schemas) for arg in union_args]
    if has_null:
        schemas.append({"type": "null"})
    return {"anyOf": schemas}


def _extract_container_schema(
    origin: Any, annotation: Any, components_schemas: dict[str, Any] | None
) -> dict[str, Any] | None:
    """Extract JSON Schema for list or dict container types.

    Args:
        origin: The typing origin type.
        annotation: The full type annotation.
        components_schemas: Optional dictionary to collect named component schemas.

    Returns:
        JSON Schema representation or None if not a supported container.
    """
    if origin is list or annotation in (list, "list"):
        args = get_args(annotation)
        items_schema = extract_payload_schema(args[0], components_schemas) if args else {}
        return {"type": "array", "items": items_schema}
    if origin is dict or annotation in (dict, "dict"):
        args = get_args(annotation)
        val_schema = extract_payload_schema(args[1], components_schemas) if len(args) > 1 else {}
        return {"type": "object", "additionalProperties": val_schema}
    return None


def _extract_msgspec_schema(annotation: Any, components_schemas: dict[str, Any] | None) -> dict[str, Any] | None:
    """Extract JSON Schema for msgspec Structs, dataclasses, TypedDicts, and Enums.

    Args:
        annotation: Python type to introspect with msgspec.
        components_schemas: Optional dictionary to collect named component schemas.

    Returns:
        JSON Schema structure or None if introspection fails.
    """
    defs_prefix = "#/$defs/"
    try:
        import msgspec

        raw_schema = msgspec.json.schema(annotation)
        defs = raw_schema.get("$defs", {})
        if components_schemas is not None:
            for name, def_schema in defs.items():
                if name not in components_schemas:
                    components_schemas[name] = _rewrite_schema_refs(def_schema)
            model_name = getattr(annotation, "__name__", None)
            if model_name and model_name in components_schemas:
                return {"$ref": f"#/components/schemas/{model_name}"}
            ref = raw_schema.get("$ref")
            if ref and isinstance(ref, str) and ref.startswith(defs_prefix):
                return {"$ref": f"#/components/schemas/{ref[len(defs_prefix) :]}"}
        return cast("dict[str, Any]", _rewrite_schema_refs(raw_schema))
    except (TypeError, ValueError, AttributeError):
        return None


def _extract_pydantic_schema(annotation: Any, components_schemas: dict[str, Any] | None) -> dict[str, Any] | None:
    """Extract JSON Schema for Pydantic v1 and v2 models.

    Args:
        annotation: Potential Pydantic model type.
        components_schemas: Optional dictionary to collect named component schemas.

    Returns:
        JSON Schema structure or None if not a Pydantic model.
    """
    if not isinstance(annotation, type):
        return None
    model_json_schema_attr = getattr(annotation, "model_json_schema", None)
    if callable(model_json_schema_attr):
        callable_v2 = cast("Any", model_json_schema_attr)
        pydantic_v2_schema = cast("dict[str, Any]", callable_v2())
        defs = cast("dict[str, Any]", pydantic_v2_schema.pop("$defs", {}))
        model_name = annotation.__name__
        if components_schemas is not None:
            for def_name, def_body in defs.items():
                if def_name not in components_schemas:
                    components_schemas[def_name] = _rewrite_schema_refs(def_body)
            components_schemas[model_name] = _rewrite_schema_refs(pydantic_v2_schema)
            return {"$ref": f"#/components/schemas/{model_name}"}
        return cast("dict[str, Any]", _rewrite_schema_refs(pydantic_v2_schema))
    schema_attr = getattr(annotation, "schema", None)
    if callable(schema_attr):
        callable_v1 = cast("Any", schema_attr)
        pydantic_v1_schema = cast("dict[str, Any]", callable_v1())
        defs = cast("dict[str, Any]", pydantic_v1_schema.pop("definitions", {}))
        model_name = annotation.__name__
        if components_schemas is not None:
            for def_name, def_body in defs.items():
                if def_name not in components_schemas:
                    components_schemas[def_name] = _rewrite_schema_refs(def_body)
            components_schemas[model_name] = _rewrite_schema_refs(pydantic_v1_schema)
            return {"$ref": f"#/components/schemas/{model_name}"}
        return cast("dict[str, Any]", _rewrite_schema_refs(pydantic_v1_schema))
    return None


def extract_payload_schema(annotation: Any, components_schemas: dict[str, Any] | None = None) -> dict[str, Any]:
    """Convert a Python type annotation to a JSON Schema for AsyncAPI message payloads.

    Supports primitives, containers, unions, msgspec.Struct, dataclasses,
    Pydantic models, TypedDicts, and Enums. Registers complex schemas
    in components_schemas when provided.

    Args:
        annotation: The type annotation to convert.
        components_schemas: Optional dictionary to collect named component schemas.

    Returns:
        JSON Schema representation or $ref dictionary for the payload.
    """
    if annotation in (None, NoneType):
        schema = {"type": "null"}
    elif annotation in _SCALAR_SCHEMA_MAP:
        schema = _SCALAR_SCHEMA_MAP[annotation].copy()
    elif (origin := get_origin(annotation)) in (Union, UnionType):
        schema = _extract_union_schema(get_args(annotation), components_schemas)
    elif container_schema := _extract_container_schema(origin, annotation, components_schemas):
        schema = container_schema
    elif msgspec_schema := _extract_msgspec_schema(annotation, components_schemas):
        schema = msgspec_schema
    elif pydantic_schema := _extract_pydantic_schema(annotation, components_schemas):
        schema = pydantic_schema
    else:
        schema = {"type": "object"}
    return schema


_py_type_to_schema = extract_payload_schema


@dataclass(slots=True)
class AsyncAPISchemaContext:
    """Context for resolving AsyncAPI schemas with optional OpenAPI and DTO parity.

    When support is None or support.enabled is False, schema resolution selects
    the zero-dependency fallback path using extract_payload_schema.
    """

    support: OpenAPISupport | None = None
    components_schemas: dict[str, Any] = field(default_factory=dict[str, Any])
    deferred_references: list[tuple[dict[str, Any], Reference]] = field(
        default_factory=list[tuple[dict[str, Any], Reference]]
    )


def extract_field_schema(
    handler: Any,
    field_definition: Any,
    context: AsyncAPISchemaContext,
    *,
    dto_attribute: str,
) -> dict[str, Any]:
    """Extract schema dictionary for a handler field with DTO and OpenAPI parity.

    Args:
        handler: The route handler owning the field.
        field_definition: FieldDefinition or type annotation.
        context: AsyncAPISchemaContext carrying OpenAPI support and collections.
        dto_attribute: Attribute name for resolving the DTO ('resolve_dto' or 'resolve_return_dto').

    Returns:
        JSON Schema representation or $ref dictionary for the payload.
    """
    annotation = getattr(field_definition, "annotation", field_definition)
    if annotation in _SCALAR_SCHEMA_MAP:
        return _SCALAR_SCHEMA_MAP[annotation].copy()

    if context.support is not None and context.support.enabled and context.support.schema_creator is not None:
        try:
            actual_field = (
                field_definition
                if isinstance(field_definition, FieldDefinition)
                else FieldDefinition.from_annotation(field_definition)
            )
            result = resolve_handler_field_schema(
                handler, actual_field, context.support.schema_creator, dto_attribute=dto_attribute
            )
            converted = asyncapi_schema_from_result(result)
            if converted is not None:
                if isinstance(result, Reference):
                    context.deferred_references.append((converted, result))
                return converted
        except (AttributeError, TypeError, ValueError):
            pass

    return extract_payload_schema(annotation, context.components_schemas)


def _slug_segment(segment: str) -> str:
    """Sanitize a path segment for use in an AsyncAPI channel key.

    Path parameter segments shaped {name} or {name:converter} return 'p_' followed
    by the sanitized parameter name. Any other segment has every run of characters
    outside [A-Za-z0-9] replaced by a single underscore.

    Args:
        segment: Path segment string.

    Returns:
        Sanitized segment string.
    """
    if segment.startswith("{") and segment.endswith("}"):
        inner = segment[1:-1]
        name = inner.split(":", 1)[0]
        sanitized = re.sub(r"[^A-Za-z0-9]+", "_", name)
        return f"p_{sanitized}"
    return re.sub(r"[^A-Za-z0-9]+", "_", segment)


def _channel_key_base(normalized_address: str) -> str:
    """Build a deterministic base channel key from a route address.

    Strips the leading slash, splits on slash, drops empty segments, applies
    _slug_segment to each, and joins with double underscores. An empty result
    returns 'root'.

    Args:
        normalized_address: The normalized route path.

    Returns:
        Deterministic base channel key.
    """
    segments = [_slug_segment(s) for s in normalized_address.lstrip("/").split("/") if s]
    return "__".join(segments) or "root"


@dataclass(slots=True)
class _ChannelKeyAllocator:
    """Allocate collision-safe channel keys across realtime sources."""

    assigned: dict[tuple[str, str], str] = field(default_factory=dict[tuple[str, str], str])
    taken: set[str] = field(default_factory=set[str])

    def allocate(self, normalized_address: str, source: str) -> str:
        """Allocate a unique channel key for a given route address and source.

        Two different sources at the same address deliberately receive different
        channel keys to prevent collisions and ensure intact operations.

        Args:
            normalized_address: The normalized route address string.
            source: Realtime source identifier ('websocket', 'channels', or 'sse').

        Returns:
            Collision-safe unique channel key.
        """
        pair = (normalized_address, source)
        if pair in self.assigned:
            return self.assigned[pair]

        base = _channel_key_base(normalized_address)
        candidate = base
        counter = 2
        while candidate in self.taken:
            candidate = f"{base}_{counter}"
            counter += 1

        self.taken.add(candidate)
        self.assigned[pair] = candidate
        return candidate


def _allocate_operation_id(prefix: str, channel_key: str, taken: set[str]) -> str:
    """Allocate a unique operation id for a channel action.

    Args:
        prefix: Operation action prefix (e.g. 'receive', 'send', 'operate', 'stream').
        channel_key: The allocated channel key.
        taken: Set of already allocated operation ids.

    Returns:
        Collision-safe unique operation id.
    """
    base = f"{prefix}_{channel_key}"
    candidate = base
    counter = 2
    while candidate in taken:
        candidate = f"{base}_{counter}"
        counter += 1
    taken.add(candidate)
    return candidate


def _merge_channels(
    channels: dict[str, AsyncAPIChannel],
    operations: dict[str, AsyncAPIOperation],
    new_channels: dict[str, AsyncAPIChannel],
    new_operations: dict[str, AsyncAPIOperation],
) -> None:
    """Merge newly extracted channels and operations into existing collections.

    If an incoming channel key already exists in channels, any operations in
    operations referencing that channel key are removed before overwriting to
    prevent dangling references.

    Args:
        channels: Existing channels dictionary to mutate.
        operations: Existing operations dictionary to mutate.
        new_channels: New channels to add or overwrite.
        new_operations: New operations to add.
    """
    for key in new_channels:
        if key in channels:
            target_ref = f"#/channels/{key}"
            stale_ops = [op_id for op_id, op in operations.items() if op.channel.get("$ref") == target_ref]
            for op_id in stale_ops:
                operations.pop(op_id, None)
    channels.update(new_channels)
    operations.update(new_operations)


def _extract_websocket_route_details(
    route: WebSocketRoute,
    context: AsyncAPISchemaContext,
    allocator: _ChannelKeyAllocator,
    operation_ids: set[str],
) -> tuple[str, AsyncAPIChannel, dict[str, AsyncAPIOperation]] | None:
    """Extract channel and operation details from a single WebSocketRoute.

    Args:
        route: The WebSocketRoute to extract.
        context: Schema context coordinating OpenAPI and DTO support.
        allocator: Allocator for collision-safe channel keys.
        operation_ids: Registry for unique operation ids.

    Returns:
        Tuple of (channel_key, channel, operations), or None if skipped.
    """
    handler = getattr(route, "route_handler", None)
    fn = getattr(handler, "fn", None)
    if (fn is not None and getattr(fn, "__module__", "").startswith("litestar.channels")) or (
        hasattr(fn, "fn") and getattr(getattr(fn, "fn", None), "__module__", "").startswith("litestar.channels")
    ):
        return None

    raw_path = route.path
    normalized = normalize_path(raw_path)
    channel_key = allocator.allocate(normalized, "websocket")

    parameters: dict[str, AsyncAPIParameter] = {}
    for param_name in extract_path_params(raw_path):
        parameters[param_name] = AsyncAPIParameter(description=f"Path parameter {param_name}")

    handler_name = getattr(handler, "handler_name", None) or getattr(handler, "name", None)
    doc = getattr(fn, "__doc__", None) or getattr(handler, "__doc__", None)

    if fn is not None and hasattr(fn, "fn"):
        inner_fn = getattr(fn, "fn", None)
        doc = getattr(inner_fn, "__doc__", None) or doc
        if not handler_name:
            handler_name = getattr(inner_fn, "__name__", None)

    if not handler_name:
        handler_name = getattr(fn, "__name__", None) or f"{channel_key}_handler"

    channel_messages: dict[str, AsyncAPIMessage] = {}
    operations: dict[str, AsyncAPIOperation] = {}

    is_listener = isinstance(handler, WebsocketListenerRouteHandler)
    if is_listener:
        data_field = getattr(handler, "parsed_data_field", None)
        return_field = getattr(handler, "parsed_return_field", None)

        if data_field is not None and getattr(data_field, "annotation", None) is not None:
            inbound_msg_name = f"{channel_key}Inbound"
            inbound_payload = extract_field_schema(handler, data_field, context, dto_attribute="resolve_dto")
            channel_messages["inbound"] = AsyncAPIMessage(
                name=inbound_msg_name, title=f"{handler_name} Inbound Message", payload=inbound_payload
            )
            op_id = _allocate_operation_id("receive", channel_key, operation_ids)
            operations[op_id] = AsyncAPIOperation(
                action="receive",
                channel={"$ref": f"#/channels/{channel_key}"},
                summary=f"Receive inbound messages on {normalized}",
                description=doc,
                messages=[{"$ref": f"#/channels/{channel_key}/messages/inbound"}],
            )

        if return_field is not None and getattr(return_field, "annotation", None) not in (None, NoneType):
            outbound_msg_name = f"{channel_key}Outbound"
            outbound_payload = extract_field_schema(handler, return_field, context, dto_attribute="resolve_return_dto")
            channel_messages["outbound"] = AsyncAPIMessage(
                name=outbound_msg_name, title=f"{handler_name} Outbound Message", payload=outbound_payload
            )
            op_id = _allocate_operation_id("send", channel_key, operation_ids)
            operations[op_id] = AsyncAPIOperation(
                action="send",
                channel={"$ref": f"#/channels/{channel_key}"},
                summary=f"Send outbound messages on {normalized}",
                description=doc,
                messages=[{"$ref": f"#/channels/{channel_key}/messages/outbound"}],
            )
    else:
        default_msg_name = f"{channel_key}Message"
        channel_messages["message"] = AsyncAPIMessage(
            name=default_msg_name, title=f"{handler_name} Message", payload={"type": "string"}
        )
        op_id = _allocate_operation_id("operate", channel_key, operation_ids)
        operations[op_id] = AsyncAPIOperation(
            action="send",
            channel={"$ref": f"#/channels/{channel_key}"},
            summary=f"WebSocket operation on {normalized}",
            description=doc,
            messages=[{"$ref": f"#/channels/{channel_key}/messages/message"}],
        )

    channel = AsyncAPIChannel(
        address=normalized,
        title=f"{handler_name} Channel",
        summary=f"WebSocket channel at {normalized}",
        description=doc,
        parameters=parameters,
        messages=channel_messages,
    )

    return channel_key, channel, operations


def extract_websocket_routes(
    app: "Litestar",
    components_schemas: dict[str, Any] | None = None,
    *,
    context: AsyncAPISchemaContext | None = None,
    allocator: _ChannelKeyAllocator | None = None,
    operation_ids: set[str] | None = None,
) -> tuple[dict[str, AsyncAPIChannel], dict[str, AsyncAPIOperation]]:
    """Extract WebSocket routes from a Litestar application into AsyncAPI channels and operations.

    Args:
        app: The Litestar application instance.
        components_schemas: Optional dictionary to collect named component schemas.
        context: Optional schema context coordinating OpenAPI and DTO support.
        allocator: Optional allocator to ensure unique channel keys across sources.
        operation_ids: Optional set to ensure unique operation ids across sources.

    Returns:
        Tuple of (channels_mapping, operations_mapping).
    """
    if context is None:
        context = AsyncAPISchemaContext(
            components_schemas=components_schemas if components_schemas is not None else {}
        )
    elif components_schemas is not None and not context.components_schemas:
        context.components_schemas = components_schemas

    if allocator is None:
        allocator = _ChannelKeyAllocator()
    if operation_ids is None:
        operation_ids = set()

    channels: dict[str, AsyncAPIChannel] = {}
    operations: dict[str, AsyncAPIOperation] = {}

    for route in app.routes:
        if not isinstance(route, WebSocketRoute):
            continue
        details = _extract_websocket_route_details(route, context, allocator, operation_ids)
        if details is not None:
            key, channel, route_ops = details
            channels[key] = channel
            operations.update(route_ops)

    return channels, operations


def _opt_payload_annotation(handler: Any) -> Any:
    """Extract an explicit AsyncAPI payload annotation from route handler opt mapping.

    Args:
        handler: The route handler or websocket listener.

    Returns:
        The configured payload annotation or None if not specified.
    """
    opt: Any = getattr(handler, "opt", None)
    if isinstance(opt, dict):
        typed_opt = cast("dict[str, Any]", opt)
        return typed_opt.get(ASYNCAPI_PAYLOAD_OPT_KEY)
    fn: Any = getattr(handler, "fn", None)
    if fn is not None:
        fn_opt: Any = getattr(fn, "opt", None)
        if isinstance(fn_opt, dict):
            typed_fn_opt = cast("dict[str, Any]", fn_opt)
            return typed_fn_opt.get(ASYNCAPI_PAYLOAD_OPT_KEY)
    return None


def _sse_payload_annotation(annotation: Any) -> Any:
    """Unwrap a handler return annotation to find the stream element type.

    Args:
        annotation: Type annotation to inspect.

    Returns:
        The extracted model type or None if untyped or text-based.
    """
    if annotation is None or annotation is NoneType or annotation is ServerSentEvent:
        return None
    try:
        if isinstance(annotation, type) and issubclass(annotation, (ServerSentEvent, str, bytes)):
            return None
    except TypeError:
        pass

    origin = get_origin(annotation)
    if origin is not None:
        for arg in get_args(annotation):
            found: Any = _sse_payload_annotation(arg)
            if found is not None:
                return found
        return None

    return cast("Any", annotation)


def _is_sse_type(annotation: Any) -> bool:
    """Determine whether a type annotation represents or contains a ServerSentEvent.

    Args:
        annotation: Type annotation to inspect.

    Returns:
        True if the annotation is or contains ServerSentEvent, otherwise False.
    """
    if annotation is None:
        return False
    target = get_origin(annotation) or annotation
    if target is ServerSentEvent:
        return True
    try:
        if isinstance(target, type) and issubclass(target, ServerSentEvent):
            return True
    except TypeError:
        pass
    origin = get_origin(annotation)
    if origin is not None:
        return any(_is_sse_type(arg) for arg in get_args(annotation))
    return False


def _extract_channels_plugin_channel(
    app: "Litestar",
    pattern: str,
    clean_root: str,
    context: AsyncAPISchemaContext,
    allocator: _ChannelKeyAllocator,
    operation_ids: set[str],
) -> tuple[str, AsyncAPIChannel, dict[str, AsyncAPIOperation]]:
    """Extract a single ChannelsPlugin channel and associated operations.

    Args:
        app: The Litestar application instance.
        pattern: The channel topic pattern string.
        clean_root: Cleaned root path string.
        context: Schema context coordinating OpenAPI and DTO support.
        allocator: Allocator for collision-safe channel keys.
        operation_ids: Registry for unique operation ids.

    Returns:
        Tuple of (channel_key, channel, operations).
    """
    clean_pattern = pattern.lstrip("/")
    channel_path = f"{clean_root}/{clean_pattern}" if clean_root else f"/{clean_pattern}"
    normalized = normalize_path(channel_path)
    channel_key = allocator.allocate(normalized, "channels")

    parameters: dict[str, AsyncAPIParameter] = {}
    for param_name in extract_path_params(pattern):
        parameters[param_name] = AsyncAPIParameter(description=f"Channel parameter {param_name}")

    located_handler: Any = None
    for route in app.routes:
        if isinstance(route, WebSocketRoute) and (
            route.path == channel_path or normalize_path(route.path) == normalized
        ):
            located_handler = getattr(route, "route_handler", None)
            break

    broadcast_payload: dict[str, Any] = {}
    opt_payload = _opt_payload_annotation(located_handler) if located_handler is not None else None
    if opt_payload is not None:
        broadcast_payload = extract_field_schema(
            located_handler, opt_payload, context, dto_attribute="resolve_return_dto"
        )
    elif located_handler is not None:
        ret_field = getattr(located_handler, "parsed_return_field", None)
        ret_annotation = getattr(ret_field, "annotation", None)
        if ret_annotation not in (None, NoneType):
            broadcast_payload = extract_field_schema(
                located_handler, ret_field, context, dto_attribute="resolve_return_dto"
            )

    broadcast_msg_name = f"{channel_key}Broadcast"
    broadcast_msg = AsyncAPIMessage(
        name=broadcast_msg_name,
        title=f"{pattern} Broadcast Message",
        summary=f"Event payload broadcast on {pattern}",
        content_type="application/json",
        payload=broadcast_payload,
    )

    channel_messages = {"broadcast": broadcast_msg}
    operations: dict[str, AsyncAPIOperation] = {}

    send_op_id = _allocate_operation_id("send", channel_key, operation_ids)
    operations[send_op_id] = AsyncAPIOperation(
        action="send",
        channel={"$ref": f"#/channels/{channel_key}"},
        summary=f"Broadcast event to subscribers on {normalized}",
        description=f"Publishes real-time events to subscribers connected to {pattern}.",
        messages=[{"$ref": f"#/channels/{channel_key}/messages/broadcast"}],
    )

    data_field = getattr(located_handler, "parsed_data_field", None) if located_handler is not None else None
    data_annotation = getattr(data_field, "annotation", None) if data_field is not None else None
    if data_annotation not in (None, NoneType):
        receive_op_id = _allocate_operation_id("receive", channel_key, operation_ids)
        operations[receive_op_id] = AsyncAPIOperation(
            action="receive",
            channel={"$ref": f"#/channels/{channel_key}"},
            summary=f"Subscribe or publish events on {normalized}",
            description=f"Receives subscriber connections and event publications on {pattern}.",
            messages=[{"$ref": f"#/channels/{channel_key}/messages/broadcast"}],
        )

    channel = AsyncAPIChannel(
        address=normalized,
        title=f"{pattern} Channel",
        summary=f"ChannelsPlugin broadcast channel at {normalized}",
        description=f"Managed Litestar channel for {pattern}.",
        parameters=parameters,
        messages=channel_messages,
        bindings={"ws": {}, "channels": {"channel": pattern}},
    )

    return channel_key, channel, operations


def extract_channels_plugin_channels(
    app: "Litestar",
    components_schemas: dict[str, Any] | None = None,
    *,
    context: AsyncAPISchemaContext | None = None,
    allocator: _ChannelKeyAllocator | None = None,
    operation_ids: set[str] | None = None,
) -> tuple[dict[str, AsyncAPIChannel], dict[str, AsyncAPIOperation]]:
    """Extract channels and operations defined in Litestar ChannelsPlugin.

    Fallback payload schema is unconstrained ({}) rather than {"type": "object"}
    because a ChannelsPlugin topic may carry arrays, strings, numbers, or bytes.

    Args:
        app: The Litestar application instance.
        components_schemas: Optional dictionary to collect named component schemas.
        context: Optional schema context coordinating OpenAPI and DTO support.
        allocator: Optional allocator to ensure unique channel keys across sources.
        operation_ids: Optional set to ensure unique operation ids across sources.

    Returns:
        Tuple of (channels_mapping, operations_mapping).
    """
    if context is None:
        context = AsyncAPISchemaContext(
            components_schemas=components_schemas if components_schemas is not None else {}
        )
    elif components_schemas is not None and not context.components_schemas:
        context.components_schemas = components_schemas

    if allocator is None:
        allocator = _ChannelKeyAllocator()
    if operation_ids is None:
        operation_ids = set()

    channels: dict[str, AsyncAPIChannel] = {}
    operations: dict[str, AsyncAPIOperation] = {}

    channels_plugin: ChannelsPlugin | None = None
    for plugin in app.plugins:
        if isinstance(plugin, ChannelsPlugin):
            channels_plugin = plugin
            break

    if channels_plugin is None:
        return channels, operations

    root_path = getattr(channels_plugin, "_handler_root_path", "/") or "/"
    channels_dict = getattr(channels_plugin, "_channels", {}) or {}

    channel_patterns = list(channels_dict.keys())
    arbitrary_allowed = getattr(channels_plugin, "_arbitrary_channels_allowed", False)

    if arbitrary_allowed and "{channel:str}" not in channel_patterns and "{channel}" not in channel_patterns:
        channel_patterns.append("{channel:str}")

    clean_root = root_path.rstrip("/")
    for pattern in channel_patterns:
        channel_key, channel, channel_ops = _extract_channels_plugin_channel(
            app, pattern, clean_root, context, allocator, operation_ids
        )
        channels[channel_key] = channel
        operations.update(channel_ops)

    return channels, operations


def extract_sse_routes(
    app: "Litestar",
    components_schemas: dict[str, Any] | None = None,
    *,
    context: AsyncAPISchemaContext | None = None,
    allocator: _ChannelKeyAllocator | None = None,
    operation_ids: set[str] | None = None,
) -> tuple[dict[str, AsyncAPIChannel], dict[str, AsyncAPIOperation]]:
    """Extract Server-Sent Event (SSE) routes from a Litestar application.

    Args:
        app: The Litestar application instance.
        components_schemas: Optional dictionary to collect named component schemas.
        context: Optional schema context coordinating OpenAPI and DTO support.
        allocator: Optional allocator to ensure unique channel keys across sources.
        operation_ids: Optional set to ensure unique operation ids across sources.

    Returns:
        Tuple of (channels_mapping, operations_mapping).
    """
    if context is None:
        context = AsyncAPISchemaContext(
            components_schemas=components_schemas if components_schemas is not None else {}
        )
    elif components_schemas is not None and not context.components_schemas:
        context.components_schemas = components_schemas

    if allocator is None:
        allocator = _ChannelKeyAllocator()
    if operation_ids is None:
        operation_ids = set()

    channels: dict[str, AsyncAPIChannel] = {}
    operations: dict[str, AsyncAPIOperation] = {}

    for route in app.routes:
        if not isinstance(route, HTTPRoute):
            continue

        for handler in route.route_handlers:
            return_field = getattr(handler, "parsed_return_field", None)
            annotation = getattr(return_field, "annotation", None)
            if annotation is None:
                annotation = getattr(handler, "return_type", None)

            if not _is_sse_type(annotation):
                continue

            raw_path = route.path
            normalized = normalize_path(raw_path)
            channel_key = allocator.allocate(normalized, "sse")

            parameters: dict[str, AsyncAPIParameter] = {}
            for param_name in extract_path_params(raw_path):
                parameters[param_name] = AsyncAPIParameter(description=f"Path parameter {param_name}")

            handler_name = getattr(handler, "handler_name", None) or getattr(handler, "name", None)
            fn = getattr(handler, "fn", None)
            doc = getattr(fn, "__doc__", None) or getattr(handler, "__doc__", None)

            if fn is not None and hasattr(fn, "fn"):
                inner_fn = getattr(fn, "fn", None)
                doc = getattr(inner_fn, "__doc__", None) or doc
                if not handler_name:
                    handler_name = getattr(inner_fn, "__name__", None)

            if not handler_name:
                handler_name = getattr(fn, "__name__", None) or f"{channel_key}_sse"

            opt_payload = _opt_payload_annotation(handler)
            resolved_type = opt_payload if opt_payload is not None else _sse_payload_annotation(annotation)
            if resolved_type is not None:
                payload = extract_field_schema(handler, resolved_type, context, dto_attribute="resolve_return_dto")
            else:
                payload = {"type": "string"}

            msg_name = f"{channel_key}Event"
            event_msg = AsyncAPIMessage(
                name=msg_name,
                title=f"{handler_name} Server-Sent Event",
                summary=f"Server-Sent Event emitted by {handler_name}",
                description=doc,
                content_type="text/event-stream",
                payload=payload,
            )

            channel_messages = {"event": event_msg}

            op_id = _allocate_operation_id("stream", channel_key, operation_ids)
            operations[op_id] = AsyncAPIOperation(
                action="send",
                channel={"$ref": f"#/channels/{channel_key}"},
                title=f"{handler_name} Stream",
                summary=f"Stream Server-Sent Events from {normalized}",
                description=doc,
                messages=[{"$ref": f"#/channels/{channel_key}/messages/event"}],
            )

            channels[channel_key] = AsyncAPIChannel(
                address=normalized,
                title=f"{handler_name} SSE Stream",
                summary=f"Server-Sent Events endpoint at {normalized}",
                description=doc,
                parameters=parameters,
                messages=channel_messages,
                bindings={"http": {}},
            )

    return channels, operations


def extract_realtime_channels(
    app: "Litestar",
    components_schemas: dict[str, Any] | None = None,
    *,
    context: AsyncAPISchemaContext | None = None,
) -> tuple[dict[str, AsyncAPIChannel], dict[str, AsyncAPIOperation]]:
    """Extract all real-time channels from WebSocket routes, ChannelsPlugin, and SSE routes.

    Args:
        app: The Litestar application instance.
        components_schemas: Optional dictionary to collect named component schemas.
        context: Optional schema context coordinating OpenAPI and DTO support.

    Returns:
        Tuple of (channels_mapping, operations_mapping).
    """
    if context is None:
        context = AsyncAPISchemaContext(
            components_schemas=components_schemas if components_schemas is not None else {}
        )
    elif components_schemas is not None and not context.components_schemas:
        context.components_schemas = components_schemas

    allocator = _ChannelKeyAllocator()
    operation_ids: set[str] = set()

    channels, operations = extract_websocket_routes(
        app, context=context, allocator=allocator, operation_ids=operation_ids
    )

    cp_channels, cp_ops = extract_channels_plugin_channels(
        app, context=context, allocator=allocator, operation_ids=operation_ids
    )
    _merge_channels(channels, operations, cp_channels, cp_ops)

    sse_channels, sse_ops = extract_sse_routes(
        app, context=context, allocator=allocator, operation_ids=operation_ids
    )
    _merge_channels(channels, operations, sse_channels, sse_ops)

    return channels, operations


def create_asyncapi_document(
    app: "Litestar", title: str = "Litestar Realtime API", version: str = "1.0.0", description: str | None = None
) -> AsyncAPIDocument:
    """Generate an AsyncAPI 3.0 document from a Litestar application.

    Args:
        app: The Litestar application instance.
        title: Title for the AsyncAPI document.
        version: Version of the API specification.
        description: Optional description of the API.

    Returns:
        A populated AsyncAPIDocument instance.
    """
    openapi_schema: dict[str, Any] | None = None
    if app.openapi_config is not None:
        with contextlib.suppress(Exception):
            openapi_schema = app.openapi_schema.to_schema()

    support = OpenAPISupport.from_app(app, openapi_schema)
    context = AsyncAPISchemaContext(support=support)
    channels, operations = extract_realtime_channels(app, context=context)

    if support.enabled and support.context is not None:
        generated = support.context.schema_registry.generate_components_schemas()
        _ = build_schema_name_map(support.context.schema_registry)
        for name, schema in generated.items():
            if name not in context.components_schemas:
                context.components_schemas[name] = schema.to_schema()
        for payload_dict, ref_obj in context.deferred_references:
            payload_dict["$ref"] = ref_obj.ref

    info = AsyncAPIInfo(title=title, version=version, description=description)
    components = AsyncAPIComponents(schemas=context.components_schemas) if context.components_schemas else None
    return AsyncAPIDocument(info=info, channels=channels, operations=operations, components=components)
