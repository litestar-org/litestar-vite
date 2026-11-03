# Web Frameworks

Litestar Vite supports every major frontend UI library, hypermedia library, and meta-framework while keeping Litestar as your single source of truth for routing, authentication, and data serialization.

---

## Supported Frameworks Matrix

| Framework | Mode | Integration & Helpers | Guide |
| --- | --- | --- | --- |
| **Inertia.js** | `hybrid` (`inertia`) | `litestar-vite-plugin`, `inertia-pages.json` | [Inertia Guide](inertia/index.md) |
| **React** | `spa` / `hybrid` / `template` | `@vitejs/plugin-react`, `litestar-vite-plugin/react` | [React Guide](react.md) |
| **Vue 3** | `spa` / `hybrid` / `template` | `@vitejs/plugin-vue`, `litestar-vite-plugin/vue` | [Vue 3 Guide](vue.md) |
| **Svelte 5** | `spa` / `hybrid` / `template` | `@sveltejs/vite-plugin-svelte`, `litestar-vite-plugin/svelte` | [Svelte 5 Guide](svelte.md) |
| **Angular** | `spa` / `external` | `litestar-vite-plugin` or `@angular/build` | [Angular Guide](angular.md) |
| **HTMX** | `template` (`htmx`) | `litestar-vite-plugin`, `<litestar-stream>` | [HTMX Guide](htmx.md) |
| **Astro** | `ssg` (`framework`) | `litestar-vite-plugin/astro` | [Astro Guide](astro.md) |
| **Nuxt** | `ssr` (`framework`) | `litestar-vite-plugin/nuxt` | [Nuxt Guide](nuxt.md) |
| **SvelteKit** | `ssr` (`framework`) | `litestar-vite-plugin/sveltekit` | [SvelteKit Guide](sveltekit.md) |

---

## Choosing a Architecture Pattern

### Server-Driven Single-Page Apps

Pair **React**, **Vue 3**, or **Svelte 5** with **Inertia.js** (`mode="hybrid"`) when you want a rich single-page frontend without maintaining a separate REST API layer, client router, or state store. Litestar route handlers return typed Python models (`msgspec.Struct`, `dataclass`, Pydantic) directly to your page components.

- [→ Inertia.js Overview](inertia/index.md)

### Client-Routed SPAs

Use **React**, **Vue 3**, **Svelte 5**, or **Angular** in `mode="spa"` when your frontend uses a client-side router (`react-router`, TanStack Router, `vue-router`, `@angular/router`) and communicates with Litestar over JSON API endpoints using the generated `@hey-api/openapi-ts` SDK.

- [→ React](react.md) · [Vue 3](vue.md) · [Svelte 5](svelte.md) · [Angular](angular.md)

### Server Templates, HTMX & Island Fragments

Use **HTMX** and Jinja2 templates (`mode="template"` or `mode="htmx"`) when HTML lives on the server, optionally embedding interactive `<litestar-island>` components rendered by React, Vue, or Svelte.

- [→ HTMX Guide](htmx.md) · [Islands & Fragment Architecture](../learn/islands-and-htmx.md)

### Meta-Frameworks

Use **Astro**, **Nuxt**, or **SvelteKit** when you want file-based routing, static site generation (SSG), or meta-framework SSR while Litestar serves your `/api/*`, `/schema/*`, and WebSocket routes through a single-port proxy.

- [→ Astro](astro.md) · [Nuxt](nuxt.md) · [SvelteKit](sveltekit.md)

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
