==========================================
Server-Side Rendering & IPC Transports
==========================================

``litestar-vite`` executes server-side rendering (SSR) and component fragments using Vite 7+'s ``RunnableDevEnvironment`` in development and a managed ``stdio`` child process in production, with zero runtime dependency on external HTTP clients.

---------------------------------
Development vs. Production Model
---------------------------------

``litestar-vite`` separates development and production SSR execution into two purpose-built paths:

.. list-table::
   :header-rows: 1
   :widths: 20 35 45

   * - Mode
     - Transport
     - Execution Model
   * - **Development** (``dev_mode=True``)
     - :class:`~litestar_vite.ipc.TCPStreamIPCTransport` (``/__litestar_ssr__``)
     - Evaluates ``resources/ssr.ts`` or individual components in-memory inside the running Vite dev server via ``server.environments.ssr.runner`` (``RunnableDevEnvironment``). No separate SSR daemon process or build step is needed during development.
   * - **Production** (``dev_mode=False``)
     - :class:`~litestar_vite.ipc.StdioIPCTransport` (``stdin`` / ``stdout`` pipes)
     - Spawns the compiled SSR bundle (for example ``node bootstrap/ssr/ssr.js``) as a managed child process communicating over newline-delimited JSON pipes.

---------------------------------
Why Not a Fixed Port Daemon?
---------------------------------

Running a standalone Node.js HTTP server on a fixed port (such as ``127.0.0.1:13714``) has operational drawbacks that ``litestar-vite`` avoids:

1. **Zero Port Collisions**:
   In development, SSR shares the existing Vite dev server port over ``/__litestar_ssr__``. In production, communication happens over anonymous OS ``stdin``/``stdout`` pipes with no listening socket or port allocation.

2. **Pipe-Bound Process Lifecycle**:
   In production, the SSR worker's lifetime is bound directly to its ``stdin`` pipe. When the Litestar worker exits, the OS closes the pipe, the Node/Bun worker receives ``EOF`` on ``stdin``, and the child process terminates immediately without leaving orphaned background processes.

3. **HMR Cache Invalidation in Dev**:
   Because development SSR runs inside Vite's ``RunnableDevEnvironment``, edits to Vue, React, or Svelte components invalidate the module and its importer chain in memory without rebuilding an SSR bundle.

---------------------------------
Production Stdio Worker Protocol
---------------------------------

In production, :class:`~litestar_vite.ipc.StdioIPCTransport` spawns the SSR bundle with ``anyio.open_process()`` and multiplexes concurrent render requests over ``stdin``/``stdout`` using newline-delimited JSON messages keyed by integer correlation IDs:

.. mermaid::

   sequenceDiagram
       autonumber
       participant App as Litestar Application
       participant Transport as StdioIPCTransport
       participant Pipe as OS Pipe (stdin/stdout)
       participant Worker as Node/Bun SSR Worker

       App->>Transport: start()
       Transport->>Pipe: anyio.open_process(command)
       Transport->>Transport: Start background stdout & stderr readers

       App->>Transport: send_request({"method": "render", "params": page})
       Transport->>Pipe: stdin.send({"id": 1, "method": "render", "params": page}\n)
       Pipe->>Worker: readline "line" event
       Worker->>Worker: await render(page)
       Worker->>Pipe: stdout.write({"id": 1, "result": {"head": [...], "body": "..."}}\n)
       Pipe->>Transport: stdout reader correlates response id=1
       Transport-->>App: Return render result dict

       App->>Transport: close()
       Transport->>Pipe: stdin.aclose() (EOF)
       Pipe->>Worker: readline "close" event
       Worker->>Worker: process.exit(0)

``StdioIPCTransport`` resolves platform executable shims (``.cmd`` / ``.exe`` on Windows) via ``shutil.which`` and continuously drains the child ``stderr`` stream in a background task so pipe buffers never block.

---------------------------------
Dual-Mode SSR Entrypoint
---------------------------------

Generated ``resources/ssr.ts`` / ``resources/ssr.tsx`` entrypoints support both modes in a single file:

1. They export ``default async function render(page)`` so Vite's ``RunnableDevEnvironment.runner`` can import and invoke ``render(page)`` directly in development.
2. When executed outside Vite dev mode (``if (!import.meta.env?.DEV)``), they start a ``node:readline`` loop over ``process.stdin`` and write JSON responses to ``process.stdout``.

---------------------------------
Python Configuration
---------------------------------

Enable SSR in ``InertiaConfig``:

.. code-block:: python

   from pathlib import Path
   from litestar import Litestar
   from litestar_vite import InertiaConfig, InertiaSSRConfig, PathConfig, ViteConfig, VitePlugin

   vite_config = ViteConfig(
       paths=PathConfig(
           root=Path(__file__).parent,
           resource_dir="resources",
           bundle_dir="public",
       ),
       inertia=InertiaConfig(
           ssr=InertiaSSRConfig(
               command=["node", "bootstrap/ssr/ssr.js"],
           ),
       ),
   )

   vite_plugin = VitePlugin(config=vite_config)
   app = Litestar(plugins=[vite_plugin])

Or instantiate an IPC transport directly:

.. code-block:: python

   from litestar_vite.ipc import StdioIPCTransport, TCPStreamIPCTransport

   stdio_transport = StdioIPCTransport(
       command=["node", "bootstrap/ssr/ssr.js"],
       max_restarts=3,
   )

   dev_transport = TCPStreamIPCTransport(
       host="127.0.0.1",
       port=5173,
       path="/__litestar_ssr__",
   )
