"""AsyncAPI 3.0 document models and WebSocket route introspection for Litestar.

This module provides data models for AsyncAPI 3.0.0 specifications and utilities
to introspect Litestar WebSocket routes and listeners into structured channels
and operations.
"""

from dataclasses import asdict, dataclass, field
from types import UnionType
from typing import TYPE_CHECKING, Any, Union, cast, get_args, get_origin

from litestar.channels import ChannelsPlugin
from litestar.handlers import WebsocketListenerRouteHandler
from litestar.response import ServerSentEvent
from litestar.routes import HTTPRoute, WebSocketRoute
from litestar.types.builtin_types import NoneType

from litestar_vite.codegen._routes import extract_path_params
from litestar_vite.codegen._ts import normalize_path

if TYPE_CHECKING:
    from litestar import Litestar


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


def extract_websocket_routes(
    app: "Litestar", components_schemas: dict[str, Any] | None = None
) -> tuple[dict[str, AsyncAPIChannel], dict[str, AsyncAPIOperation]]:
    """Extract WebSocket routes from a Litestar application into AsyncAPI channels and operations.

    Args:
        app: The Litestar application instance.
        components_schemas: Optional dictionary to collect named component schemas.

    Returns:
        Tuple of (channels_mapping, operations_mapping).
    """
    channels: dict[str, AsyncAPIChannel] = {}
    operations: dict[str, AsyncAPIOperation] = {}

    for route in app.routes:
        if not isinstance(route, WebSocketRoute):
            continue

        raw_path = route.path
        normalized = normalize_path(raw_path)
        channel_key = normalized.lstrip("/").replace("/", "_").replace("{", "").replace("}", "") or "root"

        parameters: dict[str, AsyncAPIParameter] = {}
        for param_name in extract_path_params(raw_path):
            parameters[param_name] = AsyncAPIParameter(description=f"Path parameter {param_name}")

        handler = getattr(route, "route_handler", None)
        handler_name = getattr(handler, "handler_name", None) or getattr(handler, "name", None)
        fn = getattr(handler, "fn", None)
        doc = getattr(fn, "__doc__", None) or getattr(handler, "__doc__", None)

        if fn is not None and hasattr(fn, "fn"):
            inner_fn = getattr(fn, "fn", None)
            doc = getattr(inner_fn, "__doc__", None) or doc
            if not handler_name:
                handler_name = getattr(inner_fn, "__name__", None)

        if not handler_name:
            handler_name = getattr(fn, "__name__", None) or f"{channel_key}_handler"

        channel_messages: dict[str, AsyncAPIMessage] = {}

        is_listener = isinstance(handler, WebsocketListenerRouteHandler)
        if is_listener:
            data_field = getattr(handler, "parsed_data_field", None)
            return_field = getattr(handler, "parsed_return_field", None)

            if data_field is not None and getattr(data_field, "annotation", None) is not None:
                inbound_msg_name = f"{channel_key}Inbound"
                inbound_payload = extract_payload_schema(data_field.annotation, components_schemas=components_schemas)
                inbound_msg = AsyncAPIMessage(
                    name=inbound_msg_name, title=f"{handler_name} Inbound Message", payload=inbound_payload
                )
                channel_messages["inbound"] = inbound_msg

                op_id = f"receive_{channel_key}"
                operations[op_id] = AsyncAPIOperation(
                    action="receive",
                    channel={"$ref": f"#/channels/{channel_key}"},
                    summary=f"Receive inbound messages on {normalized}",
                    description=doc,
                    messages=[{"$ref": f"#/channels/{channel_key}/messages/inbound"}],
                )

            if return_field is not None and getattr(return_field, "annotation", None) not in (None, NoneType):
                outbound_msg_name = f"{channel_key}Outbound"
                outbound_payload = extract_payload_schema(
                    return_field.annotation, components_schemas=components_schemas
                )
                outbound_msg = AsyncAPIMessage(
                    name=outbound_msg_name, title=f"{handler_name} Outbound Message", payload=outbound_payload
                )
                channel_messages["outbound"] = outbound_msg

                op_id = f"send_{channel_key}"
                operations[op_id] = AsyncAPIOperation(
                    action="send",
                    channel={"$ref": f"#/channels/{channel_key}"},
                    summary=f"Send outbound messages on {normalized}",
                    description=doc,
                    messages=[{"$ref": f"#/channels/{channel_key}/messages/outbound"}],
                )
        else:
            default_msg_name = f"{channel_key}Message"
            default_msg = AsyncAPIMessage(
                name=default_msg_name, title=f"{handler_name} Message", payload={"type": "string"}
            )
            channel_messages["message"] = default_msg

            op_id = f"operate_{channel_key}"
            operations[op_id] = AsyncAPIOperation(
                action="send",
                channel={"$ref": f"#/channels/{channel_key}"},
                summary=f"WebSocket operation on {normalized}",
                description=doc,
                messages=[{"$ref": f"#/channels/{channel_key}/messages/message"}],
            )

        channels[channel_key] = AsyncAPIChannel(
            address=normalized,
            title=f"{handler_name} Channel",
            summary=f"WebSocket channel at {normalized}",
            description=doc,
            parameters=parameters,
            messages=channel_messages,
        )

    return channels, operations


def _is_sse_type(annotation: Any) -> bool:
    """Determine whether a type annotation represents or contains a ServerSentEvent.

    Args:
        annotation: Type annotation to inspect.

    Returns:
        True if the annotation is or contains ServerSentEvent, otherwise False.
    """
    if annotation is None:
        return False
    if annotation is ServerSentEvent:
        return True
    try:
        if isinstance(annotation, type) and issubclass(annotation, ServerSentEvent):
            return True
    except TypeError:
        pass
    origin = get_origin(annotation)
    if origin is not None:
        for arg in get_args(annotation):
            if _is_sse_type(arg):
                return True
    return False


def extract_channels_plugin_channels(
    app: "Litestar",
) -> tuple[dict[str, AsyncAPIChannel], dict[str, AsyncAPIOperation]]:
    """Extract channels and operations defined in Litestar ChannelsPlugin.

    Args:
        app: The Litestar application instance.

    Returns:
        Tuple of (channels_mapping, operations_mapping).
    """
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
        clean_pattern = pattern.lstrip("/")
        channel_path = f"{clean_root}/{clean_pattern}" if clean_root else f"/{clean_pattern}"
        normalized = normalize_path(channel_path)
        channel_key = normalized.lstrip("/").replace("/", "_").replace("{", "").replace("}", "") or "root"

        parameters: dict[str, AsyncAPIParameter] = {}
        for param_name in extract_path_params(pattern):
            parameters[param_name] = AsyncAPIParameter(description=f"Channel parameter {param_name}")

        broadcast_msg_name = f"{channel_key}Broadcast"
        broadcast_msg = AsyncAPIMessage(
            name=broadcast_msg_name,
            title=f"{pattern} Broadcast Message",
            summary=f"Event payload broadcast on {pattern}",
            content_type="application/json",
            payload={"type": "object"},
        )

        channel_messages = {"broadcast": broadcast_msg}

        send_op_id = f"send_{channel_key}"
        operations[send_op_id] = AsyncAPIOperation(
            action="send",
            channel={"$ref": f"#/channels/{channel_key}"},
            summary=f"Broadcast event to subscribers on {normalized}",
            description=f"Publishes real-time events to subscribers connected to {pattern}.",
            messages=[{"$ref": f"#/channels/{channel_key}/messages/broadcast"}],
        )

        receive_op_id = f"receive_{channel_key}"
        operations[receive_op_id] = AsyncAPIOperation(
            action="receive",
            channel={"$ref": f"#/channels/{channel_key}"},
            summary=f"Subscribe or publish events on {normalized}",
            description=f"Receives subscriber connections and event publications on {pattern}.",
            messages=[{"$ref": f"#/channels/{channel_key}/messages/broadcast"}],
        )

        channels[channel_key] = AsyncAPIChannel(
            address=normalized,
            title=f"{pattern} Channel",
            summary=f"ChannelsPlugin broadcast channel at {normalized}",
            description=f"Managed Litestar channel for {pattern}.",
            parameters=parameters,
            messages=channel_messages,
            bindings={"ws": {}, "channels": {"channel": pattern}},
        )

    return channels, operations


def extract_sse_routes(app: "Litestar") -> tuple[dict[str, AsyncAPIChannel], dict[str, AsyncAPIOperation]]:
    """Extract Server-Sent Event (SSE) routes from a Litestar application.

    Args:
        app: The Litestar application instance.

    Returns:
        Tuple of (channels_mapping, operations_mapping).
    """
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
            channel_key = normalized.lstrip("/").replace("/", "_").replace("{", "").replace("}", "") or "root"

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

            msg_name = f"{channel_key}Event"
            event_msg = AsyncAPIMessage(
                name=msg_name,
                title=f"{handler_name} Server-Sent Event",
                summary=f"Server-Sent Event emitted by {handler_name}",
                description=doc,
                content_type="text/event-stream",
                payload={"type": "string"},
            )

            channel_messages = {"event": event_msg}

            op_id = f"stream_{channel_key}"
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
    app: "Litestar", components_schemas: dict[str, Any] | None = None
) -> tuple[dict[str, AsyncAPIChannel], dict[str, AsyncAPIOperation]]:
    """Extract all real-time channels from WebSocket routes, ChannelsPlugin, and SSE routes.

    Args:
        app: The Litestar application instance.
        components_schemas: Optional dictionary to collect named component schemas.

    Returns:
        Tuple of (channels_mapping, operations_mapping).
    """
    channels: dict[str, AsyncAPIChannel] = {}
    operations: dict[str, AsyncAPIOperation] = {}

    ws_channels, ws_ops = extract_websocket_routes(app, components_schemas=components_schemas)
    channels.update(ws_channels)
    operations.update(ws_ops)

    cp_channels, cp_ops = extract_channels_plugin_channels(app)
    for k, v in cp_channels.items():
        if k in channels:
            channels[k] = v
            stale_ops = [op_id for op_id, op in operations.items() if op.channel.get("$ref") == f"#/channels/{k}"]
            for op_id in stale_ops:
                operations.pop(op_id, None)
        else:
            channels[k] = v
    operations.update(cp_ops)

    sse_channels, sse_ops = extract_sse_routes(app)
    channels.update(sse_channels)
    operations.update(sse_ops)

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
    components_schemas: dict[str, Any] = {}
    channels, operations = extract_realtime_channels(app, components_schemas=components_schemas)
    info = AsyncAPIInfo(title=title, version=version, description=description)
    components = AsyncAPIComponents(schemas=components_schemas) if components_schemas else None
    return AsyncAPIDocument(info=info, channels=channels, operations=operations, components=components)
