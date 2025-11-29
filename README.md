# Litestar Vite

Litestar Vite connects the Litestar backend to a Vite toolchain. It supports SPA, Template, and Inertia flows, and can proxy Vite dev traffic through your ASGI port or run Vite directly.

## Features

- One-port dev: proxies Vite HTTP + WS/HMR through Litestar by default; switch to two-port with `VITE_PROXY_MODE=direct`.
- Production assets: reads Vite manifest from `public/manifest.json` (configurable) and serves under `asset_url`.
- Type-safe frontends: optional OpenAPI/routes export + `@hey-api/openapi-ts` via the Vite plugin.
- Inertia support: v2 protocol with session middleware and optional SPA mode.

## Quick start (SPA)

```bash
pip install litestar-vite
```

```python
from litestar import Litestar
from litestar_vite import VitePlugin, ViteConfig

app = Litestar(plugins=[VitePlugin(config=ViteConfig(dev_mode=True))])
```

```bash
litestar run  # starts Litestar; Vite dev is proxied automatically
```

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
from litestar.middleware.session.server_side import ServerSideSessionConfig, ServerSideSessionMiddleware
from litestar_vite import VitePlugin, ViteConfig
from litestar_vite.inertia import InertiaPlugin
from litestar_vite.inertia.config import InertiaConfig

app = Litestar(
    middleware=[ServerSideSessionMiddleware(config=ServerSideSessionConfig(secret="secret"))],
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

## CLI cheatsheet

- `litestar assets doctor` — diagnose/fix config
- `litestar assets init --template react|vue|svelte|...` — scaffold frontend
- `litestar assets build` / `serve` — build or watch
- `litestar assets deploy --storage gcs://bucket/assets` — upload via fsspec
- `litestar assets generate-types` — OpenAPI + routes → TS types

## Links

- Docs: <https://litestar-org.github.io/litestar-vite/>
- Examples: `examples/` (basic, inertia, spa-react)
- Issues: <https://github.com/litestar-org/litestar-vite/issues/>
