# Litestar Vite

Litestar Vite connects the Litestar backend to a Vite toolchain. It supports SPA, Template, Inertia, and meta-framework workflows, and it can proxy Vite dev traffic through your ASGI port or run Vite directly.

## Features

- One-port dev: proxies Vite HTTP + WS/HMR through Litestar by default; switch to two-port with `VITE_PROXY_MODE=direct`.
- Framework-mode support: use `mode="framework"` (alias `mode="ssr"`) for Astro, Nuxt, and SvelteKit. Litestar proxies everything except your API routes.
- Production assets: reads the Vite manifest from `public/manifest.json` (configurable) and serves under `asset_url`.
- Type-safe frontends: optional OpenAPI/routes export plus `@hey-api/openapi-ts` via the Vite plugin.
- Inertia support: stable v2 protocol with session middleware, optional script-element bootstrap, and optional SSR.

## Install

```bash
pip install litestar-vite
npm install litestar-vite-plugin
```

## Quick Start

```python
import os
from pathlib import Path
from litestar import Litestar
from litestar_vite import PathConfig, ViteConfig, VitePlugin

DEV_MODE = os.getenv("VITE_DEV_MODE", "true").lower() in ("true", "1", "yes")

app = Litestar(
    plugins=[VitePlugin(config=ViteConfig(
        dev_mode=DEV_MODE,
        paths=PathConfig(root=Path(__file__).parent),
    ))]
)
```

```bash
litestar assets init --template vue
litestar assets install
litestar run --reload
```

## Documentation

- **[Usage Guide](https://litestar-org.github.io/litestar-vite/latest/usage/)**: Core concepts, configuration, and type generation.
- **[Inertia](https://litestar-org.github.io/litestar-vite/latest/inertia/)**: Fullstack protocols and SSR.
- **[Frameworks](https://litestar-org.github.io/litestar-vite/latest/frameworks/)**: Guides for React, Vue, Svelte, Angular, Astro, and Nuxt.
- **[Reference](https://litestar-org.github.io/litestar-vite/latest/reference/)**: API and CLI documentation.

For a full list of changes, see the [Changelog](https://litestar-org.github.io/litestar-vite/latest/changelog.html).

## Common Commands

- `litestar assets init --template <name>`: scaffold a frontend or framework app
- `litestar assets install`: install frontend dependencies with the configured executor
- `litestar assets build`: build production assets
- `litestar assets serve`: run the frontend toolchain directly
- `litestar assets generate-types`: export OpenAPI, routes, and Inertia page-prop metadata
- `litestar assets doctor`: inspect and optionally repair config drift

## Development

```bash
# Install Python, docs, and JS dependencies; build package artifacts
make install && make build

# Run an example app
uv run litestar --app-dir examples/vue-inertia assets install
uv run litestar --app-dir examples/vue-inertia run
```

Replace `vue-inertia` with any other example app: `vue`, `react`, `svelte`, `react-inertia`, `htmx`, `angular`, `astro`, `nuxt`, or `sveltekit`.

For Inertia script-element bootstrap, enable `InertiaConfig(use_script_element=True)` on the Python side and keep `createInertiaApp({ defaults: { future: { useScriptElementForInitialPage: true } } })` aligned in the browser entry and SSR entry when `ssr=True` is enabled.

## Links

- Docs: <https://litestar-org.github.io/litestar-vite/latest/>
- Examples: `examples/` (React, Vue, Svelte, HTMX, Inertia, Astro, Nuxt, SvelteKit, Angular)
- Real-world example: [litestar-fullstack](https://github.com/litestar-org/litestar-fullstack)
- Issues: <https://github.com/litestar-org/litestar-vite/issues/>
