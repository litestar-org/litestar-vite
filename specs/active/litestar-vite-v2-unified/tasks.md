# Implementation Tasks: Litestar-Vite v2.0 Unified

**PRD**: [prd.md](./prd.md)
**Status**: In Progress - Phase 1 Complete
**Created**: 2025-11-27
**Updated**: 2025-11-27

---

## Phase 1: Core Architecture (Foundation) ✅ COMPLETE

### 1.1 Configuration Refactor ✅

- [x] Create new config dataclasses in `config.py`:
  - [x] `PathConfig` - file system paths
    - [x] Add `asset_url: str = "/static/"` for CDN support
    - [x] Support both `str` and `Path` types with auto-conversion
  - [x] `RuntimeConfig` - execution settings
  - [x] `TypeGenConfig` - type generation settings
  - [x] `InertiaConfig` - Inertia.js settings
  - [x] `ViteConfig` - root config with nested configs
- [x] Add validation in `__post_init__`
- [x] Support bool shortcuts (`types=True` → full TypeGenConfig)
- [x] Add `dev_mode` shortcut on root config
- [x] Maintain legacy config classes for backward compatibility (BunViteConfig, DenoViteConfig, etc.)
- [x] Update all imports

### 1.2 Remove ViteTemplateEngine ✅

- [x] Delete `src/py/litestar_vite/template_engine.py`
- [x] Update plugin to work with standard `JinjaTemplateEngine`
- [x] Make template engine optional (not required for SPA mode)
- [x] Register template callables via Jinja2's `globals`
- [x] Update tests

### 1.3 Async Asset Loader ✅

- [x] Rewrite `ViteAssetLoader` class:
  - [x] Remove singleton pattern (`_instance` class var)
  - [x] Add `async def initialize()` method
  - [x] Use `anyio` for async file I/O
  - [x] Async manifest parsing
  - [x] Async hot file reading
- [x] Keep sync methods for template rendering (use cached data)
- [x] Add `initialize_loader()` class method for sync initialization
- [x] Add proper typing
- [x] Version ID is now a hash of manifest content

### 1.4 Dependency Injection ✅

- [x] Register `ViteAssetLoader` as DI provider in plugin
- [x] Update `render_asset_tag` to get loader from request/app
- [x] Update `render_hmr_client` similarly
- [x] Update `render_static_asset` similarly
- [x] Remove global state access patterns

### 1.5 Vite Executor (Sidecar Mode) ✅

- [x] Create `src/py/litestar_vite/executor.py`:
  - [x] `JSExecutor` base class for subprocess management
  - [x] `NodeExecutor` - npm-based execution
  - [x] `BunExecutor` - bun-based execution
  - [x] `DenoExecutor` - deno-based execution
  - [x] `YarnExecutor` - yarn-based execution
  - [x] `PnpmExecutor` - pnpm-based execution
  - [x] `NodeenvExecutor` - nodeenv in Python venv
  - [x] `run()` - spawn subprocess (returns Popen)
  - [x] `execute()` - run and wait for completion
  - [x] `install()` - install dependencies
- [x] Executor auto-detection based on config
- [ ] WebSocket proxy for HMR (deferred to Phase 2)
- [ ] Subprocess lifecycle management in lifespan (basic support added)

### 1.6 Plugin Overhaul ✅

- [x] Update `VitePlugin.__init__` for new config
- [x] Update `on_app_init`:
  - [x] Register DI providers
  - [x] Conditionally register template helpers (when Jinja available)
  - [x] Support both new nested config and legacy config classes
- [x] Update `server_lifespan`:
  - [x] Use new config structure
  - [x] Initialize async loader
  - [x] Add `async_server_lifespan` context manager
- [x] Fixed health check to use `httpx.HTTPError` instead of broad `Exception`

### 1.7 Tests for Phase 1 ✅

- [x] Config validation tests (`test_config.py`)
- [x] Async loader tests (`test_asset_loader.py`)
- [x] DI registration tests (`test_plugin.py`)
- [x] Executor tests (`test_executor.py`):
  - [x] Executable resolution
  - [x] Command execution
  - [x] Install command
  - [x] NodeenvExecutor with/without detection
- [x] All 176 tests passing
- [x] `make lint` passing (Ruff, Mypy, Pyright, slots check)
- [x] `make test` passing

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

## Phase 4: Inertia.js v2 Protocol Compliance

**Note**: This phase brings full Inertia.js v2 support to litestar-vite. The current implementation has partial support for lazy/deferred props. See [PRD Inertia.js v2 section](./prd.md#inertiajs-v2-protocol-compliance) for complete analysis.

### Current Implementation Status

| Feature | Status |
|---------|--------|
| `lazy()` helper | ✅ Implemented |
| `DeferredProp` class | ✅ Implemented |
| `StaticProp` class | ✅ Implemented |
| Partial rendering (`X-Inertia-Partial-Data`) | ✅ Implemented |
| `deferredProps` in response | ❌ Missing |
| Deferred prop groups | ❌ Missing |
| `clearHistory` / `encryptHistory` | ❌ Missing |
| Merge / Deep Merge props | ❌ Missing |
| `WhenVisible` server support | ⚠️ Partial |
| Prefetch cache headers | ❌ Missing |

### 4.1 Update PageProps Type (types.py)

**Priority**: High | **Effort**: Small

- [ ] Add `clearHistory: bool = False` field
- [ ] Add `encryptHistory: bool = False` field
- [ ] Add `deferredProps: dict[str, list[str]] | None = None` field
- [ ] Add `mergeProps: list[str] | None = None` field
- [ ] Add `deepMergeProps: list[str] | None = None` field
- [ ] Update serialization to use camelCase for JSON output
- [ ] Tests for PageProps serialization

### 4.2 Implement `defer()` Helper (helpers.py)

**Priority**: High | **Effort**: Medium

- [ ] Create `DeferredPropV2` dataclass with `fn`, `group`, `_evaluated`, `_result` fields
- [ ] Implement `async evaluate()` method (handles sync and async callables)
- [ ] Create `defer(fn, group="default")` helper function
- [ ] Export `defer` and `DeferredPropV2` from `__init__.py`
- [ ] Type hints and docstrings
- [ ] Tests for defer() with groups

**Example API**:
```python
from litestar_vite.inertia import defer

@get("/users", component="Users/Index")
async def users_list() -> dict:
    return {
        "users": await get_users(),
        "permissions": defer(get_permissions),  # Default group
        "teams": defer(get_teams, group="sidebar"),  # Sidebar group
    }
```

### 4.3 Implement Merge/Deep Merge Props (helpers.py)

**Priority**: Medium | **Effort**: Small

- [ ] Create `MergeableProp` dataclass with `value` and `deep` fields
- [ ] Create `merge(value)` helper function
- [ ] Create `deep_merge(value)` helper function
- [ ] Export from `__init__.py`
- [ ] Tests for merge props

### 4.4 Update InertiaResponse for v2 Protocol (response.py)

**Priority**: High | **Effort**: Large

- [ ] Add `clear_history` and `encrypt_history` parameters to `__init__`
- [ ] Create `_build_page_props()` method to separate immediate/deferred props
- [ ] Build `deferredProps` metadata grouped by group name
- [ ] Track `mergeProps` and `deepMergeProps` lists
- [ ] Update `to_asgi_response()` to include new PageProps fields
- [ ] Handle partial reload requests for deferred props (evaluate `DeferredPropV2`)
- [ ] Tests for response building

### 4.5 Add New Inertia Headers (_utils.py)

**Priority**: Medium | **Effort**: Small

- [ ] Add `PARTIAL_EXCEPT = "X-Inertia-Partial-Except"`
- [ ] Add `RESET = "X-Inertia-Reset"`
- [ ] Verify `ERROR_BAG = "X-Inertia-Error-Bag"` is present

### 4.6 Handle Partial Except Header (request.py)

**Priority**: Medium | **Effort**: Small

- [ ] Add `partial_except` cached property to `InertiaDetails`
- [ ] Add `partial_except_keys` property returning set of excluded keys
- [ ] Update `partial_keys` logic to exclude `partial_except_keys`
- [ ] Tests for partial except header

### 4.7 Register New Prop Types (plugin.py)

**Priority**: High | **Effort**: Small

- [ ] Import `DeferredPropV2`, `MergeableProp` in `on_app_init`
- [ ] Add to `app_config.signature_types`
- [ ] Add type encoders for serialization

### 4.8 Add Prefetch Cache Configuration (config.py)

**Priority**: Low | **Effort**: Small

- [ ] Add `prefetch_cache_ttl: int = 30` field
- [ ] Add `prefetch_stale_while_revalidate: int = 60` field
- [ ] Add response header generation for prefetch requests

### 4.9 Inertia SPA Mode

**Priority**: Medium | **Effort**: Medium

- [ ] Auto-injection in SPA handler:
  - [ ] `window.__INERTIA_PAGE__` with page props
  - [ ] `data-page` attribute on `#app` div
- [ ] X-Inertia header handling:
  - [ ] Detect Inertia requests
  - [ ] Return JSON for XHR, HTML for initial
- [ ] Version mismatch handling

### 4.10 Shared Props Typing

**Priority**: Low | **Effort**: Medium

- [ ] Extract shared props sources:
  - [ ] `InertiaConfig.extra_static_page_props`
  - [ ] `InertiaConfig.extra_session_page_props`
  - [ ] Built-in props (flash, errors, csrf_token)
- [ ] Generate `SharedProps` interface
- [ ] Include in page props type

### 4.11 Component Props Extraction

**Priority**: Low | **Effort**: Medium

- [ ] Extract from `InertiaResponse[T]` type hints
- [ ] Map route → component → props
- [ ] Generate `InertiaPageProps` interface
- [ ] Generate component registry type

### 4.12 Frontend Helpers

**Priority**: Low | **Effort**: Small

- [ ] Generate `useTypedPage<T>()` hook type
- [ ] Vue composable wrapper
- [ ] React hook wrapper
- [ ] Include in generated files

### 4.13 Comprehensive Tests for Inertia v2

**Priority**: High | **Effort**: Large

Create new test file: `src/py/tests/unit/inertia/test_inertia_v2.py`

- [ ] Test `defer()` creates `DeferredPropV2` with correct group
- [ ] Test response excludes deferred props from `props`
- [ ] Test response includes `deferredProps` metadata by group
- [ ] Test partial reload returns evaluated deferred props
- [ ] Test `merge()` creates `MergeableProp` with `deep=False`
- [ ] Test `deep_merge()` creates `MergeableProp` with `deep=True`
- [ ] Test response includes `mergeProps` / `deepMergeProps` lists
- [ ] Test `clear_history=True` sets `clearHistory: true` in response
- [ ] Test `encrypt_history=True` sets `encryptHistory: true` in response
- [ ] Test full page response matches Inertia v2 protocol
- [ ] Test `X-Inertia-Partial-Except` header is respected
- [ ] Test backward compatibility with existing `lazy()` function

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

- [x] Delete `template_engine.py` entirely (Phase 1)
- [x] Remove singleton pattern from `ViteAssetLoader` (Phase 1)
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
- [x] **Phase 1**: All tasks complete ✅
- [x] **Phase 1**: Integration tests passing ✅
- [x] **Phase 1**: `make lint` passing ✅
- [x] **Phase 1**: `make test` passing ✅
- [ ] Phase 2-5: In progress

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

---

## Progress Summary

| Phase | Status | Completion |
|-------|--------|------------|
| Phase 1: Core Architecture | ✅ Complete | 100% |
| Phase 2: Dual Mode System | 🔲 Not Started | 0% |
| Phase 3: Type Generation | 🔲 Not Started | 0% |
| Phase 4: Inertia.js v2 Protocol | 🔲 Not Started | 0% |
| Phase 5: Polish & Documentation | 🔲 Not Started | 0% |

**Overall Progress**: ~20% (Phase 1 of 5 complete)

### Phase 4 Priority Order (Inertia.js v2)

The following tasks should be completed in order due to dependencies:

1. **4.1 PageProps Type** - Foundation for all other changes
2. **4.2 defer() Helper** - Core v2 feature
3. **4.3 Merge Props** - Can be done in parallel with 4.2
4. **4.5 New Headers** - Small, independent task
5. **4.4 InertiaResponse** - Depends on 4.1, 4.2, 4.3
6. **4.6 Partial Except** - Depends on 4.5
7. **4.7 Register Types** - Depends on 4.2, 4.3
8. **4.8 Prefetch Config** - Low priority, independent
9. **4.13 Tests** - Final validation, depends on all above
