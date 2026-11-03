<div align="center">

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/litestar-org/litestar-vite/main/docs/assets/banner-inline-dark.svg">
  <source media="(prefers-color-scheme: light)" srcset="https://raw.githubusercontent.com/litestar-org/litestar-vite/main/docs/assets/banner-inline-light.svg">
  <img alt="Litestar Vite" src="https://raw.githubusercontent.com/litestar-org/litestar-vite/main/docs/assets/banner-inline-light.svg" width="520">
</picture>

<p><strong>First-class Vite 7+, Inertia.js, Island Fragments, and End-to-End Type Generation for Litestar</strong></p>

[![PyPI](https://img.shields.io/pypi/v/litestar-vite?style=flat-square&color=1d4ed8)](https://pypi.org/project/litestar-vite/)
[![npm](https://img.shields.io/npm/v/litestar-vite-plugin?style=flat-square&color=1d4ed8)](https://www.npmjs.com/package/litestar-vite-plugin)
[![Python](https://img.shields.io/pypi/pyversions/litestar-vite?style=flat-square&color=1d4ed8)](https://pypi.org/project/litestar-vite/)
[![License](https://img.shields.io/badge/license-MIT-1d4ed8?style=flat-square)](https://github.com/litestar-org/litestar-vite/blob/main/LICENSE)
[![Docs](https://img.shields.io/badge/docs-litestar--vite-1d4ed8?style=flat-square)](https://litestar-org.github.io/litestar-vite/)

[Documentation](https://litestar-org.github.io/litestar-vite/) · [Getting Started](https://litestar-org.github.io/litestar-vite/getting-started/) · [Inertia.js](https://litestar-org.github.io/litestar-vite/frameworks/inertia/) · [API Reference](https://litestar-org.github.io/litestar-vite/reference/) · [Discord](https://discord.gg/litestar)

</div>

---

**Litestar Vite** connects [Litestar](https://litestar.dev) (Python ASGI) to the [Vite 7+](https://vite.dev) frontend toolchain through a single-port AnyIO streaming proxy, deterministic `.litestar.json` runtime bridge, Inertia.js protocol support, server-rendered UI islands, and automatic OpenAPI + AsyncAPI TypeScript generation.

## Install

```bash
uv add litestar-vite
npm install -D litestar-vite-plugin
```

Or with `pip`:

```bash
pip install litestar-vite
```

## Quickstart

```python
from litestar import Litestar
from litestar_vite import VitePlugin

app = Litestar(plugins=[VitePlugin()])
```

Scaffold a frontend template, install dependencies, and run both Litestar and Vite on a single port:

```bash
litestar assets init --template react-inertia
litestar assets install
litestar run --reload
```

## Capabilities

| Capability | What it provides |
| --- | --- |
| **Single-Port AnyIO Dev Proxy** | Streams Vite HTTP assets and upgrades `/vite-hmr` WebSockets directly through your Litestar port (`:8000`) with zero CORS setup |
| **Four Operating Modes** | First-class support for `spa`, `hybrid` (Inertia.js), `template` (Jinja2 + `<litestar-island>`), and `framework` (Astro, Nuxt, SvelteKit) |
| **Inertia.js Protocol & SSR** | Native `defer()`, `merge()`, `once()`, shared session props, Laravel Precognition validation, and fault-tolerant SSR (`RunnableDevEnvironment` in dev, `StdioIPCTransport` worker in prod) |
| **End-to-End Type Generation** | Deterministic SHA-256 `openapi.json`, `routes.json`, and `asyncapi.json` artifacts driving `@hey-api/openapi-ts`, ziggy-style `route()` / `wsRoute()`, and `createTypedChannels()` |
| **Islands & HTMX Fragments** | Server-rendered UI components via `ComponentResponse`, Jinja `vite_fragment()`, and `<litestar-island>` hydration with automatic CSS chunk injection |
| **Production & Cloud Deployment** | Manifest-resolved hashed bundles, immutable caching, subresource integrity (`integrity`), and `fsspec` CDN deployment (`litestar assets deploy`) |

## Documentation

- [Getting Started & Quick Starts](https://litestar-org.github.io/litestar-vite/getting-started/)
- [Core Concepts & Operating Modes](https://litestar-org.github.io/litestar-vite/learn/operating-modes/)
- [Inertia.js Guide](https://litestar-org.github.io/litestar-vite/frameworks/inertia/)
- [TypeGen, Typed Routes & Realtime Channels](https://litestar-org.github.io/litestar-vite/typegen/)
- [Internal Architecture & Animated Diagrams](https://litestar-org.github.io/litestar-vite/architecture/)
- [Python, TypeScript & CLI Reference](https://litestar-org.github.io/litestar-vite/reference/)

## Contributing & License

Contributions are welcome — see the [Contributing & Development Guide](docs/reference/contributing.md) for local workspace setup, test commands, and architecture guidelines. Distributed under the [MIT License](LICENSE).
