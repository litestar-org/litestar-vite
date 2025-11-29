# Litestar Vite

Seamless integration between [Litestar](https://litestar.dev/) and [Vite](https://vitejs.dev/).

## Features

- ⚡ **Dual Mode Serving**: Supports both SPA (no Jinja required) and Template modes.
- 🛠️ **Type-Safe Routing**: Auto-generate TypeScript types and route helpers from your Python code.
- 🚀 **Zero-Config**: Works out of the box with sensible defaults.
- 📦 **Framework Agnostic**: First-class support for React, Vue, Svelte, HTMX, and more.
- 🔄 **Inertia.js**: Built-in support for the Inertia.js protocol (v2).
- 🔌 **Extensible**: Easy to customize configuration and behavior.

## Installation

```bash
pip install litestar-vite
```

## Quick Start

### 1. Initialize Project

Use the CLI to scaffold a new project with your preferred framework:

```bash
# Create a new React project
litestar assets init --template react

# Or Vue + Inertia
litestar assets init --template vue-inertia

# Put the frontend under a custom folder (e.g., web/)
litestar assets init --template react --frontend-dir web
```

### 2. Configure Application

**SPA Mode (React/Vue/Svelte):**

```python
from litestar import Litestar
from litestar_vite import VitePlugin, ViteConfig

app = Litestar(
    plugins=[
        VitePlugin(config=ViteConfig(dev_mode=True))
    ]
)
```

**Template Mode (Jinja2/HTMX):**

```python
from litestar import Litestar
from litestar.contrib.jinja import JinjaTemplateEngine
from litestar.template.config import TemplateConfig
from litestar_vite import VitePlugin, ViteConfig

app = Litestar(
    template_config=TemplateConfig(
        engine=JinjaTemplateEngine(directory="templates")
    ),
    plugins=[
        VitePlugin(
            config=ViteConfig(
                mode="template",
                dev_mode=True,
            )
        )
    ]
)
```

### 3. Run Development Server

```bash
# Starts both Litestar and Vite
litestar run
```

#### Single-port proxy (default)

In dev, Litestar can proxy Vite traffic (HTTP + WS/HMR) through the ASGI port so you only expose one port.

- Default: `VITE_PROXY_MODE=proxy` (or leave unset). Vite binds to loopback with an auto-picked port if `VITE_PORT` is unset.
- The hotfile at `public/hot` records the chosen dev URL; the JS plugin/HMR client reads this.
- Proxied paths include `@vite` assets, `@fs`, `node_modules/.vite`, `src/`, and HMR WebSockets.
- To use the classic two-port mode, set `VITE_PROXY_MODE=direct` and run Vite separately.

## Type Generation

Keep your frontend in sync with your backend automatically.

**Enable in Config:**

```python
VitePlugin(config=ViteConfig(types=True))
```

**Generate Types:**

```bash
litestar assets generate-types
```

**Use in Frontend:**

```typescript
import { route } from './lib/api/routes';
import type { User } from './lib/api/types.gen';

// Type-safe URL generation
const url = route('users.show', { id: 123 });
```

## Documentation

For full documentation, visit [https://litestar-org.github.io/litestar-vite/](https://litestar-org.github.io/litestar-vite/).
