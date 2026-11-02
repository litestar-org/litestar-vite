# Server-Side Rendering

Litestar Vite provides unified Server-Side Rendering (SSR) for both **Inertia.js v2 pages** (`mode="hybrid"`) and **UI component islands/fragments** (`mode="template"`). Instead of requiring you to manage a separate Node HTTP server process, Litestar Vite manages the SSR IPC lifecycle automatically in both development and production.

--8<-- "tools/docs/includes/diagram-ssr-ipc.html"

---

## How Dev and Prod SSR Differ

| Stage | Development (`dev_mode=True`) | Production (`dev_mode=False`) |
| --- | --- | --- |
| **IPC Transport** | [`TCPStreamIPCTransport`](../reference/fragments-and-ipc.md#litestar_vite.ipc.TCPStreamIPCTransport) (`POST /__litestar_ssr__` over pooled `httpx2`) | [`StdioIPCTransport`](../reference/fragments-and-ipc.md#litestar_vite.ipc.StdioIPCTransport) (persistent Node/Bun/Deno subprocess over `stdin`/`stdout` NDJSON pipes) |
| **Module Evaluation** | Vite 7+ `RunnableDevEnvironment.runner.import()` (`ModuleRunner` with recursive importer HMR invalidation) | Pre-built SSR bundle (`bootstrap/ssr/ssr.js`) loaded once at worker startup |
| **Build Step Required?** | **No** — edits to `.tsx`/`.vue`/`.svelte` files reflect immediately on the next refresh | **Yes** — `litestar assets build` compiles both the client bundle and the SSR bundle |
| **Fault Tolerance** | [`SSRCircuitBreaker`](../reference/fragments-and-ipc.md#litestar_vite.ipc.SSRCircuitBreaker) + automatic fallback to client-side rendering (`fallback_to_client=True`) | [`SSRCircuitBreaker`](../reference/fragments-and-ipc.md#litestar_vite.ipc.SSRCircuitBreaker) + bounded `stderr` ring buffer + automatic worker restart |

---

## Enabling Server-Side Rendering

Enable SSR by passing `InertiaConfig(ssr=True)` (or an explicit [`InertiaSSRConfig`](../reference/plugin-and-config.md#litestar_vite.config.InertiaSSRConfig) instance):

```python title="docs/examples/learn/ssr_app.py"
--8<-- "docs/examples/learn/ssr_app.py"
```

---

## HTML Slot Splicing

When SSR returns `{ head: string[], body: string }`, Litestar Vite splices the rendered markup into your `root_template` using `_InertiaSlots`:

- If your `index.html` includes `<!--inertia-head-->` inside `<head>` and `<!--inertia-body-->` inside `<div id="app">`, Litestar Vite replaces those exact markers right-to-left in a single pass.
- If `<!--inertia-body-->` is absent, Litestar Vite automatically locates `<div id="app"></div>` (or `InertiaSSRConfig.target_selector`) and injects the rendered SSR HTML inside the container while placing `<script type="application/json" data-page="app">` immediately before it.

```html title="index.html"
<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <!--inertia-head-->
  </head>
  <body>
    <div id="app"><!--inertia-body--></div>
    <script type="module" src="/resources/main.tsx"></script>
  </body>
</html>
```

---

## Circuit Breaker & Client-Side Fallback

Production SSR should never take down your Python application if a third-party frontend component accesses `window` unguarded. `InertiaSSRConfig` configures [`SSRCircuitBreaker`](../reference/fragments-and-ipc.md#litestar_vite.ipc.SSRCircuitBreaker) by default:

- **`timeout=2.0`**: Any SSR request exceeding 2 seconds is cancelled cleanly.
- **`circuit_breaker_failure_threshold=3`**: After 3 consecutive failures, the circuit trips to `OPEN` and bypasses IPC for `circuit_breaker_reset_timeout=30.0` seconds before probing with a single `HALF_OPEN` request.
- **`fallback_to_client=True`**: Whenever SSR fails or the circuit is `OPEN`, Litestar logs a warning and returns the standard client-rendered HTML shell (200 OK) so the browser mounts the page seamlessly.
