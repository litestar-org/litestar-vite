==========================
IPC Transports & Protocols
==========================

The ``litestar_vite.ipc`` package provides cross-platform inter-process communication transports, data structures, and lifecycle managers connecting Litestar to frontend SSR workers.

Transports & Protocols
----------------------

.. automodule:: litestar_vite.ipc
    :members:
    :show-inheritance:
    :inherited-members:

Transport Overview
------------------

Litestar Vite includes three specialized transports implementing :class:`BaseIPCTransport`:

- :class:`StdioIPCTransport`: High-throughput subprocess worker operating over standard I/O anonymous pipes with NDJSON framing. Compatible with Linux, macOS, and Windows. Automatically terminates workers on stdin EOF.
- :class:`UnixSocketIPCTransport`: POSIX local domain socket transport connecting to local daemons (e.g. ``/tmp/litestar-ssr.sock``). Linux and macOS only.
- :class:`TCPStreamIPCTransport`: Lightweight AnyIO TCP stream transport for remote sidecars and multi-container topologies without third-party HTTP client dependencies.
