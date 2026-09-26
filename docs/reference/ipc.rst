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

``litestar-vite`` includes three transports implementing :class:`BaseIPCTransport`:

- :class:`StdioIPCTransport`: Subprocess worker communicating over standard I/O pipes with NDJSON framing. Supported on Linux, macOS, and Windows. Terminates the worker when ``stdin`` closes.
- :class:`UnixSocketIPCTransport`: POSIX local domain socket transport (for example ``/tmp/litestar-ssr.sock``). Supported on Linux and macOS.
- :class:`TCPStreamIPCTransport`: AnyIO TCP stream transport with NDJSON framing for remote workers and multi-container deployments.
