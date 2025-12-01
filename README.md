# Litestar Vite

Litestar Vite connects the Litestar backend to a Vite toolchain. It supports SPA, Template, and Inertia flows, and can proxy Vite dev traffic through your ASGI port or run Vite directly.

## Features

- One-port dev: proxies Vite HTTP + WS/HMR through Litestar by default; switch to two-port with `VITE_PROXY_MODE=direct`.
- SSR framework support: use `proxy_mode="ssr"` for Astro, Nuxt, SvelteKit - proxies everything except your API routes.
- Production assets: reads Vite manifest from `public/manifest.json` (configurable) and serves under `asset_url`.
- Type-safe frontends: optional OpenAPI/routes export + `@hey-api/openapi-ts` via the Vite plugin.
- Inertia support: v2 protocol with session middleware and optional SPA mode.

## Quick Start (SPA)

```bash
pip install litestar-vite
```

```python
import os
from pathlib import Path
from litestar import Litestar
from litestar_vite import VitePlugin, ViteConfig, PathConfig

DEV_MODE = os.getenv("VITE_DEV_MODE", "true").lower() in ("true", "1", "yes")

app = Litestar(
    plugins=[VitePlugin(config=ViteConfig(
        dev_mode=DEV_MODE,
        paths=PathConfig(root=Path(__file__).parent),
    ))]
)
```

```bash
litestar run --reload  # Vite dev server is proxied automatically
```

Scaffold a frontend: `litestar assets init --template vue` (or `react`, `svelte`, `htmx`, `react-inertia`, `vue-inertia`, `angular`, `astro`, `nuxt`, `sveltekit`).

## Template / HTMX

```python
from pathlib import Path
from litestar import Litestar
from litestar.contrib.jinja import JinjaTemplateEngine
from litestar.template import TemplateConfig
from litestar_vite import VitePlugin, ViteConfig, PathConfig

here = Path(__file__).parent

app = Litestar(
    template_config=TemplateConfig(directory=here / "templates", engine=JinjaTemplateEngine),
    plugins=[VitePlugin(config=ViteConfig(
        dev_mode=True,
        paths=PathConfig(root=here),
    ))],
)
```

## Inertia (v2)

Requires session middleware (32-char secret).

```python
import os
from pathlib import Path
from litestar import Litestar
from litestar.middleware.session.client_side import CookieBackendConfig
from litestar_vite import VitePlugin, ViteConfig, PathConfig
from litestar_vite.inertia import InertiaConfig

here = Path(__file__).parent
SECRET_KEY = os.environ.get("SECRET_KEY", "development-only-secret-32-chars")
session = CookieBackendConfig(secret=SECRET_KEY.encode("utf-8"))

app = Litestar(
    middleware=[session.middleware],
    plugins=[VitePlugin(config=ViteConfig(
        dev_mode=True,
        paths=PathConfig(root=here),
        inertia=InertiaConfig(root_template="index.html"),
    ))],
)
```

## Static Site Generators (Astro, Nuxt, SvelteKit)

For frameworks that generate static HTML, use `mode="spa"` with `proxy_mode="ssr"` in dev:

```python
import os
from pathlib import Path
from litestar import Litestar
from litestar_vite import VitePlugin, ViteConfig, PathConfig, RuntimeConfig

DEV_MODE = os.getenv("VITE_DEV_MODE", "true").lower() in ("true", "1", "yes")

app = Litestar(
    plugins=[
        VitePlugin(config=ViteConfig(
            mode="spa",  # Serve static build in production
            dev_mode=DEV_MODE,
            paths=PathConfig(root=Path(__file__).parent, bundle_dir=Path("dist")),
            runtime=RuntimeConfig(proxy_mode="ssr"),  # Only active when dev_mode=True
        ))
    ],
)
```

### Proxy Modes

| Mode | Alias | Use Case |
|------|-------|----------|
| `vite` | - | SPAs - proxies Vite assets only (default) |
| `direct` | - | Two-port dev - expose Vite port directly |
| `proxy` | `ssr` | Meta-frameworks - proxies everything except API routes |

### Production Deployment

Build the static site, then serve with Litestar:

```bash
# Build frontend
litestar --app-dir examples/astro assets install
litestar --app-dir examples/astro assets build
# Run in production mode
VITE_DEV_MODE=false litestar --app-dir examples/astro run
```

Configure `bundle_dir` to match your framework's build output:

| Framework | Default Output | PathConfig |
|-----------|---------------|------------|
| Astro | `dist/` | `bundle_dir=Path("dist")` |
| Nuxt | `.output/public/` | `bundle_dir=Path(".output/public")` |
| SvelteKit | `build/` | `bundle_dir=Path("build")` |

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
- Examples: `examples/` (react, vue, svelte, react-inertia, vue-inertia, astro, nuxt, sveltekit, htmx)
- Issues: <https://github.com/litestar-org/litestar-vite/issues/>
