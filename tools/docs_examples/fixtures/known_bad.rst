Known Bad Fixture
=================

.. note::

   This fixture is intentionally broken and exists solely to test the
   documentation example verification gate (task 10.3). It is not part of the
   published documentation and must never be referenced in any toctree.

.. code-block:: typescript

   import { createEventStream } from "litestar-vite-plugin/helpers"

   const stream = createEventStream({
     url: "/x",
     onMessage: (m: any) => {},
   })

   const streamMissing = createEventStream({
     url: "/y",
   })

.. code-block:: python

   @websocket_listener("/ws")
   def handle_ws() -> None:
       pass

.. code-block:: python

   from litestar_vite import TypeGenConfig

   config = TypeGenConfig(enabled=True)
