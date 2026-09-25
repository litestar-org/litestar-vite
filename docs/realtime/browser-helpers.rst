====================
Browser Helpers
====================

The ``litestar-vite-plugin/helpers`` module provides strongly typed client utilities for browser environments to manage WebSocket and SSE stream lifecycles, handle reconnects, and bind to generated channel contracts.

.. seealso::
   Full API reference for ``createEventStream()``, ``createChannelsStream()``, and
   ``createQueueEventStream()`` — including ``buildUrl``, reconnect backoff, heartbeat
   filtering, deduplication, sequence-gap handling, and ``defineStreamElement()`` —
   lives in :doc:`../usage/streams`.

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

Next Steps
----------

- Full options, lifecycle, and stream element reference: :doc:`../usage/streams`
- Connect reactive UI components in React, Vue, or Svelte: :doc:`frameworks`
