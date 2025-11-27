# Litestar-Vite v2.0: Unified Redesign PRD

**Version**: 1.0
**Created**: 2025-11-27
**Status**: Draft
**Slug**: `litestar-vite-v2-unified`

---

## Executive Summary

Litestar-Vite v2.0 is a **complete architectural overhaul** that unifies:

1. **Dual Mode Serving** - Standard SPA mode OR Template mode (no forced Jinja)
2. **Type-Safe Routing** - Auto-generated TypeScript types, Zod schemas, and typed `route()` helper
3. **Modern Architecture** - Async-first, proper DI, clean configuration
4. **Multi-Framework Support** - First-class support for Inertia, HTMX, React SPA, Vue SPA, vanilla JS

**Breaking Changes Allowed** - This is a clean slate redesign for simplicity and power.

---

## Problem Statement

### Current Pain Points

| Problem | Impact | Current State |
|---------|--------|---------------|
| **Forced Jinja Templates** | Can't use standard `index.html` | Must wrap in `.j2` even for SPAs |
| **No Type Safety** | Runtime errors, no autocomplete | Routes are strings, no TypeScript |
| **Singleton Anti-Pattern** | Hard to test, concurrency risks | `ViteAssetLoader` is singleton |
| **Synchronous I/O** | Blocks event loop at startup | Manifest read is sync |
| **Monolithic Config** | Hard to extend/validate | `ViteConfig` mixes concerns |
| **Template Engine Coupling** | Requires custom `ViteTemplateEngine` | Removed in old branch but incomplete |
| **Manual Type Sync** | Python changes break frontend silently | No codegen pipeline |

### What Users Want

```python
# Simple: Just works with standard Vite setup
app = Litestar(plugins=[VitePlugin()])

# Powerful: Full type safety when needed
app = Litestar(plugins=[
    VitePlugin(
        types=True,  # Generate TypeScript + Zod
        mode="spa",  # Or "template" or "htmx"
    )
])
```

---

## Goals

### Primary Goals

1. **Zero-Config SPA Mode** - Standard `index.html` works without Jinja
2. **Type-Safe Everything** - Routes, params, responses auto-typed
3. **Async-First** - All I/O non-blocking
4. **Framework Agnostic** - Works with React, Vue, Svelte, HTMX, vanilla
5. **Simple but Powerful** - Sensible defaults, full customization

### Non-Goals

1. **Backward Compatibility** - Clean break for v2.0
2. **Support for Python < 3.10** - Modern Python only
3. **Custom Template Engines** - Focus on Jinja2 or none

---

## Architecture Overview

### Dual Mode System

```
┌─────────────────────────────────────────────────────────────────────┐
│                     LITESTAR-VITE v2.0 MODES                        │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                    SPA MODE (New Default)                     │   │
│  │  • Standard index.html (no Jinja required)                   │   │
│  │  • Auto-injection of routes, Inertia props at runtime        │   │
│  │  • Dev: Proxy to Vite dev server                             │   │
│  │  • Prod: Serve built index.html with injection               │   │
│  │  • Perfect for: React, Vue, Svelte, Inertia SPAs             │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                      │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                    TEMPLATE MODE (Classic)                    │   │
│  │  • Jinja2 templates with {{ vite() }} helpers                │   │
│  │  • Full server-side rendering control                        │   │
│  │  • Perfect for: HTMX, multi-page apps, hybrid apps           │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                      │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                    HTMX MODE (New)                            │   │
│  │  • Template mode optimized for HTMX patterns                 │   │
│  │  • Partial template rendering                                │   │
│  │  • HX-* header handling                                      │   │
│  │  • Perfect for: HTMX + Alpine, hypermedia apps               │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

### Type Generation Pipeline

```
┌──────────────┐     ┌───────────────┐     ┌────────────────────┐
│   Litestar   │────>│   OpenAPI     │────>│   @hey-api/        │
│   Routes     │     │   Schema      │     │   openapi-ts       │
│   (Python)   │     │   (JSON)      │     │                    │
└──────────────┘     └───────────────┘     └────────────────────┘
       │                    │                       │
       │                    │                       ▼
       │                    │              ┌────────────────────┐
       │                    │              │   Generated Files  │
       │                    │              │   • types.gen.ts   │
       │                    │              │   • zod.gen.ts     │
       │                    │              │   • sdk.gen.ts     │
       │                    │              └────────────────────┘
       │                    │
       ▼                    │
┌──────────────┐           │
│   Routes     │           │
│   Metadata   │───────────┘
│   (JSON)     │
└──────────────┘
       │
       ▼
┌──────────────────────────┐
│   routes.gen.ts          │
│   • Typed route() helper │
│   • RouteName union      │
│   • RouteParams map      │
└──────────────────────────┘
```

### Component Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         VitePlugin                                   │
│  • Entry point for all configuration                                │
│  • Registers services in DI                                         │
│  • Manages server lifespan                                          │
└─────────────────────────────────────────────────────────────────────┘
         │
         ├──────────────────┬──────────────────┬──────────────────┐
         ▼                  ▼                  ▼                  ▼
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│  ViteConfig     │ │ ViteAssetLoader │ │ ViteSPAHandler  │ │ ViteTypeGen     │
│  (Dataclass)    │ │ (DI Service)    │ │ (Controller)    │ │ (Codegen)       │
│                 │ │                 │ │                 │ │                 │
│ • PathConfig    │ │ • Async I/O     │ │ • HTML inject   │ │ • Schema export │
│ • RuntimeConfig │ │ • Manifest      │ │ • Dev proxy     │ │ • Type gen      │
│ • TypeGenConfig │ │ • Tag rendering │ │ • Prod serve    │ │ • Route helper  │
└─────────────────┘ └─────────────────┘ └─────────────────┘ └─────────────────┘
```

---

## Detailed Design

### 1. Configuration System

**Clean separation of concerns:**

```python
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

@dataclass
class PathConfig:
    """File system paths."""
    root: Path = field(default_factory=Path.cwd)
    bundle_dir: Path = Path("public")
    resource_dir: Path = Path("resources")
    manifest_name: str = "manifest.json"
    hot_file: str = "hot"


@dataclass
class RuntimeConfig:
    """Execution settings."""
    dev_mode: bool = False
    hot_reload: bool = True
    host: str = "localhost"
    port: int = 5173
    protocol: Literal["http", "https"] = "http"

    # Executor settings
    executor: Literal["node", "bun", "deno"] = "node"
    run_command: list[str] | None = None  # Auto-detect if None
    build_command: list[str] | None = None


@dataclass
class TypeGenConfig:
    """Type generation settings."""
    enabled: bool = False
    output: Path = Path("src/generated")
    openapi_path: Path = Path("src/generated/openapi.json")
    routes_path: Path = Path("src/generated/routes.json")

    # @hey-api/openapi-ts options
    generate_zod: bool = True
    generate_sdk: bool = False

    # Watch patterns for regeneration
    watch_patterns: list[str] = field(default_factory=lambda: [
        "**/routes.py", "**/handlers.py", "**/controllers/**/*.py"
    ])


@dataclass
class InertiaConfig:
    """Inertia.js specific settings."""
    enabled: bool = False
    root_template: str = "index.html"

    # Shared props
    include_routes: bool = True
    include_flash: bool = True
    include_errors: bool = True


@dataclass
class ViteConfig:
    """Root configuration - the only thing users need to touch."""

    # Mode selection
    mode: Literal["spa", "template", "htmx"] = "spa"

    # Nested configs (with smart defaults)
    paths: PathConfig = field(default_factory=PathConfig)
    runtime: RuntimeConfig = field(default_factory=RuntimeConfig)
    types: TypeGenConfig | bool = False  # True = enable with defaults
    inertia: InertiaConfig | bool = False  # True = enable with defaults

    # Convenience shortcuts
    dev_mode: bool = False  # Shortcut for runtime.dev_mode

    def __post_init__(self):
        # Normalize bool to config
        if self.types is True:
            self.types = TypeGenConfig(enabled=True)
        elif self.types is False:
            self.types = TypeGenConfig(enabled=False)

        if self.inertia is True:
            self.inertia = InertiaConfig(enabled=True)
        elif self.inertia is False:
            self.inertia = InertiaConfig(enabled=False)

        # Apply dev_mode shortcut
        if self.dev_mode:
            self.runtime.dev_mode = True
```

**Usage examples:**

```python
# Minimal - SPA mode with defaults
VitePlugin(config=ViteConfig())

# Development mode
VitePlugin(config=ViteConfig(dev_mode=True))

# With type generation
VitePlugin(config=ViteConfig(
    dev_mode=True,
    types=True,  # Enable with defaults
))

# Full Inertia setup
VitePlugin(config=ViteConfig(
    dev_mode=True,
    types=True,
    inertia=True,
))

# Template mode for HTMX
VitePlugin(config=ViteConfig(
    mode="template",
    dev_mode=True,
))

# Advanced customization
VitePlugin(config=ViteConfig(
    mode="spa",
    paths=PathConfig(
        bundle_dir=Path("dist"),
        resource_dir=Path("src"),
    ),
    runtime=RuntimeConfig(
        executor="bun",
        port=3000,
    ),
    types=TypeGenConfig(
        enabled=True,
        generate_zod=True,
        generate_sdk=True,
    ),
))
```

### 2. Async-First Asset Loader

```python
from anyio import Path as AsyncPath
from litestar.di import Provide

class ViteAssetLoader:
    """Async asset loader - provided via DI, not singleton."""

    def __init__(self, config: ViteConfig) -> None:
        self._config = config
        self._manifest: dict[str, Any] = {}
        self._initialized = False

    async def initialize(self) -> None:
        """Async initialization - called during app startup."""
        if self._initialized:
            return

        if self._config.runtime.dev_mode and self._config.runtime.hot_reload:
            await self._read_hot_file()
        else:
            await self._parse_manifest()

        self._initialized = True

    async def _parse_manifest(self) -> None:
        """Async manifest parsing using anyio."""
        manifest_path = AsyncPath(
            self._config.paths.bundle_dir / self._config.paths.manifest_name
        )
        if await manifest_path.exists():
            content = await manifest_path.read_text()
            self._manifest = json.loads(content)

    async def _read_hot_file(self) -> None:
        """Read hot file for dev server URL."""
        hot_path = AsyncPath(
            self._config.paths.bundle_dir / self._config.paths.hot_file
        )
        if await hot_path.exists():
            self._vite_base_url = await hot_path.read_text()

    def render_asset_tag(self, path: str, attrs: dict | None = None) -> str:
        """Generate asset tags (sync - uses cached manifest)."""
        # ... implementation

    def render_hmr_client(self) -> str:
        """Generate HMR client script tag."""
        # ... implementation
```

### 3. SPA Mode Handler

```python
import httpx
from litestar import Controller, get
from litestar.response import Response

class ViteSPAHandler:
    """Handles SPA mode serving with HTML injection."""

    def __init__(self, config: ViteConfig, asset_loader: ViteAssetLoader):
        self._config = config
        self._loader = asset_loader
        self._html_cache: str | None = None

    async def get_html(self, request: Request) -> str:
        """Get HTML with injections."""
        if self._config.runtime.dev_mode:
            return await self._proxy_dev_server(request)
        else:
            return await self._serve_production(request)

    async def _proxy_dev_server(self, request: Request) -> str:
        """Proxy to Vite dev server and inject."""
        async with httpx.AsyncClient() as client:
            vite_url = f"{self._config.runtime.protocol}://{self._config.runtime.host}:{self._config.runtime.port}"
            response = await client.get(f"{vite_url}/")
            html = response.text

        return self._inject_litestar_data(html, request)

    async def _serve_production(self, request: Request) -> str:
        """Serve built index.html with injection."""
        if self._html_cache is None:
            index_path = AsyncPath(self._config.paths.bundle_dir / "index.html")
            self._html_cache = await index_path.read_text()

        return self._inject_litestar_data(self._html_cache, request)

    def _inject_litestar_data(self, html: str, request: Request) -> str:
        """Inject routes, Inertia props, etc. into HTML."""
        injections = []

        # Always inject routes if type gen enabled
        if self._config.types.enabled:
            routes = self._get_routes_json(request.app)
            injections.append(f'<script>window.__LITESTAR_ROUTES__={routes}</script>')

        # Inject Inertia data if enabled
        if self._config.inertia.enabled:
            page_data = self._get_inertia_page(request)
            injections.append(f'<script>window.__INERTIA_PAGE__={page_data}</script>')

            # Also set data-page on #app div
            html = self._set_data_page(html, page_data)

        # Inject into <head>
        if injections:
            injection_html = '\n'.join(injections)
            html = html.replace('</head>', f'{injection_html}\n</head>')

        return html
```

### 4. Type Generation Integration

**Python side - CLI commands:**

```python
# cli.py
@vite_group.command(name="export-schema")
def export_schema(app: Litestar, output: Path) -> None:
    """Export OpenAPI schema for type generation."""
    from litestar.cli.commands.schema import _generate_openapi_schema
    _generate_openapi_schema(app, output)


@vite_group.command(name="export-routes")
def export_routes(app: Litestar, output: Path, only: str | None, exclude: str | None) -> None:
    """Export Ziggy-like routes metadata."""
    routes = generate_routes_metadata(app, only=only, exclude=exclude)
    output.write_text(json.dumps(routes, indent=2))


@vite_group.command(name="generate-types")
def generate_types(app: Litestar, output: Path) -> None:
    """Full type generation pipeline."""
    # 1. Export OpenAPI schema
    schema_path = output / "openapi.json"
    export_schema(app, schema_path)

    # 2. Export routes metadata
    routes_path = output / "routes.json"
    export_routes(app, routes_path, only=None, exclude=None)

    # 3. Run @hey-api/openapi-ts (via subprocess)
    subprocess.run(["npx", "@hey-api/openapi-ts"], check=True)

    # 4. Generate route helper
    generate_route_helper(routes_path, output / "routes.ts")
```

**TypeScript side - Vite plugin integration:**

```typescript
// vite.config.ts
import litestar from 'litestar-vite-plugin';

export default defineConfig({
  plugins: [
    litestar({
      input: 'resources/main.ts',

      // Type generation integrated into plugin
      types: {
        enabled: true,
        output: 'src/lib/api',
        exportCommand: 'uv run litestar vite generate-types',
        watch: ['**/routes.py', '**/handlers.py'],
      },
    }),
  ],
});
```

**Generated route helper:**

```typescript
// src/lib/api/routes.ts (generated)
export type RouteName =
  | "home"
  | "users.index"
  | "users.show"
  | "users.create";

export interface RouteParams {
  "home": Record<string, never>;
  "users.index": { query?: { page?: number; limit?: number } };
  "users.show": { params: { id: string } };
  "users.create": { body: CreateUserRequest };
}

const routes = {
  "home": "/",
  "users.index": "/users",
  "users.show": "/users/{id}",
  "users.create": "/users",
} as const;

export function route<T extends RouteName>(
  name: T,
  args?: RouteParams[T] extends { params: infer P } ? P : never
): string {
  let path = routes[name] as string;
  if (args) {
    for (const [key, value] of Object.entries(args)) {
      path = path.replace(`{${key}}`, encodeURIComponent(String(value)));
    }
  }
  return path;
}

// Utilities
export const router = {
  current: () => window.location.pathname,
  has: (name: RouteName) => name in routes,
  match: (pattern: string) => {
    // Wildcard matching like 'users.*'
  },
};
```

### 5. Framework-Specific Modes

#### SPA Mode (React/Vue/Svelte)

```python
# app.py
from litestar import Litestar
from litestar_vite import VitePlugin, ViteConfig

app = Litestar(
    plugins=[
        VitePlugin(config=ViteConfig(
            mode="spa",
            dev_mode=True,
            types=True,
        ))
    ],
)
```

```html
<!-- index.html (standard Vite) -->
<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8" />
  <title>My App</title>
</head>
<body>
  <div id="app"></div>
  <script type="module" src="/src/main.ts"></script>
</body>
</html>
```

Litestar automatically:

- Serves `index.html` at `/`
- Injects `window.__LITESTAR_ROUTES__`
- Proxies to Vite dev server in dev mode

#### Inertia Mode

```python
# app.py
app = Litestar(
    plugins=[
        VitePlugin(config=ViteConfig(
            mode="spa",
            dev_mode=True,
            types=True,
            inertia=True,
        ))
    ],
    route_handlers=[
        # Inertia routes use component= parameter
        get("/", component="Home")(lambda: {"message": "Hello"}),
        get("/users/{id}", component="Users/Show")(lambda id: {"user_id": id}),
    ],
)
```

```html
<!-- index.html -->
<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8" />
</head>
<body>
  <div id="app"></div>
  <script type="module" src="/src/main.ts"></script>
</body>
</html>
```

Litestar automatically:

- Injects `window.__LITESTAR_ROUTES__`
- Injects `window.__INERTIA_PAGE__`
- Sets `data-page` attribute on `#app` div
- Handles `X-Inertia` headers for partial renders

#### Template Mode (HTMX/Multi-page)

```python
# app.py
app = Litestar(
    plugins=[
        VitePlugin(config=ViteConfig(
            mode="template",
            dev_mode=True,
        ))
    ],
    template_config=TemplateConfig(
        engine=JinjaTemplateEngine(directory="templates")
    ),
    route_handlers=[
        get("/")(lambda: Template("index.html")),
    ],
)
```

```html
<!-- templates/index.html -->
<!DOCTYPE html>
<html>
<head>
  {{ vite_hmr() }}
  {{ vite('src/main.ts') }}
</head>
<body>
  <div id="app" hx-get="/partials/content" hx-trigger="load">
    Loading...
  </div>
</body>
</html>
```

#### HTMX Mode (Enhanced Template)

```python
# app.py
app = Litestar(
    plugins=[
        VitePlugin(config=ViteConfig(
            mode="htmx",  # Template mode with HTMX helpers
            dev_mode=True,
        ))
    ],
    route_handlers=[
        # Full page
        get("/")(lambda: Template("index.html")),

        # Partials (auto-detected via HX-Request header)
        get("/users")(lambda request:
            Template("partials/users.html") if request.htmx else Template("pages/users.html")
        ),
    ],
)
```

#### Astro Mode (SSG/SSR Islands)

Astro uses Vite internally and provides its own integration system. Litestar-vite provides an optional Astro integration for API-first development:

```python
# app.py - Litestar as API backend for Astro
app = Litestar(
    plugins=[
        VitePlugin(config=ViteConfig(
            mode="astro",
            dev_mode=True,
            types=True,  # Generate types for Astro to consume
        ))
    ],
    route_handlers=[api_router],
)
```

```typescript
// astro.config.mjs
import { defineConfig } from 'astro/config';
import litestar from 'litestar-vite-plugin/astro';

export default defineConfig({
  integrations: [
    litestar({
      // Proxy API requests to Litestar during dev
      apiProxy: 'http://localhost:8000',
      // Import generated types
      typesPath: './src/generated/api',
    }),
  ],
  vite: {
    // Astro's Vite config merged with litestar-vite
  },
});
```

```typescript
// src/pages/users/[id].astro
---
import type { User } from '../generated/api/types.gen';
import { route } from '../generated/api/routes';

const { id } = Astro.params;
const response = await fetch(route('users.show', { id }));
const user: User = await response.json();
---

<html>
  <body>
    <h1>{user.name}</h1>
  </body>
</html>
```

**Astro Integration Features:**

- API proxy configuration for dev server
- Type generation integration (shares `@hey-api/openapi-ts` output)
- Route helper generation compatible with Astro's static paths
- SSR adapter support for Litestar-backed Astro apps

#### SvelteKit Mode (SSR/SPA)

SvelteKit uses Vite internally. Litestar-vite provides a SvelteKit-compatible integration:

```python
# app.py - Litestar as API backend for SvelteKit
app = Litestar(
    plugins=[
        VitePlugin(config=ViteConfig(
            mode="sveltekit",
            dev_mode=True,
            types=True,
        ))
    ],
    route_handlers=[api_router],
)
```

```typescript
// vite.config.ts
import { sveltekit } from '@sveltejs/kit/vite';
import { litestar } from 'litestar-vite-plugin';
import { defineConfig } from 'vite';

export default defineConfig({
  plugins: [
    litestar({
      // Proxy API requests to Litestar during dev
      input: [],  // SvelteKit handles entry points
      types: {
        enabled: true,
        output: 'src/lib/api',
      },
    }),
    sveltekit(),  // SvelteKit plugin comes after
  ],
});
```

```typescript
// src/routes/users/[id]/+page.ts
import type { PageLoad } from './$types';
import type { User } from '$lib/api/types.gen';
import { route } from '$lib/api/routes';

export const load: PageLoad = async ({ params, fetch }) => {
  const response = await fetch(route('users.show', { id: params.id }));
  const user: User = await response.json();
  return { user };
};
```

```svelte
<!-- src/routes/users/[id]/+page.svelte -->
<script lang="ts">
  import type { PageData } from './$types';
  export let data: PageData;
</script>

<h1>{data.user.name}</h1>
<p>{data.user.email}</p>
```

**SvelteKit Integration Features:**

- Vite plugin compatible with `@sveltejs/kit/vite`
- Type generation with SvelteKit's `$lib` alias support
- API proxy for dev server (configurable routes)
- SSR load function typing
- Svelte 5 runes compatibility

---

## Future Consideration: WASM-Based Vite Alternative

**Status: Not Recommended for v2.0**

We investigated running Vite transformations via WASM to eliminate the Node.js dependency:

| Approach | Feasibility | Performance | Recommendation |
|----------|-------------|-------------|----------------|
| **Pyodide (Python in WASM)** | N/A | N/A | Wrong direction - we need Node.js replacement, not Python |
| **esbuild-wasm** | Possible | 3x slower than native | Not recommended |
| **swc-wasm** | Possible | Slower than native | Not recommended |
| **Native esbuild binary** | Feasible | Fastest | Best alternative to Node.js |

**Why WASM is not viable:**

1. **Vite is a Node.js application** - It depends on Node's `fs`, `http`, `path` modules and cannot be compiled to WASM
2. **WASM performance overhead** - String passing between Python and WASM incurs serialization costs
3. **Missing Vite features** - Would require reimplementing import rewriting, HMR, and the plugin ecosystem
4. **Complexity vs. benefit** - The Node.js sidecar is simple and well-tested

**Future alternatives (post-v2.0):**

1. **Rolldown** - Rust-based bundler being developed by Evan You to eventually power Vite. Once stable, could provide native Python bindings
2. **Native esbuild wrapper** - Ship standalone esbuild binary with Python package, implement minimal import rewriting in Python
3. **Oxc bindings** - Rust-based JS toolchain with potential Python bindings

**Recommendation:** Keep the Node.js sidecar for v2.0. Revisit when Rolldown matures or if user demand for Node-free operation is high.

---

## Implementation Phases

### Phase 1: Core Architecture (Foundation)

1. **Configuration Refactor**
   - Split `ViteConfig` into nested dataclasses
   - Add validation and smart defaults
   - Remove `ViteTemplateEngine` (use standard Jinja)

2. **Async Asset Loader**
   - Rewrite `ViteAssetLoader` with anyio
   - Remove singleton pattern
   - Register as DI service

3. **Plugin Overhaul**
   - Update `VitePlugin` for new config
   - Register services in DI
   - Update server lifespan

### Phase 2: Dual Mode System

1. **SPA Handler**
   - Create `ViteSPAHandler` controller
   - Implement dev proxy with httpx
   - Implement production serving
   - HTML injection system

2. **Template Mode Updates**
   - Keep `{{ vite() }}` helpers working
   - Optional Jinja (not required)
   - HTMX mode helpers

### Phase 3: Type Generation

1. **Python CLI**
   - `export-schema` command (wraps Litestar)
   - `export-routes` command (Ziggy-like)
   - `generate-types` command (full pipeline)

2. **TypeScript Integration**
   - Extend Vite plugin with `types` config
   - Watch mode for Python files
   - Call `@hey-api/openapi-ts`
   - Generate route helper

3. **Route Helper**
   - Typed `route()` function
   - `RouteName` union type
   - `RouteParams` mapped type
   - Utility functions (`router.current()`, etc.)

### Phase 4: Inertia Enhancement

1. **Inertia SPA Mode**
   - Auto-injection of page props
   - `data-page` attribute setting
   - Shared props typing

2. **Type Generation for Inertia**
   - Page component → props mapping
   - `useTypedPage()` hook generation
   - Flash/errors typing

### Phase 5: Polish & Docs

1. **Examples**
   - SPA (React + Vite)
   - SPA (Vue + Inertia)
   - Template (HTMX + Alpine)
   - Full-stack typed (all features)

2. **Documentation**
   - Migration guide from v1
   - Mode selection guide
   - Type generation setup

3. **Testing**
   - Full test coverage
   - Integration tests per mode

---

## API Reference

### Python

```python
# Main exports
from litestar_vite import VitePlugin, ViteConfig

# Configuration
from litestar_vite.config import (
    ViteConfig,
    PathConfig,
    RuntimeConfig,
    TypeGenConfig,
    InertiaConfig,
)

# Services (for DI injection)
from litestar_vite.loader import ViteAssetLoader

# Inertia (optional)
from litestar_vite.inertia import InertiaPlugin, InertiaResponse
```

### TypeScript

```typescript
// From litestar-vite-plugin
import litestar from 'litestar-vite-plugin';

// From generated files
import { route, router, type RouteName, type RouteParams } from './lib/api/routes';
import type { User, CreateUserRequest } from './lib/api/types.gen';
import { UserSchema, CreateUserRequestSchema } from './lib/api/zod.gen';
```

### CLI

```bash
# Development
litestar vite dev              # Start dev server (alias for `run`)

# Schema/Type generation
litestar vite export-schema    # Export OpenAPI JSON
litestar vite export-routes    # Export routes metadata
litestar vite generate-types   # Full type generation pipeline

# Build
litestar vite build            # Production build

# Utilities
litestar vite status           # Show current config and status
litestar vite init             # Initialize new project
```

---

## Migration from v1

### Configuration Changes

```python
# v1.x
ViteConfig(
    bundle_dir="public",
    resource_dir="resources",
    hot_reload=True,
    port=5173,
    dev_mode=True,
    use_server_lifespan=True,
)

# v2.0
ViteConfig(
    dev_mode=True,  # Shortcut
    paths=PathConfig(
        bundle_dir=Path("public"),
        resource_dir=Path("resources"),
    ),
    runtime=RuntimeConfig(
        hot_reload=True,
        port=5173,
    ),
)

# Or simply:
ViteConfig(dev_mode=True)  # Uses all defaults
```

### Template Changes

```html
<!-- v1.x: Required Jinja template -->
<!DOCTYPE html>
<html>
<head>
  {{ vite_hmr() }}
  {{ vite('main.ts') }}
</head>
<body>
  <div id="app"></div>
</body>
</html>

<!-- v2.0: Standard index.html works! -->
<!DOCTYPE html>
<html>
<head>
  <script type="module" src="/src/main.ts"></script>
</head>
<body>
  <div id="app"></div>
</body>
</html>
```

### Import Changes

```python
# v1.x
from litestar_vite import ViteConfig, VitePlugin
from litestar_vite.template_engine import ViteTemplateEngine  # REMOVED

# v2.0
from litestar_vite import ViteConfig, VitePlugin
# No ViteTemplateEngine - use standard JinjaTemplateEngine
```

---

## Success Metrics

| Metric | Target |
|--------|--------|
| Zero-config SPA setup | < 5 lines of Python |
| Type generation time | < 2s for 100 routes |
| Dev server startup | < 1s (async I/O) |
| Test coverage | > 90% |
| Documentation | Complete examples for each mode |

---

## Dependencies

### Python (Required)

- `litestar >= 2.0`
- `anyio` (async I/O)
- `httpx` (dev proxy)
- `msgspec` (JSON)

### Python (Optional)

- `jinja2` (template mode only)
- `watchdog` (CLI watch mode)

### Node.js

- `litestar-vite-plugin` (Vite plugin)
- `@hey-api/openapi-ts` (type generation)
- `zod` (runtime validation)

---

## Code Removal (Clean Break)

v2.0 is a **clean break** - no deprecation warnings, no migration shims. Delete everything that's not part of the new architecture.

### Files to Delete

| File | Reason |
|------|--------|
| `src/py/litestar_vite/template_engine.py` | Replaced by standard Jinja integration |

### Code to Remove

| What | Where | Why |
|------|-------|-----|
| `ViteTemplateEngine` class | `template_engine.py` | Use standard `JinjaTemplateEngine` |
| `ViteAssetLoader._instance` | `loader.py` | Singleton replaced by DI |
| Synchronous file reads | `loader.py` | Use `anyio.Path` |
| Global state in helpers | `helpers.py` | Use request-scoped DI |
| `use_server_lifespan` option | `config.py` | Always enabled |
| `template_engine_config` | `config.py` | Not needed |
| Old flat config fields | `config.py` | Replaced by nested structure |

### v2.0 Public API

```python
# The only public imports
from litestar_vite import VitePlugin, ViteConfig
from litestar_vite.config import PathConfig, RuntimeConfig, TypeGenConfig, InertiaConfig
```

Everything else is internal implementation detail.

---

## Research Findings

This section documents key technical research findings to ensure successful implementation.

### 1. Litestar Dependency Injection Patterns

**Async Service Initialization:**
Litestar DI supports async initialization via `on_startup` hooks and `app.state`:

```python
from litestar import Litestar
from litestar.di import Provide

class ViteAssetLoader:
    def __init__(self, config: ViteConfig) -> None:
        self._config = config
        self._initialized = False

    async def initialize(self) -> None:
        """Called during app startup."""
        await self._load_manifest()
        self._initialized = True

async def create_asset_loader(app: Litestar) -> ViteAssetLoader:
    """Factory that initializes the loader."""
    config = app.state.vite_config
    loader = ViteAssetLoader(config)
    await loader.initialize()
    return loader

# In plugin on_app_init:
app.on_startup.append(lambda app: setattr(app.state, 'vite_loader', await create_asset_loader(app)))

# In route handlers, inject via:
async def my_handler(vite_loader: ViteAssetLoader = Dependency(skip_validation=True)) -> Response:
    ...
```

**Key Pattern:** Use `on_startup` for async initialization, store in `app.state`, provide via `Dependency()`.

### 2. HTML Injection Approaches

**Preferred: Jinja Template Helpers (zero overhead)**
For template mode, use Jinja globals - renders server-side with no runtime cost.

**Fallback: Regex-based injection for SPA mode**
For SPA mode where we transform raw HTML:

```python
import re

def inject_head_script(html: str, script: str) -> str:
    """Inject script before </head>."""
    return re.sub(
        r'(</head>)',
        f'{script}\n\\1',
        html,
        count=1,
        flags=re.IGNORECASE
    )

def set_data_page_attribute(html: str, page_json: str) -> str:
    """Set data-page on #app div for Inertia."""
    return re.sub(
        r'(<div[^>]*id=["\']app["\'][^>]*)>',
        f'\\1 data-page=\'{page_json}\'>',
        html,
        count=1
    )
```

**Rationale:** Regex is faster than DOM parsing for simple insertions, and `html.parser` stdlib lacks selector support.

### 3. Dev Server Architecture Options

There are three main approaches for integrating Vite dev server with a Python backend. Each has tradeoffs:

#### Option A: Reverse Proxy (Vite → Python) - **RECOMMENDED**

Vite dev server runs on its port (5173), proxies API requests to Python backend (8000).

```typescript
// vite.config.ts
export default defineConfig({
  server: {
    proxy: {
      // Proxy API requests to Litestar
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      // Proxy Inertia requests
      '/inertia': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
});
```

**Pros:**
- Standard Vite setup, well-documented
- Full HMR support with no additional work
- Vite handles all static assets natively
- No Python proxy code needed
- Works with all Vite features out of the box

**Cons:**
- Two ports during development (5173 for frontend, 8000 for API)
- Must configure proxy rules for each API path

**When to use:** Most projects. This is the standard approach used by Laravel Vite, Django Vite, etc.

#### Option B: Python Proxy (Python → Vite) - **ALTERNATIVE**

Python serves on single port, proxies asset requests to Vite dev server.

```python
import httpx
from litestar import Response

class ViteSPAHandler:
    def __init__(self, config: ViteConfig):
        self._config = config
        self._client = httpx.AsyncClient(timeout=30.0)

    async def proxy_dev_server(self, path: str = "/") -> Response:
        """Proxy request to Vite dev server."""
        vite_url = f"http://{self._config.runtime.host}:{self._config.runtime.port}{path}"

        try:
            response = await self._client.get(vite_url)
            html = response.text
            # Inject Litestar data
            html = self._inject_routes(html)
            return Response(content=html, media_type="text/html")
        except httpx.ConnectError:
            return Response(
                content="Vite dev server not running. Start it with `npm run dev`.",
                status_code=503,
                media_type="text/plain"
            )

    async def close(self) -> None:
        """Close the HTTP client."""
        await self._client.aclose()
```

**Pros:**
- Single port for developers to access
- Python controls all routing

**Cons:**
- Must proxy ALL asset requests (JS, CSS, images, etc.)
- WebSocket proxy complexity for HMR
- Additional latency for every request
- More code to maintain and debug
- Vite's HMR WebSocket connects to a different port anyway (defeating single-port goal)

**When to use:** Only if single-port is absolutely required and you can accept HMR on separate port.

#### Option C: Vite Middleware Mode (Node.js process)

Run Vite as middleware inside a Node.js server that proxies to Python.

```javascript
import express from 'express'
import { createServer as createViteServer } from 'vite'
import { createProxyMiddleware } from 'http-proxy-middleware'

async function createServer() {
  const app = express()

  const vite = await createViteServer({
    server: { middlewareMode: true },
    appType: 'custom'
  })

  app.use(vite.middlewares)

  // Proxy API to Python
  app.use('/api', createProxyMiddleware({
    target: 'http://localhost:8000',
    changeOrigin: true
  }))

  app.use('*', async (req, res) => {
    let html = fs.readFileSync('index.html', 'utf-8')
    html = await vite.transformIndexHtml(req.originalUrl, html)
    res.status(200).set({ 'Content-Type': 'text/html' }).end(html)
  })

  app.listen(3000)
}
```

**Pros:**
- Single port (3000)
- Full Vite feature support including `transformIndexHtml`
- Native HMR WebSocket handling

**Cons:**
- Requires Node.js server wrapper
- More complex deployment
- Three processes: Node, Vite, Python

**When to use:** SSR scenarios, or when you need Vite's `transformIndexHtml` API.

#### Recommendation

**Use Option A (Reverse Proxy)** for most cases. It's:
- The standard pattern (Laravel, Django, Rails all use this)
- Zero additional Python code
- Full Vite feature support
- Well-documented by Vite itself

The "two ports" concern is mitigated by:
1. Developers only access the Vite port (5173) during dev
2. Production uses single port (Python serves built assets)
3. Most modern dev workflows expect multiple services anyway

#### Option D: Vite Sidecar (Zero External Ports) - **RECOMMENDED FOR ZERO-CONFIG**

Python manages a Node.js subprocess running Vite in middleware mode. All traffic (including HMR WebSocket) flows through Python's single port.

```
Browser (port 8000 only)
    │
    ▼
Litestar (Python) ─────────────────────────────────────────────────────
    │                                                                  │
    ├─► /api/* → Litestar route handlers                              │
    ├─► /@vite/client → Proxy to Vite sidecar (internal port)        │
    ├─► /@react-refresh → Proxy (if React)                           │
    ├─► /src/**/*.ts → Proxy (source files)                          │
    ├─► /__vite_hmr__ (WebSocket) → WebSocket Proxy to Vite          │
    └─► /* (HTML) → Fetch from Vite's transformIndexHtml()           │
                                                                       │
    ▲                                                                  │
    │ (internal only, e.g., localhost:24678 - random ephemeral port)  │
    │                                                                  │
Vite Node.js Sidecar (middlewareMode) ─────────────────────────────────
    - Started by Python subprocess
    - No external HTTP server (middlewareMode: true)
    - HMR configured with clientPort: 8000 (Python's port)
    - Communicates via internal ephemeral port bound to 127.0.0.1
```

**Key Vite Configuration (in sidecar bootstrap script):**

```typescript
// vite-sidecar.js - Bundled with litestar-vite or generated
import { createServer } from 'vite';
import http from 'http';

const internalPort = parseInt(process.env.VITE_INTERNAL_PORT || '0'); // 0 = ephemeral
const clientPort = parseInt(process.env.VITE_CLIENT_PORT || '8000');  // Litestar's port

const vite = await createServer({
  server: {
    middlewareMode: true,  // No external HTTP server
    hmr: {
      clientPort: clientPort,  // Tell HMR client to connect to Litestar's port
      path: '/__vite_hmr__',
    },
  },
  appType: 'custom',
});

// Minimal internal HTTP server for Python to connect to
const server = http.createServer(vite.middlewares);
server.listen(internalPort, '127.0.0.1', () => {
  const address = server.address();
  // Protocol: Python reads this from stdout to discover the port
  console.log(JSON.stringify({ port: address.port, ready: true }));
});
```

**Python ViteExecutor Implementation:**

```python
import subprocess
import asyncio
import json
from anyio import Path as AsyncPath

class ViteExecutor:
    """Manages the Vite sidecar subprocess."""

    def __init__(self, config: ViteConfig) -> None:
        self._config = config
        self._process: subprocess.Popen | None = None
        self._internal_port: int | None = None

    async def start(self) -> None:
        """Start Vite sidecar and wait for ready signal."""
        sidecar_script = await self._get_sidecar_script()

        env = {
            **os.environ,
            'VITE_CLIENT_PORT': str(self._config.runtime.port),  # Litestar's port
            'VITE_INTERNAL_PORT': '0',  # Ephemeral
        }

        self._process = subprocess.Popen(
            ['node', sidecar_script],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
            cwd=str(self._config.paths.root),
        )

        # Read startup message to get the assigned port
        line = await asyncio.to_thread(self._process.stdout.readline)
        startup = json.loads(line.decode())
        self._internal_port = startup['port']

    async def stop(self) -> None:
        """Stop Vite sidecar gracefully."""
        if self._process:
            self._process.terminate()
            await asyncio.to_thread(self._process.wait, timeout=5)

    @property
    def internal_url(self) -> str:
        """URL for Python to connect to internal Vite server."""
        return f"http://127.0.0.1:{self._internal_port}"
```

**WebSocket Proxy for HMR:**

```python
from litestar import WebSocket
from litestar.handlers import websocket
import websockets

@websocket("/__vite_hmr__")
async def vite_hmr_proxy(socket: WebSocket, vite_executor: ViteExecutor) -> None:
    """Bidirectional WebSocket proxy for HMR."""
    await socket.accept()

    internal_ws_url = f"ws://127.0.0.1:{vite_executor._internal_port}/__vite_hmr__"

    async with websockets.connect(internal_ws_url) as internal_ws:
        async def forward_to_vite() -> None:
            try:
                async for message in socket.iter_text():
                    await internal_ws.send(message)
            except Exception:
                pass  # Connection closed

        async def forward_to_client() -> None:
            try:
                async for message in internal_ws:
                    await socket.send_text(message)
            except Exception:
                pass  # Connection closed

        # Run both directions concurrently
        await asyncio.gather(
            forward_to_vite(),
            forward_to_client(),
            return_exceptions=True,
        )
```

**Pros:**
- **Single port** - Developers only access 8000, no firewall/proxy issues
- **Zero config** - Works out of the box with standard Vite setup
- **Full HMR support** - WebSocket properly proxied
- **Auto-detection** - Knows whether to start sidecar or use production mode
- **Graceful degradation** - Works without Node.js installed (production mode only)
- **Seamless with reverse proxy** - Works behind nginx/Caddy with single port

**Cons:**
- Requires Node.js in development (not production)
- Additional subprocess management complexity
- Slight latency for proxied requests (negligible in practice)

**Auto-Detection Logic:**

```python
async def detect_vite_mode(config: ViteConfig) -> Literal["sidecar", "external", "production"]:
    """Detect optimal Vite integration mode."""

    # Check for production manifest
    manifest_path = config.paths.bundle_dir / config.paths.manifest_name
    if await AsyncPath(manifest_path).exists():
        return "production"

    # Check if Vite already running externally
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"http://localhost:5173/@vite/client", timeout=0.5)
            if resp.status_code == 200:
                return "external"
    except httpx.ConnectError:
        pass

    # Check for vite.config.ts/js
    for config_name in ["vite.config.ts", "vite.config.js", "vite.config.mts"]:
        if await AsyncPath(config.paths.root / config_name).exists():
            return "sidecar"

    # No Vite detected
    return "production"
```

**When to use:** This is the **recommended default** for zero-config developer experience. Falls back gracefully to production mode when Node.js isn't available.

#### Mode-Specific Recommendations

| Mode | Recommended Approach | Why |
|------|---------------------|-----|
| **SPA (Zero-Config)** | Option D (Vite Sidecar) | Single port, auto-detection, seamless HMR - best DX |
| **SPA (Manual)** | Option A (Vite → Python) | If you prefer running Vite separately |
| **Template/HTMX** | Option D or Direct Litestar | Sidecar works, or access Litestar directly (8000) |

**Template Mode Detail:** In Template mode, the HTML source of truth is Litestar/Jinja, not Vite. With Option D (Sidecar), templates can reference assets via the same port. Alternatively, users can access Litestar directly (port 8000) and templates inject `<script src="http://localhost:5173/src/main.ts">` tags.

**Recommendation Summary:** Use **Option D (Vite Sidecar)** as the default for all modes. It provides the best developer experience with zero configuration. Fall back to Option A if the user explicitly runs Vite separately.

### 4. Vite Plugin Hooks for Type Generation

```typescript
import { exec } from 'node:child_process';
import { promisify } from 'node:util';
import type { Plugin, ViteDevServer } from 'vite';

const execPromise = promisify(exec);

interface TypesConfig {
  enabled: boolean;
  output: string;
  exportCommand: string;
  watch: string[];
  debounce: number;
}

export function typeGenerationPlugin(config: TypesConfig): Plugin {
  let debounceTimer: NodeJS.Timeout | null = null;

  async function generateTypes(): Promise<void> {
    console.log('[vite-litestar] Generating types...');
    await execPromise(config.exportCommand);
    console.log('[vite-litestar] Types generated.');
  }

  return {
    name: 'litestar-type-generation',
    apply: 'serve', // Only in dev mode

    // Generate types on dev server start
    async buildStart() {
      if (config.enabled) {
        await generateTypes();
      }
    },

    // Watch Python files and regenerate
    configureServer(server: ViteDevServer) {
      if (!config.enabled) return;

      // Add Python files to watcher
      config.watch.forEach(pattern => server.watcher.add(pattern));

      server.watcher.on('change', (filepath: string) => {
        if (filepath.endsWith('.py')) {
          // Debounce to batch rapid changes
          if (debounceTimer) clearTimeout(debounceTimer);
          debounceTimer = setTimeout(async () => {
            await generateTypes();
            // Notify client to trigger HMR
            server.ws.send({ type: 'custom', event: 'types-updated' });
          }, config.debounce);
        }
      });
    },

    // Trigger full reload when generated files change
    handleHotUpdate({ file, server }) {
      if (file.includes(config.output)) {
        server.ws.send({ type: 'full-reload' });
        return [];
      }
    }
  };
}
```

**Key Hooks:**

- `buildStart`: Run type generation on dev server start (async supported)
- `configureServer`: Access `server.watcher` for file watching
- `handleHotUpdate`: Custom HMR events for regenerated types
- `server.ws.send()`: Notify clients of type updates

### 5. @hey-api/openapi-ts Programmatic API

```typescript
import { createClient } from '@hey-api/openapi-ts';

// Programmatic usage (not just CLI)
await createClient({
  input: 'src/generated/openapi.json',
  output: 'src/generated/api',
  // Zod schemas
  plugins: ['@hey-api/schemas'],
  // Or SDK generation
  // plugins: ['@hey-api/sdk'],
});
```

**Configuration via config file:**

```typescript
// openapi-ts.config.ts
import { defineConfig } from '@hey-api/openapi-ts';

export default defineConfig({
  input: 'src/generated/openapi.json',
  output: 'src/generated/api',
  plugins: [
    '@hey-api/types',  // TypeScript types
    '@hey-api/schemas', // Zod schemas
  ],
});
```

### 6. HTMX Integration Patterns

**ASGI Middleware for HX-* Headers:**

```python
from litestar import Request

def is_htmx_request(request: Request) -> bool:
    """Check if request is from HTMX."""
    return request.headers.get("HX-Request") == "true"

def htmx_response_headers(
    trigger: str | None = None,
    trigger_after_swap: str | None = None,
    trigger_after_settle: str | None = None,
    redirect: str | None = None,
    refresh: bool = False,
    retarget: str | None = None,
    reswap: str | None = None,
) -> dict[str, str]:
    """Build HTMX response headers."""
    headers = {}
    if trigger:
        headers["HX-Trigger"] = trigger
    if trigger_after_swap:
        headers["HX-Trigger-After-Swap"] = trigger_after_swap
    if trigger_after_settle:
        headers["HX-Trigger-After-Settle"] = trigger_after_settle
    if redirect:
        headers["HX-Redirect"] = redirect
    if refresh:
        headers["HX-Refresh"] = "true"
    if retarget:
        headers["HX-Retarget"] = retarget
    if reswap:
        headers["HX-Reswap"] = reswap
    return headers
```

**Template Partials Pattern (jinja-partials):**

```python
# Using jinja-partials for fragment rendering
from jinja_partials import render_partial

@get("/users")
async def users_list(request: Request) -> Response:
    users = await get_users()
    if is_htmx_request(request):
        # Return just the fragment
        return render_partial("partials/user_list.html", users=users)
    # Return full page
    return Template("pages/users.html", users=users)
```

**Key Libraries:**

- [asgi-htmx](https://github.com/florimondmanca/asgi-htmx) - HTMX integration for ASGI apps
- [jinja-partials](https://pypi.org/project/jinja-partials/) - Fragment rendering for Jinja

---

## Known Risks & Mitigations

Based on technical review, these areas require careful implementation:

### Risk 1: HTML Injection via Regex

**Problem:** Regex parsing of HTML is fragile. Edge cases like `<!-- </head> -->` can break injection.

**Mitigation:**
- Use case-insensitive matching with `re.IGNORECASE`
- Prefer matching only outside comments (or use `html.parser` for complex cases)
- Add comprehensive test cases for edge cases

```python
# Safer regex pattern - avoids matching inside comments
def inject_before_head_close(html: str, content: str) -> str:
    # Simple but effective for most cases
    return re.sub(
        r'(</head>)',
        f'{content}\n\\1',
        html,
        count=1,
        flags=re.IGNORECASE
    )
```

### Risk 2: Route Metadata Extraction Complexity

**Problem:** Mapping Python path converters (`/users/{id:int}`) to TypeScript is error-prone.

**Challenges:**
- Litestar regex constraints
- Mount paths (app mounted under `/api/v1`)
- Parameter type mapping (`uuid` → `string`, `int` → `number`)

**Mitigation:**
- Use `litestar.app.Litestar.route_handler_method_view` for extraction
- Normalize all paths to `{param}` syntax
- Create extensive test suite for path edge cases
- Document limitations clearly

### Risk 3: SPA Catch-All Route Ordering

**Problem:** In SPA mode, catch-all route `get("/{path:path}")` can swallow API routes or be shadowed by static files.

**Mitigation:**
- Register catch-all with lowest priority
- Use route guards to exclude `/api/*` paths
- Document the route registration order clearly

```python
# Example: Ensure API routes take precedence
@get("/{path:path}", opt={"priority": -1000})
async def spa_catchall(path: str) -> Response:
    return await serve_spa_html()
```

### Risk 4: Windows Path Compatibility

**Problem:** Generated TypeScript files may have incorrect path separators on Windows.

**Mitigation:**
- Normalize all generated paths to POSIX style (`/`)
- Use `pathlib.PurePosixPath` for route generation

### Risk 5: Content Security Policy (CSP)

**Problem:** Vite uses inline scripts. CSP policies may block these.

**Mitigation:**
- Support nonce injection in HTML transformer
- Document CSP configuration requirements
- Provide `csp_nonce` option in `ViteConfig`

```python
@dataclass
class RuntimeConfig:
    # ... existing fields ...
    csp_nonce: str | None = None  # If set, inject into script tags
```

### Risk 6: Asset Base Path in Production

**Problem:** Assets may be served from CDN with different base URL.

**Mitigation:**
- Add `asset_url` to `PathConfig`
- Read from Vite manifest's `base` property as fallback

```python
@dataclass
class PathConfig:
    # ... existing fields ...
    asset_url: str = "/static/"  # CDN URL in production
```

### Risk 7: HTMX Partial Asset Loading

**Problem:** HTMX partials may need specific CSS/JS chunks not in main entry.

**Mitigation:**
- Add `vite_partial(entry)` template helper for specific entry points
- Document pattern for asset-aware partials

```html
{# In HTMX partial template #}
{{ vite_partial('components/modal.ts') }}
<div class="modal">...</div>
```

### Risk 8: Vite Sidecar Subprocess Management

**Problem:** Managing Node.js subprocess lifecycle is complex. Orphan processes, port conflicts, and crash recovery need careful handling.

**Mitigation:**
- Use ephemeral ports (port 0) to avoid conflicts
- Bind sidecar to `127.0.0.1` only for security
- Read port from stdout JSON message
- Register `atexit` handler for cleanup
- Sidecar script listens for stdin close to self-terminate
- Clear error messages when Node.js not available

```python
import atexit

class ViteExecutor:
    def __init__(self) -> None:
        atexit.register(self._cleanup)

    def _cleanup(self) -> None:
        if self._process and self._process.poll() is None:
            self._process.terminate()
            try:
                self._process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self._process.kill()
```

### Risk 9: WebSocket Proxy Reliability

**Problem:** WebSocket proxying for HMR must be rock-solid. Dropped connections cause page reloads and poor DX.

**Mitigation:**
- Use proven `websockets` library for client connection
- Implement heartbeat/ping handling
- Graceful error handling without exceptions bubbling
- Log disconnects at DEBUG level only
- Test with rapid file changes (stress test HMR)

### Risk 10: Node.js Dependency in Development

**Problem:** Sidecar requires Node.js installed. Users might not have it.

**Mitigation:**
- Clear error message with installation instructions
- Graceful fallback to Option A (external Vite) if Node.js missing
- Production mode never requires Node.js
- Document Node.js requirement in README

```python
def _check_node_available() -> bool:
    try:
        subprocess.run(['node', '--version'], capture_output=True, check=True)
        return True
    except (FileNotFoundError, subprocess.CalledProcessError):
        return False
```

### Risk 11: Sidecar Startup Latency

**Problem:** Starting Node.js subprocess adds delay to dev server startup.

**Mitigation:**
- Start sidecar in parallel with Litestar startup
- Use `asyncio.create_task()` for non-blocking start
- Show clear "Waiting for Vite..." message
- Timeout with helpful error if sidecar fails to start

```python
async def start_with_timeout(self, timeout: float = 10.0) -> None:
    try:
        await asyncio.wait_for(self.start(), timeout=timeout)
    except asyncio.TimeoutError:
        raise ViteStartupError(
            "Vite sidecar failed to start within 10 seconds. "
            "Check that node_modules are installed: npm install"
        )
```

---

## Keeping Documentation & Templates Up-to-Date

This section provides procedures for agents and developers to keep the library aligned with upstream dependencies.

### Vite Backend Integration

**Source**: https://vite.dev/guide/backend-integration

**When to update**: Before each major release, or when Vite releases a new major version.

**Update procedure**:

1. **Fetch latest Vite docs**:
   ```bash
   # Use Context7 MCP or fetch directly
   curl -s https://vite.dev/guide/backend-integration | head -500
   ```

2. **Check manifest format** - Verify `ManifestChunk` interface matches:
   ```typescript
   interface ManifestChunk {
     src?: string
     file: string
     css?: string[]
     assets?: string[]
     isEntry?: boolean
     name?: string
     names?: string[]
     isDynamicEntry?: boolean
     imports?: string[]
     dynamicImports?: string[]
   }
   ```
   Update `src/py/litestar_vite/loader.py` if fields change.

3. **Check dev server injection** - Verify HMR client path:
   ```html
   <script type="module" src="http://localhost:5173/@vite/client"></script>
   ```
   Update `render_hmr_client()` if path changes.

4. **Check React Refresh preamble** (if using React):
   ```html
   <script type="module">
     import RefreshRuntime from 'http://localhost:5173/@react-refresh'
     RefreshRuntime.injectIntoGlobalHook(window)
     window.$RefreshReg$ = () => {}
     window.$RefreshSig$ = () => (type) => type
     window.__vite_plugin_react_preamble_installed__ = true
   </script>
   ```

5. **Update version constraints** in `package.json`:
   ```json
   {
     "peerDependencies": {
       "vite": "^5.0 || ^6.0 || ^7.0"
     }
   }
   ```

### Litestar Compatibility

**Source**: https://docs.litestar.dev/

**When to update**: When Litestar releases new versions, especially major versions.

**Update procedure**:

1. **Check plugin API**:
   ```bash
   # Verify InitPlugin interface hasn't changed
   grep -r "class InitPlugin" $(python -c "import litestar; print(litestar.__path__[0])")
   ```

2. **Check DI patterns**:
   - Verify `Provide` and `Dependency` imports
   - Check `on_startup` hook signature
   - Verify `app.state` access patterns

3. **Check template engine integration**:
   - Verify `JinjaTemplateEngine` API
   - Check template global registration

4. **Update version constraints** in `pyproject.toml`:
   ```toml
   dependencies = ["litestar>=2.0,<4.0"]
   ```

### litestar-htmx Compatibility

**Source**: https://github.com/litestar-org/litestar-htmx

**When to update**: When litestar-htmx releases new versions.

**Update procedure**:

1. **Verify plugin still works**:
   ```python
   from litestar_htmx import HTMXPlugin, HTMXRequest, HTMXTemplate
   ```

2. **Check for new response helpers**:
   - `TriggerEvent`, `Reswap`, `ReplaceUrl`, `Retarget`
   - Document any new helpers in our HTMX mode docs

3. **Adopt upstream features** - If litestar-htmx adds features, integrate rather than duplicate.

### @hey-api/openapi-ts Updates

**Source**: https://heyapi.dev/

**When to update**: Quarterly, or when users report type generation issues.

**Update procedure**:

1. **Check latest version**:
   ```bash
   npm view @hey-api/openapi-ts version
   ```

2. **Verify programmatic API**:
   ```typescript
   import { createClient } from '@hey-api/openapi-ts';
   await createClient({
     input: 'openapi.json',
     output: 'src/generated',
     plugins: ['@hey-api/types', '@hey-api/schemas'],
   });
   ```

3. **Check for breaking changes** in their changelog

4. **Update peer dependency**:
   ```json
   {
     "peerDependencies": {
       "@hey-api/openapi-ts": ">=0.50"
     }
   }
   ```

### Inertia.js Protocol

**Source**: https://inertiajs.com/the-protocol

**When to update**: When Inertia.js releases new protocol versions.

**Update procedure**:

1. **Check protocol version**:
   - `X-Inertia-Version` header handling
   - Page object structure: `{ component, props, url, version }`

2. **Verify response format**:
   ```json
   {
     "component": "Users/Index",
     "props": { "users": [...] },
     "url": "/users",
     "version": "abc123"
   }
   ```

3. **Check for new headers**:
   - `X-Inertia`, `X-Inertia-Version`, `X-Inertia-Location`
   - Any new headers for partial reloads, etc.

### Template Update Checklist

Run this checklist before each release:

- [ ] Vite manifest format matches latest Vite docs
- [ ] HMR client injection path is correct
- [ ] React Refresh preamble is current (if applicable)
- [ ] Litestar plugin API compatibility verified
- [ ] litestar-htmx not duplicated
- [ ] @hey-api/openapi-ts API still works
- [ ] Inertia.js protocol version matched
- [ ] All version constraints updated in pyproject.toml and package.json
- [ ] Examples tested with latest dependency versions

---

## Project Scaffolding & Init Templates

The `litestar vite init` command provides framework-specific scaffolding to bootstrap new projects. Templates are Jinja2 files that generate the minimal boilerplate for each framework.

### CLI Usage

```bash
# Interactive mode - prompts for framework choice
litestar vite init

# Direct template selection
litestar vite init --template react
litestar vite init --template vue
litestar vite init --template vue-inertia
litestar vite init --template svelte
litestar vite init --template htmx
litestar vite init --template astro

# With options
litestar vite init --template react --tailwind --typescript
litestar vite init --template vue-inertia --tailwind
```

### Template Structure

```
src/py/litestar_vite/templates/
├── base/                    # Shared across all templates
│   ├── vite.config.ts.j2
│   ├── package.json.j2
│   ├── tsconfig.json.j2
│   ├── main.ts.j2
│   └── styles.css.j2
├── react/                   # React SPA
│   ├── App.tsx.j2
│   ├── main.tsx.j2
│   └── index.html.j2
├── vue/                     # Vue SPA
│   ├── App.vue.j2
│   ├── main.ts.j2
│   └── index.html.j2
├── vue-inertia/             # Vue + Inertia.js
│   ├── App.vue.j2
│   ├── main.ts.j2
│   ├── pages/
│   │   ├── Home.vue.j2
│   │   └── Users/
│   │       └── Index.vue.j2
│   └── index.html.j2
├── svelte/                  # Svelte SPA
│   ├── App.svelte.j2
│   ├── main.ts.j2
│   └── index.html.j2
├── htmx/                    # HTMX + Alpine.js
│   ├── main.js.j2
│   ├── templates/
│   │   ├── base.html.j2
│   │   └── index.html.j2
│   └── index.html.j2
├── astro/                   # Astro
│   ├── astro.config.mjs.j2
│   ├── src/
│   │   └── pages/
│   │       └── index.astro.j2
│   └── package.json.j2
├── sveltekit/               # SvelteKit
│   ├── svelte.config.js.j2
│   ├── vite.config.ts.j2
│   └── src/
│       └── routes/
│           └── +page.svelte.j2
└── addons/                  # Optional add-ons
    └── tailwindcss/
        ├── tailwind.config.js.j2
        └── postcss.config.js.j2
```

### Template Variables

Templates receive these Jinja2 variables:

| Variable | Type | Description |
|----------|------|-------------|
| `project_name` | `str` | Project directory name |
| `resource_path` | `str` | Path to frontend resources |
| `bundle_path` | `str` | Path to build output |
| `entry_point` | `list[str]` | Entry point files |
| `asset_url` | `str` | Base URL for assets |
| `hot_file` | `str` | Hot file location |
| `include_tailwind` | `bool` | Whether to include TailwindCSS |
| `include_typescript` | `bool` | Whether to use TypeScript |
| `include_inertia` | `bool` | Whether to include Inertia.js |
| `port` | `int` | Vite dev server port |
| `litestar_port` | `int` | Litestar server port |

### Framework-Specific Templates

#### React Template

**`templates/react/App.tsx.j2`**:
```tsx
const App = () => {
  return (
    <div>
      <h1>{{ project_name }} - Litestar + Vite + React</h1>
    </div>
  );
};

export default App;
```

**`templates/react/main.tsx.j2`**:
```tsx
import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App";
{% if include_tailwind %}import "./styles.css";{% endif %}

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
```

#### Vue Template

**`templates/vue/App.vue.j2`**:
```vue
<template>
  <div>
    <h1>{{ project_name }} - Litestar + Vite + Vue</h1>
  </div>
</template>

<script setup lang="ts">
// Your component logic here
</script>
```

#### HTMX Template

**`templates/htmx/main.js.j2`**:
```javascript
import htmx from "htmx.org";
{% if include_tailwind %}import "./styles.css";{% endif %}

// Make htmx available globally
window.htmx = htmx;

// Optional: Configure htmx
htmx.config.defaultSwapStyle = "innerHTML";
htmx.config.historyCacheSize = 10;
```

#### Svelte Template

**`templates/svelte/App.svelte.j2`**:
```svelte
<script lang="ts">
  let count = $state(0);  // Svelte 5 runes
</script>

<main>
  <h1>{{ project_name }} - Litestar + Vite + Svelte</h1>
  <button onclick={() => count++}>Count: {count}</button>
</main>

<style>
  main {
    text-align: center;
    padding: 2rem;
  }
</style>
```

#### TailwindCSS Addon

**`templates/addons/tailwindcss/tailwind.config.js.j2`**:
```javascript
/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "{{ resource_path }}/**/*.{js,jsx,ts,tsx,vue,svelte,astro,html}",
    "templates/**/*.{html,j2}",
  ],
  theme: {
    extend: {},
  },
  plugins: [
    require("@tailwindcss/forms"),
  ],
};
```

### Interactive Console UI (Rich-based)

The `litestar vite init` command provides an interactive, user-friendly experience using the [Rich](https://github.com/Textualize/rich) library.

**Interactive Flow**:

```
$ litestar vite init

╭─────────────────────────────────────────────────────────────╮
│               🚀 Litestar + Vite Project Setup              │
╰─────────────────────────────────────────────────────────────╯

? Project name: my-app
? Select a framework:
  ❯ React        → Modern React SPA with TypeScript
    Vue          → Vue 3 SPA with Composition API
    Vue+Inertia  → Vue 3 with Inertia.js for SPA routing
    Svelte       → Svelte 5 with runes
    SvelteKit    → Full-stack Svelte with SSR
    HTMX         → Hypermedia-driven with Alpine.js
    Astro        → Content-focused with islands architecture

? Enable TypeScript? (Y/n): Y
? Include TailwindCSS? (Y/n): Y
? Vite dev server port (5173):
? Litestar server port (8000):

Creating project structure...
  ✓ Created vite.config.ts
  ✓ Created package.json
  ✓ Created tsconfig.json
  ✓ Created src/main.tsx
  ✓ Created src/App.tsx
  ✓ Created tailwind.config.js
  ✓ Created postcss.config.js

╭─────────────────────────────────────────────────────────────╮
│  ✨ Project created successfully!                           │
│                                                              │
│  Next steps:                                                 │
│    cd my-app                                                 │
│    npm install                                               │
│    litestar run --reload                                     │
╰─────────────────────────────────────────────────────────────╯
```

**Implementation using Rich + questionary**:

```python
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn
import questionary
from questionary import Style

console = Console()

# Custom style for questionary prompts
custom_style = Style([
    ('qmark', 'fg:cyan bold'),
    ('question', 'bold'),
    ('answer', 'fg:green'),
    ('pointer', 'fg:cyan bold'),
    ('highlighted', 'fg:cyan'),
    ('selected', 'fg:green'),
])

FRAMEWORKS = {
    "react": {"name": "React", "desc": "Modern React SPA with TypeScript"},
    "vue": {"name": "Vue", "desc": "Vue 3 SPA with Composition API"},
    "vue-inertia": {"name": "Vue+Inertia", "desc": "Vue 3 with Inertia.js for SPA routing"},
    "svelte": {"name": "Svelte", "desc": "Svelte 5 with runes"},
    "sveltekit": {"name": "SvelteKit", "desc": "Full-stack Svelte with SSR"},
    "htmx": {"name": "HTMX", "desc": "Hypermedia-driven with Alpine.js"},
    "astro": {"name": "Astro", "desc": "Content-focused with islands architecture"},
}

async def init_project(
    template: str | None = None,
    tailwind: bool | None = None,
    typescript: bool | None = None,
    port: int = 5173,
    litestar_port: int = 8000,
) -> None:
    """Initialize a new Litestar + Vite project."""

    # Show welcome banner
    console.print(Panel(
        "[bold cyan]🚀 Litestar + Vite Project Setup[/]",
        expand=False,
    ))

    # Prompt for project name
    project_name = questionary.text(
        "Project name:",
        default="my-app",
        style=custom_style,
    ).ask()

    # Prompt for framework if not provided
    if template is None:
        choices = [
            questionary.Choice(
                title=f"{info['name']:12} → {info['desc']}",
                value=key,
            )
            for key, info in FRAMEWORKS.items()
        ]
        template = questionary.select(
            "Select a framework:",
            choices=choices,
            style=custom_style,
        ).ask()

    # Prompt for TypeScript
    if typescript is None:
        typescript = questionary.confirm(
            "Enable TypeScript?",
            default=True,
            style=custom_style,
        ).ask()

    # Prompt for TailwindCSS
    if tailwind is None:
        tailwind = questionary.confirm(
            "Include TailwindCSS?",
            default=True,
            style=custom_style,
        ).ask()

    # Prompt for ports (with defaults)
    port = questionary.text(
        "Vite dev server port:",
        default=str(port),
        style=custom_style,
    ).ask()

    litestar_port = questionary.text(
        "Litestar server port:",
        default=str(litestar_port),
        style=custom_style,
    ).ask()

    # Generate project with progress
    console.print()
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Creating project structure...", total=None)

        # Generate files
        generated_files = await generate_project_files(
            project_name=project_name,
            template=template,
            typescript=typescript,
            tailwind=tailwind,
            port=int(port),
            litestar_port=int(litestar_port),
        )

        progress.update(task, completed=True)

    # Show generated files
    for file in generated_files:
        console.print(f"  [green]✓[/] Created {file}")

    # Show success message
    console.print()
    console.print(Panel(
        f"[green]✨ Project created successfully![/]\n\n"
        f"[bold]Next steps:[/]\n"
        f"  cd {project_name}\n"
        f"  npm install\n"
        f"  litestar run --reload",
        expand=False,
    ))
```

**Dependencies for CLI**:

```toml
# pyproject.toml
[project.optional-dependencies]
cli = [
    "rich>=13.0",
    "questionary>=2.0",
]
```

**Non-Interactive Mode**:

All prompts can be skipped by providing CLI flags:

```bash
# Fully non-interactive
litestar vite init \
  --name my-app \
  --template react \
  --typescript \
  --tailwind \
  --port 5173 \
  --litestar-port 8000 \
  --no-interactive
```

### Generated Package Dependencies

The init command generates appropriate `package.json` dependencies:

| Template | Dependencies | Dev Dependencies |
|----------|-------------|------------------|
| **React** | `react`, `react-dom` | `@vitejs/plugin-react`, `@types/react`, `@types/react-dom` |
| **Vue** | `vue` | `@vitejs/plugin-vue`, `vue-tsc` |
| **Vue + Inertia** | `vue`, `@inertiajs/vue3` | `@vitejs/plugin-vue`, `vue-tsc` |
| **Svelte** | `svelte` | `@sveltejs/vite-plugin-svelte` |
| **HTMX** | `htmx.org`, `alpinejs` | - |
| **Astro** | `astro` | - |
| **SvelteKit** | - | `@sveltejs/kit`, `svelte` |
| **TailwindCSS** (addon) | - | `tailwindcss`, `postcss`, `autoprefixer`, `@tailwindcss/forms` |

### Maintenance: Keeping Templates Updated

Templates should be updated when upstream frameworks release new versions. Here's where to find the latest patterns:

| Framework | Upstream Source | What to Check |
|-----------|----------------|---------------|
| **React** | [create-vite templates](https://github.com/vitejs/vite/tree/main/packages/create-vite/template-react-ts) | `main.tsx` structure, `App.tsx` patterns |
| **Vue** | [create-vite templates](https://github.com/vitejs/vite/tree/main/packages/create-vite/template-vue-ts) | `main.ts`, `App.vue`, `vite.config.ts` |
| **Svelte** | [create-svelte](https://github.com/sveltejs/kit/tree/main/packages/create-svelte) | Svelte 5 runes syntax, `+page.svelte` patterns |
| **HTMX** | [htmx.org docs](https://htmx.org/docs/) | Config options, extension patterns |
| **Inertia** | [Inertia.js docs](https://inertiajs.com/client-side-setup) | `createInertiaApp()` setup, page resolution |
| **Astro** | [create-astro](https://github.com/withastro/astro/tree/main/packages/create-astro) | `astro.config.mjs` format |
| **TailwindCSS** | [TailwindCSS docs](https://tailwindcss.com/docs/installation/using-vite) | Config format, plugin list |

**Update procedure**:
```bash
# Check latest create-vite templates
npm create vite@latest test-app -- --template react-ts
npm create vite@latest test-app -- --template vue-ts
npm create vite@latest test-app -- --template svelte-ts

# Compare generated files with our templates
diff -r test-app/src src/py/litestar_vite/templates/react/

# Update templates to match latest patterns
```

---

## Inertia.js v2 Protocol Compliance

This section documents the enhancements needed to fully support Inertia.js v2 features. Based on analysis of the current implementation and the latest Inertia.js v2 protocol.

### Current Implementation Status

The current codebase has **partial support** for lazy/deferred props:

| Feature | Status | Location |
|---------|--------|----------|
| `lazy()` helper | ✅ Implemented | `helpers.py:53-72` |
| `DeferredProp` class | ✅ Implemented | `helpers.py:90-134` |
| `StaticProp` class | ✅ Implemented | `helpers.py:75-87` |
| Partial rendering (`X-Inertia-Partial-Data`) | ✅ Implemented | `request.py`, `response.py` |
| `deferredProps` in response | ❌ Missing | `types.py:PageProps` |
| Deferred prop groups | ❌ Missing | - |
| `clearHistory` / `encryptHistory` | ❌ Missing | `types.py:PageProps` |
| Merge / Deep Merge props | ❌ Missing | - |
| `WhenVisible` server support | ⚠️ Partial | Works with manual `only[]` requests |
| Prefetch cache headers | ❌ Missing | - |

### Inertia.js v2 Protocol Changes

#### 1. Updated Page Object Structure

The Inertia.js v2 protocol requires additional fields in the page object:

```json
{
    "component": "Posts/Index",
    "props": {
        "errors": {},
        "user": { "name": "Jonathan" }
    },
    "url": "/posts",
    "version": "6b16b94d7c51cbe5b1fa42aac98241d5",
    "clearHistory": false,
    "encryptHistory": false,
    "deferredProps": {
        "default": ["comments", "analytics"],
        "sidebar": ["relatedPosts"]
    }
}
```

**Required Changes to `PageProps`:**

```python
# types.py - Updated PageProps
@dataclass
class PageProps(Generic[T]):
    """Inertia Page Props Type."""

    component: str
    url: str
    version: str
    props: dict[str, Any]
    clearHistory: bool = False
    encryptHistory: bool = False
    deferredProps: dict[str, list[str]] | None = None
    mergeProps: list[str] | None = None  # Props that should be merged
    deepMergeProps: list[str] | None = None  # Props that should be deep merged
```

#### 2. Deferred Props with Groups

Inertia.js v2 allows grouping deferred props for parallel fetching:

```php
// Laravel example
'permissions' => Inertia::defer(fn () => Permission::all()),  // default group
'teams' => Inertia::defer(fn () => Team::all(), 'sidebar'),   // sidebar group
'projects' => Inertia::defer(fn () => Project::all(), 'sidebar'),
```

**Proposed Python API:**

```python
from litestar_vite.inertia import defer, lazy

@get("/users", component="Users/Index")
async def users_list() -> InertiaResponse:
    return InertiaResponse({
        "users": await get_users(),  # Immediate
        "roles": await get_roles(),  # Immediate

        # Deferred props - fetched after initial render
        "permissions": defer(get_permissions),  # Default group
        "teams": defer(get_teams, group="sidebar"),  # Sidebar group
        "projects": defer(get_projects, group="sidebar"),

        # Legacy lazy() still works for partial reloads
        "optional": lazy("optional", get_optional_data),
    })
```

**Implementation:**

```python
# helpers.py - New defer() function
@dataclass
class DeferredPropV2(Generic[T]):
    """Inertia v2 deferred prop with group support."""

    fn: Callable[[], T | Awaitable[T]]
    group: str = "default"
    _evaluated: bool = field(default=False, init=False)
    _result: T | None = field(default=None, init=False)

    async def evaluate(self) -> T:
        """Evaluate the deferred prop."""
        if self._evaluated:
            return self._result

        result = self.fn()
        if inspect.isawaitable(result):
            self._result = await result
        else:
            self._result = result
        self._evaluated = True
        return self._result


def defer(
    fn: Callable[[], T | Awaitable[T]],
    group: str = "default",
) -> DeferredPropV2[T]:
    """Create a deferred prop that loads after initial page render.

    Args:
        fn: A callable that returns the prop value (sync or async).
        group: The group name for parallel fetching. Props in the same
               group are fetched together in a single request.

    Returns:
        A DeferredPropV2 instance.

    Example:
        @get("/users", component="Users/Index")
        async def handler() -> dict:
            return {
                "users": await get_users(),
                "permissions": defer(get_permissions),
                "teams": defer(get_teams, group="sidebar"),
            }
    """
    return DeferredPropV2(fn=fn, group=group)
```

#### 3. Merge and Deep Merge Props

For infinite scroll and pagination patterns:

```python
# helpers.py - Merge prop wrappers
@dataclass
class MergeableProp(Generic[T]):
    """A prop that should be merged with existing client state."""

    value: T
    deep: bool = False


def merge(value: T) -> MergeableProp[T]:
    """Mark a prop for shallow merging with existing client state.

    Useful for pagination where you want to append new items.

    Example:
        @get("/users", component="Users/Index")
        async def handler(page: int = 1) -> dict:
            users = await get_users_page(page)
            return {
                "users": merge(users),  # Appends to existing users
            }
    """
    return MergeableProp(value=value, deep=False)


def deep_merge(value: T) -> MergeableProp[T]:
    """Mark a prop for deep merging with existing client state.

    Useful for nested data structures like paginated results.

    Example:
        @get("/users", component="Users/Index")
        async def handler(page: int = 1) -> dict:
            return {
                "results": deep_merge({
                    "data": await get_users_page(page),
                    "meta": {"page": page},
                }),
            }
    """
    return MergeableProp(value=value, deep=True)
```

#### 4. History Control

```python
# response.py - Updated InertiaResponse
class InertiaResponse(Response[T]):
    def __init__(
        self,
        content: T,
        *,
        clear_history: bool = False,
        encrypt_history: bool = False,
        # ... existing params
    ) -> None:
        self.clear_history = clear_history
        self.encrypt_history = encrypt_history
```

#### 5. Response Building with Deferred Props

The response builder needs to:
1. Separate immediate props from deferred props
2. Build the `deferredProps` metadata grouped by group name
3. Exclude deferred props from initial `props` payload

```python
# response.py - Updated to_asgi_response
def _build_page_props(self, content: dict[str, Any]) -> tuple[dict[str, Any], dict[str, list[str]]]:
    """Separate immediate and deferred props.

    Returns:
        Tuple of (immediate_props, deferred_props_metadata)
    """
    immediate_props: dict[str, Any] = {}
    deferred_metadata: dict[str, list[str]] = {}

    for key, value in content.items():
        if isinstance(value, DeferredPropV2):
            # Add to deferred metadata by group
            group = value.group
            if group not in deferred_metadata:
                deferred_metadata[group] = []
            deferred_metadata[group].append(key)
        elif isinstance(value, MergeableProp):
            immediate_props[key] = value.value
            # Track merge props separately
        else:
            immediate_props[key] = value

    return immediate_props, deferred_metadata or None
```

#### 6. Deferred Props Endpoint

When the Inertia client requests deferred props, it sends:
- `X-Inertia-Partial-Data`: Comma-separated prop names
- `X-Inertia-Partial-Component`: The component name

The current implementation already handles this via `partial_keys`, but needs enhancement to:
1. Evaluate only the requested `DeferredPropV2` instances
2. Return proper response format

### New Inertia Headers

| Header | Purpose | Current Support |
|--------|---------|-----------------|
| `X-Inertia-Partial-Data` | Specify props to reload | ✅ Supported |
| `X-Inertia-Partial-Component` | Specify component for partial | ✅ Supported |
| `X-Inertia-Partial-Except` | Props to exclude | ❌ Missing |
| `X-Inertia-Reset` | Reset props (clear merge state) | ❌ Missing |

**Add to `_utils.py`:**

```python
class InertiaHeaders(str, Enum):
    """Enum for Inertia Headers"""

    ENABLED = "X-Inertia"
    VERSION = "X-Inertia-Version"
    PARTIAL_DATA = "X-Inertia-Partial-Data"
    PARTIAL_COMPONENT = "X-Inertia-Partial-Component"
    PARTIAL_EXCEPT = "X-Inertia-Partial-Except"  # NEW
    RESET = "X-Inertia-Reset"  # NEW
    LOCATION = "X-Inertia-Location"
    REFERER = "Referer"
    ERROR_BAG = "X-Inertia-Error-Bag"
```

### Migration from Current `lazy()` to `defer()`

The current `lazy()` function serves a different purpose than Inertia v2's `defer()`:

| Feature | `lazy()` (Current) | `defer()` (Inertia v2) |
|---------|-------------------|----------------------|
| **Purpose** | Only load when explicitly requested via partial reload | Load automatically after initial render |
| **Initial Response** | Excluded from response | Excluded, but metadata sent |
| **Client Behavior** | User must trigger reload | Automatic fetch after mount |
| **Groups** | No | Yes |

**Recommendation:** Keep both:
- `lazy(key, value)` - For optional props loaded on demand
- `defer(fn, group)` - For Inertia v2 deferred props

### Prefetch Support

Inertia v2 supports link prefetching. Server-side support includes:

```python
# config.py - Add prefetch configuration
@dataclass
class InertiaConfig:
    # ... existing fields ...

    # Prefetch settings
    prefetch_cache_ttl: int = 30  # seconds
    prefetch_stale_while_revalidate: int = 60  # seconds
```

**Response headers for prefetched requests:**

```python
# When responding to a prefetch request
headers = {
    "Cache-Control": f"private, max-age={config.prefetch_cache_ttl}, stale-while-revalidate={config.prefetch_stale_while_revalidate}",
    "Vary": "X-Inertia, X-Inertia-Version, X-Inertia-Partial-Data",
}
```

### Testing Requirements

Add tests for:

1. **Deferred Props:**
   - `defer()` creates `DeferredPropV2` with correct group
   - Response excludes deferred props from `props`
   - Response includes `deferredProps` metadata
   - Partial reload returns evaluated deferred props

2. **Merge Props:**
   - `merge()` creates `MergeableProp` with `deep=False`
   - `deep_merge()` creates `MergeableProp` with `deep=True`
   - Response includes `mergeProps` / `deepMergeProps` lists

3. **History Control:**
   - `clear_history=True` sets `clearHistory: true` in response
   - `encrypt_history=True` sets `encryptHistory: true` in response

4. **Protocol Compliance:**
   - Full page response matches Inertia v2 protocol
   - Partial response matches Inertia v2 protocol

---

## References

- [Litestar Documentation](https://docs.litestar.dev/)
- [Litestar HTMX Plugin](https://docs.litestar.dev/latest/usage/htmx) - **Use this, don't reinvent**
- [litestar-htmx GitHub](https://github.com/litestar-org/litestar-htmx)
- [Vite Backend Integration](https://vite.dev/guide/backend-integration) - **Canonical source for manifest/injection**
- [Vite create-vite Templates](https://github.com/vitejs/vite/tree/main/packages/create-vite) - **Template scaffolding reference**
- [@hey-api/openapi-ts](https://heyapi.dev/)
- [Ziggy (Laravel)](https://github.com/tighten/ziggy) - Route helper inspiration
- [Inertia.js Protocol](https://inertiajs.com/the-protocol) - **v2 protocol reference**
- [Inertia.js Client Setup](https://inertiajs.com/client-side-setup) - **Template patterns**
- [Inertia.js Deferred Props](https://inertiajs.com/deferred-props) - **v2 deferred props**
- [Inertia.js Prefetching](https://inertiajs.com/prefetching) - **v2 prefetching**
- [Inertia.js Polling](https://inertiajs.com/polling) - **v2 polling**
- [Inertia.js Merging Props](https://inertiajs.com/merging-props) - **v2 merge/deep merge**
- [Inertia.js WhenVisible](https://inertiajs.com/load-when-visible) - **v2 lazy loading**
- [Vite Plugin API](https://vitejs.dev/guide/api-plugin.html)
- [Svelte/SvelteKit](https://svelte.dev/docs/kit) - **Svelte 5 patterns**
- [Astro Docs](https://docs.astro.build/) - **Astro integration**
- [TailwindCSS + Vite](https://tailwindcss.com/docs/installation/using-vite) - **TailwindCSS setup**
- [PR #32 - CLI Templates](https://github.com/litestar-org/litestar-vite/pull/32) - Historical reference
