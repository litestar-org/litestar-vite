==================================
AsyncAPI Export & Type Generation
==================================

Just as ``litestar-vite`` exports OpenAPI schemas and generates TypeScript SDKs for REST routes, it provides first-class export and code generation for real-time channels using the AsyncAPI 3.0 standard.

Configuration
-------------

Enable channel generation in your ``ViteConfig``:

.. code-block:: python

   from pathlib import Path
   from litestar_vite.config import TypeGenConfig, ViteConfig

   vite_config = ViteConfig(
       types=TypeGenConfig(
           enabled=True,
           output=Path("src/generated"),
           generate_channels=True,  # Default is True when types are configured
           asyncapi_path=Path("src/generated/asyncapi.json"),
           channels_ts_path=Path("src/generated/channels.ts"),
       ),
   )

CLI Commands
------------

Export AsyncAPI 3.0 Schema
^^^^^^^^^^^^^^^^^^^^^^^^^^

Export the introspected AsyncAPI 3.0 specification file directly:

.. code-block:: bash

   litestar assets export-asyncapi --output src/generated/asyncapi.json --pretty

This produces a spec-compliant AsyncAPI 3.0 document containing all WebSocket endpoints, ``ChannelsPlugin`` topics, SSE endpoints, and their message schemas.

Generate All TypeScript Types
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Generate both REST types (routes, OpenAPI models, SDK) and realtime channels in one command:

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
       protocol: "ws";
       params: Record<string, never>;
       sendPayload: ChatMessage;
       receivePayload: ChatResponse;
     };
     "room": {
       address: "/ws/rooms/{room_id}";
       protocol: "ws";
       params: {
         room_id: number;
       };
       sendPayload: unknown;
       receivePayload: RoomEvent;
     };
     "notifications": {
       address: "notifications";
       protocol: "channels";
       params: Record<string, never>;
       sendPayload: unknown;
       receivePayload: NotificationMessage;
     };
   }

   // Metadata dictionary containing runtime address information:
   export const CHANNEL_METADATA = {
     "chat": {
       address: "/ws/chat",
       protocol: "ws",
     },
     "room": {
       address: "/ws/rooms/{room_id}",
       protocol: "ws",
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
   * - ``ChannelAddress<K>``
     - The channel address string or template for channel ``K``.
   * - ``ChannelProtocol<K>``
     - The protocol for channel ``K`` (``"ws" | "channels" | "sse"``).
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
