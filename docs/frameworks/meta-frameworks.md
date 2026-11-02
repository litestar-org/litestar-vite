# Meta-Frameworks (Astro, Nuxt & SvelteKit)

When building with **Astro**, **Nuxt 3**, **SvelteKit**, or **Angular CLI**, the meta-framework manages its own server/file router and Vite pipeline while Litestar serves your `/api/*`, `/schema/*`, and WebSocket routes.

Setting `ViteConfig(mode="framework")` (or its alias `mode="ssr"`) configures `ViteProxyMiddleware` in **denylist mode (`proxy_mode="proxy"`)**: every request that does *not* match a registered Litestar route is streamed to the meta-framework's dev server over your single Litestar port (`:8000`).

---

## 1. Python Configuration (`mode="framework"`)

```python
from litestar import Litestar, get
from litestar_vite import RuntimeConfig, TypeGenConfig, ViteConfig, VitePlugin


@get("/api/health", sync_to_thread=False)
def health_check() -> dict[str, str]:
    """Return API health status while non-API routes proxy to the meta-framework."""
    return {"status": "ok"}


app = Litestar(
    route_handlers=[health_check],
    plugins=[
        VitePlugin(
            config=ViteConfig(
                mode="framework",
                dev_mode=True,
                runtime=RuntimeConfig(port=4321),
                types=TypeGenConfig(generate_sdk=True, generate_routes=True),
            ),
        ),
    ],
)
```

---

## 2. Meta-Framework Plugin Configuration

`litestar-vite-plugin` provides dedicated integrations for Astro, Nuxt, and SvelteKit that read `.litestar.json`, write the `hot` file so `ViteProxyMiddleware` discovers the bound port automatically, and run TypeScript codegen on startup:

=== "Astro (`astro.config.mjs`)"

    ```typescript title="astro.config.mjs"
    import { defineConfig } from "astro/config";
    import litestarAstro from "litestar-vite-plugin/astro";

    export default defineConfig({
      integrations: [
        litestarAstro({
          apiPrefix: "/api",
          types: true,
        }),
      ],
    });
    ```

=== "Nuxt 3 (`nuxt.config.ts`)"

    ```typescript title="nuxt.config.ts"
    import litestarNuxt from "litestar-vite-plugin/nuxt";

    export default defineNuxtConfig({
      modules: [
        [
          litestarNuxt,
          {
            apiPrefix: "/api",
            types: true,
          },
        ],
      ],
    });
    ```

=== "SvelteKit (`vite.config.ts`)"

    ```typescript title="vite.config.ts"
    import { sveltekit } from "@sveltejs/kit/vite";
    import { defineConfig } from "vite";
    import { litestarSvelteKit } from "litestar-vite-plugin/sveltekit";

    export default defineConfig({
      plugins: [
        sveltekit(),
        litestarSvelteKit({
          apiPrefix: "/api",
          types: true,
        }),
      ],
    });
    ```

---

## 3. Scaffolding a Meta-Framework Workspace

Use `litestar assets init --template <framework>` to generate a ready-to-run Astro, Nuxt, SvelteKit, or Angular workspace:

```bash
litestar assets init --template astro
litestar assets install
litestar run --reload
```
