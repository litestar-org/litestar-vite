"""Unit tests for AsyncAPI 3.0 codegen models and WebSocket route introspection."""

from collections.abc import AsyncGenerator
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, TypedDict

import msgspec
from litestar import Litestar, get, websocket, websocket_listener
from litestar.channels import ChannelsPlugin
from litestar.channels.backends.memory import MemoryChannelsBackend
from litestar.connection import WebSocket
from litestar.response import ServerSentEvent

from litestar_vite import PathConfig, ViteConfig, VitePlugin
from litestar_vite.codegen import (
    ASYNCAPI_PAYLOAD_OPT_KEY,
    AsyncAPIChannel,
    AsyncAPIComponents,
    AsyncAPIDocument,
    AsyncAPIInfo,
    AsyncAPIMessage,
    AsyncAPIOperation,
    AsyncAPIParameter,
    AsyncAPIServer,
    ExportResult,
    create_asyncapi_document,
    export_asyncapi,
    export_integration_assets,
    extract_channels_plugin_channels,
    extract_payload_schema,
    extract_realtime_channels,
    extract_sse_routes,
    extract_websocket_routes,
)
from litestar_vite.config import TypeGenConfig


def test_asyncapi_info_and_server_models() -> None:
    """Test AsyncAPI 3.0 info and server dataclasses."""
    info = AsyncAPIInfo(title="Chat API", version="1.0.0", description="Realtime chat service")
    info_dict = info.to_dict()

    assert info_dict == {"title": "Chat API", "version": "1.0.0", "description": "Realtime chat service"}

    server = AsyncAPIServer(host="localhost:8000", protocol="ws", description="Local dev server")
    server_dict = server.to_dict()

    assert server_dict == {"host": "localhost:8000", "protocol": "ws", "description": "Local dev server"}


def test_asyncapi_document_serialization() -> None:
    """Test full AsyncAPI 3.0 document serialization."""
    doc = AsyncAPIDocument(
        info=AsyncAPIInfo(title="Realtime Stream", version="0.1.0"),
        servers={"development": AsyncAPIServer(host="127.0.0.1:8000", protocol="ws")},
        channels={
            "chat": AsyncAPIChannel(
                address="/ws/chat/{room_id}",
                title="Chat Room Channel",
                parameters={"room_id": AsyncAPIParameter(description="Target room identifier")},
                messages={"chatMessage": AsyncAPIMessage(name="ChatMessage", payload={"type": "string"})},
            )
        },
        operations={
            "receiveChat": AsyncAPIOperation(
                action="receive",
                channel={"$ref": "#/channels/chat"},
                summary="Receive user message",
                messages=[{"$ref": "#/channels/chat/messages/chatMessage"}],
            )
        },
        components=AsyncAPIComponents(
            messages={"broadcastMessage": AsyncAPIMessage(name="BroadcastMessage", payload={"type": "object"})}
        ),
    )

    data = doc.to_dict()

    assert data["asyncapi"] == "3.0.0"
    assert data["info"]["title"] == "Realtime Stream"
    assert "development" in data["servers"]
    assert "chat" in data["channels"]
    assert data["channels"]["chat"]["address"] == "/ws/chat/{room_id}"
    assert "room_id" in data["channels"]["chat"]["parameters"]
    assert "receiveChat" in data["operations"]
    assert data["operations"]["receiveChat"]["action"] == "receive"
    assert "broadcastMessage" in data["components"]["messages"]


def test_extract_websocket_routes_raw() -> None:
    """Test route extraction from raw @websocket route handlers."""

    @websocket("/ws/raw/{room_id:str}")
    async def raw_chat_handler(socket: WebSocket, room_id: str) -> None:
        """Raw websocket handler for a chat room."""
        await socket.accept()
        await socket.close()

    app = Litestar(route_handlers=[raw_chat_handler])
    channels, operations = extract_websocket_routes(app)

    assert len(channels) == 1
    channel_key = next(iter(channels))
    channel = channels[channel_key]

    assert channel.address == "/ws/raw/{room_id}"
    assert "room_id" in channel.parameters
    assert len(operations) >= 1


def test_extract_websocket_listener_routes() -> None:
    """Test route extraction from @websocket_listener handlers."""

    @websocket_listener("/ws/feed/{topic_id:int}")
    def feed_listener(data: str, topic_id: int) -> dict[str, int]:
        """Feed listener echoing payload length."""
        return {"length": len(data)}

    app = Litestar(route_handlers=[feed_listener])
    channels, operations = extract_websocket_routes(app)

    assert len(channels) == 1
    channel_key = next(iter(channels))
    channel = channels[channel_key]

    assert channel.address == "/ws/feed/{topic_id}"
    assert "topic_id" in channel.parameters

    receive_ops = [op for op in operations.values() if op.action == "receive"]
    send_ops = [op for op in operations.values() if op.action == "send"]

    assert len(receive_ops) == 1
    assert len(send_ops) == 1


def test_extract_websocket_routes_empty_app() -> None:
    """Test extraction on an app with no websocket routes."""
    app = Litestar(route_handlers=[])
    channels, operations = extract_websocket_routes(app)

    assert channels == {}
    assert operations == {}


def test_extract_channels_plugin_channels_predefined() -> None:
    """Test channel extraction from configured ChannelsPlugin channels."""
    plugin = ChannelsPlugin(
        backend=MemoryChannelsBackend(), channels=["notifications", "room/{room_id:str}"], ws_handler_base_path="/ws"
    )
    app = Litestar(plugins=[plugin])

    channels, operations = extract_channels_plugin_channels(app)

    assert "ws__notifications" in channels
    assert "ws__room__p_room_id" in channels

    notif_channel = channels["ws__notifications"]
    assert notif_channel.address == "/ws/notifications"
    assert "broadcast" in notif_channel.messages
    assert notif_channel.bindings["channels"]["channel"] == "notifications"

    room_channel = channels["ws__room__p_room_id"]
    assert room_channel.address == "/ws/room/{room_id}"
    assert "room_id" in room_channel.parameters

    assert "send_ws__notifications" in operations
    assert "receive_ws__notifications" not in operations
    assert operations["send_ws__notifications"].action == "send"


def test_extract_channels_plugin_channels_arbitrary() -> None:
    """Test channel extraction when arbitrary channels are allowed."""
    plugin = ChannelsPlugin(
        backend=MemoryChannelsBackend(), arbitrary_channels_allowed=True, ws_handler_base_path="/ws"
    )
    app = Litestar(plugins=[plugin])

    channels, _operations = extract_channels_plugin_channels(app)

    assert "ws__p_channel" in channels
    arbitrary_channel = channels["ws__p_channel"]
    assert arbitrary_channel.address == "/ws/{channel}"
    assert "channel" in arbitrary_channel.parameters


def test_extract_channels_plugin_no_plugin() -> None:
    """Test ChannelsPlugin extraction on app without ChannelsPlugin."""
    app = Litestar(route_handlers=[])
    channels, operations = extract_channels_plugin_channels(app)

    assert channels == {}
    assert operations == {}


def test_extract_sse_routes_single_and_stream() -> None:
    """Test extraction of ServerSentEvent HTTP endpoints."""

    @get("/events")
    async def single_event_handler() -> ServerSentEvent:
        """Emit a single event."""
        return ServerSentEvent(content="update")

    @get("/stream/{stream_id:int}")
    async def stream_event_handler(stream_id: int) -> AsyncGenerator[ServerSentEvent, None]:
        """Stream continuous events."""

        async def gen() -> AsyncGenerator[ServerSentEvent, None]:
            yield ServerSentEvent(content=f"event-{stream_id}")

        return gen()

    @get("/json-endpoint")
    async def regular_json_handler() -> dict[str, str]:
        """Standard HTTP handler that should not be extracted."""
        return {"status": "ok"}

    app = Litestar(route_handlers=[single_event_handler, stream_event_handler, regular_json_handler])
    channels, operations = extract_sse_routes(app)

    assert "events" in channels
    assert "stream__p_stream_id" in channels
    assert "json-endpoint" not in channels

    events_channel = channels["events"]
    assert events_channel.address == "/events"
    assert "event" in events_channel.messages
    assert events_channel.messages["event"].content_type == "text/event-stream"
    assert "http" in events_channel.bindings

    stream_channel = channels["stream__p_stream_id"]
    assert stream_channel.address == "/stream/{stream_id}"
    assert "stream_id" in stream_channel.parameters

    assert "stream_events" in operations
    assert operations["stream_events"].action == "send"
    assert "stream_stream__p_stream_id" in operations
    assert operations["stream_stream__p_stream_id"].action == "send"


def test_extract_sse_routes_no_sse() -> None:
    """Test SSE extraction on an app with no SSE routes."""

    @get("/hello")
    def hello_handler() -> str:
        """Greeting endpoint."""
        return "hello"

    app = Litestar(route_handlers=[hello_handler])
    channels, operations = extract_sse_routes(app)

    assert channels == {}
    assert operations == {}


def test_extract_realtime_channels_and_create_asyncapi_document() -> None:
    """Test full realtime channel extraction and AsyncAPIDocument generation."""

    @websocket("/ws/chat")
    async def chat_handler(socket: WebSocket) -> None:
        """Raw websocket handler."""
        await socket.accept()
        await socket.close()

    @get("/sse/metrics")
    async def metrics_handler() -> ServerSentEvent:
        """SSE metrics endpoint."""
        return ServerSentEvent(content="cpu:45%")

    channels_plugin = ChannelsPlugin(
        backend=MemoryChannelsBackend(), channels=["broadcasts"], ws_handler_base_path="/ws"
    )

    app = Litestar(route_handlers=[chat_handler, metrics_handler], plugins=[channels_plugin])

    channels, _operations = extract_realtime_channels(app)

    assert "ws__chat" in channels
    assert "sse__metrics" in channels
    assert "ws__broadcasts" in channels

    doc = create_asyncapi_document(
        app, title="Application Realtime API", version="2.1.0", description="Full realtime messaging catalog"
    )

    doc_dict = doc.to_dict()
    assert doc_dict["asyncapi"] == "3.0.0"
    assert doc_dict["info"]["title"] == "Application Realtime API"
    assert doc_dict["info"]["version"] == "2.1.0"
    assert "ws__chat" in doc_dict["channels"]
    assert "sse__metrics" in doc_dict["channels"]
    assert "ws__broadcasts" in doc_dict["channels"]


def test_extract_payload_schema_primitives_and_containers() -> None:
    """Test extract_payload_schema with primitive scalars and container types."""
    comps: dict[str, Any] = {}

    assert extract_payload_schema(str, comps) == {"type": "string"}
    assert extract_payload_schema(int, comps) == {"type": "integer"}
    assert extract_payload_schema(float, comps) == {"type": "number"}
    assert extract_payload_schema(bool, comps) == {"type": "boolean"}
    assert extract_payload_schema(bytes, comps) == {"type": "string", "contentMediaType": "application/octet-stream"}
    assert extract_payload_schema(list[int], comps) == {"type": "array", "items": {"type": "integer"}}
    assert extract_payload_schema(dict[str, float], comps) == {
        "type": "object",
        "additionalProperties": {"type": "number"},
    }
    assert extract_payload_schema(str | None, comps) == {"anyOf": [{"type": "string"}, {"type": "null"}]}
    assert extract_payload_schema(int | str, comps) == {"anyOf": [{"type": "integer"}, {"type": "string"}]}


def test_extract_payload_schema_dataclass_and_msgspec() -> None:
    """Test extract_payload_schema with dataclasses and msgspec Structs."""

    @dataclass
    class Location:
        lat: float
        lon: float

    class UserPresence(msgspec.Struct):
        user_id: str
        location: Location
        active: bool

    comps: dict[str, Any] = {}
    loc_ref = extract_payload_schema(Location, comps)
    presence_ref = extract_payload_schema(UserPresence, comps)

    assert loc_ref == {"$ref": "#/components/schemas/Location"}
    assert presence_ref == {"$ref": "#/components/schemas/UserPresence"}
    assert "Location" in comps
    assert "UserPresence" in comps
    assert comps["Location"]["type"] == "object"
    assert "lat" in comps["Location"]["properties"]
    assert comps["UserPresence"]["type"] == "object"
    assert comps["UserPresence"]["properties"]["location"] == {"$ref": "#/components/schemas/Location"}


def test_extract_payload_schema_enums_and_typeddicts() -> None:
    """Test extract_payload_schema with Enums and TypedDicts."""

    class EventType(str, Enum):
        JOIN = "join"
        LEAVE = "leave"

    class EventPayload(TypedDict):
        event: EventType
        timestamp: int

    comps: dict[str, Any] = {}
    payload_ref = extract_payload_schema(EventPayload, comps)

    assert payload_ref == {"$ref": "#/components/schemas/EventPayload"}
    assert "EventPayload" in comps
    assert "EventType" in comps
    assert comps["EventType"]["enum"] == ["join", "leave"]


def test_create_asyncapi_document_with_typed_listener() -> None:
    """Test create_asyncapi_document collects schemas from websocket listeners into components."""

    @dataclass
    class InboundData:
        room: str
        message: str

    class OutboundData(msgspec.Struct):
        echo: str
        timestamp: int

    @websocket_listener("/ws/typed-chat")
    def typed_chat_handler(data: InboundData) -> OutboundData:
        """Typed chat listener handler."""
        return OutboundData(echo=data.message, timestamp=123456)

    app = Litestar(route_handlers=[typed_chat_handler])
    doc = create_asyncapi_document(app, title="Typed Chat Service", version="1.0.0")

    doc_dict = doc.to_dict()
    assert doc_dict["asyncapi"] == "3.0.0"
    assert "components" in doc_dict
    assert "schemas" in doc_dict["components"]
    assert "InboundData" in doc_dict["components"]["schemas"]
    assert "OutboundData" in doc_dict["components"]["schemas"]

    channel = doc_dict["channels"]["ws__typed_chat"]
    assert channel["messages"]["inbound"]["payload"] == {"$ref": "#/components/schemas/InboundData"}
    assert channel["messages"]["outbound"]["payload"] == {"$ref": "#/components/schemas/OutboundData"}


def test_export_asyncapi_pipeline(tmp_path: Path) -> None:
    """Test export_asyncapi function writes asyncapi.json and detects unchanged content."""

    @dataclass
    class Ping:
        msg: str

    @websocket_listener("/ws/ping")
    def ping_handler(data: Ping) -> Ping:
        """Ping listener handler."""
        return data

    app = Litestar(route_handlers=[ping_handler])
    types_config = TypeGenConfig(output=tmp_path / "types_out")

    result = ExportResult()
    export_asyncapi(app=app, types_config=types_config, result=result)

    asyncapi_file = tmp_path / "types_out" / "asyncapi.json"
    assert asyncapi_file.exists()
    assert len(result.exported_files) == 1
    assert "asyncapi" in result.exported_files[0]
    assert result.asyncapi_schema is not None
    assert "ws__ping" in result.asyncapi_schema["channels"]

    result2 = ExportResult()
    export_asyncapi(app=app, types_config=types_config, result=result2)
    assert len(result2.exported_files) == 0
    assert result2.unchanged_files == ["asyncapi.json"]


def test_export_integration_assets_includes_asyncapi(tmp_path: Path) -> None:
    """Test export_integration_assets includes asyncapi.json export."""

    @get("/api/health")
    async def health_check() -> dict[str, str]:
        """Health check endpoint."""
        return {"status": "ok"}

    @dataclass
    class FeedData:
        item: str

    @websocket_listener("/ws/feed")
    def feed_handler(data: FeedData) -> FeedData:
        """Feed listener."""
        return data

    types_config = TypeGenConfig(output=tmp_path / "sdk", generate_channels=True)
    vite_config = ViteConfig(paths=PathConfig(bundle_dir=tmp_path / "public"), types=types_config)
    plugin = VitePlugin(config=vite_config)

    app = Litestar(route_handlers=[health_check, feed_handler], plugins=[plugin])

    result = export_integration_assets(app=app, config=vite_config)

    assert result.asyncapi_schema is not None
    assert "ws__feed" in result.asyncapi_schema["channels"]
    asyncapi_file = tmp_path / "sdk" / "asyncapi.json"
    assert asyncapi_file.exists()


def test_to_dict_preserves_dict_payload_additional_properties() -> None:
    """Test to_dict preserves additionalProperties in dict payloads."""

    @websocket_listener("/ws/kv")
    def kv_handler(data: dict[str, str]) -> dict:
        """Key-value listener."""
        return data

    app = Litestar(route_handlers=[kv_handler])
    doc = create_asyncapi_document(app).to_dict()

    channel = doc["channels"]["ws__kv"]
    inbound_payload = channel["messages"]["inbound"]["payload"]
    outbound_payload = channel["messages"]["outbound"]["payload"]

    assert inbound_payload == {"type": "object", "additionalProperties": {"type": "string"}}
    assert "additionalProperties" in outbound_payload
    assert outbound_payload["additionalProperties"] == {}


def test_to_dict_preserves_list_payload_items() -> None:
    """Test to_dict preserves items in list payloads."""

    @websocket_listener("/ws/items")
    def items_handler(data: list) -> None:
        """Items listener."""

    app = Litestar(route_handlers=[items_handler])
    doc = create_asyncapi_document(app).to_dict()

    channel = doc["channels"]["ws__items"]
    inbound_payload = channel["messages"]["inbound"]["payload"]

    assert inbound_payload == {"type": "array", "items": {}}


def test_to_dict_preserves_binding_markers() -> None:
    """Test to_dict preserves empty binding markers for protocols."""

    @get("/events")
    def sse_handler() -> ServerSentEvent:
        """SSE event feed."""
        return ServerSentEvent(content="ping")

    channels_plugin = ChannelsPlugin(
        backend=MemoryChannelsBackend(), channels=["broadcast"], create_ws_route_handlers=True
    )
    app = Litestar(route_handlers=[sse_handler], plugins=[channels_plugin])
    doc = create_asyncapi_document(app).to_dict()

    sse_channel = doc["channels"]["events"]
    assert sse_channel["bindings"] == {"http": {}}

    broadcast_channel = doc["channels"]["broadcast"]
    assert broadcast_channel["bindings"]["ws"] == {}


def test_to_dict_still_prunes_metadata_nulls() -> None:
    """Test to_dict still prunes metadata None values and empty parameters."""

    @websocket_listener("/ws/noparams")
    def simple_handler(data: str) -> str:
        """Simple listener with no parameters."""
        return data

    app = Litestar(route_handlers=[simple_handler])
    doc = create_asyncapi_document(app).to_dict()

    assert "description" not in doc["info"]
    assert "parameters" not in doc["channels"]["ws__noparams"]


def _assert_refs_resolve(doc: dict[str, Any]) -> None:
    """Verify all operation channel and message refs resolve to existing channel and message definitions."""
    channels = doc.get("channels", {})
    operations = doc.get("operations", {})

    for op_id, op in operations.items():
        channel_ref = op["channel"]["$ref"]
        assert channel_ref.startswith("#/channels/"), f"Invalid channel $ref {channel_ref} in {op_id}"
        channel_key = channel_ref[len("#/channels/") :]
        assert channel_key in channels, f"Operation {op_id} references missing channel {channel_key}"

        channel = channels[channel_key]
        messages = channel.get("messages", {})
        for msg in op.get("messages", []):
            msg_ref = msg["$ref"]
            expected_prefix = f"#/channels/{channel_key}/messages/"
            assert msg_ref.startswith(expected_prefix), f"Invalid message $ref {msg_ref} in {op_id}"
            msg_key = msg_ref[len(expected_prefix) :]
            assert msg_key in messages, (
                f"Operation {op_id} references missing message {msg_key} in channel {channel_key}"
            )


def test_distinct_paths_get_distinct_channel_keys() -> None:
    """Test distinct paths produce distinct channel keys without collisions."""

    @websocket("/ws/a/b")
    async def handler_slash(socket: WebSocket) -> None:
        """Handler for /ws/a/b."""
        await socket.accept()
        await socket.close()

    @websocket("/ws/a_b")
    async def handler_underscore(socket: WebSocket) -> None:
        """Handler for /ws/a_b."""
        await socket.accept()
        await socket.close()

    @websocket("/ws/{a:str}/b")
    async def handler_param(socket: WebSocket, a: str) -> None:
        """Handler for /ws/{a}/b."""
        await socket.accept()
        await socket.close()

    app = Litestar(route_handlers=[handler_slash, handler_underscore, handler_param])
    doc = create_asyncapi_document(app).to_dict()

    assert len(doc["channels"]) == 3
    assert len(set(doc["channels"].keys())) == 3
    _assert_refs_resolve(doc)


def test_websocket_and_sse_on_same_path_do_not_collide() -> None:
    """Test WebSocket and SSE handlers on the same route path do not collide."""

    @websocket("/feed")
    async def ws_feed_handler(socket: WebSocket) -> None:
        """WebSocket feed handler."""
        await socket.accept()
        await socket.close()

    @get("/feed")
    async def sse_feed_handler() -> ServerSentEvent:
        """SSE feed handler."""
        return ServerSentEvent(content="ping")

    app = Litestar(route_handlers=[ws_feed_handler, sse_feed_handler])
    doc = create_asyncapi_document(app).to_dict()

    assert len(doc["channels"]) == 2
    for channel_key in doc["channels"].keys():
        referencing_ops = [
            op for op in doc["operations"].values() if op["channel"]["$ref"] == f"#/channels/{channel_key}"
        ]
        assert len(referencing_ops) >= 1
    _assert_refs_resolve(doc)


def test_all_operation_refs_resolve() -> None:
    """Test all operation channel and message references resolve across combined extractors."""

    @websocket("/chat/{room:str}")
    async def chat_handler(socket: WebSocket, room: str) -> None:
        """Chat socket handler."""
        await socket.accept()
        await socket.close()

    @get("/live/events")
    async def sse_handler() -> ServerSentEvent:
        """Live SSE handler."""
        return ServerSentEvent(content="update")

    channels_plugin = ChannelsPlugin(
        backend=MemoryChannelsBackend(), channels=["system_broadcast"], create_ws_route_handlers=True
    )

    app = Litestar(route_handlers=[chat_handler, sse_handler], plugins=[channels_plugin])
    doc = create_asyncapi_document(app).to_dict()

    _assert_refs_resolve(doc)


def test_operation_ids_are_unique() -> None:
    """Test all operation ids across combined extractors are unique."""

    @websocket("/events")
    async def ws_events(socket: WebSocket) -> None:
        """WS events."""
        await socket.accept()
        await socket.close()

    @get("/events")
    async def sse_events() -> ServerSentEvent:
        """SSE events."""
        return ServerSentEvent(content="event")

    channels_plugin = ChannelsPlugin(
        backend=MemoryChannelsBackend(), channels=["events"], create_ws_route_handlers=True
    )

    app = Litestar(route_handlers=[ws_events, sse_events], plugins=[channels_plugin])
    doc = create_asyncapi_document(app).to_dict()

    op_ids = list(doc["operations"].keys())
    assert len(op_ids) == len(set(op_ids))
    _assert_refs_resolve(doc)


def test_sse_payload_from_opt() -> None:
    """Test SSE payload extracted from handler opt ASYNCAPI_PAYLOAD_OPT_KEY."""

    @dataclass
    class Alert:
        level: str
        message: str

    @get("/stream/alerts", opt={ASYNCAPI_PAYLOAD_OPT_KEY: Alert})
    async def alert_handler() -> ServerSentEvent:
        """Stream alerts."""
        return ServerSentEvent(content="alert")

    app = Litestar(route_handlers=[alert_handler])
    doc = create_asyncapi_document(app).to_dict()

    assert "components" in doc
    assert "schemas" in doc["components"]
    assert "Alert" in doc["components"]["schemas"]
    sse_channel = doc["channels"]["stream__alerts"]
    assert sse_channel["messages"]["event"]["payload"] == {"$ref": "#/components/schemas/Alert"}


def test_sse_payload_from_generator_annotation() -> None:
    """Test SSE payload extracted from generator element annotation."""

    @dataclass
    class Metric:
        name: str
        value: float

    @get("/stream/metrics")
    async def metric_handler() -> AsyncGenerator[ServerSentEvent[Metric], None]:
        """Stream metrics."""

        async def gen() -> AsyncGenerator[ServerSentEvent[Metric], None]:
            yield ServerSentEvent(content=Metric(name="cpu", value=42.0))

        return gen()

    app = Litestar(route_handlers=[metric_handler])
    doc = create_asyncapi_document(app).to_dict()

    assert "components" in doc
    assert "schemas" in doc["components"]
    assert "Metric" in doc["components"]["schemas"]
    sse_channel = doc["channels"]["stream__metrics"]
    assert sse_channel["messages"]["event"]["payload"] == {"$ref": "#/components/schemas/Metric"}


def test_sse_payload_defaults_to_string() -> None:
    """Test untyped SSE payload defaults to string."""

    @get("/stream/raw")
    async def raw_handler() -> ServerSentEvent:
        """Stream raw text."""
        return ServerSentEvent(content="raw text")

    app = Litestar(route_handlers=[raw_handler])
    doc = create_asyncapi_document(app).to_dict()

    sse_channel = doc["channels"]["stream__raw"]
    assert sse_channel["messages"]["event"]["payload"] == {"type": "string"}
    assert sse_channel["messages"]["event"]["contentType"] == "text/event-stream"


def test_channels_plugin_broadcast_payload_unconstrained() -> None:
    """Test ChannelsPlugin broadcast payload is unconstrained when untyped."""
    channels_plugin = ChannelsPlugin(
        backend=MemoryChannelsBackend(), channels=["notify"], create_ws_route_handlers=True
    )
    app = Litestar(plugins=[channels_plugin])
    doc = create_asyncapi_document(app).to_dict()

    channel = doc["channels"]["notify"]
    assert channel["messages"]["broadcast"]["payload"] == {}
    ops = [
        op_id for op_id in doc["operations"] if "notify" in op_id and doc["operations"][op_id]["action"] == "receive"
    ]
    assert ops == []


def test_channels_plugin_receive_operation_when_handler_accepts_data() -> None:
    """Test ChannelsPlugin emits receive operation when handler accepts data."""

    @websocket_listener("/notify")
    async def custom_listener(data: str) -> None:
        """Listener with data parameter."""

    channels_plugin = ChannelsPlugin(
        backend=MemoryChannelsBackend(), channels=["notify"], create_ws_route_handlers=False
    )
    app = Litestar(route_handlers=[custom_listener], plugins=[channels_plugin])
    _channels, operations = extract_channels_plugin_channels(app)

    receive_ops = [
        op_id for op_id, op in operations.items() if op.action == "receive" and "notify" in op.channel["$ref"]
    ]
    send_ops = [op_id for op_id, op in operations.items() if op.action == "send" and "notify" in op.channel["$ref"]]
    assert len(receive_ops) == 1
    assert len(send_ops) == 1
