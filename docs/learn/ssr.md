# Server-Side Rendering

Litestar Vite provides unified Server-Side Rendering (SSR) for both **Inertia.js v2 pages** (`mode="hybrid"`) and **UI component islands/fragments** (`mode="template"`). Instead of requiring you to manage a separate Node HTTP server process, Litestar Vite manages the SSR IPC lifecycle automatically in both development and production.

--8<-- "tools/docs/includes/diagram-ssr-ipc.html"

---

## How Dev and Prod SSR Differ

| Stage | Development (`dev_mode=True`) | Production (`dev_mode=False`) | Production without JS Runtime (`ssr_transport="wasm"`) |
| --- | --- | --- | --- |
| **IPC Transport** | [`TCPStreamIPCTransport`](../reference/fragments-and-ipc.md#litestar_vite.ipc.TCPStreamIPCTransport) (`POST /__litestar_ssr__` over pooled `httpx2`) | [`StdioIPCTransport`](../reference/fragments-and-ipc.md#litestar_vite.ipc.StdioIPCTransport) (persistent Node/Bun/Deno subprocess over `stdin`/`stdout` NDJSON pipes) | [`WasmIPCTransport`](../reference/fragments-and-ipc.md#litestar_vite.ipc.WasmIPCTransport) (embedded QuickJS engine on a dedicated worker thread via `litestar-vite[wasm]`) |
| **Module Evaluation** | Vite 7+ `RunnableDevEnvironment.runner.import()` (`ModuleRunner` with recursive importer HMR invalidation) | Self-contained SSR bundle (`bootstrap/ssr/ssr.js`) loaded once at worker startup | Self-contained ES-module `ssr.js` (`ssr.noExternal: true`) loaded via `Context.module` |
| **Build Step Required?** | **No** — edits to `.tsx`/`.vue`/`.svelte` files reflect immediately on the next refresh | **Yes** — `litestar assets build` compiles both the client bundle and the SSR bundle | **Yes** — `litestar assets build` inlines dependencies into `ssr.js` |
| **Fault Tolerance** | [`SSRCircuitBreaker`](../reference/fragments-and-ipc.md#litestar_vite.ipc.SSRCircuitBreaker) + automatic fallback to client-side rendering (`fallback_to_client=True`) | [`SSRCircuitBreaker`](../reference/fragments-and-ipc.md#litestar_vite.ipc.SSRCircuitBreaker) + bounded `stderr` ring buffer + automatic worker restart | [`SSRCircuitBreaker`](../reference/fragments-and-ipc.md#litestar_vite.ipc.SSRCircuitBreaker) + per-request `set_time_limit(timeout)` + automatic context rebuild on timeout |

---

## Self-Contained Production SSR & `WasmIPCTransport`

When building the production SSR bundle (`ssrOutputDir`), `litestar-vite-plugin` defaults `ssr.noExternal` to `true` so `ssr.js` is self-contained and can run under Node, Bun, Deno, or the experimental in-process [`WasmIPCTransport`](../reference/fragments-and-ipc.md#litestar_vite.ipc.WasmIPCTransport) (`uv add "litestar-vite[wasm]"`).

Production transport selection is controlled by `RuntimeConfig.ssr_transport` (`"auto"`, `"stdio"`, or `"wasm"`) and resolved by [`resolve_ssr_transport()`](../reference/fragments-and-ipc.md#litestar_vite.ipc.resolve_ssr_transport):

- **`"auto"` (default)**: An explicit `InertiaSSRConfig.command` wins, followed by the configured JavaScript runtime (`node`, `bun`, or `deno`), and finally `WasmIPCTransport` when `quickjs` is installed.
- **`"stdio"`**: Spawns the compiled `ssr.js` bundle in a child process (`node`, `bun run`, or `deno run --allow-read --allow-env`). The worker (`startSsrWorker` from `litestar-vite-plugin/ssr-worker`) reads `process.stdin` using a streaming `TextDecoder` (without `node:readline`) and exits with status `0` once `stdin` reaches EOF and in-flight renders drain.
- **`"wasm"` (experimental)**: Evaluates `ssr.js` inside an embedded QuickJS engine on a dedicated worker thread with no external JS runtime required on the host. Each request enforces a CPU time limit (`timeout`) and automatically rebuilds the context if a render times out.

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
