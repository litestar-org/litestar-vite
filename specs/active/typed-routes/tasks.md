# Implementation Tasks: Typed Routes Generation

## Overview

Consolidate route handling from two systems (runtime injection + static file) into a single build-time generated `routes.ts` with full type safety.

## Phase 1: Configuration & Core Generation

### 1.1 Update TypeGenConfig
**File**: `src/py/litestar_vite/config.py`

- [ ] Add `generate_routes: bool = True` field
- [ ] Add `routes_ts_path: Path | None = None` field (defaults to `output / "routes.ts"`)
- [ ] Update docstrings

### 1.2 Create Routes TypeScript Generator
**File**: `src/py/litestar_vite/codegen.py`

- [ ] Add `generate_routes_ts(app, openapi_schema=None) -> str` function
- [ ] Generate file header with `@generated` tag
- [ ] Generate `API_URL` constant from `import.meta.env.VITE_API_URL` (for separate dev servers)
- [ ] Generate `RouteName` union type from route names
- [ ] Generate `RoutePathParams` interface with per-route path params
- [ ] Generate `RouteQueryParams` interface with per-route query params
- [ ] Generate `RouteParams<T>` combined type
- [ ] Generate `routes` const object with metadata
- [ ] Generate type-safe `route()` function with overloads
- [ ] Generate helper functions: `hasRoute()`, `getRouteNames()`, `getRoute()`

### 1.3 Type Mapping Utilities
**File**: `src/py/litestar_vite/codegen.py`

- [ ] Create `_python_to_ts_type()` mapping function
- [ ] Handle primitives: int→number, str→string, bool→boolean
- [ ] Handle optionals: add `| undefined` or make property optional
- [ ] Handle arrays: `list[T]` → `T[]`
- [ ] Handle UUID, date, datetime → `string`

## Phase 2: Plugin Integration

### 2.1 Plugin Startup Generation
**File**: `src/py/litestar_vite/plugin.py`

- [ ] Call `generate_routes_ts()` in `on_app_init` when `types.generate_routes=True`
- [ ] Write to `types.routes_ts_path` (or default)
- [ ] Pass OpenAPI schema for enhanced type info

### 2.2 CLI Integration
**File**: `src/py/litestar_vite/cli.py`

- [ ] Add `--typescript` / `--ts` flag to `export-routes` command
- [ ] Generate `routes.ts` alongside `routes.json` when flag is set
- [ ] Consider standalone `generate-routes` subcommand

## Phase 3: Cleanup (Delete Unreleased Code)

### 3.1 Remove Runtime Injection
**File**: `src/py/litestar_vite/config.py`

- [ ] Remove `SPAConfig.inject_routes` config option (not released yet)

### 3.2 Remove Runtime Helper
**File**: `src/js/src/helpers/routes.ts`

- [ ] Delete `helpers/routes.ts` (not released yet, replaced by generated routes)
- [ ] Update `src/js/src/helpers/index.ts` exports

### 3.3 Update SPA Handler
**File**: `src/py/litestar_vite/spa.py`

- [ ] Remove `window.__LITESTAR_ROUTES__` injection code (not released yet)

## Phase 4: Query Parameter Support

### 4.1 Extract Query Params
**File**: `src/py/litestar_vite/codegen.py`

- [ ] Use existing `_extract_query_params()` function
- [ ] Include in `RouteQueryParams` interface generation
- [ ] Handle required vs optional (has default value)

### 4.2 Update Route Function
In generated `routes.ts`:

- [ ] Add query parameter handling to `route()` function
- [ ] Properly encode query string values
- [ ] Only include non-undefined values

## Phase 5: Testing

### 5.1 Python Unit Tests
**File**: `src/py/tests/unit/test_codegen.py`

- [ ] Test `generate_routes_ts()` basic output
- [ ] Test path parameter extraction and typing
- [ ] Test query parameter extraction and typing
- [ ] Test optional parameter handling
- [ ] Test Inertia component inclusion
- [ ] Test type mapping (int→number, etc.)

### 5.2 TypeScript Compilation Test
**File**: `src/py/tests/unit/test_codegen.py`

- [ ] Generate routes.ts to temp file
- [ ] Run `tsc --noEmit` to verify valid TypeScript
- [ ] Assert no compilation errors

### 5.3 JavaScript Tests
**File**: `src/js/tests/routes.test.ts`

- [ ] Create test file for generated route helpers
- [ ] Test `route()` URL generation without params
- [ ] Test `route()` with path params
- [ ] Test `route()` with query params
- [ ] Test `route()` with mixed path + query params
- [ ] Test `hasRoute()` validation
- [ ] Test API URL application for separate dev servers

## Phase 6: Documentation & Examples

### 6.1 Update Examples
For each example app:

- [ ] Enable `generate_routes=True` in config
- [ ] Import `route` from generated file
- [ ] Update components to use type-safe routing
- [ ] Remove any `window.__LITESTAR_ROUTES__` usage

### 6.2 Documentation
- [ ] Update README with typed routes usage
- [ ] Document `VITE_API_URL` env var for separate dev servers
- [ ] Document query parameter support

### 6.3 Vite Plugin Enhancement (Optional)
**File**: `src/js/src/index.ts`

- [ ] Auto-detect `.litestar.json` when running `npm run dev` separately
- [ ] Set `VITE_API_URL` from `.litestar.json` host/port if not already set
- [ ] Log helpful message about separate dev server mode

## Verification Checklist

After implementation:

- [ ] `make lint` passes
- [ ] `make test` passes
- [ ] All examples generate valid `routes.ts`
- [ ] TypeScript compilation succeeds in examples
- [ ] IDE autocomplete works for route names
- [ ] IDE shows errors for invalid route names
- [ ] IDE shows errors for missing required params
- [ ] Query params work correctly
- [ ] `VITE_API_URL` env var works for separate dev servers
- [ ] HMR updates routes on file changes

## Files to Modify

| File | Action | Description |
|------|--------|-------------|
| `src/py/litestar_vite/config.py` | Modify | Add generate_routes config |
| `src/py/litestar_vite/codegen.py` | Modify | Add generate_routes_ts() |
| `src/py/litestar_vite/plugin.py` | Modify | Call generation on startup |
| `src/py/litestar_vite/cli.py` | Modify | Add --typescript flag |
| `src/py/litestar_vite/spa.py` | Modify | Remove `window.__LITESTAR_ROUTES__` |
| `src/js/src/helpers/routes.ts` | Delete | Replaced by generated routes |
| `src/js/src/helpers/index.ts` | Modify | Remove routes.ts export |
| `src/py/tests/unit/test_codegen.py` | Modify | Add routes.ts tests |
| `src/js/tests/routes.test.ts` | Create | Test generated helpers |
| `examples/*/app.py` | Modify | Enable generate_routes |

## Usage Notes

### Default (Integrated Dev)

No configuration needed. Run:
```bash
litestar assets serve  # Starts Vite dev server with proxy
litestar run           # Starts Litestar
```

Routes generate as relative paths (`/api/books`), and Vite proxies API requests to Litestar.

### Separate Dev Servers

If running Vite separately (`npm run dev`), set the API URL:
```bash
# .env
VITE_API_URL=http://localhost:8000
```

Or the Vite plugin can auto-detect from `.litestar.json`.

### Import in Frontend

```typescript
import { route } from '@/generated/routes'

// Type-safe with autocomplete!
const url = route('book_detail', { book_id: 123 })
```
