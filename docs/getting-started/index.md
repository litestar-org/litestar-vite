# Getting Started

Litestar Vite pairs two packages that work together across the `.litestar.json` contract:

- **`litestar-vite`** (Python): The Litestar plugin (`VitePlugin`), configuration models (`ViteConfig`), AnyIO dev proxy (`ViteProxyMiddleware`), Inertia v2 protocol engine, fragment renderer, and `litestar assets` CLI.
- **`litestar-vite-plugin`** (TypeScript): The Vite 7+ plugin that reads `.litestar.json`, writes `<bundle_dir>/hot`, runs `@hey-api/openapi-ts` and AsyncAPI codegen, and registers the dev SSR / fragment RPC middleware (`/__litestar_ssr__`).

---

## 1. Installation

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

> [!TIP]
> If you use Jinja2 templates (`mode="template"` or Jinja-based root templates), install the `jinja` extra (`uv add "litestar-vite[jinja]"`).

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

## 2. Scaffolding with `litestar assets init`

The fastest way to bootstrap a new frontend workspace is `litestar assets init`, which generates `package.json`, `vite.config.ts`, `tsconfig.json`, and framework entrypoints aligned with your `ViteConfig`:

```bash
litestar assets init --template react-inertia
litestar assets install
litestar run --reload
```

### Available Scaffolding Templates

| Template Flag (`--template`) | Operating Mode | Stack |
| --- | --- | --- |
| `react` | `mode="spa"` | React 19 + TypeScript + Vite 7+ |
| `vue` | `mode="spa"` | Vue 3 + TypeScript + Vite 7+ |
| `svelte` | `mode="spa"` | Svelte 5 + TypeScript + Vite 7+ |
| `angular` | `mode="framework"` | Angular CLI + Litestar proxy |
| `react-inertia` | `mode="hybrid"` | React 19 + `@inertiajs/react` v2 |
| `vue-inertia` | `mode="hybrid"` | Vue 3 + `@inertiajs/vue3` v2 |
| `svelte-inertia` | `mode="hybrid"` | Svelte 5 + `@inertiajs/svelte` v2 |
| `jinja-htmx` | `mode="template"` | Jinja2 + HTMX + `<litestar-island>` |
| `astro` | `mode="framework"` | Astro + `@litestar/vite-plugin/astro` |
| `nuxt` | `mode="framework"` | Nuxt 3 + `@litestar/vite-plugin/nuxt` |
| `sveltekit` | `mode="framework"` | SvelteKit + `@litestar/vite-plugin/sveltekit` |

---

## 3. Pick Your Quick-Start Walkthrough

Choose the walkthrough that matches your architecture:

1. [**Quick Start: Single-Page Application (`mode="spa"`)**](quick-start-spa.md) — Litestar serves JSON/OpenAPI routes and injects Vite scripts into `index.html` for a client-routed SPA.
2. [**Quick Start: Inertia.js v2 (`mode="hybrid"`)**](quick-start-inertia.md) — Server-driven routing with React, Vue, or Svelte page components and typed `PageProps`.
3. [**Quick Start: Jinja2 Templates & Islands (`mode="template"`)**](quick-start-templates.md) — Server-rendered HTML templates with `vite_hmr()`, `vite()`, `<litestar-island>` hydration, and HTMX `ComponentResponse` fragments.
