---
title: Overview
hide:
  - navigation
---

<div class="lv-home-hero" align="center">
  <img class="lv-hero-banner lv-hero-banner--light" alt="Litestar Vite" src="assets/banner-inline-light.svg">
  <img class="lv-hero-banner lv-hero-banner--dark" alt="Litestar Vite" src="assets/banner-inline-dark.svg">
  <p><strong>First-class Vite 7+, Inertia.js, Server-Rendered Islands, and End-to-End Type Generation for Litestar.</strong></p>
</div>

---

**Litestar Vite** bridges [Litestar](https://litestar.dev) (Python ASGI) and [Vite 7+](https://vite.dev) into a unified full-stack runtime. During development, your browser connects solely to Litestar (`:8000`) while the single-port proxy streams frontend modules and hot-reload WebSocket updates from a managed Vite process. In production, the asset loader serves hashed, immutable bundles directly from the Vite manifest.

--8<-- "tools/docs/includes/diagram-dev-proxy.html"

---

## Choose Your Operating Mode

Litestar Vite adapts to your frontend architecture through a single mode setting on `ViteConfig`:

<div class="grid cards" markdown>

-   :lucide-layout-grid: **Single-Page Application**

    ---

    Litestar serves your JSON and OpenAPI routes while transforming `index.html` with Vite asset tags for React, Vue, Svelte, or Angular SPAs.

    [→ Quick Start: SPA](getting-started/quick-start-spa.md)

-   :lucide-repeat: **Inertia.js Hybrid**

    ---

    Build React, Vue, or Svelte single-page applications without maintaining a separate client API layer. Return Python models directly as typed page props.

    [→ Quick Start: Inertia.js](getting-started/quick-start-inertia.md)

-   :lucide-blocks: **Jinja2 & Islands**

    ---

    Render server-side Jinja2 templates enhanced with Vite HMR, interactive island hydration, and server component fragments for HTMX swaps.

    [→ Quick Start: Templates & Islands](getting-started/quick-start-templates.md)

-   :lucide-globe: **Meta-Frameworks**

    ---

    Run Astro, Nuxt, or SvelteKit behind Litestar's reverse proxy with automatic OpenAPI SDK, route helper, and AsyncAPI channel generation.

    [→ Astro](frameworks/astro.md) · [Nuxt](frameworks/nuxt.md) · [SvelteKit](frameworks/sveltekit.md)

</div>

---

## Installation and Setup

### Install the Python and Vite Packages

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

Install the paired Vite 7+ plugin in your frontend workspace:

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

### Register the Plugin on Your Litestar App

```python title="docs/examples/getting_started/spa_app.py"
--8<-- "docs/examples/getting_started/spa_app.py"
```

### Scaffold and Run on a Single Port

```console
$ litestar assets init --template react
✓ Created vite.config.ts, package.json, tsconfig.json
$ litestar assets install
✓ Frontend dependencies installed
$ litestar run --reload
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
INFO:     Vite dev server started on http://127.0.0.1:5173 (proxied via :8000)
```

When `litestar run --reload` starts:

1. `VitePlugin` writes `.litestar.json` (the configuration bridge read by the Vite plugin) and exports OpenAPI and route schemas when type generation is enabled.
2. `VitePlugin` spawns the Vite dev server and reads its bound address from the `hot` file in your bundle directory.
3. Every browser request hits `http://127.0.0.1:8000` — Python API routes execute in Litestar, while Vite asset and HMR WebSocket traffic streams transparently through the single-port proxy.

---

## Explore the Documentation

| Section | What You Will Learn |
| --- | --- |
| [**Getting Started**](getting-started/index.md) | Installation, CLI scaffolding (`litestar assets init`), and end-to-end walkthroughs for SPA, Inertia.js, and Jinja2 + Islands |
| [**Core Concepts**](learn/index.md) | The four operating modes, layered `ViteConfig` sub-configs, build-time Static Props, Islands & HTMX fragments, Dev/Prod SSR, and production CDN deployment |
| [**Frameworks & Inertia**](frameworks/index.md) | Deep dive into Inertia.js (`defer`, `merge`, `once`, shared props, Precognition), React/Vue/Svelte setup, and Astro/Nuxt/SvelteKit integration |
| [**TypeGen & Realtime**](typegen/index.md) | Zero-drift OpenAPI SDK generation (`@hey-api/openapi-ts`), type-safe `route()` / `toRoute()` URL builders, and AsyncAPI WebSocket channel typing |
| [**Architecture**](architecture/index.md) | Interactive animated SVG/CSS diagrams of the Single-Port AnyIO Proxy, Operating Modes, Inertia.js Lifecycle, SSR IPC, and TypeGen Pipeline |
| [**Reference**](reference/index.md) | Complete Python API (`litestar_vite`), TypeScript 18-subpath API (`litestar-vite-plugin`), `litestar assets` CLI reference, and wire contracts |
