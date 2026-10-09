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

``litestar-vite`` includes three transports implementing :class:`BaseIPCTransport`:

- :class:`StdioIPCTransport`: Production subprocess worker communicating over standard I/O pipes (``stdin``/``stdout``) with newline-delimited JSON framing. Supported on Linux, macOS, and Windows. The worker exits on ``stdin`` EOF once in-flight requests have drained.
- :class:`WasmIPCTransport`: Production in-process transport that evaluates the self-contained SSR bundle inside an embedded QuickJS engine (``litestar-vite[wasm]``) on a dedicated worker thread. No JavaScript runtime binary is required on the host. ES-module bundles are loaded through ``Context.module``; a per-request CPU time limit (``timeout``) interrupts runaway scripts and the context is rebuilt on the next request. The transport is **experimental**: the shimmed globals (``TextEncoder``/``TextDecoder``, ``queueMicrotask``, ``setTimeout``) cover React/Vue/Svelte string rendering but not Node APIs such as ``fs`` or ``crypto``. Requests are serialized through a single engine.
- :class:`TCPStreamIPCTransport`: Pooled ``httpx2`` HTTP transport used in development mode to dispatch SSR and fragment render requests to the running Vite dev server's ``/__litestar_ssr__`` endpoint.

Production transport selection is controlled by ``RuntimeConfig.ssr_transport`` (``"auto"``, ``"stdio"``, or ``"wasm"``) and resolved by :func:`resolve_ssr_transport`. In ``"auto"`` mode an explicit ``InertiaSSRConfig.command`` wins, followed by the configured JS runtime, and finally the WASM transport when ``quickjs`` is importable.
