# Tasks: Inertia Integration Fixes

## Phase 1: Planning ✓

- [x] Create PRD
- [x] Identify affected components
- [x] Research Laravel Vite plugin behavior
- [x] Analyze root cause of ViteSPAHandler bug
- [x] Consensus analysis on portal vs sync approach
- [x] Decision: Use sync initialize() - portal pattern is over-engineering
- [x] Comprehensive async/sync pattern review of ALL litestar_vite source
- [x] Decision: Follow ViteAssetLoader pattern (dual _async/_sync methods)
- [x] Decision: Keep InertiaPlugin.portal (different use case - user async callables)

## Phase 2: Issue 3 - ViteSPAHandler Initialization (Priority: Critical) ✓

**Pattern to follow**: `ViteAssetLoader` in `loader.py:315-358` (has both `_load_manifest_async` and `_load_manifest_sync`)

### 2.1 Implementation - Follow ViteAssetLoader Pattern ✓

**Naming Convention**: Methods with both async and sync versions MUST use `_async` and `_sync` suffixes.

- [x] Rename `_load_index_html()` → `_load_index_html_async()` (async version using `anyio.Path`)
- [x] Add `_load_index_html_sync()` method using `pathlib.Path`
- [x] Rename `initialize()` → `initialize_async()` (async version for async contexts)
- [x] Add `initialize_sync()` method that calls `_load_index_html_sync()`
- [x] Add lazy init fallback in `get_html_sync()` calling `initialize_sync()` with warning
- [x] Update `plugin.py` lifespan to call `initialize_sync()` (simpler, no await needed)
- [x] Rename `shutdown()` → `shutdown_async()` (still needs `aclose()` for AsyncClient)
- [x] Keep `anyio` import for `*_async` methods (consistent with ViteAssetLoader)
- [x] Update all call sites to use new method names
- [x] Extract shared HTTP client init logic to `_init_http_clients()` helper
- [x] Add `_raise_index_not_found()` helper with `NoReturn` type hint

### 2.2 Testing ✓
- [x] Unit test: ViteSPAHandler initialization (22 tests pass)
- [x] Unit test: Lazy initialization fallback triggers warning
- [x] Update test file to use new method names

## Phase 3: Issue 4 - Auto-detect mode=hybrid when InertiaConfig present ✓

- [x] Update `_detect_mode()` in `config.py` to default to hybrid when InertiaConfig present
- [x] Update tests to reflect new behavior
- [x] All 48 config tests pass

## Phase 4: Issue 1 - Flash Messages for Inertia SPA ✓

### 4.1 Analysis ✓
- [x] Verified `get_shared_props()` already extracts flash from `request.session.pop("_messages", [])`
- [x] Flash messages expected format: `{"category": "...", "message": "..."}`

### 4.2 Implementation ✓
- [x] Implemented `flash()` helper in `helpers.py`
- [x] Exported `flash` from `litestar_vite.inertia.__init__.py`
- [x] Added comprehensive docstring with usage example

### 4.3 Testing ✓
- [x] All 49 Inertia tests pass
- [x] Verified import works: `from litestar_vite.inertia import flash`

## Phase 5: Issue 2 - Dev Server Index Page ✓

### 5.1 Implementation ✓
- [x] Modified `configureServer` middleware in `index.ts`
- [x] Extended placeholder serving from just `/index.html` to also include `/` (root)
- [x] APP_URL substitution works correctly

### 5.2 Testing ✓
- [x] Updated tests to reflect new behavior
- [x] All 236 TypeScript tests pass

## Phase 6: Testing & Validation ✓

- [x] Run full test suite: `make test` (all pass)
- [x] Run linting: `make lint` (all pass)
- [x] TypeScript build: `npm run build` (success)
- [x] Biome lint: clean

## Phase 7: Quality Gate ✓

- [x] All tests pass: `make test`
- [x] Linting clean: `make lint`
- [x] mypy: 0 issues
- [x] pyright: 0 errors
- [x] slotscheck: All OK
- [ ] Archive workspace to `specs/archive/`

## Summary of Changes

### Python Files Modified
- `src/py/litestar_vite/spa.py`:
  - Added `initialize_async()` and `initialize_sync()` dual methods
  - Added `_load_index_html_async()` and `_load_index_html_sync()` dual methods
  - Renamed `shutdown()` to `shutdown_async()`
  - Added `_init_http_clients()` helper method
  - Added `_raise_index_not_found()` helper with `NoReturn` type
  - Added lazy init fallback in `get_html_sync()` with warning log

- `src/py/litestar_vite/plugin.py`:
  - Updated to call `initialize_sync()` instead of `await initialize()`
  - Updated to call `shutdown_async()` instead of `shutdown()`

- `src/py/litestar_vite/config.py`:
  - Updated `_detect_mode()` to default to hybrid when InertiaConfig is present

- `src/py/litestar_vite/inertia/helpers.py`:
  - Added `flash()` function for template-less flash message support

- `src/py/litestar_vite/inertia/__init__.py`:
  - Exported `flash` function

### TypeScript Files Modified
- `src/js/src/index.ts`:
  - Extended placeholder serving to include root `/` path when no index.html exists

### Test Files Updated
- `src/py/tests/unit/test_spa.py`: Updated to use new method names
- `src/py/tests/unit/test_config.py`: Updated to reflect new hybrid default for Inertia
- `src/js/tests/index.test.ts`: Updated to reflect placeholder serving at root

## Notes

### File Locations
- `src/py/litestar_vite/spa.py` - ViteSPAHandler class
- `src/py/litestar_vite/inertia/helpers.py` - Helper functions
- `src/py/litestar_vite/inertia/__init__.py` - Public exports
- `src/js/src/index.ts` - Vite plugin
- `src/js/src/dev-server-index.html` - Placeholder page

### Commands
```bash
# Run tests
make test

# Run specific test file
uv run pytest src/py/tests/unit/test_spa.py -v

# Run linting
make lint

# Check type errors
make type-check

# Run example
cd examples/react-inertia && litestar assets serve
```
