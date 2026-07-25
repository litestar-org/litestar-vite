"""JSON stream example using Channels and the declarative stream element."""

import asyncio
import json
import os
from collections.abc import AsyncGenerator
from pathlib import Path
from typing import Any

from litestar import Litestar, WebSocket, get, post, websocket
from litestar.channels import ChannelsPlugin
from litestar.channels.backends.memory import MemoryChannelsBackend
from litestar.di import NamedDependency
from litestar.plugins.jinja import JinjaTemplateEngine
from litestar.response import ServerSentEvent, Template
from litestar.template.config import TemplateConfig

from litestar_vite import PathConfig, RuntimeConfig, ViteConfig, VitePlugin

here = Path(__file__).parent
DEV_MODE = os.getenv("VITE_DEV_MODE", "true").lower() in {"true", "1", "yes"}


def queue_frames() -> list[dict[str, Any]]:
    """Return a deterministic queue-shaped stream with one sequence gap."""
    return [
        {
            "type": "task.progress",
            "id": "demo-1",
            "taskId": "demo",
            "attempt": 1,
            "sequence": 1,
            "message": "Connected",
            "payload": {"percent": 25},
        },
        {"type": "ping"},
        {
            "type": "task.progress",
            "id": "demo-3",
            "taskId": "demo",
            "attempt": 1,
            "sequence": 3,
            "message": "Gap detected without a client-side fill",
            "payload": {"percent": 75},
        },
    ]


@get("/")
async def index() -> Template:
    """Render the stream demo."""
    return Template(template_name="index.html.j2")


@get("/api/summary")
async def summary() -> dict[str, str]:
    """Return the standard example health payload."""
    return {"app": "litestar-vite streams", "headline": "WebSocket and SSE helpers"}


@post("/api/channels/publish")
async def publish_channel(channels: NamedDependency[ChannelsPlugin]) -> dict[str, bool]:
    """Publish one ordinary Channels message."""
    await channels.wait_published({"kind": "notice", "message": "ChannelsPlugin message"}, "demo")
    return {"published": True}


@websocket("/events/ws")
async def queue_websocket(socket: WebSocket) -> None:
    """Send the queue-shaped demonstration over WebSocket."""
    await socket.accept()
    for frame in queue_frames():
        await socket.send_json(frame)
        await asyncio.sleep(0.01)
    await socket.close()


async def queue_sse_frames() -> AsyncGenerator[dict[str, str], None]:
    """Yield named SSE frames understood by the queue preset."""
    for frame in queue_frames():
        yield {"event": "task.progress", "data": json.dumps(frame)}
        await asyncio.sleep(0.01)


@get("/events/sse")
async def queue_sse() -> ServerSentEvent:
    """Send the queue-shaped demonstration over SSE."""
    return ServerSentEvent(queue_sse_frames())


channels = ChannelsPlugin(
    backend=MemoryChannelsBackend(history=200),
    channels=["demo"],
    create_ws_route_handlers=True,
    ws_handler_base_path="/channels",
    ws_handler_send_history=20,
)
vite = VitePlugin(
    config=ViteConfig(
        mode="template",
        dev_mode=DEV_MODE,
        paths=PathConfig(root=here, resource_dir="resources"),
        runtime=RuntimeConfig(port=5070),
    )
)
templates = TemplateConfig(directory=here / "templates", engine=JinjaTemplateEngine)

app = Litestar(
    route_handlers=[index, summary, publish_channel, queue_websocket, queue_sse],
    plugins=[channels, vite],
    template_config=templates,
    debug=True,
)
