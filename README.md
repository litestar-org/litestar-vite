# Litestar Vite

Litestar Vite connects the Litestar backend to a Vite toolchain. It supports SPA, Template, and Inertia flows, and can proxy Vite dev traffic through your ASGI port or run Vite directly.

## Features

- One-port dev: proxies Vite HTTP + WS/HMR through Litestar by default; switch to two-port with `VITE_PROXY_MODE=direct`.
- Production assets: reads Vite manifest from `public/manifest.json` (configurable) and serves under `asset_url`.
- Type-safe frontends: optional OpenAPI/routes export + `@hey-api/openapi-ts` via the Vite plugin.
- Inertia support: v2 protocol with session middleware and optional SPA mode.

## Quick start (React TanStack SPA)

```bash
pip install litestar-vite
litestar assets init --template react-tanstack
litestar assets install  # installs frontend deps via configured executor
```

```python
from litestar import Litestar
from litestar_vite import VitePlugin, ViteConfig

app = Litestar(plugins=[VitePlugin(config=ViteConfig(dev_mode=True))])  # SPA mode by default
```

```bash
litestar run --reload  # starts Litestar; Vite dev is proxied automatically
```

Other templates: `react`, `vue`, `svelte`, `htmx`, `react-inertia`, `vue-inertia`, `svelte-inertia`, `angular`, `angular-cli`, `astro`, `nuxt`, `sveltekit` (see `litestar assets init --help`).

## Template / HTMX

```python
from litestar import Litestar
from litestar.contrib.jinja import JinjaTemplateEngine
from litestar.template.config import TemplateConfig
from litestar_vite import VitePlugin, ViteConfig

app = Litestar(
    template_config=TemplateConfig(engine=JinjaTemplateEngine(directory="templates")),
    plugins=[VitePlugin(config=ViteConfig(mode="template", dev_mode=True))],
)
```

## Inertia (v2)

Requires session middleware.

```python
from litestar import Litestar
from litestar.middleware.session.client_side import CookieBackendConfig
from litestar_vite import VitePlugin, ViteConfig
from litestar_vite.inertia import InertiaPlugin
from litestar_vite.inertia.config import InertiaConfig

session_backend = CookieBackendConfig(secret="dev-secret")

app = Litestar(
    middleware=[session_backend.middleware],
    plugins=[
        VitePlugin(config=ViteConfig(mode="template", inertia=True, dev_mode=True)),
        InertiaPlugin(InertiaConfig()),
    ],
)
```

## Type generation

```python
VitePlugin(config=ViteConfig(types=True))  # enable exports
```

```bash
litestar assets generate-types  # one-off or CI
```

## CLI cheat sheet

- `litestar assets doctor` — diagnose/fix config
- `litestar assets init --template react|vue|svelte|...` — scaffold frontend
- `litestar assets build` / `serve` — build or watch
- `litestar assets deploy --storage gcs://bucket/assets` — upload via fsspec
- `litestar assets generate-types` — OpenAPI + routes → TS types
- `litestar assets install` — install frontend deps with the configured executor

### Doctor command highlights

- Prints Python vs Vite config snapshot (asset URLs, bundle/hot paths, ports, modes).
- Flags missing hot file (dev proxy), missing manifest (prod), type-gen exports, env/config mismatches, and plugin install issues.
- `--fix` can rewrite simple vite.config values (assetUrl, bundleDirectory, hotFile, type paths) after creating a backup.

## Links

- Docs: <https://litestar-org.github.io/litestar-vite/>
- Examples: `examples/` (basic, inertia, spa-react)
- Issues: <https://github.com/litestar-org/litestar-vite/issues/>
