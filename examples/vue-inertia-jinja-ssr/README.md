# Vue + Inertia.js + Jinja shell + SSR

`mode="template"` with a Jinja2 page shell at `templates/index.html`, plus
Inertia server-side rendering. The Jinja shell renders
`<div id="app"></div>`; the Inertia SSR endpoint POSTs the page payload to
the Node `/render` server, then `_render_template` replaces the `#app`
element's outer HTML with the Node-rendered Inertia tree before the page is
sent to the browser.

`InertiaSSRConfig.target_selector` is set explicitly to `"#app"` for clarity
(it is the default for template mode).

## Run (two processes)

```bash
litestar --app-dir examples/vue-inertia-jinja-ssr assets install
npm --prefix examples/vue-inertia-jinja-ssr run build:ssr
npm --prefix examples/vue-inertia-jinja-ssr run start:ssr  # Terminal 1

litestar --app-dir examples/vue-inertia-jinja-ssr run        # Terminal 2
```

## What it demonstrates

- `mode="template"` + Jinja `TemplateConfig` + `InertiaConfig(ssr=...)`
- The full template-mode SSR injection path (`_render_template` →
  `target_selector="#app"`)
- Symmetric to `examples/vue-inertia-ssr` but with a Jinja shell instead of
  HTML transformation
