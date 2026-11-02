# Nuxt

Build full-stack Vue applications with [Nuxt](https://nuxt.com) and Litestar using the `litestar-vite-plugin/nuxt` module (`mode="ssr"` / `mode="framework"`).

---

## Quick Start

```bash
litestar assets init --template nuxt
litestar assets install
litestar run --reload
```

---

## Project Structure

```text
my-project/
├── app.py                  # Litestar API + ViteConfig(mode="ssr")
├── nuxt.config.ts          # Nuxt configuration with litestar-vite-plugin/nuxt
├── package.json
├── tsconfig.json
├── app.vue                 # Root Nuxt component
├── pages/
│   └── index.vue           # File-based Nuxt routes
└── generated/              # Auto-generated routes.ts, schemas.ts, api/
```

---

## Configuration

=== "Python (`app.py`)"

    ```python title="app.py"
    from pathlib import Path

    from litestar import Litestar, get
    from msgspec import Struct
    from litestar_vite import PathConfig, RuntimeConfig, TypeGenConfig, ViteConfig, VitePlugin


    class Summary(Struct):
        title: str
        headline: str


    @get("/api/summary", name="summary", sync_to_thread=False)
    def get_summary() -> Summary:
        """Return typed summary payload for Nuxt SSR and client fetches."""
        return Summary(title="Litestar + Nuxt", headline="Universal Vue Rendering & Typed API")


    app = Litestar(
        route_handlers=[get_summary],
        plugins=[
            VitePlugin(
                config=ViteConfig(
                    mode="ssr",
                    dev_mode=True,
                    paths=PathConfig(resource_dir=Path("."), bundle_dir=Path(".output/public")),
                    runtime=RuntimeConfig(executor="node"),
                    types=TypeGenConfig(output=Path("generated"), generate_sdk=True, generate_routes=True),
                ),
            ),
        ],
    )
    ```

=== "Nuxt (`nuxt.config.ts`)"

    ```typescript title="nuxt.config.ts"
    import litestarNuxt from "litestar-vite-plugin/nuxt";

    export default defineNuxtConfig({
      compatibilityDate: "2025-01-01",
      modules: [
        [
          litestarNuxt,
          {
            apiPrefix: "/api",
            types: "auto",
          },
        ],
      ],
    });
    ```

---

## Using `useFetch` with Generated `route()`

In Nuxt pages and composables, combine `useFetch` with the generated `route()` helper for SSR-hydrated, type-safe data fetching:

```vue title="pages/index.vue"
<script setup lang="ts">
import { route } from "~/generated/routes";
import type { Summary } from "~/generated/api";

declare function useFetch<T>(url: string): Promise<{ data: { value: T | null }; pending: { value: boolean } }>;

const { data: summary, pending } = await useFetch<Summary>(route("summary"));
</script>

<template>
  <main v-if="!pending && summary">
    <h1>{{ summary.title }}</h1>
    <p>{{ summary.headline }}</p>
  </main>
</template>
```

---

## Production Deployment

1. **Static Generation (`nuxt generate`)**: Outputs static HTML and client bundles to `.output/public`, which Litestar serves directly in production.
2. **Universal SSR (`nuxt build`)**: Outputs a Nitro server in `.output/server/index.mjs`; run Litestar and Nitro behind a reverse proxy or let Nitro proxy `/api/**` to Litestar via `routeRules`.
