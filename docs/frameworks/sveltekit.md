# SvelteKit

Build full-stack Svelte 5 applications with [SvelteKit](https://svelte.dev/docs/kit) and Litestar using `litestarSvelteKit()` from `litestar-vite-plugin/sveltekit`.

---

## Quick Start

```bash
litestar assets init --template sveltekit
litestar assets install
litestar run --reload
```

---

## Project Structure

```text
my-project/
├── app.py                  # Litestar API + ViteConfig(mode="ssr")
├── package.json
├── svelte.config.js        # @sveltejs/adapter-node configuration
├── tsconfig.json
├── vite.config.ts          # litestarSvelteKit() + sveltekit()
└── src/
    ├── app.html
    ├── hooks.server.ts     # Server-side /api/* proxy forwarding during SSR load()
    ├── lib/
    │   └── generated/      # Auto-generated routes.ts, schemas.ts, api/
    └── routes/
        ├── +layout.svelte
        ├── +page.ts        # Universal load function using route()
        └── +page.svelte
```

---

## Configuration

> [!IMPORTANT]
> Register `litestarSvelteKit()` **before** `sveltekit()` in `vite.config.ts` so the `/api` proxy middleware runs before SvelteKit's catch-all route matcher.

=== "Python (`app.py`)"

    ```python title="app.py"
    from pathlib import Path

    from litestar import Litestar, get
    from msgspec import Struct
    from litestar_vite import PathConfig, TypeGenConfig, ViteConfig, VitePlugin


    class Summary(Struct):
        title: str
        headline: str


    @get("/api/summary", name="summary", sync_to_thread=False)
    def get_summary() -> Summary:
        """Return typed summary payload for SvelteKit load functions."""
        return Summary(title="Litestar + SvelteKit", headline="Typed Load Functions & Svelte 5 Runes")


    app = Litestar(
        route_handlers=[get_summary],
        plugins=[
            VitePlugin(
                config=ViteConfig(
                    mode="ssr",
                    dev_mode=True,
                    paths=PathConfig(resource_dir=Path("src"), bundle_dir=Path("build")),
                    types=TypeGenConfig(output=Path("src/lib/generated"), generate_sdk=True, generate_routes=True),
                ),
            ),
        ],
    )
    ```

=== "Vite (`vite.config.ts`)"

    ```typescript title="vite.config.ts"
    import { sveltekit } from "@sveltejs/kit/vite";
    import { defineConfig } from "vite";
    import { litestarSvelteKit } from "litestar-vite-plugin/sveltekit";

    export default defineConfig({
      plugins: [
        litestarSvelteKit({
          apiPrefix: "/api",
          types: "auto",
        }),
        sveltekit(),
      ],
    });
    ```

---

## Typed `load` Functions (`+page.ts`)

Use SvelteKit's universal `load` function (`+page.ts`) with the generated `route()` helper so both SSR and client-side navigations fetch typed data from Litestar:

=== "`src/routes/+page.ts`"

    <!-- docs-example: skip -->
    ```typescript title="src/routes/+page.ts"
    import { route } from "$lib/generated/routes";
    import type { Summary } from "$lib/generated/api";
    import type { PageLoad } from "./$types";

    export const load: PageLoad = async ({ fetch }) => {
      const response = await fetch(route("summary"));
      const summary = (await response.json()) as Summary;
      return { summary };
    };
    ```

=== "`src/routes/+page.svelte`"

    <!-- docs-example: skip -->
    ```svelte title="src/routes/+page.svelte"
    <script lang="ts">
      import type { PageProps } from "./$types";

      let { data }: PageProps = $props();
    </script>

    <main>
      <h1>{data.summary.title}</h1>
      <p>{data.summary.headline}</p>
    </main>
    ```

For general SvelteKit routing, adapters (`@sveltejs/adapter-node`, `@sveltejs/adapter-static`), and hooks, see the official [SvelteKit documentation](https://svelte.dev/docs/kit).
