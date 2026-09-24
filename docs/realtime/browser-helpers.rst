====================
Browser Helpers
====================

The ``litestar-vite-plugin/helpers`` module provides strongly typed client utilities for browser environments to manage WebSocket and SSE stream lifecycles, handle reconnects, and bind to generated channel contracts.

Channels Streams (WebSockets)
-----------------------------

The ``createChannelsStream`` helper connects to Litestar WebSocket endpoints or ``ChannelsPlugin`` streams. It returns a receive-only ``EventStream`` instance; teardown is performed via ``stream.dispose()``:

.. code-block:: typescript

   import { createChannelsStream } from "litestar-vite-plugin/helpers";

   interface ChatMessage {
     user: string;
     text: string;
   }

   const stream = createChannelsStream<ChatMessage>({
     channel: "chat",
     basePath: "/ws",
     onOpen: (url: string) => {
       console.log("WebSocket connected to", url);
     },
     onEvent: (message: ChatMessage) => {
       console.log("New message:", message.text);
     },
     onClose: () => {
       console.log("Stream closed");
     },
   });

   // Connect the stream:
   stream.connect();

   // Disconnect and release resources when done:
   stream.dispose();

Channel Parameter Interpolation
-------------------------------

When channels use dynamic path segments (e.g., ``/ws/rooms/{room_id}``), pass the parameters in the ``params`` option:

.. code-block:: typescript

   import { createChannelsStream } from "litestar-vite-plugin/helpers";

   interface RoomEvent {
     type: string;
     payload: string;
   }

   const roomStream = createChannelsStream<RoomEvent, { room_id: number }>({
     channel: "/ws/rooms/{room_id}",
     params: { room_id: 42 },
     onEvent: (event: RoomEvent) => {
       console.log("Room update:", event);
     },
   });

   roomStream.connect();

The helper replaces ``{room_id}`` with the URL-encoded value ``42``, resolving to ``/ws/rooms/42``.

Binding to Generated Channel Contracts
--------------------------------------

Combine ``createChannelsStream`` with types from the generated ``channels.ts`` for complete end-to-end type safety:

.. code-block:: typescript

   import { createChannelsStream } from "litestar-vite-plugin/helpers";
   import type {
     ChannelParams,
     ChannelReceivePayload,
     ChannelSendPayload,
   } from "@/generated/channels";

   type RoomEvent = ChannelReceivePayload<"room">;
   type RoomParams = ChannelParams<"room">;

   const stream = createChannelsStream<RoomEvent, RoomParams>({
     channel: "room",
     params: { room_id: 101 },
     onEvent: (msg: RoomEvent) => {
       console.log("Room message:", msg);
     },
   });

   stream.connect();

Server-Sent Event Streams
-------------------------

The ``createEventStream`` helper wraps browser ``EventSource`` with typed event parsing. Set ``transport: "sse"`` explicitly when connecting to SSE endpoints:

.. code-block:: typescript

   import { createEventStream } from "litestar-vite-plugin/helpers";

   interface OrderStatus {
     order_id: string;
     status: "pending" | "processing" | "shipped";
   }

   const sse = createEventStream<OrderStatus>({
     url: "/api/orders/123/stream",
     transport: "sse",
     sseEvents: ["status_update"],
     onEvent: (update: OrderStatus) => {
       console.log(`Order status is now: ${update.status}`);
     },
   });

   sse.connect();

Queue Task Progress Streams
---------------------------

For background job progress (such as tasks submitted through Litestar background tasks or queues), use ``createQueueEventStream`` with a discriminated scope target:

.. code-block:: typescript

   import { createQueueEventStream } from "litestar-vite-plugin/helpers";

   interface TaskProgress {
     percentage: number;
     message: string;
   }

   const taskStream = createQueueEventStream<TaskProgress>({
     scope: "task",
     taskId: "job-9876",
     onEvent: (progress: TaskProgress) => {
       console.log(`Task ${progress.percentage}% complete: ${progress.message}`);
     },
   });

   taskStream.connect();

Next Steps
----------

- Connect reactive UI components in React, Vue, or Svelte: :doc:`frameworks`
