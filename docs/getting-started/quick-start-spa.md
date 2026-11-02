# Quick Start: Single-Page Application (`mode="spa"`)

In **SPA mode** (`mode="spa"`), Litestar owns your JSON API routes and serves a transformed `index.html` shell for all unmatched non-API GET routes via `AppHandler`. Your frontend router (`react-router`, `vue-router`, or TanStack Router) handles client-side navigation while `TypeGenConfig` generates a fully typed TypeScript SDK from Litestar's OpenAPI schema.

---

## 1. Install Dependencies

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

And in your frontend workspace:

=== "npm"

    ```bash
    npm install -D litestar-vite-plugin @hey-api/openapi-ts
    ```

=== "pnpm"

    ```bash
    pnpm add -D litestar-vite-plugin @hey-api/openapi-ts
    ```

=== "bun"

    ```bash
    bun add -d litestar-vite-plugin @hey-api/openapi-ts
    ```

---

## 2. Configure Litestar (`app.py`)

Register `VitePlugin` with `mode="spa"` and enable `TypeGenConfig` so Litestar exports `openapi.json` and `routes.json` on startup:

```python title="docs/examples/getting_started/spa_app.py"
--8<-- "docs/examples/getting_started/spa_app.py"
```

---

## 3. Configure Vite (`vite.config.ts`)

Point `litestar-vite-plugin` at your application entrypoint (`src/main.tsx` or `src/main.ts`). All path, port, and typegen settings are automatically synchronized from `.litestar.json`:

```typescript title="vite.config.ts"
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import litestar from "litestar-vite-plugin";

export default defineConfig({
  plugins: [
    react(),
    litestar({
      input: ["src/main.tsx"],
    }),
  ],
});
```

---

## 4. Create `index.html` and Run

Place `index.html` in your project root (or `resource_dir`). In `mode="spa"`, `AppHandler` automatically injects `@vite/client` (and the React Fast Refresh preamble when `is_react=True`) in development, and swaps in hashed `manifest.json` bundle tags in production:

```html title="index.html"
<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Litestar SPA</title>
  </head>
  <body>
    <div id="app"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
```

Start the unified development server:

```bash
litestar run --reload
```

Open `http://127.0.0.1:8000` in your browser:

- `GET /api/summary` returns the JSON `SummaryStats` response from Litestar.
- `GET /` (and any client route like `/settings`) serves the transformed `index.html` shell.
- `/src/main.tsx` and `/vite-hmr` stream through `ViteProxyMiddleware` over port `8000`.
