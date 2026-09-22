"""Unit tests for AsyncAPI 3.0 codegen models and WebSocket route introspection."""

from collections.abc import AsyncGenerator

from litestar import Litestar, get, websocket, websocket_listener
from litestar.channels import ChannelsPlugin
from litestar.channels.backends.memory import MemoryChannelsBackend
from litestar.connection import WebSocket
from litestar.response import ServerSentEvent

from litestar_vite.codegen._asyncapi import (
    AsyncAPIChannel,
    AsyncAPIComponents,
    AsyncAPIDocument,
    AsyncAPIInfo,
    AsyncAPIMessage,
    AsyncAPIOperation,
    AsyncAPIParameter,
    AsyncAPIServer,
    create_asyncapi_document,
    extract_channels_plugin_channels,
    extract_realtime_channels,
    extract_sse_routes,
    extract_websocket_routes,
)


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

    assert "ws_notifications" in channels
    assert "ws_room_room_id" in channels

    notif_channel = channels["ws_notifications"]
    assert notif_channel.address == "/ws/notifications"
    assert "broadcast" in notif_channel.messages
    assert notif_channel.bindings["channels"]["channel"] == "notifications"

    room_channel = channels["ws_room_room_id"]
    assert room_channel.address == "/ws/room/{room_id}"
    assert "room_id" in room_channel.parameters

    assert "send_ws_notifications" in operations
    assert "receive_ws_notifications" in operations
    assert operations["send_ws_notifications"].action == "send"
    assert operations["receive_ws_notifications"].action == "receive"


def test_extract_channels_plugin_channels_arbitrary() -> None:
    """Test channel extraction when arbitrary channels are allowed."""
    plugin = ChannelsPlugin(
        backend=MemoryChannelsBackend(), arbitrary_channels_allowed=True, ws_handler_base_path="/ws"
    )
    app = Litestar(plugins=[plugin])

    channels, _operations = extract_channels_plugin_channels(app)

    assert "ws_channel" in channels
    arbitrary_channel = channels["ws_channel"]
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
    assert "stream_stream_id" in channels
    assert "json-endpoint" not in channels

    events_channel = channels["events"]
    assert events_channel.address == "/events"
    assert "event" in events_channel.messages
    assert events_channel.messages["event"].content_type == "text/event-stream"
    assert "http" in events_channel.bindings

    stream_channel = channels["stream_stream_id"]
    assert stream_channel.address == "/stream/{stream_id}"
    assert "stream_id" in stream_channel.parameters

    assert "stream_events" in operations
    assert operations["stream_events"].action == "send"
    assert "stream_stream_stream_id" in operations
    assert operations["stream_stream_stream_id"].action == "send"


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

    assert "ws_chat" in channels
    assert "sse_metrics" in channels
    assert "ws_broadcasts" in channels

    doc = create_asyncapi_document(
        app, title="Application Realtime API", version="2.1.0", description="Full realtime messaging catalog"
    )

    doc_dict = doc.to_dict()
    assert doc_dict["asyncapi"] == "3.0.0"
    assert doc_dict["info"]["title"] == "Application Realtime API"
    assert doc_dict["info"]["version"] == "2.1.0"
    assert "ws_chat" in doc_dict["channels"]
    assert "sse_metrics" in doc_dict["channels"]
    assert "ws_broadcasts" in doc_dict["channels"]
