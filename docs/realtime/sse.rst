==================
Server-Sent Events
==================

Server-Sent Events (SSE) provide a lightweight, unidirectional stream from server to client over standard HTTP. Unlike WebSockets, SSE works over standard HTTP/1.1 or HTTP/2 connections without protocol upgrades, supports automatic browser reconnection natively, and bypasses restrictive corporate firewalls.

Basic SSE Stream Handler
------------------------

Litestar routes can return a ``ServerSentEvent`` response wrapping an async generator:

.. code-block:: python

   import asyncio
   from collections.abc import AsyncGenerator
   from dataclasses import dataclass
   from litestar import Litestar, get
   from litestar.response import ServerSentEvent
   from litestar.response.sse import ServerSentEventMessage

   @dataclass
   class StockUpdate:
       symbol: str
       price: float

   async def stock_ticker() -> AsyncGenerator[ServerSentEventMessage, None]:
       prices = {"AAPL": 150.0, "GOOGL": 140.0}
       for i in range(10):
           await asyncio.sleep(1.0)
           prices["AAPL"] += 0.5
           yield ServerSentEventMessage(
               data=f'{{"symbol": "AAPL", "price": {prices["AAPL"]}}}',
               event="quote",
               id=str(i),
           )

   @get("/api/stocks")
   async def stream_stocks() -> ServerSentEvent:
       return ServerSentEvent(stock_ticker())

   app = Litestar(route_handlers=[stream_stocks])

Custom Event Names & IDs
------------------------

Each ``ServerSentEvent`` response wrapper accepts default metadata fields:

- **content**: Positional payload stream or value (valid ``SSEData`` includes ``str``, ``int``, ``bytes``, ``dict``, or ``ServerSentEventMessage``).
- **event_type**: Default event type string (e.g., ``"notification"``, ``"metric"``, ``"completed"``).
- **event_id**: Tracking ID for resuming missed events after reconnects.
- **retry_duration**: Reconnect interval hint sent to the browser in milliseconds.
- **comment_message**: Comment line (often used as heartbeats/keepalives).

When yielding individual messages from an async generator, use ``ServerSentEventMessage``:

.. code-block:: python

   from litestar.response.sse import ServerSentEventMessage

   yield ServerSentEventMessage(
       data='{"status": "processing", "progress": 42}',
       event="job_progress",
       id="evt_42",
       retry=5000,
   )

Heartbeats & Keep-Alive
-----------------------

Long-lived connections may be closed by intermediate proxies or load balancers if idle. Send periodic comment events to keep connections active:

.. code-block:: python

   yield ": ping"

AsyncAPI 3.0 Documentation
--------------------------

``litestar-vite`` detects routes returning ``ServerSentEvent``:

- The endpoint path is registered as an AsyncAPI channel with the ``http`` protocol binding.
- Message payloads yielded by the generator are inspected to build the message schema.
- Event names are recorded in message headers or traits.

Consuming SSE in Browser Code
-----------------------------

Use the typed ``createEventStream`` helper from ``litestar-vite-plugin/helpers``, specifying ``transport: "sse"`` explicitly:

.. code-block:: typescript

   import { createEventStream } from "litestar-vite-plugin/helpers";

   interface StockQuote {
     symbol: string;
     price: number;
   }

   const stream = createEventStream<StockQuote>({
     url: "/api/stocks",
     transport: "sse",
     sseEvents: ["quote"],
     onEvent: (quote: StockQuote) => {
       console.log(`Received quote for ${quote.symbol}: $${quote.price}`);
     },
   });

   stream.connect();

   // To disconnect when unmounting:
   stream.dispose();

Next Steps
----------

- Export AsyncAPI specifications: :doc:`typegen`
- Use reactive composables: :doc:`frameworks`
