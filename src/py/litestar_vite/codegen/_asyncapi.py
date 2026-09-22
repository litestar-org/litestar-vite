"""AsyncAPI 3.0 document models and WebSocket route introspection for Litestar.

This module provides data models for AsyncAPI 3.0.0 specifications and utilities
to introspect Litestar WebSocket routes and listeners into structured channels
and operations.
"""

from dataclasses import asdict, dataclass, field
from types import UnionType
from typing import TYPE_CHECKING, Any, Union, get_args, get_origin

from litestar.handlers import WebsocketListenerRouteHandler
from litestar.routes import WebSocketRoute
from litestar.types.builtin_types import NoneType

from litestar_vite.codegen._routes import extract_path_params
from litestar_vite.codegen._ts import normalize_path

if TYPE_CHECKING:
    from litestar import Litestar


def _clean_dict(d: dict[str, Any]) -> dict[str, Any]:
    """Recursively remove None values and empty collections from a dictionary.

    Args:
        d: The dictionary to clean.

    Returns:
        A cleaned dictionary with non-empty values.
    """
    cleaned: dict[str, Any] = {}
    for key, value in d.items():
        if value is None:
            continue
        if isinstance(value, dict):
            sub_dict = _clean_dict(value)
            if sub_dict:
                cleaned[key] = sub_dict
        elif isinstance(value, list):
            sub_list = [_clean_dict(item) if isinstance(item, dict) else item for item in value if item is not None]
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
    enum: list[str] = field(default_factory=list)
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
    payload: dict[str, Any] = field(default_factory=dict)

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
    parameters: dict[str, AsyncAPIParameter] = field(default_factory=dict)
    messages: dict[str, AsyncAPIMessage] = field(default_factory=dict)
    bindings: dict[str, Any] = field(default_factory=dict)

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
    messages: list[dict[str, str]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert the operation object to a dictionary.

        Returns:
            Dictionary representation of the operation object.
        """
        return _clean_dict(asdict(self))


@dataclass(slots=True)
class AsyncAPIComponents:
    """AsyncAPI 3.0 Components Object."""

    messages: dict[str, AsyncAPIMessage] = field(default_factory=dict)
    schemas: dict[str, Any] = field(default_factory=dict)
    parameters: dict[str, AsyncAPIParameter] = field(default_factory=dict)

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
    servers: dict[str, AsyncAPIServer] = field(default_factory=dict)
    channels: dict[str, AsyncAPIChannel] = field(default_factory=dict)
    operations: dict[str, AsyncAPIOperation] = field(default_factory=dict)
    components: AsyncAPIComponents | None = None

    def to_dict(self) -> dict[str, Any]:
        """Serialize the complete document to an AsyncAPI 3.0 specification dictionary.

        Returns:
            Deterministic dictionary representation of the AsyncAPI 3.0 specification.
        """
        data: dict[str, Any] = {
            "asyncapi": self.asyncapi,
            "info": self.info.to_dict(),
        }
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
}


def _py_type_to_schema(annotation: Any) -> dict[str, Any]:
    """Map a Python type annotation to a basic JSON Schema dictionary.

    Args:
        annotation: Python type annotation.

    Returns:
        JSON Schema dictionary.
    """
    if annotation in _SCALAR_SCHEMA_MAP:
        return _SCALAR_SCHEMA_MAP[annotation].copy()

    origin = get_origin(annotation)
    if origin is list:
        args = get_args(annotation)
        items_schema = _py_type_to_schema(args[0]) if args else {}
        return {"type": "array", "items": items_schema}

    if origin in (Union, UnionType):
        args = [arg for arg in get_args(annotation) if arg is not NoneType]
        if len(args) == 1:
            return _py_type_to_schema(args[0])
        return {"anyOf": [_py_type_to_schema(arg) for arg in args]}

    return {"type": "object"}


def extract_websocket_routes(
    app: "Litestar",
) -> tuple[dict[str, AsyncAPIChannel], dict[str, AsyncAPIOperation]]:
    """Extract WebSocket routes from a Litestar application into AsyncAPI channels and operations.

    Args:
        app: The Litestar application instance.

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
            parameters[param_name] = AsyncAPIParameter(
                description=f"Path parameter {param_name}",
            )

        handler = getattr(route, "route_handler", None)
        handler_name = getattr(handler, "handler_name", None) or getattr(handler, "name", None)
        fn = getattr(handler, "fn", None)
        doc = getattr(fn, "__doc__", None) or getattr(handler, "__doc__", None)

        if hasattr(fn, "fn"):
            inner_fn = fn.fn
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
                inbound_payload = _py_type_to_schema(data_field.annotation)
                inbound_msg = AsyncAPIMessage(
                    name=inbound_msg_name,
                    title=f"{handler_name} Inbound Message",
                    payload=inbound_payload,
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
                outbound_payload = _py_type_to_schema(return_field.annotation)
                outbound_msg = AsyncAPIMessage(
                    name=outbound_msg_name,
                    title=f"{handler_name} Outbound Message",
                    payload=outbound_payload,
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
                name=default_msg_name,
                title=f"{handler_name} Message",
                payload={"type": "string"},
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
