# Svelte 5 + Inertia.js

`mode="hybrid"` (auto-derived from `InertiaConfig` + `index.html` presence)
with Svelte 5 + `@inertiajs/svelte@3`. Server handlers expose Inertia
components (`@get("/", component="Home")`) and the SPA bootstraps from the
`#app_page` script element.

## Run

```bash
litestar --app-dir examples/svelte-inertia run
```

Production:

```bash
VITE_DEV_MODE=false litestar --app-dir examples/svelte-inertia run
```

## What it demonstrates

- Svelte 5 runes (`$props()`) inside Inertia pages
- `mount(App, ...)` Svelte 5 entrypoint
- `@inertiajs/svelte` client app + visit options + CSRF headers
- Single-port asset pipeline through `litestar-vite-plugin`
