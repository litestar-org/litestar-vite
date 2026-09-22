====================
Channels & Fan-Out
====================

Litestar's ``ChannelsPlugin`` provides publish/subscribe messaging across application instances and WebSocket clients. It decouples message producers (such as background workers or HTTP request handlers) from active browser connections.

Configuring ChannelsPlugin
--------------------------

Register the ``ChannelsPlugin`` with your chosen backend:

.. code-block:: python

   from litestar import Litestar
   from litestar.channels import ChannelsPlugin
   from litestar.channels.backends.memory import MemoryChannelsBackend
   from litestar_vite import VitePlugin

   channels = ChannelsPlugin(
       backend=MemoryChannelsBackend(),
       channels=["notifications", "system_events"],
       arbitrary_channels_allowed=True,
   )

   app = Litestar(
       plugins=[channels, VitePlugin()],
   )

For multi-process or multi-server deployments, use the Redis or PostgreSQL channel backends:

.. code-block:: python

   from litestar.channels.backends.redis import RedisChannelsBackend

   channels = ChannelsPlugin(
       backend=RedisChannelsBackend(url="redis://localhost:6379"),
       channels=["chat_{room_id}"],
   )

Publishing Messages
-------------------

Any route handler, service, or background task can broadcast messages to active channel subscribers:

.. code-block:: python

   from dataclasses import dataclass
   from litestar import Litestar, post
   from litestar.channels import ChannelsPlugin

   @dataclass
   class AlertEvent:
       title: str
       level: str

   @post("/api/alerts")
   async def broadcast_alert(data: AlertEvent, channels: ChannelsPlugin) -> dict:
       await channels.publish(data, channels=["notifications"])
       return {"status": "broadcasted"}

Dynamic & Parameterized Channels
--------------------------------

Channels can include dynamic segments such as user IDs or room IDs:

.. code-block:: python

   @post("/api/rooms/{room_id:int}/message")
   async def send_room_message(
       room_id: int,
       text: str,
       channels: ChannelsPlugin,
   ) -> dict:
       channel_name = f"chat_{room_id}"
       await channels.publish({"message": text}, channels=[channel_name])
       return {"status": "sent"}

Subscribing via WebSockets
--------------------------

``ChannelsPlugin`` provides a built-in WebSocket handler stream:

.. code-block:: python

   # Built-in handler streaming all channel messages to connected client:
   route_handlers = [
       channels.create_route_handler("/ws/events"),
   ]

AsyncAPI 3.0 Introspection
--------------------------

When ``litestar-vite`` inspects your application:
- All static channels listed in ``channels=[...]`` are extracted as individual AsyncAPI channels.
- Dynamic channels with parameter patterns (e.g., ``chat_{room_id}``) are converted to parameterized AsyncAPI channel addresses.
- Message payloads published through the plugin are introspected into schema definitions under AsyncAPI components.

Next Steps
----------

- Stream server events using HTTP: :doc:`sse`
- Export AsyncAPI schemas and TypeScript contracts: :doc:`typegen`
- Connect from browser code: :doc:`browser-helpers`
