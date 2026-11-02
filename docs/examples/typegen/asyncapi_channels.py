"""AsyncAPI 3.0 document normalization and realtime WebSocket channel typegen."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from litestar_vite import TypeGenConfig
from litestar_vite.codegen import normalize_asyncapi_document


def build_sample_asyncapi_document() -> dict[str, Any]:
    """Construct a sample AsyncAPI 3.0 document for realtime notifications."""
    raw_doc: dict[str, Any] = {
        "asyncapi": "3.0.0",
        "info": {"title": "Realtime Notifications", "version": "1.0.0"},
        "channels": {
            "notifications": {
                "address": "/ws/notifications",
                "messages": {
                    "OrderCreated": {
                        "payload": {
                            "type": "object",
                            "required": ["orderId", "amountCents"],
                            "properties": {"orderId": {"type": "string"}, "amountCents": {"type": "integer"}},
                        }
                    }
                },
            }
        },
        "operations": {"receiveNotifications": {"action": "receive", "channel": {"$ref": "#/channels/notifications"}}},
    }
    return normalize_asyncapi_document(raw_doc)


def build_channel_typegen_config() -> TypeGenConfig:
    """Configure ``TypeGenConfig`` to export ``asyncapi.json`` and ``channels.ts``."""
    return TypeGenConfig(output=Path("src/generated"), generate_channels=True)


def main() -> None:
    """Verify AsyncAPI 3.0 document normalization and ``TypeGenConfig`` settings."""
    normalized = build_sample_asyncapi_document()
    cfg = build_channel_typegen_config()
    assert normalized["asyncapi"] == "3.0.0"
    assert "ws__notifications" in normalized["channels"]
    assert cfg.generate_channels is True
    assert cfg.channels_ts_path == Path("src/generated/channels.ts")


__all__ = ("build_channel_typegen_config", "build_sample_asyncapi_document", "main")
