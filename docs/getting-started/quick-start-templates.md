# Quick Start: Jinja2 Templates & Islands

In **Template mode** (`mode="template"`), Litestar renders server-side Jinja2 templates while `VitePlugin` registers template callables (`vite_hmr()`, `vite()`, `vite_fragment()`, `vite_static()`) and mounts `<litestar-island>` web components or HTMX `ComponentResponse` fragments.

---

## Install Dependencies

Install Litestar Vite with the `jinja` extra:

=== "uv"

    ```bash
    uv add "litestar-vite[jinja]"
    ```

=== "pip"

    ```bash
    pip install "litestar-vite[jinja]"
    ```

=== "pdm"

    ```bash
    pdm add "litestar-vite[jinja]"
    ```

=== "poetry"

    ```bash
    poetry add "litestar-vite[jinja]"
    ```

Install `litestar-vite-plugin` in your frontend workspace:

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

---

## Configure Litestar

Configure `TemplateConfig(engine=JinjaTemplateEngine)` alongside `VitePlugin(config=ViteConfig(mode="template"))`. Route handlers can return standard `Template` responses for full pages or `ComponentResponse` for partial HTMX swaps:

```python title="docs/examples/getting_started/template_app.py"
--8<-- "docs/examples/getting_started/template_app.py"
```

---

## Author the Jinja2 Template

Use `{{ vite_hmr() }}` and `{{ vite('resources/main.ts') }}` in `<head>`, and embed interactive islands with `{{ vite_fragment('components/MetricsCard.tsx', props={'activeOrders': initial_count}, hydrate='visible') }}`:

```html title="home.html.j2"
<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <title>{{ title }}</title>
    {{ vite_hmr() }}
    {{ vite('resources/main.ts') }}
  </head>
  <body>
    <main>
      <h1>{{ title }}</h1>
      {{ vite_fragment(
          'components/MetricsCard.tsx',
          props={'activeOrders': initial_count, 'latencyMs': 11.4},
          hydrate='visible'
      ) }}
      <button
        hx-get="/fragments/metrics-card"
        hx-target="#live-metrics"
        hx-swap="innerHTML">
        Refresh Metrics
      </button>
      <div id="live-metrics"></div>
    </main>
  </body>
</html>
```

---

## Register Island Hydration

Register the `<litestar-island>` custom element in your client entrypoint so islands hydrate according to their `data-hydrate` strategy (`load`, `idle`, `visible`, or `media`):

```typescript title="resources/main.ts"
import { hydrateIslands } from "litestar-vite-plugin/fragments/client";
import { hydrateReact } from "litestar-vite-plugin/fragments/react";

hydrateIslands({
  "islands/RevenueChart": {
    load: () => import("./islands/RevenueChart"),
    hydrate: hydrateReact,
  },
});
```

See [Islands Architecture & HTMX Integration](../learn/islands-and-htmx.md) for the complete lifecycle of `vite_fragment()`, `<litestar-island>`, and `ComponentResponse`.
