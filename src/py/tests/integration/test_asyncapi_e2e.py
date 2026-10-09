"""End-to-end integration test for AsyncAPI, WebSocket routes, SSE, and ChannelsPlugin export."""

from collections.abc import AsyncGenerator
from pathlib import Path

import msgspec
from litestar import Litestar, get
from litestar.channels import ChannelsPlugin
from litestar.channels.backends.memory import MemoryChannelsBackend
from litestar.handlers import websocket_listener
from litestar.params import FromPath
from litestar.response import ServerSentEvent
from litestar.testing import TestClient
from litestar_asyncapi import AsyncAPIConfig, AsyncAPIPlugin, ChannelDefinition, MessageDefinition, OperationDefinition
from litestar_asyncapi.spec import Server

from litestar_vite.codegen import export_integration_assets
from litestar_vite.config import PathConfig, TypeGenConfig, ViteConfig
from litestar_vite.plugin import VitePlugin


class ChatInbound(msgspec.Struct):
    text: str


class ChatOutbound(msgspec.Struct):
    room_id: str
    text: str


def test_asyncapi_and_websocket_routes_end_to_end(tmp_path: Path) -> None:
    """Full pipeline exports synchronized asyncapi.json, routes.json, and routes.ts for WS, SSE, and Channels."""

    @get("/api/ping", name="ping", sync_to_thread=False)
    def ping() -> dict[str, str]:
        return {"status": "ok"}

    @websocket_listener("/ws/chat/{room_id:str}", name="chat_room")
    async def chat_room(data: ChatInbound, room_id: FromPath[str]) -> ChatOutbound:
        payload = msgspec.convert(data, ChatInbound) if isinstance(data, dict) else data
        return ChatOutbound(room_id=room_id, text=payload.text.upper())

    @get("/sse/events", name="sse_events")
    async def sse_events() -> ServerSentEvent:
        async def _stream() -> AsyncGenerator[bytes, None]:
            yield b"event: tick\ndata: 1\n\n"

        return ServerSentEvent(_stream())

    channels_plugin = ChannelsPlugin(
        backend=MemoryChannelsBackend(),
        channels=["notifications"],
        create_ws_route_handlers=True,
        ws_handler_base_path="/channels",
    )
    asyncapi_plugin = AsyncAPIPlugin(
        config=AsyncAPIConfig(
            servers={"local": Server(host="localhost:8000", protocol="ws")},
            channels=[
                ChannelDefinition(
                    key="/sse/events",
                    address="/sse/events",
                    bindings={"http": {}},
                    operations=[
                        OperationDefinition(
                            action="send",
                            messages=[
                                MessageDefinition(
                                    name="ServerEvent", content_type="text/event-stream", payload=ChatOutbound
                                )
                            ],
                        )
                    ],
                )
            ],
        )
    )
    sdk_dir = tmp_path / "sdk"
    vite_config = ViteConfig(
        paths=PathConfig(bundle_dir=tmp_path / "public"),
        types=TypeGenConfig(
            output=sdk_dir, generate_channels=True, generate_routes=True, generate_sdk=False, generate_zod=False
        ),
    )
    app = Litestar(
        route_handlers=[ping, chat_room, sse_events],
        plugins=[VitePlugin(config=vite_config), channels_plugin, asyncapi_plugin],
    )

    result = export_integration_assets(app=app, config=vite_config)
    assert result.asyncapi_schema is not None
    assert (sdk_dir / "asyncapi.json").exists()
    assert (sdk_dir / "routes.json").exists()
    assert (sdk_dir / "routes.ts").exists()
    assert (sdk_dir / "openapi.json").exists()

    asyncapi_doc = msgspec.json.decode((sdk_dir / "asyncapi.json").read_bytes())
    routes_doc = msgspec.json.decode((sdk_dir / "routes.json").read_bytes())
    routes_ts = (sdk_dir / "routes.ts").read_text(encoding="utf-8")

    channels = asyncapi_doc["channels"]
    assert "ws__chat__p_room_id" in channels
    assert channels["ws__chat__p_room_id"]["bindings"] == {"ws": {}}
    assert "sse__events" in channels
    assert channels["sse__events"]["bindings"] == {"http": {}}
    assert any("notifications" in key for key in channels)

    schemas = asyncapi_doc.get("components", {}).get("schemas", {})
    assert any("ChatInbound" in name for name in schemas)
    assert any("ChatOutbound" in name for name in schemas)

    assert routes_doc["servers"] == {"local": {"host": "localhost:8000", "protocol": "ws"}}
    assert routes_doc["routes"]["chat_room"]["protocol"] == "websocket"
    assert routes_doc["routes"]["chat_room"]["channel_key"] == "ws__chat__p_room_id"
    assert routes_doc["routes"]["chat_room"]["uri"] == "/ws/chat/{room_id}"
    assert "protocol" not in routes_doc["routes"]["ping"]
    assert "protocol" not in routes_doc["routes"]["sse_events"]
    for route_entry in routes_doc["routes"].values():
        assert not route_entry["uri"].startswith("/channels")

    assert "export const WS_SERVER_URL =" in routes_ts
    assert "|| 'ws://localhost:8000';" in routes_ts
    assert "export type WebSocketRouteName =\n  | 'chat_room';" in routes_ts
    assert "export function wsRoute<" in routes_ts
    assert "route.ws = wsRoute;" in routes_ts

    with TestClient(app=app) as client, client.websocket_connect("/ws/chat/lobby") as ws:
        ws.send_json({"text": "hello"})
        reply = ws.receive_json()
        assert reply == {"room_id": "lobby", "text": "HELLO"}
