# Frameworks & Inertia.js v2

`litestar-vite` supports every major JavaScript UI library and meta-framework while keeping Litestar as your single source of truth for routing, authentication, and data serialization.

---

## Choose Your Integration Path

<div class="grid cards" markdown>

-   :material-layers-triple-outline: **Inertia.js v2 (`mode="hybrid"`)**

    ---

    Build single-page React, Vue 3, or Svelte 5 apps driven directly by Litestar controllers — with `defer()` groups, `merge()` pagination, `once()` client caching, shared session props, and Laravel Precognition live validation.

    [:octicons-arrow-right-24: Inertia.js v2 Guide](inertia/index.md)

-   :material-react: **React, Vue 3 & Svelte 5 (`mode="spa"` / `mode="template"`)**

    ---

    Configure Vite 7+ plugins (`@vitejs/plugin-react`, `@vitejs/plugin-vue`, `@sveltejs/vite-plugin-svelte`), Fast Refresh preambles, and `<litestar-island>` hydration adapters.

    [:octicons-arrow-right-24: React, Vue & Svelte](react-vue-svelte.md)

-   :material-web: **Meta-Frameworks (`mode="framework"`)**

    ---

    Pair Litestar with Astro, Nuxt 3, SvelteKit, or Angular CLI using `litestar-vite-plugin/{astro,nuxt,sveltekit}` and `proxy_mode="proxy"`.

    [:octicons-arrow-right-24: Astro, Nuxt & SvelteKit](meta-frameworks.md)

</div>

---

## Feature Matrix by Framework Mode

| Capability | Inertia v2 (`mode="hybrid"`) | SPA (`mode="spa"`) | Jinja + Islands (`mode="template"`) | Meta-Frameworks (`mode="framework"`) |
| --- | --- | --- | --- | --- |
| **Routing Owner** | Litestar `@get(..., component="...")` | Client router (`react-router`, TanStack) | Litestar `@get(...)` -> `Template` | Astro / Nuxt / SvelteKit file router |
| **Data Transport** | Typed `PageProps` JSON (`X-Inertia: true`) | `@hey-api/openapi-ts` client SDK | Jinja context + `ComponentResponse` | `@hey-api/openapi-ts` client SDK |
| **Server-Side Rendering** | Built-in (`RunnableDevEnvironment` & `StdioIPCTransport`) | Client-rendered shell | Server HTML + `<litestar-island>` SSR | Handled by Meta-Framework server |
| **Typed URL Helper (`route()`)** | Supported (`routes.ts`) | Supported (`routes.ts`) | Supported (`routes.ts`) | Supported (`routes.ts`) |
| **Realtime Channels (`channels.ts`)** | Supported (`createTypedChannels()`) | Supported (`createTypedChannels()`) | Supported (`createTypedChannels()`) | Supported (`createTypedChannels()`) |
