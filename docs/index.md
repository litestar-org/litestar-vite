# Litestar Vite

<div align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="assets/banner-inline-dark.svg">
    <source media="(prefers-color-scheme: light)" srcset="assets/banner-inline-light.svg">
    <img alt="Litestar Vite" src="assets/banner-inline-light.svg" width="58%">
  </picture>
  <p><strong>First-class Vite 7+, Inertia.js v2, Server-Rendered Islands, and End-to-End Type Generation for Litestar.</strong></p>
</div>

---

**Litestar Vite** bridges [Litestar](https://litestar.dev) (Python ASGI) and [Vite 7+](https://vite.dev) into a unified full-stack runtime. During development, your browser connects solely to Litestar (`:8000`) while `ViteProxyMiddleware` streams frontend modules and `/vite-hmr` WebSocket updates from a managed Vite process. In production, `ViteAssetLoader` and `GranianPlugin` serve hashed, immutable bundles with zero-copy speed.

--8<-- "tools/docs/includes/diagram-dev-proxy.html"

---

## Choose Your Operating Mode

Litestar Vite adapts to your frontend architecture through a single `ViteConfig(mode=...)` setting:

<div class="grid cards" markdown>

-   :material-react: **Single-Page Application (`mode="spa"`)**

    ---

    Litestar serves your JSON/OpenAPI routes and transforms `index.html` with Vite asset tags for React, Vue, Svelte, or Angular SPAs.

    [:octicons-arrow-right-24: Quick Start: SPA](getting-started/quick-start-spa.md)

-   :material-layers-triple-outline: **Inertia.js v2 Hybrid (`mode="hybrid"`)**

    ---

    Build React, Vue, or Svelte single-page apps without writing a client API layer. Return Python dicts or `msgspec.Struct` models directly as typed `PageProps`.

    [:octicons-arrow-right-24: Quick Start: Inertia v2](getting-started/quick-start-inertia.md)

-   :material-file-code-outline: **Jinja2 + Islands (`mode="template"`)**

    ---

    Server-rendered Jinja2 templates enhanced with Vite HMR, `<litestar-island>` partial hydration, and `ComponentResponse` fragments for HTMX swaps.

    [:octicons-arrow-right-24: Quick Start: Templates & Islands](getting-started/quick-start-templates.md)

-   :material-web: **Meta-Frameworks (`mode="framework"`)**

    ---

    Run Astro, Nuxt, or SvelteKit behind Litestar's reverse proxy with automatic OpenAPI SDK, route helper, and AsyncAPI channel generation.

    [:octicons-arrow-right-24: Meta-Frameworks Guide](frameworks/meta-frameworks.md)

</div>

---

## 60-Second Quick Start

### 1. Install the Python and Vite Packages

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

### 2. Register `VitePlugin` on Your Litestar App

```python title="docs/examples/getting_started/spa_app.py"
--8<-- "docs/examples/getting_started/spa_app.py"
```

### 3. Scaffold and Run on a Single Port

```bash
litestar assets init --template react
litestar assets install
litestar run --reload
```

When `litestar run --reload` starts:

1. `VitePlugin` writes `.litestar.json` (the deterministic contract consumed by `litestar-vite-plugin`) and exports `openapi.json` and `routes.json` when `types=True`.
2. `VitePlugin` spawns the Vite dev server and reads its bound address from `<bundle_dir>/hot`.
3. Every browser request hits `http://127.0.0.1:8000` — Python API routes execute in Litestar, while Vite asset and `/vite-hmr` WebSocket traffic streams transparently through `ViteProxyMiddleware`.

---

## Explore the Documentation

| Section | What You Will Learn |
| --- | --- |
| [**Getting Started**](getting-started/index.md) | Installation, CLI scaffolding (`litestar assets init`), and end-to-end walkthroughs for SPA, Inertia v2, and Jinja2 + Islands |
| [**Core Concepts**](learn/index.md) | The four operating modes, layered `ViteConfig` sub-configs, build-time Static Props, Islands & HTMX fragments, Dev/Prod SSR, and production CDN/Granian deployment |
| [**Frameworks & Inertia**](frameworks/index.md) | Deep dive into Inertia.js v2 (`defer`, `merge`, `once`, shared props, Precognition), React/Vue/Svelte setup, and Astro/Nuxt/SvelteKit integration |
| [**TypeGen & Realtime**](typegen/index.md) | Zero-drift OpenAPI SDK generation (`@hey-api/openapi-ts`), type-safe `route()` / `wsRoute()` URL builders, and AsyncAPI WebSocket channel typing |
| [**Architecture**](architecture/index.md) | Interactive animated SVG/CSS diagrams of the Single-Port AnyIO Proxy, Operating Modes, Inertia v2 Lifecycle, SSR IPC, and TypeGen Pipeline |
| [**Reference**](reference/index.md) | Complete Python API (`litestar_vite`), TypeScript 18-subpath API (`litestar-vite-plugin`), `litestar assets` CLI reference, and wire contracts |
