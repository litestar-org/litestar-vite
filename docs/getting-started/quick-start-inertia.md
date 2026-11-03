# Quick Start: Inertia.js

In **Inertia Hybrid mode** (`mode="hybrid"`), Litestar owns server-side routing, authentication, and data loading while React, Vue, or Svelte renders each page component. Route handlers declare `component="Dashboard/Index"` and return a Python `dict` or `msgspec.Struct` directly — no client REST or GraphQL boilerplate required.

---

## Install Dependencies

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

Install `litestar-vite-plugin` and your Inertia.js adapter:

=== "npm"

    ```bash
    npm install -D litestar-vite-plugin
    npm install @inertiajs/react react react-dom
    ```

=== "pnpm"

    ```bash
    pnpm add -D litestar-vite-plugin
    pnpm add @inertiajs/react react react-dom
    ```

=== "bun"

    ```bash
    bun add -d litestar-vite-plugin
    bun add @inertiajs/react react react-dom
    ```

---

## Configure Litestar

Set `mode="hybrid"` and configure `InertiaConfig(root_template="index.html")`. When `mode="hybrid"` is active, `VitePlugin` automatically activates `InertiaPlugin` and `InertiaMiddleware`:

```python title="docs/examples/getting_started/inertia_app.py"
--8<-- "docs/examples/getting_started/inertia_app.py"
```

---

## Create the Root HTML Shell and Client Entrypoint

In `mode="hybrid"`, `index.html` needs only `<div id="app"></div>` and your module entrypoint. By default (`InertiaConfig(use_script_element=True)`), Litestar Vite injects `<script type="application/json" data-page="app">{...}</script>` right before `<div id="app"></div>`:

```html title="index.html"
<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Litestar + Inertia.js</title>
  </head>
  <body>
    <div id="app"></div>
    <script type="module" src="/resources/main.tsx"></script>
  </body>
</html>
```

Initialize Inertia in `resources/main.tsx` using `resolvePageComponent` from `litestar-vite-plugin/inertia-helpers` and enable `useScriptElementForInitialPage: true`:

```tsx title="resources/main.tsx"
import { createInertiaApp } from "@inertiajs/react";
import { createRoot } from "react-dom/client";
import { resolvePageComponent } from "litestar-vite-plugin/inertia-helpers";

createInertiaApp({
  defaults: {
    future: {
      useScriptElementForInitialPage: true,
    },
  },
  resolve: (name: string) =>
    resolvePageComponent(
      `./pages/${name}.tsx`,
      import.meta.glob("./pages/**/*.tsx"),
    ),
  setup({ el, App, props }: { el: HTMLElement; App: any; props: any }) {
    createRoot(el).render(<App {...props} />);
  },
});
```

---

## Run and Navigate

Start Litestar and Vite together:

```bash
litestar run --reload
```

- On initial visit to `GET /`, Litestar renders `index.html` with the initial `PageProps` JSON and Vite asset scripts.
- On subsequent `<Link href="...">` clicks, Inertia sends `X-Inertia: true` and swaps only the JSON `PageProps` payload.
- See the [Inertia.js Guide](../frameworks/inertia/index.md) for deferred props (`defer`), infinite scroll (`merge`), shared session data (`share`), and SSR.
