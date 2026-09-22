====================
Browser Helpers
====================

The ``litestar-vite-plugin/helpers`` module provides strongly typed client utilities for browser environments to manage WebSocket and SSE stream lifecycles, handle reconnects, and bind to generated channel contracts.

Channels Streams (WebSockets)
-----------------------------

The ``createChannelsStream`` helper connects to Litestar WebSocket endpoints or ``ChannelsPlugin`` streams:

.. code-block:: typescript

   import { createChannelsStream } from "litestar-vite-plugin/helpers";

   interface ChatMessage {
     user: string;
     text: string;
   }

   const stream = createChannelsStream<ChatMessage>({
     channel: "chat",
     basePath: "/ws",
     onOpen: () => {
       console.log("WebSocket connected");
     },
     onMessage: (message) => {
       console.log("New message:", message.text);
     },
     onError: (error) => {
       console.error("Stream error:", error);
     },
     onClose: (event) => {
       console.log("Closed with code:", event.code);
     },
     reconnect: true,
     reconnectAttempts: 5,
     reconnectDelay: 1000,
   });

   // Send a message over the stream:
   stream.send({ user: "Alice", text: "Hello!" });

   // Close connection when done:
   stream.close();

Channel Parameter Interpolation
-------------------------------

When channels use dynamic path segments (e.g., ``/ws/rooms/{room_id}``), pass the parameters in the ``params`` option:

.. code-block:: typescript

   const roomStream = createChannelsStream<RoomEvent, { room_id: number }>({
     channel: "/ws/rooms/{room_id}",
     params: { room_id: 42 },
     onMessage: (event) => {
       console.log("Room update:", event);
     },
   });

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
     onMessage: (msg) => {
       // msg is strictly typed as ChannelReceivePayload<"room">
     },
   });

Server-Sent Event Streams
-------------------------

The ``createEventStream`` helper wraps browser ``EventSource`` with typed event parsing:

.. code-block:: typescript

   import { createEventStream } from "litestar-vite-plugin/helpers";

   interface OrderStatus {
     order_id: string;
     status: "pending" | "processing" | "shipped";
   }

   const sse = createEventStream<OrderStatus>({
     url: "/api/orders/123/stream",
     sseEvents: ["status_update"],
     onMessage: (update) => {
       console.log(`Order status is now: ${update.status}`);
     },
     onError: (err) => {
       console.warn("EventSource disconnected:", err);
     },
   });

Queue Task Progress Streams
---------------------------

For background job progress (such as tasks submitted through Litestar background tasks or queues), use ``createQueueEventStream``:

.. code-block:: typescript

   import { createQueueEventStream } from "litestar-vite-plugin/helpers";

   interface TaskProgress {
     percentage: number;
     message: string;
   }

   const taskStream = createQueueEventStream<TaskProgress>({
     taskId: "job-9876",
     onProgress: (progress) => {
       console.log(`Task ${progress.percentage}% complete`);
     },
     onComplete: (result) => {
       console.log("Task finished:", result);
     },
   });

Next Steps
----------

- Connect reactive UI components in React, Vue, or Svelte: :doc:`frameworks`
