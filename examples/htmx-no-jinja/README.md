# HTMX without Jinja

`mode="template"` is valid even when **no `TemplateConfig`** is wired and Jinja2
is not installed. Handlers in `app.py` return raw HTML strings (`Response(...,
media_type="text/html")`) and the Vite asset pipeline still ships the HTMX
runtime through `resources/main.js`.

This example exists to lock the C1 contract from
`.agents/specs/dev-proxy-architecture_20260503/c1-template-jinja-decoupling/spec.md`
at the example level: template mode does not require Jinja.

## Run

```bash
litestar --app-dir examples/htmx-no-jinja run
```

Production:

```bash
VITE_DEV_MODE=false litestar --app-dir examples/htmx-no-jinja run
```

## What it demonstrates

- `mode="template"` with no `template_config=` argument
- Raw-HTML handlers (`Response(content=..., media_type="text/html")`)
- HTMX swaps via `hx-get` against fragment routes
- Vite single-port asset pipeline for the HTMX runtime
