==================
Server-Sent Events
==================

Server-Sent Events (SSE) provide a lightweight, unidirectional stream from server to client over standard HTTP. Unlike WebSockets, SSE works over standard HTTP/1.1 or HTTP/2 connections without protocol upgrades, supports automatic browser reconnection natively, and bypasses restrictive corporate firewalls.

Basic SSE Stream Handler
------------------------

Litestar routes can return an async generator yielding ``ServerSentEvent`` instances:

.. code-block:: python

   import asyncio
   from collections.abc import AsyncGenerator
   from dataclasses import dataclass
   from litestar import Litestar, get
   from litestar.response import ServerSentEvent

   @dataclass
   class StockUpdate:
       symbol: str
       price: float

   async def stock_ticker() -> AsyncGenerator[ServerSentEvent, None]:
       prices = {"AAPL": 150.0, "GOOGL": 140.0}
       for i in range(10):
           await asyncio.sleep(1.0)
           prices["AAPL"] += 0.5
           yield ServerSentEvent(
               data=StockUpdate(symbol="AAPL", price=prices["AAPL"]),
               event="quote",
               event_id=str(i),
           )

   @get("/api/stocks", response_class=ServerSentEvent)
   async def stream_stocks() -> AsyncGenerator[ServerSentEvent, None]:
       return stock_ticker()

   app = Litestar(route_handlers=[stream_stocks])

Custom Event Names & IDs
------------------------

Each ``ServerSentEvent`` accepts metadata fields:

- **data**: Payload object (automatically JSON-serialized if a dataclass, msgspec Struct, or Pydantic model).
- **event**: Custom event type string (e.g., ``"notification"``, ``"metric"``, ``"completed"``).
- **event_id**: Unique tracking ID for resuming missed events after reconnects.
- **retry_duration_milliseconds**: Reconnect interval hint sent to the browser.
- **comment**: Comment line (often used as heartbeats/keepalives).

.. code-block:: python

   yield ServerSentEvent(
       data={"status": "processing", "progress": 42},
       event="job_progress",
       event_id="evt_42",
       retry_duration_milliseconds=5000,
   )

Heartbeats & Keep-Alive
-----------------------

Long-lived connections may be closed by intermediate proxies or load balancers if idle. Send periodic comment events to keep connections active:

.. code-block:: python

   yield ServerSentEvent(comment="ping")

AsyncAPI 3.0 Documentation
--------------------------

``litestar-vite`` detects routes returning ``ServerSentEvent``:
- The endpoint path is registered as an AsyncAPI channel with the ``http`` protocol binding.
- Message payloads yielded by the generator are inspected to build the message schema.
- Event names are recorded in message headers or traits.

Consuming SSE in Browser Code
-----------------------------

Use the typed ``createEventStream`` helper from ``litestar-vite-plugin/helpers``:

.. code-block:: typescript

   import { createEventStream } from "litestar-vite-plugin/helpers";

   interface StockQuote {
     symbol: string;
     price: number;
   }

   const stream = createEventStream<StockQuote>({
     url: "/api/stocks",
     sseEvents: ["quote"],
     onMessage: (quote) => {
       console.log(`Received quote for ${quote.symbol}: $${quote.price}`);
     },
   });

   // To disconnect when unmounting:
   stream.close();

Next Steps
----------

- Export AsyncAPI specifications: :doc:`typegen`
- Use reactive composables: :doc:`frameworks`
