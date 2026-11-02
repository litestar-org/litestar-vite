# Islands Architecture & HTMX Fragments

When building server-driven applications in `mode="template"` (or `mode="htmx"`), you often want 90% of a page rendered via fast Jinja2 HTML templates or HTMX partial swaps while hydrating specific interactive components (charts, command palettes, rich editors) in React, Vue, or Svelte.

`litestar-vite` provides two complementary primitives powered by [`FragmentEngine`](../reference/fragments-and-ipc.md#litestar_vite.fragments.FragmentEngine):

1. **`vite_fragment()` + `<litestar-island>`**: Pre-renders a UI component inside a Jinja2 template and wraps it in a `<litestar-island>` custom element that hydrates on the client according to `hydrate="load" | "idle" | "visible" | "media"`.
2. **`ComponentResponse` (`render_fragment()`)**: Returns a standalone pre-rendered HTML fragment (plus scoped `<link rel="stylesheet">` tags from `manifest.json`) directly from a Litestar route handler for HTMX (`hx-get` / `hx-post`) partial swaps.

---

## 1. Returning Server-Rendered Fragments for HTMX (`ComponentResponse`)

Route handlers can return [`ComponentResponse`](../reference/fragments-and-ipc.md#litestar_vite.fragments.ComponentResponse) directly. During request handling, Litestar invokes `FragmentEngine.render()` over the SSR IPC transport (`TCPStreamIPCTransport` in dev, `StdioIPCTransport` or `WasmIPCTransport` in prod) and returns `text/html`:

```python title="docs/examples/learn/islands_and_fragments.py"
--8<-- "docs/examples/learn/islands_and_fragments.py"
```

### Static vs Island Fragment Modes

| `ComponentResponse` / `vite_fragment` Mode | Client JavaScript | Output HTML |
| --- | --- | --- |
| **`mode="island"`** (or `hydrate="load"\|"idle"\|"visible"\|"media"`) | Hydrates interactive component on client | Wraps pre-rendered HTML in `<litestar-island data-component="..." data-hydrate="...">` with serialized props and client entry `<script>`. |
| **`mode="static"`** (or `hydrate="none"`) | Zero client-side hydration | Returns pure server-rendered HTML and scoped `<link rel="stylesheet">` tags without `<litestar-island>` wrapper overhead. |

---

## 2. Embedding Interactive Islands in Jinja2 (`vite_fragment`)

Inside any Jinja2 template, call `vite_fragment(component, props=..., hydrate=..., media=...)`:

```html title="templates/dashboard.html.j2"
{{ vite_fragment(
    'islands/RevenueChart.tsx',
    props={'period': '30d', 'series': [120, 145, 190, 210]},
    hydrate='visible'
) }}
```

`vite_fragment()` emits a `<litestar-island>` custom element containing:

- The server-rendered HTML inside `<div data-island-root>...</div>` (so there is zero layout shift before JS loads).
- `<script type="application/json" data-island-props>{...}</script>` carrying serialized component props.
- Scoped `<link rel="stylesheet">` tags resolved from `manifest.json` in production.

### Hydration Strategies (`hydrate=`)

| Strategy | Attribute | When the Component Hydrates |
| --- | --- | --- |
| **`"load"`** (default) | `data-hydrate="load"` | Immediately when `<litestar-island>` connects to the DOM |
| **`"idle"`** | `data-hydrate="idle"` | Inside `requestIdleCallback()` (falls back to `200ms` timeout) |
| **`"visible"`** | `data-hydrate="visible"` | When scrolled within `200px` of the viewport (`IntersectionObserver`) |
| **`"media"`** | `data-hydrate="media"` + `data-media="(min-width: 768px)"` | When the CSS media query matches (`matchMedia`) |
| **`"none"`** | `data-hydrate="none"` | Server-rendered HTML only; never mounts client JavaScript |

---

## 3. Client-Side Island Registration & HTMX Extension

Register `<litestar-island>` and the Litestar HTMX CSRF/Directive extension (`registerHtmxExtension()`) in your frontend entrypoint:

=== "React"

    ```typescript title="resources/main.ts"
    import { hydrateIslands } from "litestar-vite-plugin/fragments/client";
    import { hydrateReact } from "litestar-vite-plugin/fragments/react";
    import { registerHtmxExtension } from "litestar-vite-plugin/helpers";

    registerHtmxExtension();
    hydrateIslands({
      "islands/RevenueChart": {
        load: () => import("./islands/RevenueChart"),
        hydrate: hydrateReact,
      },
    });
    ```

=== "Vue 3"

    ```typescript title="resources/main.ts"
    import { hydrateIslands } from "litestar-vite-plugin/fragments/client";
    import { hydrateVue } from "litestar-vite-plugin/fragments/vue";
    import { registerHtmxExtension } from "litestar-vite-plugin/helpers";

    registerHtmxExtension();
    hydrateIslands({
      "islands/RevenueChart": {
        load: () => import("./islands/RevenueChart.vue"),
        hydrate: hydrateVue,
      },
    });
    ```

=== "Svelte 5"

    ```typescript title="resources/main.ts"
    import { hydrateIslands } from "litestar-vite-plugin/fragments/client";
    import { hydrateSvelte } from "litestar-vite-plugin/fragments/svelte";
    import { registerHtmxExtension } from "litestar-vite-plugin/helpers";

    registerHtmxExtension();
    hydrateIslands({
      "islands/RevenueChart": {
        load: () => import("./islands/RevenueChart.svelte"),
        hydrate: hydrateSvelte,
      },
    });
    ```

---

## 4. Production Fragment SSR Worker (`createFragmentRenderer`)

For production SSR of fragments (`dev_mode=False`), configure `createFragmentRenderer` with `startSsrWorker` in `resources/ssr.ts` and configure `devSsr.componentRoots` in `vite.config.ts`:

```typescript title="resources/ssr.ts"
import { createFragmentRenderer } from "litestar-vite-plugin/fragments";
import { startSsrWorker } from "litestar-vite-plugin/ssr-worker";

const renderFragment = createFragmentRenderer(
  import.meta.glob("./islands/**/*.tsx") as Record<string, () => Promise<unknown>>,
  {
    clientEntry: "resources/main.ts",
  },
);

export default renderFragment;
startSsrWorker({ renderFragment });
```
