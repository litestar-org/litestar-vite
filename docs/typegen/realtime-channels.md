# AsyncAPI Channels, WebSockets & Server-Sent Events

When your Litestar application registers `litestar-asyncapi`'s `AsyncAPIPlugin` (for WebSockets, `ChannelsPlugin`, or Server-Sent Events), Litestar Vite extracts and normalizes the AsyncAPI 3.0 document into `src/generated/asyncapi.json` and generates a zero-dependency typed client in `src/generated/channels.ts`.

---

## AsyncAPI Ownership & Configuration

`litestar-asyncapi` owns AsyncAPI 3.0 schema extraction across your Litestar routes, while `litestar_vite.codegen.normalize_asyncapi_document()` normalizes channel addresses, collision-safe channel keys, and JSON Schema message payloads:

```python title="docs/examples/typegen/asyncapi_channels.py"
--8<-- "docs/examples/typegen/asyncapi_channels.py"
```

---

## ChannelsPlugin Pub/Sub Fan-Out

Use Litestar's `ChannelsPlugin` when you want server-side publish/subscribe fan-out across one or more application workers:

| Backend | Import | Best For |
| --- | --- | --- |
| `MemoryChannelsBackend(history=200)` | `litestar.channels.backends.memory` | Single-process deployments and local development with bounded event replay. |
| `RedisChannelsPubSubBackend` | `litestar.channels.backends.redis` | Low-latency multi-worker pub/sub fan-out over Redis. |
| `RedisChannelsStreamBackend` | `litestar.channels.backends.redis` | Durable Redis Streams with consumer history and reconnect replay. |

```python
from litestar import Litestar, post
from litestar.channels import ChannelsPlugin
from litestar.channels.backends.memory import MemoryChannelsBackend


@post("/api/rooms/{room_id:str}/broadcast", sync_to_thread=False)
def broadcast_to_room(room_id: str, message: str, channels: ChannelsPlugin) -> dict[str, str]:
    """Publish a payload to a dynamic channel subscribed by WebSocket clients."""
    channels.publish({"room_id": room_id, "message": message}, channels=[f"chat_{room_id}"])
    return {"status": "published"}


app = Litestar(
    route_handlers=[broadcast_to_room],
    plugins=[
        ChannelsPlugin(
            backend=MemoryChannelsBackend(history=100),
            arbitrary_channels_allowed=True,
            create_ws_route_handlers=True,
            ws_handler_base_path="/ws",
        ),
    ],
)
```

---

## WebSocket Handlers

Use `@websocket_listener` for typed request/response message loops or low-level `@websocket` when you need full lifecycle control over `socket.accept()`, `socket.send_json()`, and disconnect handling:

```python
from litestar import WebSocket, websocket, websocket_listener
from msgspec import Struct


class ChatInbound(Struct):
    text: str


class ChatOutbound(Struct):
    room_id: str
    sender: str
    text: str


@websocket_listener("/ws/chat/{room_id:str}", name="chat:room")
def handle_chat_message(data: ChatInbound, room_id: str) -> ChatOutbound:
    """Receive typed JSON and broadcast a typed response."""
    return ChatOutbound(room_id=room_id, sender="user", text=data.text)


@websocket("/ws/raw/{stream_id:str}", name="raw:stream")
async def raw_socket_handler(socket: WebSocket, stream_id: str) -> None:
    """Low-level WebSocket lifecycle handler."""
    await socket.accept()
    await socket.send_json({"stream_id": stream_id, "status": "connected"})
    await socket.close()
```

---

## Server-Sent Events

For unidirectional server-to-browser streaming over HTTP/1.1 or HTTP/2, return a `ServerSentEvent` wrapping an async generator of `ServerSentEventMessage` items:

```python
import asyncio
from collections.abc import AsyncGenerator
from litestar import get
from litestar.response import ServerSentEvent, ServerSentEventMessage
from litestar.serialization import encode_json
from msgspec import Struct


class OrderStatusEvent(Struct):
    order_id: str
    status: str


async def _order_event_generator(order_id: str) -> AsyncGenerator[ServerSentEventMessage, None]:
    for step, status in enumerate(("queued", "processing", "completed"), start=1):
        payload = encode_json(OrderStatusEvent(order_id=order_id, status=status)).decode("utf-8")
        yield ServerSentEventMessage(data=payload, event="order.updated", id=str(step), retry=3000)
        await asyncio.sleep(0.5)


@get("/api/orders/{order_id:str}/events", name="orders:events", sync_to_thread=False)
def stream_order_events(order_id: str) -> ServerSentEvent:
    """Stream Server-Sent Events for an order."""
    return ServerSentEvent(_order_event_generator(order_id))
```

---

## Generated `channels.ts` & `createTypedChannels`

When `TypeGenConfig(generate_channels=True)` is active, `src/generated/channels.ts` exports:

- `RealtimeChannels` — Mapping of every AsyncAPI channel key to `{ address, protocol, params, sendPayload, receivePayload }`.
- `ChannelKey`, `ChannelAddress<K>`, `ChannelProtocol<K>`, `ChannelParams<K>`, `ChannelSendPayload<K>`, `ChannelReceivePayload<K>`.
- `CHANNEL_METADATA` — Runtime descriptor passed to `createTypedChannels(CHANNEL_METADATA)`.

```typescript title="src/realtime.ts"
import { createTypedChannels } from "litestar-vite-plugin/helpers";
import { CHANNEL_METADATA, type RealtimeChannels } from "./generated/channels";

const channels = createTypedChannels<RealtimeChannels>(CHANNEL_METADATA);
const stream = channels.stream("ws__notifications", {
  onEvent: (payload: { orderId: string; amountCents: number }) => {
    console.log(payload.orderId);
  },
});
```

See [Browser & Framework Event Streams](event-streams.md) for `createEventStream()`, `<litestar-stream>`, React/Vue/Svelte hooks, authentication tickets, and gap recovery.
