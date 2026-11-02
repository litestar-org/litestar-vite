# Astro

Pair [Astro](https://astro.build) with Litestar using `litestar-vite-plugin/astro` (`mode="ssg"` or `mode="framework"`) to build content-focused sites with Islands Architecture, file-based routing, and end-to-end OpenAPI + route type generation.

---

## Quick Start

```bash
litestar assets init --template astro
litestar assets install
litestar run --reload
```

---

## Project Structure

```text
my-project/
├── app.py                  # Litestar API + ViteConfig(mode="ssg")
├── astro.config.mjs        # Astro config with litestar() integration
├── package.json
├── tsconfig.json
└── src/
    ├── pages/
    │   └── index.astro     # Astro pages with frontmatter data fetching
    ├── layouts/
    │   └── Layout.astro
    └── generated/          # Auto-generated routes.ts, schemas.ts, api/
```

---

## Configuration

=== "Python (`app.py`)"

    ```python title="app.py"
    from pathlib import Path

    from litestar import Litestar, get
    from msgspec import Struct
    from litestar_vite import PathConfig, RuntimeConfig, TypeGenConfig, ViteConfig, VitePlugin


    class Book(Struct):
        id: int
        title: str
        author: str


    @get("/api/books", name="books", sync_to_thread=False)
    def list_books() -> list[Book]:
        """Return typed book list for Astro pages."""
        return [Book(id=1, title="Astro + Litestar", author="Litestar Team")]


    app = Litestar(
        route_handlers=[list_books],
        plugins=[
            VitePlugin(
                config=ViteConfig(
                    mode="ssg",
                    dev_mode=True,
                    paths=PathConfig(resource_dir=Path("src"), bundle_dir=Path("dist")),
                    runtime=RuntimeConfig(executor="node"),
                    types=TypeGenConfig(output=Path("src/generated"), generate_sdk=True, generate_routes=True),
                ),
            ),
        ],
    )
    ```

=== "Astro (`astro.config.mjs`)"

    ```typescript title="astro.config.mjs"
    import { defineConfig } from "astro/config";
    import litestar from "litestar-vite-plugin/astro";

    export default defineConfig({
      integrations: [
        litestar({
          apiPrefix: "/api",
          types: true,
        }),
      ],
    });
    ```

---

## How `litestar-vite-plugin/astro` Works

1. **Bridge & Hotfile Sync**: Reads `.litestar.json` on startup and writes the active Astro dev server URL to the `hot` file (`dist/hot`) so Litestar's single-port `ViteProxyMiddleware` routes non-API requests to Astro automatically.
2. **Dev Proxy**: Configures Vite's `server.proxy` for `apiPrefix` (default `"/api"`) so direct visits to Astro's port also forward API requests to Litestar.
3. **Automatic Codegen**: Runs `@hey-api/openapi-ts` when `openapi.json` or `routes.json` change.

---

## Fetching Typed Data in `.astro` Pages

Import `route()` and OpenAPI types directly inside Astro's server frontmatter fence (`---`):

```astro title="src/pages/index.astro"
---
import Layout from "../layouts/Layout.astro";
import { route } from "../generated/routes";
import type { Book } from "../generated/api";

const apiOrigin = import.meta.env.PUBLIC_API_URL || "http://127.0.0.1:8000";
const response = await fetch(`${apiOrigin}${route("books")}`);
const books: Book[] = await response.json();
---

<Layout title="Catalog">
  <main>
    <h1>Books</h1>
    <ul>
      {books.map((book) => (
        <li><strong>{book.title}</strong> — {book.author}</li>
      ))}
    </ul>
  </main>
</Layout>
```

---

## Rendering Modes & Interactive Islands

| Astro Output Mode | Litestar `ViteConfig(mode=...)` | Behavior |
| --- | --- | --- |
| `output: "static"` (default) | `mode="ssg"` | `litestar assets build` compiles static HTML into `dist/`; Litestar serves static pages and `/api/*` in production. |
| `output: "server"` | `mode="ssr"` | Astro runs a Node/Deno adapter for dynamic SSR; combine with React/Vue/Svelte `client:load` or `client:visible` islands. |
