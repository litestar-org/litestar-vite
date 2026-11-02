# Fragments & SSR IPC Reference

API reference for UI component fragments (`litestar_vite.fragments`) and the Server-Side Rendering IPC transport and circuit breaker subsystem (`litestar_vite.ipc`).

---

## UI Component Fragments & Islands

::: litestar_vite.fragments.FragmentEngine

::: litestar_vite.fragments.ComponentResponse

::: litestar_vite.fragments.vite_fragment
    options:
      heading_level: 4

::: litestar_vite.fragments.render_fragment
    options:
      heading_level: 4

---

## SSR IPC Transports

::: litestar_vite.ipc.BaseIPCTransport

::: litestar_vite.ipc.StdioIPCTransport

::: litestar_vite.ipc.TCPStreamIPCTransport

::: litestar_vite.ipc.IPCRequest
    options:
      heading_level: 4

::: litestar_vite.ipc.IPCResponse
    options:
      heading_level: 4

---

## Circuit Breaker & IPC Exceptions

::: litestar_vite.ipc.SSRCircuitBreaker

::: litestar_vite.ipc.CircuitState
    options:
      heading_level: 4

::: litestar_vite.ipc.IPCError
    options:
      heading_level: 4

::: litestar_vite.ipc.IPCTimeoutError
    options:
      heading_level: 4

::: litestar_vite.ipc.IPCWorkerCrashError
    options:
      heading_level: 4

::: litestar_vite.ipc.CircuitBreakerOpenError
    options:
      heading_level: 4
