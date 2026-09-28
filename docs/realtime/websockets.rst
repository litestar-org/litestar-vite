==========
WebSockets
==========

Litestar provides two ways to build WebSocket endpoints:

1. Low-level ``@websocket`` route handlers for explicit lifecycle and stream management.
2. Declarative ``websocket_listener`` handlers for automatic deserialization, validation, and response serialization.

For generated contracts, register ``litestar-asyncapi.AsyncAPIPlugin`` and configure
the endpoint schemas there. ``litestar-vite`` exports its document; it does not
infer contracts directly from these handlers.

Declarative WebSocket Listeners
--------------------------------

The ``websocket_listener`` decorator is the recommended way to build WebSocket message handlers. It automatically parses incoming JSON frames into typed structures (such as msgspec ``Struct`` or Python dataclasses) and serializes the return value back to the client:

.. code-block:: python

   from dataclasses import dataclass
   from litestar import Litestar
   from litestar.handlers import websocket_listener

   @dataclass
   class ChatMessage:
       text: str
       user_id: int

   @dataclass
   class ChatResponse:
       status: str
       echo: ChatMessage

   @websocket_listener("/ws/chat")
   def handle_chat_message(data: ChatMessage) -> ChatResponse:
       return ChatResponse(status="delivered", echo=data)

   app = Litestar(route_handlers=[handle_chat_message])

Document ``ChatMessage`` and ``ChatResponse`` in your AsyncAPI configuration to
carry their payload shapes into generated frontend contracts.

Low-Level WebSocket Handlers
----------------------------

For full control over connection lifecycles, heartbeats, authentication, or streaming loops, use ``@websocket``:

.. code-block:: python

   from litestar import Litestar, WebSocket, websocket

   @websocket("/ws/stream")
   async def handle_stream(socket: WebSocket) -> None:
       await socket.accept()
       try:
           while True:
               data = await socket.receive_json()
               await socket.send_json({"ack": True, "received": data})
       except Exception:
           await socket.close()

   app = Litestar(route_handlers=[handle_stream])

Path Parameters in WebSocket Endpoints
--------------------------------------

WebSocket routes support URL parameters:

.. code-block:: python

   from litestar import WebSocket, websocket

   @websocket("/ws/rooms/{room_id:int}")
   async def room_stream(socket: WebSocket, room_id: int) -> None:
       """Manage an individual room stream."""
       await socket.accept()
       await socket.send_json({"room": room_id, "status": "connected"})

The generated TypeScript parameter types follow the channel parameters in the
AsyncAPIPlugin document. Review that document when configuring typed URL parameters.

Authentication and Guards
-------------------------

WebSocket connections can be guarded like HTTP endpoints:

.. code-block:: python

   from litestar.connection import ASGIConnection
   from litestar.exceptions import NotAuthorizedException
   from litestar.handlers import BaseRouteHandler, websocket_listener

   def require_auth(connection: ASGIConnection, _: BaseRouteHandler) -> None:
       if not connection.scope.get("user"):
           raise NotAuthorizedException("Authentication required")

   @websocket_listener("/ws/secure", guards=[require_auth])
   def secure_handler(data: dict) -> dict:
       return {"status": "authorized"}

Next Steps
----------

- Connect WebSocket endpoints to publish/subscribe backends: :doc:`channels`
- Export typed contracts for frontend clients: :doc:`typegen`
- Use the typed client helper in browser code: :doc:`browser-helpers`
