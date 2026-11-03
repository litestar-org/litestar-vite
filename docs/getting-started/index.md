# Getting Started

Litestar Vite pairs two packages that work together across the `.litestar.json` contract:

- **Litestar Vite** (Python): The Litestar plugin (`VitePlugin`), configuration models (`ViteConfig`), AnyIO dev proxy (`ViteProxyMiddleware`), Inertia.js protocol engine, fragment renderer, and `litestar assets` CLI.
- **`litestar-vite-plugin`** (TypeScript): The Vite 7+ plugin that reads `.litestar.json`, writes `<bundle_dir>/hot`, runs `@hey-api/openapi-ts` and AsyncAPI codegen, and registers the dev SSR / fragment RPC middleware (`/__litestar_ssr__`).

---

## Installation

Install the Python package in your backend environment:

=== "uv"

    ```bash
    uv add litestar-vite
    ```

=== "pip"

    ```bash
    pip install litestar-vite
    ```

=== "pdm"

    ```bash
    pdm add litestar-vite
    ```

=== "poetry"

    ```bash
    poetry add litestar-vite
    ```

!!! tip "Optional Extras (`jinja`, `asyncapi`, `node`, `bun`, `deno`, `wasm`)"
    - **Jinja2 templates (`mode="template"`)**: `uv add "litestar-vite[jinja]"`
    - **AsyncAPI channel codegen (`generate_channels=True`)**: `uv add "litestar-vite[asyncapi]"`
    - **Self-contained JS runtime wheels (no host Node/Bun/Deno needed)**: `uv add "litestar-vite[node]"`, `"litestar-vite[bun]"`, or `"litestar-vite[deno]"`
    - **In-process QuickJS SSR (`WasmIPCTransport`)**: `uv add "litestar-vite[wasm]"`

Install the Vite plugin in your frontend directory (`package.json`):

=== "npm"

    ```bash
    npm install -D litestar-vite-plugin
    ```

=== "pnpm"

    ```bash
    pnpm add -D litestar-vite-plugin
    ```

=== "bun"

    ```bash
    bun add -d litestar-vite-plugin
    ```

---

## Scaffolding a New Frontend

The fastest way to bootstrap a new frontend workspace is `litestar assets init`, which generates `package.json`, `vite.config.ts`, `tsconfig.json`, and framework entrypoints aligned with your `ViteConfig`:

```console
$ litestar assets init --template react-inertia
✓ Created vite.config.ts, package.json, tsconfig.json
✓ Created resources/main.tsx and resources/pages/Home.tsx
$ litestar assets install
✓ Frontend dependencies installed
$ litestar run --reload
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
```

### Available Scaffolding Templates

| Template Flag (`--template`) | Operating Mode | Stack |
| --- | --- | --- |
| `react` | `mode="spa"` | React + TypeScript + Vite 7+ |
| `vue` | `mode="spa"` | Vue 3 + TypeScript + Vite 7+ |
| `svelte` | `mode="spa"` | Svelte 5 + TypeScript + Vite 7+ |
| `angular` | `mode="spa"` | Angular + `@analogjs/vite-plugin-angular` |
| `angular-cli` | `mode="external"` | Angular CLI (`@angular/build`) + Litestar proxy |
| `react-inertia` | `mode="hybrid"` | React + `@inertiajs/react` |
| `vue-inertia` | `mode="hybrid"` | Vue 3 + `@inertiajs/vue3` |
| `svelte-inertia` | `mode="hybrid"` | Svelte 5 + `@inertiajs/svelte` |
| `htmx` | `mode="htmx"` | Jinja2 + HTMX + `registerHtmxExtension()` |
| `astro` | `mode="ssg"` | Astro + `litestar-vite-plugin/astro` |
| `nuxt` | `mode="ssr"` | Nuxt + `litestar-vite-plugin/nuxt` |
| `sveltekit` | `mode="ssr"` | SvelteKit + `litestar-vite-plugin/sveltekit` |

---

## Pick Your Quick-Start Walkthrough

Choose the walkthrough that matches your architecture:

1. [**Quick Start: Single-Page Application (`mode="spa"`)**](quick-start-spa.md) — Litestar serves JSON/OpenAPI routes and injects Vite scripts into `index.html` for a client-routed SPA.
2. [**Quick Start: Inertia.js (`mode="hybrid"`)**](quick-start-inertia.md) — Server-driven routing with React, Vue, or Svelte page components and typed `PageProps`.
3. [**Quick Start: Jinja2 Templates & Islands (`mode="template"`)**](quick-start-templates.md) — Server-rendered HTML templates with `vite_hmr()`, `vite()`, `<litestar-island>` hydration, and HTMX `ComponentResponse` fragments.
