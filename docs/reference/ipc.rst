==========================
IPC Transports & Protocols
==========================

The ``litestar_vite.ipc`` package provides cross-platform inter-process communication transports, data structures, and circuit breakers connecting Litestar to frontend SSR workers and the Vite dev server.

Transports & Protocols
----------------------

.. automodule:: litestar_vite.ipc
    :members:
    :show-inheritance:
    :inherited-members:

Transport Overview
------------------

``litestar-vite`` includes two transports implementing :class:`BaseIPCTransport`:

- :class:`StdioIPCTransport`: Production subprocess worker communicating over standard I/O pipes (``stdin``/``stdout``) with newline-delimited JSON framing. Supported on Linux, macOS, and Windows. Terminates the worker automatically when ``stdin`` closes.
- :class:`TCPStreamIPCTransport`: AnyIO HTTP/1.1 transport used in development mode to dispatch SSR and fragment render requests to the running Vite dev server's ``/__litestar_ssr__`` endpoint.
