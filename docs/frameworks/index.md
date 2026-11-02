# Web Frameworks

`litestar-vite` supports every major frontend UI library, hypermedia library, and meta-framework while keeping Litestar as your single source of truth for routing, authentication, and data serialization.

---

## Supported Frameworks Matrix

| Framework | Mode | Vite Plugin / Integration | TypeGen (`routes.ts` / SDK) | Realtime Helper | Guide |
| --- | --- | --- | --- | --- | --- |
| **Inertia.js v2 / v3** | `hybrid` (`inertia`) | `litestar-vite-plugin` | Yes + `inertia-pages.json` | Framework adapter | [Inertia Guide](inertia/index.md) |
| **React** | `spa` / `hybrid` / `template` | `litestar-vite-plugin` + `@vitejs/plugin-react` | Yes | `litestar-vite-plugin/react` | [React Guide](react.md) |
| **Vue 3** | `spa` / `hybrid` / `template` | `litestar-vite-plugin` + `@vitejs/plugin-vue` | Yes | `litestar-vite-plugin/vue` | [Vue 3 Guide](vue.md) |
| **Svelte 5** | `spa` / `hybrid` / `template` | `litestar-vite-plugin` + `@sveltejs/vite-plugin-svelte` | Yes | `litestar-vite-plugin/svelte` | [Svelte 5 Guide](svelte.md) |
| **Angular** | `spa` (AnalogJS) / `external` (CLI) | `litestar-vite-plugin` or `@angular/build` | Yes | `litestar-vite-plugin/helpers` | [Angular Guide](angular.md) |
| **HTMX** | `template` (`htmx`) | `litestar-vite-plugin` | Yes (`route()`) | `<litestar-stream>` | [HTMX Guide](htmx.md) |
| **Astro** | `ssg` (`framework`) | `litestar-vite-plugin/astro` | Yes | `litestar-vite-plugin/helpers` | [Astro Guide](astro.md) |
| **Nuxt** | `ssr` (`framework`) | `litestar-vite-plugin/nuxt` | Yes | `litestar-vite-plugin/vue` | [Nuxt Guide](nuxt.md) |
| **SvelteKit** | `ssr` (`framework`) | `litestar-vite-plugin/sveltekit` | Yes | `litestar-vite-plugin/svelte` | [SvelteKit Guide](sveltekit.md) |

---

## Choosing a Architecture Pattern

### 1. Server-Driven Single-Page Apps (Inertia.js)

Pair **React**, **Vue 3**, or **Svelte 5** with **Inertia.js** (`mode="hybrid"`) when you want a rich single-page frontend without maintaining a separate REST API layer, client router, or state store. Litestar route handlers return typed Python models (`msgspec.Struct`, `dataclass`, Pydantic) directly to your page components.

- [:octicons-arrow-right-24: Inertia.js v2 / v3 Overview](inertia/index.md)

### 2. Client-Routed SPAs (`mode="spa"`)

Use **React**, **Vue 3**, **Svelte 5**, or **Angular** in `mode="spa"` when your frontend uses a client-side router (`react-router`, TanStack Router, `vue-router`, `@angular/router`) and communicates with Litestar over JSON API endpoints using the generated `@hey-api/openapi-ts` SDK.

- [:octicons-arrow-right-24: React](react.md) · [Vue 3](vue.md) · [Svelte 5](svelte.md) · [Angular](angular.md)

### 3. Server Templates, HTMX & Island Fragments (`mode="template"`)

Use **HTMX** and Jinja2 templates (`mode="template"` or `mode="htmx"`) when HTML lives on the server, optionally embedding interactive `<litestar-island>` components rendered by React, Vue, or Svelte.

- [:octicons-arrow-right-24: HTMX Guide](htmx.md) · [Islands & Fragment Architecture](../learn/islands-and-htmx.md)

### 4. Meta-Frameworks (`mode="ssr"` / `mode="ssg"` / `mode="framework"`)

Use **Astro**, **Nuxt**, or **SvelteKit** when you want file-based routing, static site generation (SSG), or meta-framework SSR while Litestar serves your `/api/*`, `/schema/*`, and WebSocket routes through a single-port proxy.

- [:octicons-arrow-right-24: Astro](astro.md) · [Nuxt](nuxt.md) · [SvelteKit](sveltekit.md)

---

## Quick Scaffolding

Generate a complete, ready-to-run project for any supported framework using `litestar assets init`:

<!-- termynal -->

```console
$ litestar assets init --template react-inertia
✓ Created vite.config.ts, package.json, tsconfig.json
✓ Created resources/main.tsx and resources/pages/Home.tsx
$ litestar assets install
---> 100%
✓ Frontend dependencies installed
$ litestar run --reload
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
INFO:     Vite dev server started on http://127.0.0.1:5173 (proxied via :8000)
```

=== "UI Libraries (SPA)"

    ```bash
    litestar assets init --template react
    litestar assets init --template vue
    litestar assets init --template svelte
    litestar assets init --template angular
    litestar assets init --template angular-cli
    ```

=== "Inertia.js (Server-Driven SPA)"

    ```bash
    litestar assets init --template react-inertia
    litestar assets init --template vue-inertia
    litestar assets init --template svelte-inertia
    litestar assets init --template react-inertia-jinja
    litestar assets init --template vue-inertia-jinja
    ```

=== "Meta-Frameworks & Hypermedia"

    ```bash
    litestar assets init --template htmx
    litestar assets init --template astro
    litestar assets init --template nuxt
    litestar assets init --template sveltekit
    ```

---

## Production Reference Applications

- **[litestar-fullstack](https://github.com/litestar-org/litestar-fullstack)** — Fullstack reference architecture with React SPA, SQLAlchemy (`advanced-alchemy`), SAQ background workers, and Docker Compose.
- **[litestar-fullstack-inertia](https://github.com/litestar-org/litestar-fullstack-inertia)** — Fullstack Inertia reference application with authentication, OAuth2, team management, and SSR.
