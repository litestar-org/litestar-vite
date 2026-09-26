==========================================
Server-Side Rendering & IPC Transports
==========================================

``litestar-vite`` communicates with JavaScript SSR workers over AnyIO inter-process communication (IPC) transports rather than an external HTTP client.

---------------------------------
Process Lifecycle & Transports
---------------------------------

Running a standalone Node.js HTTP server on a fixed port (such as ``127.0.0.1:13714``) for SSR has a few operational drawbacks:

1. **Port Collisions**:
   Fixed TCP ports collide when multiple dev servers or test workers run on the same host.

2. **Orphaned Worker Processes**:
   If the parent Python process exits abruptly, an independent HTTP server process can remain running in the background holding its port open.

3. **Pipe-Bound Lifecycle**:
   With standard I/O pipes, the child worker's lifetime is tied to its ``stdin`` stream. When the Python process exits, the OS closes the pipe, the worker receives ``EOF`` on ``stdin``, and the worker exits.

---------------------------------
Transport Matrix
---------------------------------

``litestar-vite`` provides three transports in ``litestar_vite.ipc``, configured via ``InertiaConfig``:

.. list-table::
   :header-rows: 1
   :widths: 25 25 25 25

   * - Transport
     - Platforms
     - Framing
     - Process Model
   * - ``StdioIPCTransport``
     - Linux, macOS, Windows
     - Line-delimited JSON (NDJSON)
     - Managed subprocess (``stdin`` EOF terminates child)
   * - ``UnixSocketIPCTransport``
     - Linux, macOS (POSIX)
     - NDJSON over ``AF_UNIX`` stream
     - Local filesystem socket (e.g. ``/tmp/litestar-ssr.sock``)
   * - ``TCPStreamIPCTransport``
     - Linux, macOS, Windows
     - NDJSON over AnyIO TCP stream
     - Remote worker or container sidecar

~~~~~~~~~~~~~~~~~~~~~~~~~
Stdio Worker (NDJSON RPC)
~~~~~~~~~~~~~~~~~~~~~~~~~

``StdioIPCTransport`` is the default transport across all platforms. Litestar spawns the SSR worker with ``anyio.open_process()`` and exchanges newline-delimited JSON (NDJSON) messages keyed by integer request IDs:

.. mermaid::

   sequenceDiagram
       autonumber
       participant App as Litestar Application
       participant Transport as StdioIPCTransport
       participant Pipe as OS Pipe
       participant Worker as Node/Bun SSR Worker

       App->>Transport: start()
       Transport->>Pipe: anyio.open_process(node/bun, ssr.ts)
       Transport->>Transport: Start background stdout & stderr readers

       App->>Transport: send_request(payload)
       Transport->>Pipe: stdin.send({"id": 1, "method": "render", "params": ...}\n)
       Pipe->>Worker: readline "line" event
       Worker->>Worker: Render component to HTML
       Worker->>Pipe: stdout.write({"id": 1, "result": {...}}\n)
       Pipe->>Transport: stdout reader parses NDJSON
       Transport-->>App: Return render result dict

       App->>Transport: stop()
       Transport->>Pipe: stdin.aclose() (EOF)
       Pipe->>Worker: readline "close" event
       Worker->>Worker: process.exit(0)

~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Unix Domain Sockets (UDS)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

On Linux and macOS, ``UnixSocketIPCTransport`` communicates over a local ``AF_UNIX`` socket using ``anyio.connect_unix()``. If the configured socket path exceeds the macOS 104-byte ``sun_path`` limit, ``litestar-vite`` hashes the path into ``/tmp/lv-<hash>.sock``.

~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
TCP Stream
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

When the SSR worker runs in a separate container or host, ``TCPStreamIPCTransport`` connects via ``anyio.connect_tcp()`` and uses the same NDJSON request/response framing over the socket stream.

---------------------------------
Windows Support
---------------------------------

Python's default ``ProactorEventLoop`` on Windows does not support asynchronous ``AF_UNIX`` stream sockets in AnyIO. ``UnixSocketIPCTransport`` raises ``UnsupportedPlatformError`` on Windows; use ``StdioIPCTransport`` (the default) or ``TCPStreamIPCTransport`` on Windows.

``StdioIPCTransport`` resolves executable shims (``.cmd`` / ``.exe``) via ``shutil.which`` and continuously drains the child ``stderr`` stream in a background task so pipe buffers do not block on Windows.

---------------------------------
Bun Runtime Usage
---------------------------------

The SSR worker entrypoint runs on both Node.js and Bun:

.. docs-example: skip
.. code-block:: bash

   bun run resources/ssr.ts --stdio

---------------------------------
Python Configuration
---------------------------------

Enable SSR in ``InertiaConfig``:

.. code-block:: python

   from pathlib import Path
   from litestar import Litestar
   from litestar_vite import InertiaConfig, PathConfig, ViteConfig, VitePlugin

   vite_config = ViteConfig(
       paths=PathConfig(
           root=Path(__file__).parent,
           resource_dir="resources",
           bundle_dir="public",
       ),
       inertia=InertiaConfig(
           ssr=True,
       ),
   )

   vite_plugin = VitePlugin(config=vite_config)
   app = Litestar(plugins=[vite_plugin])

Or instantiate an IPC transport directly:

.. code-block:: python

   from litestar_vite.ipc import StdioIPCTransport, UnixSocketIPCTransport

   stdio_transport = StdioIPCTransport(
       command=["node", "resources/bootstrap/ssr/ssr.js", "--stdio"],
       max_restarts=3,
   )

   uds_transport = UnixSocketIPCTransport(
       socket_path="/tmp/litestar-ssr.sock",
   )
