---
title: Architecture Overview
description: Visual overview of how Litestar (Python ASGI) and Vite 7+ coordinate across operating modes, development HMR proxying, and production asset serving.
---

# Architecture Overview

Litestar Vite bridges two runtimes with distinct responsibilities:

- **Litestar (Python ASGI)** owns routing, dependency injection, authentication guards, OpenAPI/AsyncAPI schema metadata, CSRF protection, and HTML shell or JSON serialization.
- **Vite 7+ (JavaScript / TypeScript)** owns ES module transformation, Hot Module Replacement (HMR), CSS/Tailwind pipelines, SSR module execution (`RunnableDevEnvironment`), and production Rollup/Rolldown bundling.

Use the interactive switcher below to inspect how HTML shell ownership, routing, and data transport change across the four operating modes:

--8<-- "tools/docs/includes/diagram-operating-modes.html"

---

## Operating Mode Matrix

| Operating Mode | HTML Shell Owner | Router Owner | Primary Data Transport | Typical Stack |
| :--- | :--- | :--- | :--- | :--- |
| `mode="spa"` | `AppHandler` (`index.html`) | Client router | `@hey-api/openapi-ts` + `route()` | React Router, Vue Router, TanStack Router |
| `mode="hybrid"` | `AppHandler` / Jinja + SSR | Litestar (`component=`) | Inertia v2 `PageProps` JSON | `@inertiajs/react`, `@inertiajs/vue3`, `@inertiajs/svelte` |
| `mode="template"` | Jinja2 (`vite()`, `vite_hmr()`) | Litestar controllers | Server HTML + `<litestar-island>` + HTMX | Jinja2, HTMX (`hx-swap="json"`), WebSocket/SSE |
| `mode="framework"` | Meta-framework server | Meta-framework router | `/api/*` proxy + shared TypeGen | Astro 5, SvelteKit, Nuxt 4 |

---

## Development vs. Production Execution

During development (`dev_mode=True`), Litestar proxies asset and HMR WebSocket traffic to a live Vite 7+ process over a single browser origin (`127.0.0.1:8000`). In production (`dev_mode=False`), Node is not required for static assets: `ViteAssetLoader` resolves hashed bundles from `manifest.json` while Granian or Litestar serves immutable static files directly.

--8<-- "tools/docs/includes/diagram-dev-vs-prod.html"

---

## Architecture Deep Dives

<div class="grid cards" markdown>

-   **Single-Port Dev Proxy & `.litestar.json` Bridge**

    ---

    How `ViteProxyMiddleware` streams HTTP/1.1 assets (`anyio.connect_tcp`) and tunnels `/vite-hmr` WebSockets (`wsproto`) without CORS, coordinated by `.litestar.json` and the `hot` file.

    [Explore Dev Proxy & Bridge](dev-proxy-and-bridge.md)

-   **SSR, Server Fragments, & IPC Transports**

    ---

    How `InertiaResponse` and `FragmentEngine` render components across `TCPStreamIPCTransport` (`/__litestar_ssr__` in dev) and `StdioIPCTransport` (NDJSON worker pool in prod) with `SSRCircuitBreaker`.

    [Explore SSR & IPC](ssr-and-ipc.md)

-   **End-to-End TypeGen Pipeline**

    ---

    How Python route and schema introspection emits deterministic `openapi.json`, `routes.json`, `inertia-pages.json`, and `asyncapi.json` artifacts consumed by the Vite plugin.

    [Explore Codegen Pipeline](codegen-pipeline.md)

</div>
