# Operating Modes

Every full-stack Python + JavaScript application must answer four architectural questions:

1. **Who owns the initial HTML shell?** (Vite `index.html`, Jinja2 template, or an external framework server?)
2. **Who owns URL routing?** (Client router, Litestar route handlers, or a meta-framework router?)
3. **How are Vite `<script>` and `<link>` tags injected?** (HTML transform pipeline, Jinja template helpers, or framework middleware?)
4. **How does data cross from Python to the UI?** (Typed OpenAPI JSON, Inertia `PageProps`, or HTML fragments?)

`ViteConfig(mode=...)` answers all four questions with a single setting. Use the interactive diagram below to compare the primary operating modes:

--8<-- "tools/docs/includes/diagram-operating-modes.html"

---

## Comparison Matrix

| Dimension | `mode="spa"` | `mode="hybrid"` (`"inertia"`) | `mode="template"` (`"htmx"`) | `mode="framework"` (`"ssr"` / `"ssg"`) | `mode="external"` |
| --- | --- | --- | --- | --- | --- |
| **HTML Shell Owner** | `index.html` served & transformed by `AppHandler` | `index.html` (or Jinja `root_template`) transformed by `InertiaPlugin` | Litestar `JinjaTemplateEngine` (`*.html.j2`) | Meta-framework server (`:4321` / `:3000` / `:5173`) | External CLI dev server (`ng serve`) |
| **Router Owner** | Client router (`react-router`, `vue-router`, TanStack Router) | Litestar `@get(..., component="...")` + Inertia client router | Litestar `@get(...)` returning `Template` or `ComponentResponse` | Meta-framework file router; Litestar serves `/api/*` | Angular / external router |
| **Asset Tag Injection** | Automatic via `transform_html_scripts()` on `index.html` | Automatic via `transform_html_scripts()` + `<script data-page="app">` | Explicit `{{ vite_hmr() }}` and `{{ vite('...') }}` in Jinja | Handled by the meta-framework Vite pipeline | Handled by external bundler |
| **Dev Proxy Mode** | `proxy_mode="vite"` (allowlist: Vite assets + HMR) | `proxy_mode="vite"` (allowlist: Vite assets + HMR) | `proxy_mode="vite"` (allowlist: Vite assets + HMR) | `proxy_mode="proxy"` (denylist: proxies all non-API routes) | `proxy_mode="proxy"` to `ExternalDevServer.target` |
| **Primary Data Contract** | `@hey-api/openapi-ts` SDK + `route()` | Inertia `PageProps` (`page-props.ts`) + `route()` | Jinja context + `<litestar-island>` / `ComponentResponse` | `@hey-api/openapi-ts` SDK + `route()` | `@hey-api/openapi-ts` SDK + `route()` |

---

## Mode Aliases

For readability across different frontend stacks, `ViteConfig.mode` accepts descriptive aliases that normalize to the canonical mode:

- **`"spa"`** — Single-Page Application (`index.html` catch-all route served by Litestar).
- **`"hybrid"`** or **`"inertia"`** — Inertia.js v2 / v3 server-driven SPA.
- **`"template"`** or **`"htmx"`** — Server-rendered Jinja2 templates, HTMX partials, and `<litestar-island>` fragments.
- **`"framework"`**, **`"ssr"`**, or **`"ssg"`** — Meta-frameworks (Astro, Nuxt, SvelteKit) where Litestar proxies non-API routes in development.
- **`"external"`** — Non-Vite build tools (such as Angular CLI `ng serve`) managed via `RuntimeConfig(external_dev_server=ExternalDevServer(...))`.

---

## Configuring Each Mode in Python

```python title="docs/examples/learn/vite_config_modes.py"
--8<-- "docs/examples/learn/vite_config_modes.py"
```

---

## Mode Auto-Detection

When `ViteConfig.mode` is omitted (`mode=None`), `ViteConfig.__post_init__` resolves the operating mode deterministically:

1. If `inertia` is enabled (`InertiaConfig` or `inertia=True`) and `root_template` ends with `.html` -> **`mode="hybrid"`**.
2. If `inertia` is enabled and `root_template` is a Jinja template (`.j2`, `.jinja`, `.jinja2`) -> **`mode="hybrid"`** with Jinja rendering.
3. If `Litestar(template_config=...)` is registered without Inertia -> **`mode="template"`**.
4. If an `index.html` exists in `root_dir`, `resource_dir`, or `public_dir` -> **`mode="spa"`**.

> [!TIP]
> Always set `mode` explicitly (`mode="spa"`, `mode="hybrid"`, `mode="template"`, `mode="framework"`, or `mode="external"`) in production applications so your intent is self-documenting and validated at startup.
