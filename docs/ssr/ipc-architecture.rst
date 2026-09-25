=================================================
Server-Side Rendering & Modern IPC Architecture
=================================================

Server-Side Rendering (SSR) in modern web frameworks bridges fast initial page delivery, SEO discoverability, and rich client interactivity. Traditional Python integrations delegate SSR to Node.js via external HTTP servers communicating over local TCP sockets (such as ``http://127.0.0.1:13714``). While conceptually simple, HTTP-over-TCP introduces structural bottlenecks, cross-platform hazards, and operational debt in production and development environments.

Litestar Vite replaces legacy HTTP loopback runners with an AnyIO-powered, multi-transport Inter-Process Communication (IPC) architecture. This system delivers zero-HTTPX execution, robust process lifecycle coupling, high throughput, and seamless parity across Linux, macOS, and Windows.

--------------------------------------------
The TCP Bottleneck & Zero-Zombie Mandate
--------------------------------------------

The legacy model of spawning a standalone Node.js process listening on a hardcoded HTTP port exhibits several failure modes:

1. **Port Collisions and Contention**:
   Fixed ports (such as 13714) collide when multiple developers, microservices, continuous integration runners, or parallel test workers execute concurrently on a single machine. Dynamic port allocation requires orchestration files, lockfiles, or environment variable handshakes that add brittleness.

2. **Protocol and Socket Overhead**:
   HTTP/1.1 over loopback TCP incurs connection handshakes, header serialization, HTTP parser state machines, TCP slow-start, and ephemeral socket allocation. For short-lived fragment rendering or rapid Inertia navigations, this protocol tax degrades response latency.

3. **Zombie and Orphan Processes**:
   When the host Litestar application terminates abruptly—due to keyboard interrupts (``Ctrl+C``), uncaught exceptions, container SIGTERM signals, or worker restarts—the background Node.js HTTP server frequently remains running in an orphaned state. These zombie processes hold ports open, preventing subsequent application boots until killed manually.

4. **The Zero-Zombie Mandate**:
   Operating systems provide a native mechanism for coupling process lifecycles: **standard I/O anonymous pipes**. When a parent process terminates, the operating system closes the write end of the pipe, causing the child worker's ``stdin`` stream to immediately emit an End-Of-File (``EOF``) event. By binding the worker lifetime to ``stdin`` EOF, Litestar Vite guarantees that when Python exits, the Node.js or Bun worker exits immediately, with zero orphan processes.

---------------------------------
Architecture & Transport Matrix
---------------------------------

Litestar Vite implements a tiered transport matrix configured via ``InertiaConfig`` and the ``litestar_vite.ipc`` package:

.. list-table::
   :header-rows: 1
   :widths: 20 20 25 35

   * - Transport
     - Target Environments
     - Protocol Framing
     - Lifecycle Coupling
   * - ``StdioIPCTransport``
     - Linux, macOS, Windows
     - Line-delimited JSON (NDJSON)
     - Strict OS pipe binding (stdin EOF terminates child)
   * - ``UnixSocketIPCTransport``
     - Linux, macOS (POSIX)
     - NDJSON over ``AF_UNIX`` stream
     - Shared filesystem socket (e.g. ``/tmp/litestar-ssr.sock``)
   * - ``TCPStreamIPCTransport``
     - Multi-host containers, Kubernetes
     - Raw AnyIO TCP stream (zero HTTPX)
     - Remote daemon or sidecar lifecycle

~~~~~~~~~~~~~~~~~~~~~~~~~
Stdio Worker (NDJSON RPC)
~~~~~~~~~~~~~~~~~~~~~~~~~

The default, recommended transport across all operating systems is ``StdioIPCTransport``. Under this model, Litestar spawns the SSR worker bundle as an asynchronous child process using ``anyio.open_process()``. Communication uses newline-delimited JSON (NDJSON) with monotonic integer correlation IDs:

.. mermaid::

   sequenceDiagram
       autonumber
       participant App as Litestar Application
       participant Transport as StdioIPCTransport
       participant Pipe as Anonymous OS Pipe
       participant Worker as Node/Bun SSR Worker

       Note over App, Worker: Worker Initialization & Lifespan
       App->>Transport: start()
       Transport->>Pipe: anyio.open_process(node/bun, ssr.ts)
       Transport->>Transport: Launch background stdout & stderr reader tasks

       Note over App, Worker: Concurrent NDJSON Request Dispatch
       App->>Transport: send_request(payload)
       Transport->>Transport: Assign monotonic correlation ID (id: 42)
       Transport->>Pipe: stdin.send({"id": 42, "payload": ...}\n)
       Pipe->>Worker: readline "line" event
       Worker->>Worker: Render component to HTML string
       Worker->>Pipe: stdout.write({"id": 42, "result": {...}}\n)
       Pipe->>Transport: stdout reader parses NDJSON
       Transport->>Transport: Correlate ID 42 & unblock waiting caller
       Transport-->>App: Return render result dictionary

       Note over App, Worker: Clean Shutdown & Zero Zombies
       App->>Transport: close()
       Transport->>Pipe: stdin.aclose() (EOF)
       Pipe->>Worker: readline "close" / EOF event
       Worker->>Worker: process.exit(0)

~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Unix Domain Sockets (UDS)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

For high-concurrency production deployments on Linux and macOS where a persistent daemon pool is preferred, ``UnixSocketIPCTransport`` connects to a local POSIX socket file using ``anyio.connect_unix()``. Filesystem permissions (such as ``0600``) ensure that only the application user can dispatch render workloads, completely bypassing network firewalls and eliminating port conflicts.

~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Raw AnyIO TCP Stream
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

When running in containerized architectures with separated frontend and backend pods, ``TCPStreamIPCTransport`` connects to remote SSR workers via ``anyio.connect_tcp()``. Unlike legacy HTTP clients, this transport operates directly on AnyIO byte streams with lightweight request framing, eliminating third-party HTTP client dependencies like ``httpx`` from the core Litestar Vite package.

---------------------------------
Windows Compatibility Analysis
---------------------------------

Cross-platform parity is a core requirement for Litestar Vite. However, supporting local sockets on Microsoft Windows presents unique challenges in the Python ecosystem:

- In Python on Windows, the default asyncio event loop (``ProactorEventLoop``) does not implement asynchronous Unix Domain Sockets (``AF_UNIX``). Calling ``loop.create_unix_connection()`` or AnyIO's ``connect_unix()`` raises ``NotImplementedError``.
- While Windows 10 (build 17063+) introduced kernel-level ``AF_UNIX`` support, Python's Windows asynchronous I/O primitives do not bind to them asynchronously through completion ports.

``StdioIPCTransport`` completely resolves this disparity. Because standard input/output pipes are supported uniformly by Windows, Linux, and macOS, Litestar Vite achieves 100% feature-identical, high-performance IPC on Windows without requiring WSL2, TCP port binding, or platform-specific conditional branches in user application code.

---------------------------------
Bun Runtime Integration
---------------------------------

While Node.js is fully supported, the Bun JavaScript runtime offers compelling advantages for server-side rendering:

- **Near-Instant Cold Starts**: Bun initializes JavaScript and TypeScript bundles in under 5 milliseconds, enabling on-demand worker initialization without noticeable application startup pauses.
- **Native TypeScript Execution**: Bun executes ``ssr.ts`` directly without requiring an ahead-of-time compilation pass during local development.
- **Reduced Memory Footprint**: Bun's lean process architecture minimizes RSS memory usage across multi-worker deployments.

To utilize Bun, configure the executable command in your worker or specify Bun in your process supervisor:

.. docs-example: skip
.. code-block:: bash

   # Direct execution using Bun runtime
   bun run resources/ssr.ts --stdio

---------------------------------
Python Configuration Examples
---------------------------------

Configuring IPC SSR within a Litestar application is straightforward:

.. docs-example: skip
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

To customize the underlying IPC transport or worker parameters directly:

.. docs-example: skip
.. code-block:: python

   from litestar_vite.ipc import StdioIPCTransport, UnixSocketIPCTransport

   # Stdio worker transport for local process management
   stdio_transport = StdioIPCTransport(
       command=["node", "resources/bootstrap/ssr/ssr.js", "--stdio"],
       timeout=5.0,
       max_retries=3,
   )

   # Unix Domain Socket transport for high-speed POSIX daemons
   uds_transport = UnixSocketIPCTransport(
       socket_path="/tmp/litestar-ssr.sock",
       timeout=5.0,
   )
