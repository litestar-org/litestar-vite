# Litestar Vite

Litestar Vite connects the Litestar backend to a Vite toolchain. It supports SPA, Template, and Inertia flows, and can proxy Vite dev traffic through your ASGI port or run Vite directly.

## Features

- One-port dev: proxies Vite HTTP + WS/HMR through Litestar by default; switch to two-port with `VITE_PROXY_MODE=direct`.
- SSR framework support: use `proxy_mode="ssr"` for Astro, Nuxt, SvelteKit - proxies everything except your API routes.
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

## SSR Frameworks (Astro, Nuxt, SvelteKit)

For SSR frameworks that handle their own routing, use `proxy_mode="ssr"`:

```python
import os
from pathlib import Path
from litestar import Litestar
from litestar_vite import VitePlugin, ViteConfig, PathConfig, RuntimeConfig

DEV_MODE = os.getenv("VITE_DEV_MODE", "true").lower() in ("true", "1", "yes")

app = Litestar(
    plugins=[
        VitePlugin(config=ViteConfig(
            dev_mode=DEV_MODE,
            paths=PathConfig(root=Path(__file__).parent),
            runtime=RuntimeConfig(
                proxy_mode="ssr" if DEV_MODE else None,  # Proxy in dev, static in prod
                spa_handler=not DEV_MODE,  # Serve built files in production
            ),
        ))
    ],
)
```

### Proxy Modes

| Mode | Alias | Use Case |
|------|-------|----------|
| `vite` | - | SPAs - proxies Vite assets only (default) |
| `direct` | - | Two-port dev - expose Vite port directly |
| `proxy` | `ssr` | SSR frameworks - proxies everything except API routes |

### Production Deployment

**Static Build (recommended):** Build your SSR framework to static files, then serve with Litestar:

```bash
# Build frontend
cd examples/astro-api && npm run build

# Run in production mode
VITE_DEV_MODE=false litestar --app-dir examples/astro-api run
```

Configure `bundle_dir` to match your framework's build output:

| Framework | Default Output | PathConfig |
|-----------|---------------|------------|
| Astro | `dist/` | `bundle_dir=Path("dist")` |
| Nuxt | `.output/public/` | `bundle_dir=Path(".output/public")` |
| SvelteKit | `build/` | `bundle_dir=Path("build")` |

**Two-Service:** For dynamic SSR, run the Node server alongside Litestar behind a reverse proxy.

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
