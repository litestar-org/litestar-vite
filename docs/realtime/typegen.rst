==================================
AsyncAPI Export & Type Generation
==================================

``litestar-vite`` exports AsyncAPI 3.0 schemas and generates TypeScript channel contracts alongside its OpenAPI and route generators.

Configuration
-------------

Register ``AsyncAPIPlugin`` from ``litestar-asyncapi`` and enable channel generation in your ``ViteConfig``:

.. code-block:: python

   from pathlib import Path
   from litestar import Litestar
   from litestar_asyncapi import AsyncAPIPlugin
   from litestar_vite import VitePlugin
   from litestar_vite.config import TypeGenConfig, ViteConfig

   vite_config = ViteConfig(
       types=TypeGenConfig(
           output=Path("src/generated"),
           generate_channels=True,
           asyncapi_path=Path("src/generated/asyncapi.json"),
           channels_ts_path=Path("src/generated/channels.ts"),
       ),
   )

   app = Litestar(
       plugins=[
           AsyncAPIPlugin(),
           VitePlugin(config=vite_config),
       ],
   )

CLI Commands
------------

Generate All TypeScript Types and Schemas
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Generate REST types (routes, OpenAPI models, SDK) and realtime channels in one command:

.. code-block:: bash

   litestar assets generate-types

This runs the TypeGen pipeline, generating:

- ``src/generated/openapi.json`` and ``src/generated/routes.json``
- ``src/generated/asyncapi.json``
- ``src/generated/channels.ts`` (Realtime contracts)
- ``src/generated/schemas.ts`` (Ergonomic form and response types)
- ``src/generated/routes.ts`` (Type-safe Ziggy-style router)

The Generated ``channels.ts`` Contract
---------------------------------------

The emitted ``channels.ts`` file contains strongly typed interfaces mapping every channel in your application:

.. code-block:: typescript

   // RealtimeChannels maps channel identifier keys to contracts:
   export interface RealtimeChannels {
     "chat": {
       address: "/ws/chat";
       protocol: "websocket";
       params: Record<string, never>;
       send: ChatMessage;
       receive: ChatResponse;
     };
     "room": {
       address: "/ws/rooms/{room_id}";
       protocol: "websocket";
       params: {
         room_id: string;
       };
       send: never;
       receive: RoomEvent;
     };
     "notifications": {
       address: "notifications";
       protocol: "channels";
       params: Record<string, never>;
       send: never;
       receive: NotificationPayload;
     };
   }

   export type ChannelKey = keyof RealtimeChannels;

   export interface ChannelMetadata {
     address: string;
     protocol: "websocket" | "channels" | "sse";
   }

   // Metadata dictionary containing runtime address information:
   export const CHANNEL_METADATA: Record<ChannelKey, ChannelMetadata> = {
     "chat": {
       address: "/ws/chat",
       protocol: "websocket",
     },
     "room": {
       address: "/ws/rooms/{room_id}",
       protocol: "websocket",
     },
     "notifications": {
       address: "notifications",
       protocol: "channels",
     },
   } as const;

Type Helpers
------------

The generated file exports ergonomic utility types for use in application code:

.. list-table::
   :widths: 35 65
   :header-rows: 1

   * - Type Helper
     - Purpose
   * - ``ChannelKey``
     - Union of all registered channel keys (e.g., ``"chat" | "room" | "notifications"``).
   * - ``ChannelAddress``
     - Union of all registered channel address strings or templates.
   * - ``ChannelProtocol<K>``
     - The protocol for channel ``K`` (``"websocket" | "channels" | "sse"``).
   * - ``ChannelParams<K>``
     - TypeScript object representing required URL/channel parameters.
   * - ``ChannelSendPayload<K>``
     - Expected message payload shape when sending to channel ``K``.
   * - ``ChannelReceivePayload<K>``
     - Expected message payload shape when receiving from channel ``K``.

Next Steps
----------

- Connect using browser helpers: :doc:`browser-helpers`
- Connect using framework composables: :doc:`frameworks`
