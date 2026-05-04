# Svelte 5 + Inertia.js + Jinja shell

`mode="template"` with a Jinja2 page shell at `templates/index.html`. The
page payload is injected through the stable script-element bootstrap
(`<script type="application/json" id="app_page" data-page="app">`). The
client uses `@inertiajs/svelte@3` and Svelte 5's `mount()` API.

## Run

```bash
litestar --app-dir examples/svelte-inertia-jinja run
```

Production:

```bash
VITE_DEV_MODE=false litestar --app-dir examples/svelte-inertia-jinja run
```

## What it demonstrates

- `mode="template"` + Jinja `TemplateConfig`
- Inertia + script-element bootstrap (Inertia v3 default)
- Svelte 5 runes inside Inertia pages
- Mirrors the existing `react-inertia-jinja` and `vue-inertia-jinja` flows for symmetry
