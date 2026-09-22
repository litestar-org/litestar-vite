"""Unit tests for AsyncAPI 3.0 codegen models and WebSocket route introspection."""


from litestar import Litestar, websocket, websocket_listener
from litestar.connection import WebSocket

from litestar_vite.codegen._asyncapi import (
    AsyncAPIChannel,
    AsyncAPIComponents,
    AsyncAPIDocument,
    AsyncAPIInfo,
    AsyncAPIMessage,
    AsyncAPIOperation,
    AsyncAPIParameter,
    AsyncAPIServer,
    extract_websocket_routes,
)


def test_asyncapi_info_and_server_models() -> None:
    """Test AsyncAPI 3.0 info and server dataclasses."""
    info = AsyncAPIInfo(title="Chat API", version="1.0.0", description="Realtime chat service")
    info_dict = info.to_dict()

    assert info_dict == {
        "title": "Chat API",
        "version": "1.0.0",
        "description": "Realtime chat service",
    }

    server = AsyncAPIServer(host="localhost:8000", protocol="ws", description="Local dev server")
    server_dict = server.to_dict()

    assert server_dict == {
        "host": "localhost:8000",
        "protocol": "ws",
        "description": "Local dev server",
    }


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
