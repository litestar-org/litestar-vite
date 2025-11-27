# Implementation Tasks: Litestar-Vite v2.0 Unified

**PRD**: [prd.md](./prd.md)
**Status**: Planning
**Created**: 2025-11-27

---

## Phase 1: Core Architecture (Foundation)

### 1.1 Configuration Refactor

- [ ] Create new config dataclasses in `config.py`:
  - [ ] `PathConfig` - file system paths
    - [ ] Add `asset_url: str = "/static/"` for CDN support
  - [ ] `RuntimeConfig` - execution settings
    - [ ] Add `csp_nonce: str | None = None` for CSP support
  - [ ] `TypeGenConfig` - type generation settings
  - [ ] `InertiaConfig` - Inertia.js settings
  - [ ] `ViteConfig` - root config with nested configs
- [ ] Add validation in `__post_init__`
- [ ] Support bool shortcuts (`types=True` → full TypeGenConfig)
- [ ] Add `dev_mode` shortcut on root config
- [ ] Remove old monolithic config
- [ ] Update all imports

### 1.2 Remove ViteTemplateEngine

- [ ] Delete `src/py/litestar_vite/template_engine.py`
- [ ] Update plugin to work with standard `JinjaTemplateEngine`
- [ ] Make template engine optional (not required for SPA mode)
- [ ] Update tests

### 1.3 Async Asset Loader

- [ ] Rewrite `ViteAssetLoader` class:
  - [ ] Remove singleton pattern (`_instance` class var)
  - [ ] Add `async def initialize()` method
  - [ ] Use `anyio.Path` for async file I/O
  - [ ] Async manifest parsing
  - [ ] Async hot file reading
- [ ] Keep sync methods for template rendering (use cached data)
- [ ] Add proper typing

### 1.4 Dependency Injection

- [ ] Register `ViteAssetLoader` as DI provider in plugin
- [ ] Update `render_asset_tag` to get loader from request/app
- [ ] Update `render_hmr_client` similarly
- [ ] Remove global state access patterns

### 1.5 Vite Executor (Sidecar Mode)

- [ ] Create `src/py/litestar_vite/executor.py`:
  - [ ] `ViteExecutor` class for subprocess management
  - [ ] `async def start()` - spawn Node.js subprocess
  - [ ] `async def stop()` - graceful shutdown with timeout
  - [ ] `async def health_check()` - verify sidecar is responsive
  - [ ] `internal_url` property - URL for Python to connect to
- [ ] Create sidecar bootstrap script:
  - [ ] `src/js/src/sidecar.ts` - Node.js entry point
  - [ ] Vite `createServer()` with `middlewareMode: true`
  - [ ] Configure `server.hmr.clientPort` to Python's port
  - [ ] Bind to ephemeral port on 127.0.0.1
  - [ ] Print JSON ready message to stdout
- [ ] Auto-detection logic:
  - [ ] `detect_vite_mode()` function
  - [ ] Check for production manifest → production
  - [ ] Check for running Vite on 5173 → external
  - [ ] Check for vite.config.ts → sidecar
- [ ] WebSocket proxy for HMR:
  - [ ] `/__vite_hmr__` WebSocket handler
  - [ ] Bidirectional message forwarding
  - [ ] Graceful disconnect handling
- [ ] Subprocess lifecycle management:
  - [ ] Start in `server_lifespan` context
  - [ ] Stop on shutdown/SIGTERM
  - [ ] Auto-restart on crash (optional)
  - [ ] Health monitoring

### 1.6 Plugin Overhaul

- [ ] Update `VitePlugin.__init__` for new config
- [ ] Update `on_app_init`:
  - [ ] Register DI providers
  - [ ] Register ViteExecutor for dev mode
  - [ ] Conditionally register template helpers (template mode)
  - [ ] Conditionally register SPA handler (spa mode)
  - [ ] Register WebSocket HMR proxy route
- [ ] Update `server_lifespan`:
  - [ ] Use new config structure
  - [ ] Initialize async loader
  - [ ] Start ViteExecutor if sidecar mode
  - [ ] Stop ViteExecutor on shutdown
- [ ] Add mode detection logic

### 1.7 Tests for Phase 1

- [ ] Config validation tests
- [ ] Async loader tests
- [ ] DI registration tests
- [ ] Mode detection tests
- [ ] ViteExecutor tests:
  - [ ] Subprocess start/stop lifecycle
  - [ ] Port detection from stdout
  - [ ] Health check functionality
  - [ ] Graceful shutdown on SIGTERM
- [ ] WebSocket proxy tests:
  - [ ] Bidirectional message forwarding
  - [ ] Connection cleanup on disconnect

---

## Phase 2: Dual Mode System

### 2.1 SPA Handler

- [ ] Create `src/py/litestar_vite/spa.py`:
  - [ ] `ViteSPAHandler` class
  - [ ] `async def get_html(request)` method
- [ ] Implement dev mode proxy:
  - [ ] Use `httpx.AsyncClient`
  - [ ] Proxy to Vite dev server
  - [ ] Handle errors gracefully
- [ ] Implement production serving:
  - [ ] Async read of `index.html`
  - [ ] Cache HTML in memory
  - [ ] Serve with injections
- [ ] Register as route handler in plugin

### 2.2 HTML Injection System

- [ ] Create `src/py/litestar_vite/html.py`:
  - [ ] `HtmlTransformer` class (using regex, with `html.parser` fallback for edge cases)
  - [ ] `inject_head_script(html, script)` method
  - [ ] `inject_body_content(html, content)` method
  - [ ] `set_data_attribute(html, selector, attr, value)` method
- [ ] Injection types:
  - [ ] `window.__LITESTAR_ROUTES__` (routes metadata)
  - [ ] `window.__INERTIA_PAGE__` (Inertia props)
  - [ ] `data-page` attribute on `#app`
- [ ] **Risk mitigation tests:**
  - [ ] Test with HTML containing `<!-- </head> -->` comments
  - [ ] Test with malformed HTML
  - [ ] Test case sensitivity

### 2.3 Template Mode Updates

- [ ] Keep `{{ vite() }}` and `{{ vite_hmr() }}` working
- [ ] Make Jinja optional (only for template mode)
- [ ] Integrate with `litestar-htmx` for HTMX support
- [ ] Document litestar-htmx + litestar-vite integration
- [ ] Add `vite_partial(entry)` template helper for HTMX partial asset loading

### 2.4 Mode Selection Logic

- [ ] Implement mode auto-detection:
  - [ ] Check for `index.html` in resource dir → SPA
  - [ ] Check for template config → Template
  - [ ] Explicit `mode=` overrides auto-detection
- [ ] Validate mode vs config combinations

### 2.5 Tests for Phase 2

- [ ] SPA handler tests (mock Vite server)
- [ ] HTML injection tests
- [ ] Template mode tests
- [ ] Mode selection tests

---

## Phase 3: Type Generation

### 3.1 Python CLI Commands

- [ ] Add `export-schema` command:
  - [ ] Wrap Litestar's `_generate_openapi_schema`
  - [ ] `--output` option
  - [ ] `--format` option (json/yaml)
- [ ] Add `export-routes` command:
  - [ ] Generate Ziggy-like routes metadata
  - [ ] Include: path, methods, params, component
  - [ ] `--only` option (whitelist patterns)
  - [ ] `--except` option (blacklist patterns)
  - [ ] `--include-components` flag
- [ ] Add `generate-types` command:
  - [ ] Run export-schema
  - [ ] Run export-routes
  - [ ] Call `npx @hey-api/openapi-ts`
  - [ ] Generate route helper

### 3.2 Routes Metadata Generator

- [ ] Create `src/py/litestar_vite/codegen.py`:
  - [ ] `RouteMetadata` dataclass
  - [ ] `extract_route_metadata(app)` function using `route_handler_method_view`
  - [ ] `generate_routes_json(app, config)` function
- [ ] Extract from Litestar routes:
  - [ ] Route name (handler name or explicit)
  - [ ] Path with parameter placeholders (normalized to `{param}` syntax)
  - [ ] HTTP methods
  - [ ] Path parameters with types (map `int`→`number`, `uuid`→`string`, etc.)
  - [ ] Query parameters with types
  - [ ] Inertia component (from `opt`)
  - [ ] Mount path handling (if app mounted under `/api/v1`)
- [ ] Output Ziggy-compatible JSON format
- [ ] Use `pathlib.PurePosixPath` for cross-platform compatibility
- [ ] **Risk mitigation tests:**
  - [ ] Test path parameters: `/users/{id:int}`, `/items/{uuid:uuid}`
  - [ ] Test mount paths
  - [ ] Test regex constraints
  - [ ] Test on Windows (path separators)

### 3.3 TypeScript Route Helper Generator

- [ ] Create route helper codegen (Python or TS):
  - [ ] Parse routes.json
  - [ ] Generate `RouteName` union type
  - [ ] Generate `RouteParams` interface
  - [ ] Generate `route()` function
  - [ ] Generate `router` utilities
- [ ] Output to configurable path

### 3.4 Vite Plugin Integration

- [ ] Extend `PluginConfig` interface:
  ```typescript
  types?: {
    enabled?: boolean;
    output?: string;
    exportCommand?: string;
    watch?: string[];
    debounce?: number;
  } | boolean;
  ```
- [ ] Implement in plugin:
  - [ ] Run export on dev server start
  - [ ] Watch Python files with chokidar
  - [ ] Debounced regeneration
  - [ ] HMR event on type change

### 3.5 @hey-api/openapi-ts Integration

- [ ] Add as peer dependency
- [ ] Create default `openapi-ts.config.ts` template
- [ ] Document configuration options
- [ ] Support Zod generation
- [ ] Support SDK generation (optional)

### 3.6 Tests for Phase 3

- [ ] Route metadata extraction tests
- [ ] CLI command tests
- [ ] Generated TypeScript compilation tests
- [ ] Watch mode tests

---

## Phase 4: Inertia Enhancement

### 4.1 Inertia SPA Mode

- [ ] Auto-injection in SPA handler:
  - [ ] `window.__INERTIA_PAGE__` with page props
  - [ ] `data-page` attribute on `#app` div
- [ ] X-Inertia header handling:
  - [ ] Detect Inertia requests
  - [ ] Return JSON for XHR, HTML for initial
- [ ] Version mismatch handling

### 4.2 Shared Props Typing

- [ ] Extract shared props sources:
  - [ ] `InertiaConfig.extra_static_page_props`
  - [ ] `InertiaConfig.extra_session_page_props`
  - [ ] Built-in props (flash, errors, csrf_token)
- [ ] Generate `SharedProps` interface
- [ ] Include in page props type

### 4.3 Component Props Extraction

- [ ] Extract from `InertiaResponse[T]` type hints
- [ ] Map route → component → props
- [ ] Generate `InertiaPageProps` interface
- [ ] Generate component registry type

### 4.4 Frontend Helpers

- [ ] Generate `useTypedPage<T>()` hook type
- [ ] Vue composable wrapper
- [ ] React hook wrapper
- [ ] Include in generated files

### 4.5 Tests for Phase 4

- [ ] Inertia injection tests
- [ ] Page props typing tests
- [ ] XHR vs HTML response tests

---

## Phase 5: Polish & Documentation

### 5.1 Framework Integrations

#### Astro Integration

- [ ] Create `src/js/src/astro.ts` - Astro integration entry point
- [ ] Implement `litestar()` Astro integration:
  - [ ] API proxy configuration for dev server
  - [ ] `astro:config:setup` hook for Vite config merge
  - [ ] `astro:server:setup` hook for middleware injection
- [ ] Share type generation output with standard Vite plugin

#### SvelteKit Integration

- [ ] Create `src/js/src/sveltekit.ts` - SvelteKit-compatible Vite plugin
- [ ] Ensure plugin works alongside `@sveltejs/kit/vite`:
  - [ ] Plugin ordering (litestar before sveltekit)
  - [ ] No conflicts with SvelteKit's entry point handling
  - [ ] `$lib` alias support for generated types
- [ ] API proxy configuration for SvelteKit dev server
- [ ] Type generation compatible with SvelteKit's `+page.ts` load functions
- [ ] Svelte 5 runes compatibility testing

### 5.2 Project Scaffolding Templates

#### CLI Init Command

- [ ] Create `src/py/litestar_vite/scaffolding/` module
- [ ] Implement `litestar vite init` command in `cli.py`:
  - [ ] `--template` option (react, vue, vue-inertia, svelte, sveltekit, htmx, astro)
  - [ ] `--tailwind` flag for TailwindCSS addon
  - [ ] `--typescript` flag (default: True)
  - [ ] `--port` option (default: 5173)
  - [ ] `--litestar-port` option (default: 8000)
  - [ ] `--no-interactive` flag for CI/scripts
  - [ ] `--name` option for project name

#### Interactive Console UI (Rich-based)

- [ ] Add `rich>=13.0` and `questionary>=2.0` to `[project.optional-dependencies].cli`
- [ ] Create `src/py/litestar_vite/scaffolding/ui.py`:
  - [ ] Welcome banner with Rich Panel
  - [ ] Framework selection with questionary.select()
  - [ ] Boolean prompts for TypeScript, TailwindCSS
  - [ ] Port configuration prompts
  - [ ] Progress spinner during file generation
  - [ ] Success message with next steps
- [ ] Add custom questionary Style for consistent branding

#### Base Templates

- [ ] Reorganize `src/py/litestar_vite/templates/`:
  - [ ] Create `base/` directory for shared templates
  - [ ] Move existing `vite.config.ts.j2`, `package.json.j2`, `tsconfig.json.j2` to `base/`
  - [ ] Add template variable support for all conditionals

#### Framework-Specific Templates

- [ ] Create `templates/react/`:
  - [ ] `App.tsx.j2` - React App component
  - [ ] `main.tsx.j2` - React entry point
  - [ ] `index.html.j2` - HTML template
  - [ ] Update `package.json.j2` with React dependencies

- [ ] Create `templates/vue/`:
  - [ ] `App.vue.j2` - Vue 3 App component
  - [ ] `main.ts.j2` - Vue entry point
  - [ ] `index.html.j2` - HTML template

- [ ] Create `templates/vue-inertia/`:
  - [ ] `App.vue.j2` - Inertia App wrapper
  - [ ] `main.ts.j2` - Inertia createApp setup
  - [ ] `pages/Home.vue.j2` - Example home page
  - [ ] `pages/Users/Index.vue.j2` - Example list page

- [ ] Create `templates/svelte/`:
  - [ ] `App.svelte.j2` - Svelte 5 component with runes
  - [ ] `main.ts.j2` - Svelte entry point
  - [ ] `index.html.j2` - HTML template

- [ ] Create `templates/sveltekit/`:
  - [ ] `svelte.config.js.j2` - SvelteKit config
  - [ ] `vite.config.ts.j2` - Vite config with SvelteKit
  - [ ] `src/routes/+page.svelte.j2` - Index page

- [ ] Create `templates/htmx/`:
  - [ ] `main.js.j2` - HTMX + Alpine.js setup
  - [ ] `templates/base.html.j2` - Jinja base template
  - [ ] `templates/index.html.j2` - Index page

- [ ] Create `templates/astro/`:
  - [ ] `astro.config.mjs.j2` - Astro config
  - [ ] `src/pages/index.astro.j2` - Index page

#### Template Addons

- [ ] Create `templates/addons/tailwindcss/`:
  - [ ] `tailwind.config.js.j2`
  - [ ] `postcss.config.js.j2`
  - [ ] Merge logic for adding to base styles

#### Template Generation Logic

- [ ] Create `src/py/litestar_vite/scaffolding/generator.py`:
  - [ ] `TemplateContext` dataclass for all template variables
  - [ ] `generate_project_files()` async function
  - [ ] File copying with Jinja2 rendering
  - [ ] Directory creation with proper permissions
  - [ ] Conflict detection (warn if files exist)

#### Template Tests

- [ ] Unit tests for each template rendering
- [ ] Integration tests: init → npm install → npm run build
- [ ] Test non-interactive mode works correctly
- [ ] Test template variable substitution

### 5.3 Examples

- [ ] `examples/spa-react/` - React SPA with types
- [ ] `examples/spa-vue-inertia/` - Vue + Inertia
- [ ] `examples/spa-svelte/` - Svelte 5 SPA with types
- [ ] `examples/sveltekit-api/` - SvelteKit + Litestar API
- [ ] `examples/template-htmx/` - HTMX + Alpine
- [ ] `examples/astro-api/` - Astro + Litestar API
- [ ] `examples/fullstack-typed/` - All features
- [ ] Update existing examples to v2 API

### 5.4 Documentation

- [ ] Update `docs/usage/vite.rst`
- [ ] Create mode selection guide
- [ ] Create type generation setup guide
- [ ] Create migration guide from v1
- [ ] Update README.md

### 5.5 Testing & CI

- [ ] Full test coverage (>90%)
- [ ] Integration tests for each mode
- [ ] TypeScript compilation tests
- [ ] CI pipeline updates

### 5.6 Cleanup (Clean Break)

- [ ] Delete `template_engine.py` entirely
- [ ] Remove singleton pattern from `ViteAssetLoader`
- [ ] Remove all v1.x config options (no deprecation shims)
- [ ] Remove `use_server_lifespan`, `template_engine_config` options
- [ ] Update `__init__.py` exports to v2.0 public API only
- [ ] Changelog for v2.0 (breaking changes section)
- [ ] Archive old PRDs

---

## Definition of Done

### Per Task
- [ ] Implementation complete
- [ ] Unit tests passing
- [ ] Type hints complete
- [ ] Docstrings added

### Per Phase
- [ ] All tasks complete
- [ ] Integration tests passing
- [ ] `make lint` passing
- [ ] `make test` passing
- [ ] Documentation updated

### For Release
- [ ] All phases complete
- [ ] Examples working
- [ ] Migration guide complete
- [ ] Changelog written
- [ ] Version bumped to 2.0.0

---

## Dependencies

### Python (add to pyproject.toml)

```toml
dependencies = [
    "litestar>=2.0",
    "anyio>=4.0",
    "httpx>=0.25",
    "msgspec>=0.18",
]

[project.optional-dependencies]
jinja = ["jinja2>=3.0"]
```

### Node.js (add to package.json)

```json
{
  "dependencies": {
    "vite": "^5.0 || ^6.0 || ^7.0"
  },
  "peerDependencies": {
    "@hey-api/openapi-ts": ">=0.50",
    "zod": ">=3.0"
  }
}
```

---

## Pre-Implementation: Upstream Sync

Before starting implementation, verify alignment with upstream dependencies.

### Sync Checklist

- [ ] **Vite Backend Integration** (https://vite.dev/guide/backend-integration)
  - [ ] Verify `ManifestChunk` interface fields match our loader
  - [ ] Verify `@vite/client` HMR injection path
  - [ ] Check for new manifest fields in Vite 7.x
  - [ ] Document React Refresh preamble if needed

- [ ] **litestar-htmx** (https://github.com/litestar-org/litestar-htmx)
  - [ ] Confirm we're NOT duplicating any functionality
  - [ ] Document integration: `plugins=[HTMXPlugin(), VitePlugin()]`
  - [ ] Check for new response helpers to document

- [ ] **@hey-api/openapi-ts** (https://heyapi.dev/)
  - [ ] Check latest version: `npm view @hey-api/openapi-ts version`
  - [ ] Verify `createClient` API still works
  - [ ] Check Zod plugin availability

- [ ] **Inertia.js Protocol** (https://inertiajs.com/the-protocol)
  - [ ] Verify page object structure
  - [ ] Check for new headers
  - [ ] Verify version handling

### Quick Sync Commands

```bash
# Context7 MCP (if available)
mcp__context7__get-library-docs(
  context7CompatibleLibraryID="/websites/vite_dev",
  topic="backend integration manifest"
)

# Or manual checks
npm view @hey-api/openapi-ts version
gh api repos/litestar-org/litestar-htmx/releases/latest --jq '.tag_name'
```

---

## Notes

- Breaking changes are allowed - prioritize clean API
- SPA mode should be zero-config for standard Vite projects
- Type generation should be opt-in but trivial to enable
- Async I/O is critical for performance
- DI pattern enables proper testing
- **Use litestar-htmx for HTMX support** - don't reinvent the wheel
