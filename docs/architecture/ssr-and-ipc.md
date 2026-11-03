---
title: SSR, Server Fragments, & IPC
description: Internal architecture of Inertia.js lifecycle, Dev TCP vs. Prod Stdio SSR IPC transports, SSRCircuitBreaker, and <litestar-island> hydration.
---

# SSR, Server Fragments, & IPC

Litestar Vite provides a unified inter-process communication (IPC) engine (`BaseIPCTransport`) shared by both **Inertia.js Server-Side Rendering (`InertiaResponse`)** and **Standalone Server Fragments (`FragmentEngine` / `vite_fragment`)**.

--8<-- "tools/docs/includes/diagram-ssr-ipc.html"

---

## Development vs. Production IPC Transports

| Transport | Active When | Wire Protocol | Process & Cache Model |
| :--- | :--- | :--- | :--- |
| `TCPStreamIPCTransport` | `dev_mode=True` | HTTP/1.1 `POST /__litestar_ssr__` over pooled `httpx2` | Executes SSR modules inside Vite 7+'s `RunnableDevEnvironment` (`ServerModuleRunner`). Rejects browser requests (`Origin` or `Sec-Fetch-Site` headers return 403). Recursively invalidates parent importer chains on HMR updates. |
| `StdioIPCTransport` | `dev_mode=False` (`ssr_transport="stdio"` or `"auto"`) | Newline-delimited JSON (`IPCRequest` / `IPCResponse`) over `stdin` / `stdout` pipes | Spawns a persistent worker (`startSsrWorker` from `litestar-vite-plugin/ssr-worker` using streaming `TextDecoder` with zero `node:readline` imports, compatible with Node, Bun, and Deno). Drains `stderr` concurrently into a bounded 100-line ring buffer to prevent 4 KB OS pipe buffer deadlocks. Exits with status `0` on `stdin` EOF once in-flight renders drain, and restarts on crash up to `max_restarts`. |
| `WasmIPCTransport` | `dev_mode=False` (`ssr_transport="wasm"` or auto-detected via `resolve_ssr_transport`) | In-process JSON dispatch via `globalThis.__litestar_ssr_dispatch__` | Evaluates the self-contained ES-module `ssr.js` bundle (`ssr.noExternal: true`) inside an embedded QuickJS context (`litestar-vite[wasm]`) on a dedicated worker thread via `Context.module`. Enforces per-request `set_time_limit(timeout)` and rebuilds the context automatically after a timeout. |

---

## Circuit Breaker & Client Fallback

Every SSR and fragment render passes through `SSRCircuitBreaker`:

1. **`CLOSED` (Normal Operation)**: Requests are dispatched to the active `BaseIPCTransport`.
2. **`OPEN` (Tripped after `failure_threshold` consecutive errors)**: Subsequent requests bypass IPC immediately for `recovery_timeout` seconds. When `fallback_to_client=True`, `InertiaResponse` returns the client-side HTML shell with `data-page` (or `<script type="application/json" id="app_page">`) so users never see a 500 page when an SSR component throws.
3. **`HALF_OPEN` (Probe Window)**: After `recovery_timeout` elapses, a single probe render is dispatched. A successful render resets the breaker to `CLOSED`; a failure re-opens the circuit.

---

## HTML Splicing & Island Hydration

Once the JavaScript runtime returns `{ head: string[], body: string }` (for Inertia SSR) or `{ html: string, head: string[], css: string[] }` (for `FragmentEngine`):

- **Right-to-Left Offset Splicing (`inject_inertia_ssr_tags`)**: An `HTMLParser` state machine (`_InertiaSlots`) locates `<!--inertia-head-->` / `@inertiaHead` inside `<head>` and `<!--inertia-->` / `@inertia` inside `<body>` (ignoring matches inside `<script>`, `<style>`, `<pre>`, or `<code>`) and splices the rendered markup from right to left by character offset.
- **Progressive Island Hydration (`<litestar-island>`)**: When a fragment is rendered with `mode="island"`, `renderFragment()` wraps the server HTML in `<litestar-island data-island-id="..." data-island-component="..." data-island-props="...">` and appends a module loader for `clientEntry`. On the client, `hydrateIslands()` (`litestar-vite-plugin/fragments/client`) serializes mount/teardown transitions with a revision counter and restores the original SSR markup on disconnect so HTMX swaps never leave orphaned roots.

---

## Inertia.js Request & Prop Evaluation Lifecycle

In `mode="hybrid"`, `InertiaPlugin` and `InertiaResponse` implement the complete Inertia.js wire protocol across initial HTML visits, `X-Inertia` JSON transitions, deferred prop groups, partial reloads, and 303/409 status codes:

--8<-- "tools/docs/includes/diagram-inertia-lifecycle.html"
