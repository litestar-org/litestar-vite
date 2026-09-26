"""Unit tests for AsyncAPI plugin discovery, normalization, and export."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import msgspec
import pytest
from litestar import Litestar, WebSocket, get, websocket
from litestar.channels import ChannelsPlugin
from litestar.channels.backends.memory import MemoryChannelsBackend
from litestar.config.app import AppConfig
from litestar.handlers import websocket_listener
from litestar.plugins import InitPluginProtocol
from litestar.response import ServerSentEvent
from litestar_asyncapi import AsyncAPIConfig, ChannelDefinition, DocsConfig, MessageDefinition, OperationDefinition
from litestar_asyncapi import AsyncAPIPlugin as RealAsyncAPIPlugin

from litestar_vite.codegen import (
    ExportResult,
    asyncapi_docs_paths,
    export_asyncapi,
    export_integration_assets,
    find_asyncapi_plugin,
    normalize_asyncapi_document,
    resolve_asyncapi_document,
)
from litestar_vite.config import PathConfig, TypeGenConfig, ViteConfig
from litestar_vite.plugin import VitePlugin


@dataclass
class _FakeDocsConfig:
    path: str = "/asyncapi"


@dataclass
class _FakeAsyncAPIConfig:
    docs: _FakeDocsConfig = field(default_factory=_FakeDocsConfig)


class AsyncAPIPlugin(InitPluginProtocol):
    """Test double for duck-typed litestar-asyncapi plugin."""

    def __init__(
        self,
        doc: dict[str, Any] | None = None,
        *,
        docs_path: str = "/asyncapi",
        raise_err: bool = False,
        json_bytes: bytes | None = None,
    ) -> None:
        self.doc = doc
        self.config = _FakeAsyncAPIConfig(docs=_FakeDocsConfig(path=docs_path))
        self.raise_err = raise_err
        self.json_bytes = json_bytes

    def on_app_init(self, app_config: AppConfig) -> AppConfig:
        return app_config

    def get_asyncapi_schema(self, app: Any) -> Any:
        if self.raise_err:
            raise TypeError("Simulated plugin exception")
        return self.doc

    def get_asyncapi_json(self, app: Any) -> bytes:
        if self.json_bytes is not None:
            return self.json_bytes
        return msgspec.json.encode(self.doc or {})


def _assert_refs_resolve(doc: dict[str, Any]) -> None:
    """Verify all operation channel and message refs resolve to existing definitions."""
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


def test_find_asyncapi_plugin_returns_none_without_plugin() -> None:
    """Test find_asyncapi_plugin returns None when no AsyncAPIPlugin is registered."""
    app = Litestar(route_handlers=[])
    assert find_asyncapi_plugin(app) is None
    assert asyncapi_docs_paths(app) == ()


def test_find_asyncapi_plugin_when_not_installed(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test find_asyncapi_plugin returns None when ASYNCAPI_INSTALLED is False."""
    monkeypatch.setattr("litestar_vite.codegen._asyncapi.ASYNCAPI_INSTALLED", False)
    app = Litestar(plugins=[RealAsyncAPIPlugin()])
    assert find_asyncapi_plugin(app) is None


def test_find_asyncapi_plugin_and_docs_paths_with_real_plugin() -> None:
    """Test find_asyncapi_plugin and asyncapi_docs_paths with real AsyncAPIPlugin."""
    plugin = RealAsyncAPIPlugin(config=AsyncAPIConfig(docs=DocsConfig(path="/custom-asyncapi")))
    app = Litestar(plugins=[plugin])
    assert find_asyncapi_plugin(app) is plugin
    assert asyncapi_docs_paths(app) == ("/asyncapi", "/custom-asyncapi")


def test_resolve_asyncapi_document_returns_none_without_plugin() -> None:
    """Test resolve_asyncapi_document returns None when AsyncAPIPlugin is not registered."""

    @websocket_listener("/ws/chat")
    async def chat_handler(data: str) -> str:
        return data

    @get("/sse/events", sync_to_thread=False)
    def sse_handler() -> ServerSentEvent:
        return ServerSentEvent(content="ping")

    channels_plugin = ChannelsPlugin(
        backend=MemoryChannelsBackend(), channels=["notifications"], create_ws_route_handlers=True
    )
    app = Litestar(route_handlers=[chat_handler, sse_handler], plugins=[channels_plugin])
    assert resolve_asyncapi_document(app) is None


def test_export_integration_assets_skips_asyncapi_without_plugin(tmp_path: Path) -> None:
    """Test export_integration_assets does not emit asyncapi.json when AsyncAPIPlugin is absent."""

    @get("/api/health")
    async def health_check() -> dict[str, str]:
        return {"status": "ok"}

    @websocket_listener("/ws/chat")
    async def chat_handler(data: str) -> str:
        return data

    channels_plugin = ChannelsPlugin(
        backend=MemoryChannelsBackend(), channels=["notifications"], create_ws_route_handlers=True
    )
    types_config = TypeGenConfig(output=tmp_path / "generated", generate_channels=True)
    vite_config = ViteConfig(paths=PathConfig(bundle_dir=tmp_path / "public"), types=types_config)
    app = Litestar(
        route_handlers=[health_check, chat_handler], plugins=[channels_plugin, VitePlugin(config=vite_config)]
    )

    result = export_integration_assets(app=app, config=vite_config)
    assert result.asyncapi_schema is None
    assert not (tmp_path / "generated" / "asyncapi.json").exists()


def test_export_asyncapi_noop_without_plugin(tmp_path: Path) -> None:
    """Test export_asyncapi is a no-op when AsyncAPIPlugin is not registered."""

    @websocket_listener("/ws/ping")
    def ping_handler(data: str) -> str:
        return data

    app = Litestar(route_handlers=[ping_handler])
    types_config = TypeGenConfig(output=tmp_path / "types_out")
    result = ExportResult()
    export_asyncapi(app=app, types_config=types_config, result=result)

    assert result.asyncapi_schema is None
    assert result.exported_files == []
    assert not (tmp_path / "types_out" / "asyncapi.json").exists()


def test_resolve_asyncapi_document_with_real_asyncapi_plugin() -> None:
    """Test resolve_asyncapi_document normalizes schema from real litestar_asyncapi.AsyncAPIPlugin."""

    @dataclass
    class ChatInbound:
        text: str

    @dataclass
    class ChatOutbound:
        reply: str

    @websocket_listener("/ws/chat/{room_id:str}")
    def chat_handler(data: ChatInbound, room_id: str) -> ChatOutbound:
        return ChatOutbound(reply=data.text)

    @websocket("/ws/raw")
    async def raw_handler(socket: WebSocket) -> None:
        await socket.accept()

    channels_plugin = ChannelsPlugin(
        backend=MemoryChannelsBackend(), channels=["notifications", "alerts/{level:str}"], create_ws_route_handlers=True
    )
    asyncapi_plugin = RealAsyncAPIPlugin(
        config=AsyncAPIConfig(
            title="Realtime Test API",
            version="2.1.0",
            include_raw_websocket_routes=False,
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
    app = Litestar(route_handlers=[chat_handler, raw_handler], plugins=[channels_plugin, asyncapi_plugin])

    doc = resolve_asyncapi_document(app)
    assert doc is not None
    assert doc["asyncapi"] == "3.1.0"
    assert doc["info"]["title"] == "Realtime Test API"
    assert doc["info"]["version"] == "2.1.0"

    assert "ws__chat__p_room_id" in doc["channels"]
    assert "notifications" in doc["channels"]
    assert "alerts__p_level" in doc["channels"]
    assert "sse__events" in doc["channels"]

    assert doc["channels"]["ws__chat__p_room_id"]["bindings"] == {"ws": {}}
    assert doc["channels"]["sse__events"]["bindings"] == {"http": {}}
    assert doc["channels"]["notifications"]["bindings"] == {}
    assert doc["channels"]["alerts__p_level"]["bindings"] == {}

    assert any(k.endswith("ChatInbound") for k in doc["components"]["schemas"])
    assert any(k.endswith("ChatOutbound") for k in doc["components"]["schemas"])

    _assert_refs_resolve(doc)


def test_export_asyncapi_pipeline_with_real_plugin(tmp_path: Path) -> None:
    """Test export_asyncapi writes asyncapi.json and detects unchanged content when AsyncAPIPlugin is registered."""

    @dataclass
    class Ping:
        msg: str

    @websocket_listener("/ws/ping")
    def ping_handler(data: Ping) -> Ping:
        return data

    app = Litestar(route_handlers=[ping_handler], plugins=[RealAsyncAPIPlugin()])
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


def test_export_integration_assets_includes_asyncapi_with_plugin(tmp_path: Path) -> None:
    """Test export_integration_assets exports asyncapi.json when AsyncAPIPlugin is registered."""

    @get("/api/health")
    async def health_check() -> dict[str, str]:
        return {"status": "ok"}

    @dataclass
    class FeedData:
        item: str

    @websocket_listener("/ws/feed")
    def feed_handler(data: FeedData) -> FeedData:
        return data

    types_config = TypeGenConfig(output=tmp_path / "sdk", generate_channels=True)
    vite_config = ViteConfig(paths=PathConfig(bundle_dir=tmp_path / "public"), types=types_config)
    plugin = VitePlugin(config=vite_config)

    app = Litestar(route_handlers=[health_check, feed_handler], plugins=[plugin, RealAsyncAPIPlugin()])

    result = export_integration_assets(app=app, config=vite_config)

    assert result.asyncapi_schema is not None
    assert "ws__feed" in result.asyncapi_schema["channels"]
    asyncapi_file = tmp_path / "sdk" / "asyncapi.json"
    assert asyncapi_file.exists()


def test_export_asyncapi_without_openapi_config_when_plugin_present(tmp_path: Path) -> None:
    """Test export_integration_assets exports asyncapi.json when openapi_config=None and AsyncAPIPlugin is present."""

    @websocket_listener("/ws/events")
    def ws_handler(data: str) -> str:
        return data

    vite_config = ViteConfig(
        paths=PathConfig(bundle_dir=tmp_path / "public"),
        types=TypeGenConfig(output=tmp_path / "types", generate_channels=True),
    )
    app = Litestar(
        route_handlers=[ws_handler], openapi_config=None, plugins=[VitePlugin(config=vite_config), RealAsyncAPIPlugin()]
    )

    result = export_integration_assets(app=app, config=vite_config)
    assert result.openapi_schema is None
    assert result.asyncapi_schema is not None
    assert (tmp_path / "types" / "asyncapi.json").exists()
    assert not (tmp_path / "types" / "openapi.json").exists()


def test_resolve_document_with_duck_typed_plugin() -> None:
    """Test resolve_asyncapi_document uses duck-typed plugin document when available."""
    raw_310_doc: dict[str, Any] = {
        "asyncapi": "3.1.0",
        "info": {"title": "Realtime Chat", "version": "1.0.0"},
        "channels": {
            "chat": {
                "address": "/chat",
                "bindings": {"ws": {}},
                "messages": {"chatMessage": {"payload": {"$ref": "#/components/schemas/ChatMessage"}}},
            }
        },
        "operations": {
            "receiveChatMessage": {
                "action": "receive",
                "channel": {"$ref": "#/channels/chat"},
                "messages": [{"$ref": "#/channels/chat/messages/chatMessage"}],
            },
            "sendChatMessage": {
                "action": "send",
                "channel": {"$ref": "#/channels/chat"},
                "messages": [{"$ref": "#/channels/chat/messages/chatMessage"}],
            },
        },
        "components": {
            "schemas": {
                "ChatMessage": {"type": "object", "properties": {"text": {"type": "string"}}, "required": ["text"]}
            }
        },
    }

    plugin = AsyncAPIPlugin(doc=raw_310_doc, docs_path="/asyncapi")
    app = Litestar(plugins=[plugin])

    resolved_doc = resolve_asyncapi_document(app, title="Custom Title", version="3.0.0")
    assert resolved_doc is not None
    assert resolved_doc["asyncapi"] == "3.1.0"
    assert resolved_doc["info"]["title"] == "Custom Title"
    assert resolved_doc["info"]["version"] == "3.0.0"
    assert "chat" in resolved_doc["channels"]
    assert resolved_doc["operations"]["receiveChatMessage"]["channel"]["$ref"] == "#/channels/chat"
    assert (
        resolved_doc["operations"]["receiveChatMessage"]["messages"][0]["$ref"]
        == "#/channels/chat/messages/chatMessage"
    )
    assert resolved_doc["operations"]["sendChatMessage"]["channel"]["$ref"] == "#/channels/chat"
    assert (
        resolved_doc["operations"]["sendChatMessage"]["messages"][0]["$ref"] == "#/channels/chat/messages/chatMessage"
    )


def test_resolve_document_falls_back_to_get_asyncapi_json() -> None:
    """Test resolve_asyncapi_document falls back to get_asyncapi_json when get_asyncapi_schema returns None."""
    raw_doc: dict[str, Any] = {
        "asyncapi": "3.1.0",
        "info": {"title": "From JSON", "version": "1.0.0"},
        "channels": {"/ws/json": {"address": "/ws/json"}},
        "operations": {"recv": {"action": "receive", "channel": {"$ref": "#/channels/~1ws~1json"}}},
    }
    plugin = AsyncAPIPlugin(doc=None, json_bytes=msgspec.json.encode(raw_doc))
    app = Litestar(plugins=[plugin])

    resolved_doc = resolve_asyncapi_document(app)
    assert resolved_doc is not None
    assert "ws__json" in resolved_doc["channels"]
    assert resolved_doc["operations"]["recv"]["channel"]["$ref"] == "#/channels/ws__json"


def test_resolve_document_returns_none_when_plugin_raises() -> None:
    """Test resolve_asyncapi_document returns None when plugin raises TypeError."""
    plugin = AsyncAPIPlugin(raise_err=True)
    app = Litestar(plugins=[plugin])

    assert resolve_asyncapi_document(app) is None


def test_normalize_asyncapi_document_channel_collisions_and_bindings() -> None:
    """Test normalize_asyncapi_document handles colliding channel addresses across protocols."""
    raw_doc: dict[str, Any] = {
        "asyncapi": "3.0.0",
        "info": {"title": "Collision Test", "version": "1.0.0"},
        "channels": {
            "ws_feed": {"address": "/feed", "messages": {"inMsg": {"payload": {"type": "string"}}}},
            "sse_feed": {
                "address": "/feed",
                "messages": {"sseMsg": {"contentType": "text/event-stream", "payload": {"type": "string"}}},
            },
            "pub_feed": {"address": "/feed", "messages": {"pubMsg": {"contentType": "text/plain"}}},
        },
        "operations": {
            "ws_recv": {
                "action": "receive",
                "channel": {"$ref": "#/channels/ws_feed"},
                "messages": [{"$ref": "#/channels/ws_feed/messages/inMsg"}],
            },
            "sse_send": {
                "action": "send",
                "channel": {"$ref": "#/channels/sse_feed"},
                "messages": [{"$ref": "#/channels/sse_feed/messages/sseMsg"}],
            },
            "pub_send": {
                "action": "send",
                "channel": {"$ref": "#/channels/pub_feed"},
                "messages": [{"$ref": "#/channels/pub_feed/messages/pubMsg"}],
            },
        },
    }

    normalized = normalize_asyncapi_document(raw_doc)
    assert set(normalized["channels"].keys()) == {"feed", "feed_2", "feed_3"}
    assert normalized["channels"]["feed"]["bindings"] == {"ws": {}}
    assert normalized["channels"]["feed_2"]["bindings"] == {"http": {}}
    assert normalized["channels"]["feed_3"]["bindings"] == {}
    assert normalized["channels"]["feed_3"]["messages"]["pubMsg"]["payload"] == {}
    _assert_refs_resolve(normalized)
