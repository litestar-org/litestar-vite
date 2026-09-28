====================
Realtime & AsyncAPI
====================

Litestar supports WebSockets, event broadcasting via ``ChannelsPlugin``, and Server-Sent Events (SSE).

``litestar-vite`` connects these server-side endpoints with frontend code:

- **AsyncAPI Export**: Exports the registered ``AsyncAPIPlugin`` document as ``asyncapi.json``.
- **TypeScript Channel Contracts**: Generates channel definitions (``channels.ts``) for frontend clients.
- **Client Streams & Composables**: Connects to channels and event feeds with typed React hooks, Vue composables, and Svelte stores.

.. grid:: 1 1 2 2
   :gutter: 2

   .. grid-item-card:: :octicon:`plug` WebSockets
      :link: websockets
      :link-type: doc

      Build full-duplex interactive WebSocket endpoints using ``@websocket`` and ``websocket_listener``.

   .. grid-item-card:: :octicon:`broadcast` Channels & Fan-Out
      :link: channels
      :link-type: doc

      Publish and subscribe across channels using ``ChannelsPlugin`` with Memory, Redis, or Postgres backends.

   .. grid-item-card:: :octicon:`rss` Server-Sent Events
      :link: sse
      :link-type: doc

      Stream lightweight unidirectional event feeds to web clients using ``ServerSentEvent`` handlers.

   .. grid-item-card:: :octicon:`code` AsyncAPI & TypeGen
      :link: typegen
      :link-type: doc

      Export AsyncAPI specifications and emit type-safe TypeScript channel interfaces.

   .. grid-item-card:: :octicon:`tools` Browser Helpers
      :link: browser-helpers
      :link-type: doc

      Bind generated channel contracts to browser streams and link onward to the full helper reference.

   .. grid-item-card:: :octicon:`apps` Framework Composables
      :link: frameworks
      :link-type: doc

      Integrate real-time streams with React (hooks), Vue 3 (composables), and Svelte 5 (stores).

Mental Model
------------

Realtime in ``litestar-vite`` operates on a unified contract pipeline:

.. mermaid::

   flowchart LR
       subgraph Backend ["Litestar Backend"]
           WS["@websocket / listener"]
           CH["ChannelsPlugin"]
           SSE["ServerSentEvent"]
       end

       subgraph Pipeline ["Contract Pipeline"]
           GEN["Registered AsyncAPIPlugin"]
           SCHEMA["asyncapi.json"]
           TS["channels.ts"]
       end

       subgraph Frontend ["Frontend Consumer"]
           HELPERS["createChannelsStream"]
           UI["React / Vue / Svelte"]
       end

       WS --> GEN
       CH --> GEN
       SSE --> GEN
       GEN --> SCHEMA
       SCHEMA --> TS
       TS --> HELPERS
       HELPERS --> UI

1. **Schema ownership**: Configure realtime contracts in ``litestar-asyncapi`` and register its ``AsyncAPIPlugin``.
2. **Schema Emission**: With channel generation enabled, ``litestar assets build`` (or ``generate-types``) exports that plugin's document as ``asyncapi.json``. Without the plugin, no realtime document is exported.
3. **TypeScript Generation**: TypeGen emits strongly typed TypeScript contracts (``channels.ts``) directly into your frontend sources.
4. **Client Consumption**: Browser helpers and UI framework composables bind directly to the emitted types.

.. toctree::
   :maxdepth: 1
   :hidden:

   websockets
   channels
   sse
   typegen
   browser-helpers
   frameworks
