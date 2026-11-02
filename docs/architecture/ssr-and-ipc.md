---
title: SSR, Server Fragments, & IPC
description: Internal architecture of Inertia v2 lifecycle, Dev TCP vs. Prod Stdio SSR IPC transports, SSRCircuitBreaker, and <litestar-island> hydration.
---

# SSR, Server Fragments, & IPC

`litestar-vite` provides a unified inter-process communication (IPC) engine (`BaseIPCTransport`) shared by both **Inertia v2 Server-Side Rendering (`InertiaResponse`)** and **Standalone Server Fragments (`FragmentEngine` / `vite_fragment`)**.

--8<-- "tools/docs/includes/diagram-ssr-ipc.html"

---

## Development vs. Production IPC Transports

| Transport | Active When | Wire Protocol | Process & Cache Model |
| :--- | :--- | :--- | :--- |
| `TCPStreamIPCTransport` | `dev_mode=True` | HTTP/1.1 `POST /__litestar_ssr__` over `anyio.connect_tcp` | Executes SSR modules inside Vite 7+'s `RunnableDevEnvironment` (`ServerModuleRunner`). Rejects browser requests (`Origin` or `Sec-Fetch-Site` headers return `403`). Recursively invalidates parent importer chains on HMR updates. |
| `StdioIPCTransport` | `dev_mode=False` | Newline-delimited JSON (`IPCRequest` / `IPCResponse`) over `stdin` / `stdout` pipes | Spawns a persistent worker (`litestar-vite-ssr-worker` / `startSsrWorker`). Drains `stderr` concurrently into a bounded 100-line ring buffer to prevent 4 KB OS pipe buffer deadlocks on Windows and Linux. Automatically restarts on crash up to `max_restarts`. |
| `WasmIPCTransport` | `ssr_transport="wasm"` | In-process `quickjs` ESM evaluation on a dedicated worker thread | Loads compiled ESM `ssr.js` bundles without an external Node/Bun process, enforcing per-request execution time limits and draining microtasks after each dispatch. |

---

## Resilience & `SSRCircuitBreaker`

Every SSR and fragment render passes through `SSRCircuitBreaker`:

1. **`CLOSED` (Normal Operation)**: Requests are dispatched to the active `BaseIPCTransport`.
2. **`OPEN` (Tripped after `failure_threshold` consecutive errors)**: Subsequent requests bypass IPC immediately for `recovery_timeout` seconds. When `fallback_to_csr=True`, `InertiaResponse` returns the client-side HTML shell with `data-page` (or `<script type="application/json" id="app_page">`) so users never see a `500` page when an SSR component throws.
3. **`HALF_OPEN` (Probe Window)**: After `recovery_timeout` elapses, a single probe render is dispatched. A successful render resets the breaker to `CLOSED`; a failure re-opens the circuit.

---

## HTML Splicing (`_InertiaSlots`) & `<litestar-island>`

Once the JavaScript runtime returns `{ head: string[], body: string }` (for Inertia SSR) or `{ html: string, head: string[], css: string[] }` (for `FragmentEngine`):

- **Right-to-Left Offset Splicing (`inject_inertia_ssr_tags`)**: An `HTMLParser` state machine (`_InertiaSlots`) locates `<!--inertia-head-->` / `@inertiaHead` inside `<head>` and `<!--inertia-->` / `@inertia` inside `<body>` (ignoring matches inside `<script>`, `<style>`, `<pre>`, or `<code>`) and splices the rendered markup from right to left by character offset.
- **Progressive Island Hydration (`<litestar-island>`)**: When a fragment is rendered with `mode="island"`, `renderFragment()` wraps the server HTML in `<litestar-island data-island-id="..." data-island-component="..." data-island-props="...">` and appends a module loader for `clientEntry`. On the client, `hydrateIslands()` (`litestar-vite-plugin/fragments/client`) serializes mount/teardown transitions with a revision counter and restores the original SSR markup on disconnect so HTMX swaps never leave orphaned roots.

---

## Inertia v2 Request & Prop Evaluation Lifecycle

In `mode="hybrid"`, `InertiaPlugin` and `InertiaResponse` implement the complete Inertia v2 wire protocol across initial HTML visits, `X-Inertia` JSON transitions, deferred prop groups, partial reloads, and `303`/`409` status codes:

--8<-- "tools/docs/includes/diagram-inertia-lifecycle.html"
