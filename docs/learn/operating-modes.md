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

| Dimension | `spa` | `hybrid` (`inertia`) | `template` (`htmx`) | `framework` (`ssr` / `ssg`) | `external` |
| --- | --- | --- | --- | --- | --- |
| **HTML Shell** | `index.html` transformed by `AppHandler` | `index.html` or Jinja transformed by `InertiaPlugin` | Litestar Jinja2 templates | Meta-framework server | External CLI dev server |
| **Router** | Client router (React Router, Vue Router, TanStack) | Litestar route handlers + Inertia client router | Litestar route handlers (`Template` / `ComponentResponse`) | Meta-framework file router; Litestar serves `/api/*` | Angular or external router |
| **Asset Tags** | Automatic HTML script transform | Automatic transform + `data-page` JSON script | Explicit `vite_hmr()` and `vite()` in Jinja | Meta-framework Vite pipeline | External bundler |
| **Dev Proxy** | `proxy_mode="vite"` (Vite assets + HMR) | `proxy_mode="vite"` (Vite assets + HMR) | `proxy_mode="vite"` (Vite assets + HMR) | `proxy_mode="proxy"` (all non-API routes) | `proxy_mode="proxy"` to external target |
| **Data Contract** | OpenAPI SDK + `route()` | Inertia `PageProps` + `route()` | Jinja context + `<litestar-island>` | OpenAPI SDK + `route()` | OpenAPI SDK + `route()` |

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

!!! tip
    Always set `mode` explicitly (`mode="spa"`, `mode="hybrid"`, `mode="template"`, `mode="framework"`, or `mode="external"`) in production applications so your intent is self-documenting and validated at startup.
