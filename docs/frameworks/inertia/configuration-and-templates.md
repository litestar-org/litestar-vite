# Configuration & Root Templates

Setting `ViteConfig(mode="hybrid")` (or `mode="inertia"`) enables Inertia support automatically. You can customize every aspect of the protocol by passing an [`InertiaConfig`](../../reference/plugin-and-config.md#litestar_vite.config.InertiaConfig) instance (or `inertia=True` for defaults) to `ViteConfig`.

---

## Inertia Configuration

```python title="app.py"
from litestar import Litestar
from litestar.middleware.session.server_side import ServerSideSessionConfig
from litestar_vite import InertiaConfig, InertiaSSRConfig, TypeGenConfig, ViteConfig, VitePlugin
from litestar_vite.config import InertiaTypeGenConfig, SPAConfig

app = Litestar(
    route_handlers=[],
    middleware=[ServerSideSessionConfig().middleware],
    plugins=[
        VitePlugin(
            config=ViteConfig(
                mode="hybrid",
                spa=SPAConfig(app_selector="#app"),
                inertia=InertiaConfig(
                    root_template="index.html.j2",
                    redirect_unauthorized_to="/login",
                    redirect_404="/404",
                    encrypt_history=False,
                    use_script_element=True,
                    precognition=True,
                    ssr=InertiaSSRConfig(enabled=True, timeout=5.0),
                    type_gen=InertiaTypeGenConfig(
                        include_default_auth=True,
                        include_default_flash=True,
                    ),
                ),
                types=TypeGenConfig(generate_page_props=True),
            ),
        ),
    ],
)
```

### Key Configuration Options

| Option | Default | Description |
| --- | --- | --- |
| `root_template` | `"index.html"` | Root HTML or Jinja2 template rendered on initial full-page Inertia visits. |
| `component_opt_keys` | `("component", "page")` | Route handler `opt` keys inspected to determine the Inertia page component name. |
| `use_script_element` | `True` | Emit initial page JSON inside `<script type="application/json" id="app_page" data-page="app">` instead of an HTML-escaped `data-page` attribute. |
| `app_selector` | `"#app"` | CSS ID selector for the root mount container (`#app`, `#root`). |
| `encrypt_history` | `False` | Globally enable browser `window.history.state` encryption via Web Crypto. |
| `precognition` | `False` | Register the Laravel Precognition validation exception handler (422 / 204). |
| `redirect_unauthorized_to` | `None` | Automatically redirect unauthenticated (401) Inertia requests to this path. |
| `redirect_404` | `None` | Automatically redirect 404 Not Found Inertia requests to this path. |
| `extra_static_page_props` | `{}` | Static key-value dictionary merged into every Inertia response's `props`. |
| `extra_session_page_props` | `set()` | Session keys automatically read from `request.session` and merged into `props`. |
| `shared_page_prop_types` | `{}` | Mapping of shared prop keys to Python types (`{"auth": AuthProp}`) for `page-props.ts` codegen. |
| `ssr` | `False` | `bool` or [`InertiaSSRConfig`](../../reference/plugin-and-config.md#litestar_vite.config.InertiaSSRConfig) enabling server-side rendering. |

---

## Vite Plugin Boundary

In Litestar Vite projects, **`litestar-vite-plugin` is the sole Vite bridge owner**. Do **not** install `@inertiajs/vite` alongside `litestar-vite-plugin`:

- `litestar-vite-plugin` auto-detects Inertia mode from `.litestar.json` (`mode: "hybrid"` or `mode: "template"` with Inertia enabled).
- It manages the `hot` file, `/__litestar_ssr__` dev SSR endpoint, React Fast Refresh preamble, and type generation without conflicting middleware.

---

## Root Templates: SPA Mode vs Jinja2 Template Mode

Inertia works in two HTML shell modes:

=== "SPA Mode (`mode='hybrid'`, no Jinja2 required)"

    In `mode="hybrid"` without `TemplateConfig`, Litestar reads your plain `index.html` (from the project root or `resources/index.html`) and transforms it at runtime — injecting the Vite HMR client, module scripts, and the `<script type="application/json" id="app_page" data-page="app">` payload around `<div id="app"></div>`:

    ```html title="index.html"
    <!doctype html>
    <html lang="en">
      <head>
        <meta charset="UTF-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1.0" />
        <title>My Inertia App</title>
      </head>
      <body>
        <div id="app"></div>
        <script type="module" src="/resources/main.tsx"></script>
      </body>
    </html>
    ```

=== "Jinja2 Template Mode (`TemplateConfig`)"

    When you configure Litestar's `TemplateConfig(engine=JinjaTemplateEngine)`, `InertiaResponse` renders `root_template` through Jinja2 using the `vite_hmr()`, `vite()`, and `inertia` template callables:

    ```html title="templates/index.html.j2"
    <!doctype html>
    <html lang="en">
      <head>
        <meta charset="UTF-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1.0" />
        <title>My Inertia App</title>
        {{ vite_hmr() }}
        {{ vite('resources/main.tsx') }}
      </head>
      <body>
        {{ inertia }}
      </body>
    </html>
    ```

---

## Script-Element Initial Page Bootstrap

By default, `InertiaConfig(use_script_element=True)` serializes initial page props into `<script type="application/json" id="app_page" data-page="app">{...}</script><div id="app"></div>` rather than an HTML-escaped `data-page="&quot;...&quot;"` attribute. This cuts initial HTML payload size by ~30% and avoids HTML entity decoding overhead.

- **Inertia v3 clients** read the `<script type="application/json" data-page="app">` element automatically with `defaults: {}`.
- **Inertia v2 clients** enable script-element parsing by setting `defaults: { future: { useScriptElementForInitialPage: true } }` in `createInertiaApp(...)`:

=== "Inertia v3 Client (`resources/main.tsx`)"

    ```tsx title="resources/main.tsx"
    import { createInertiaApp } from "@inertiajs/react";
    import { createRoot } from "react-dom/client";
    import { csrfHeaders } from "litestar-vite-plugin/helpers";
    import { resolvePageComponent } from "litestar-vite-plugin/inertia-helpers";

    createInertiaApp({
      defaults: {
        visitOptions: (_href: string, options: { headers?: Record<string, string> }) => ({
          headers: csrfHeaders(options.headers ?? {}),
        }),
      },
      resolve: (name: string) =>
        resolvePageComponent(`./pages/${name}.tsx`, import.meta.glob("./pages/**/*.tsx")),
      setup({ el, App, props }: { el: HTMLElement; App: any; props: any }) {
        createRoot(el).render(<App {...props} />);
      },
    });
    ```

=== "Inertia v2 Client (`resources/main.tsx`)"

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
        resolvePageComponent(`./pages/${name}.tsx`, import.meta.glob("./pages/**/*.tsx")),
      setup({ el, App, props }: { el: HTMLElement; App: any; props: any }) {
        createRoot(el).render(<App {...props} />);
      },
    });
    ```

!!! note
    If you prefer the legacy `data-page="..."` attribute on `<div id="app">`, set `InertiaConfig(use_script_element=False)`.

---

## Custom Mount Selector & Multiple Root Templates

- **Custom Mount Container**: If your frontend mounts to `#root` instead of `#app`, set `InertiaConfig(app_selector="#root")`. Litestar automatically emits `<script type="application/json" id="root_page" data-page="root">` and `<div id="root"></div>`.
- **Per-Route Template Override**: Pass `template_name="admin.html.j2"` to `InertiaResponse(..., template_name="admin.html.j2")` when specific route groups need a distinct HTML shell.
