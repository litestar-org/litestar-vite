# Tasks: Fix Hybrid/Inertia Dev Mode Asset URLs

## Phase 1: Planning ✓

- [x] Analyze root cause of 404 errors
- [x] Identify that Vite doesn't register @vite/client without index.html
- [x] Create PRD with two-part fix approach

## Phase 2: Implementation ✓

### Task 2.1: JS Plugin - Let Vite See index.html (PRIMARY FIX) ✓

**File**: `src/js/src/index.ts`

- [x] Remove the early `return null` for `inertiaMode` in `findIndexHtmlPath()`
- [x] Let the function find and return the actual index.html path
- [x] Modify the middleware to check `pluginConfig.inertiaMode` directly
- [x] When `inertiaMode && (req.url === "/" || req.url === "/index.html")`, serve placeholder

### Task 2.2: Python - Use Relative URLs with Base Prefix (SECONDARY FIX) ✓

**File**: `src/py/litestar_vite/html_transform.py`

- [x] Add `asset_url: str = "/static/"` parameter to `inject_vite_dev_scripts()`
- [x] Change Vite client script URL from `{vite_url}/@vite/client` to `{asset_url}@vite/client`
- [x] Change React preamble import from `{vite_url}/@react-refresh` to `{asset_url}@react-refresh`
- [x] Update docstring

**File**: `src/py/litestar_vite/handler/_app.py`

- [x] Pass `self._config.asset_url` to `inject_vite_dev_scripts()` calls in:
  - `_get_hybrid_dev_html_async()` (line ~344)
  - `_get_hybrid_dev_html_sync()` (line ~372)

## Phase 3: Testing

### Task 3.1: Automated Tests ✓

- [x] Verify `make lint` passes
- [x] Verify unit tests pass (531 passed)

### Task 3.2: Manual Testing (Pending User Verification)

- [ ] Run `cd examples/react-inertia && litestar assets serve`
- [ ] Test `http://localhost:5173/` shows placeholder
- [ ] Test `http://localhost:5173/static/@vite/client` returns JS (not 404)
- [ ] Test `http://localhost:8000/` loads full app without 404s
- [ ] Test HMR works (edit a component, see hot reload)
- [ ] Test React Fast Refresh works (component state preserved)

## Phase 4: Quality Gate

- [x] Unit tests pass (531 passed)
- [x] Linting clean
- [ ] Manual testing confirms fix
- [ ] No regressions in SPA mode

## Changes Made

### JS Plugin (`src/js/src/index.ts`)

1. **Removed early null return** in `findIndexHtmlPath()` for inertiaMode (line ~328-333)
   - Vite now sees the index.html, which allows it to register `@vite/client`
   - Added comment explaining the change and linking to Vite issue

2. **Updated middleware** to check `pluginConfig.inertiaMode` directly (line ~698-715)
   - In inertia mode, serves placeholder for `/` and `/index.html` requests
   - This happens BEFORE Vite's index.html serving, so the placeholder is shown

### Python (`src/py/litestar_vite/html_transform.py`)

1. **Added `asset_url` parameter** to `inject_vite_dev_scripts()` (line ~384)
   - Default value: `/static/`
   - Scripts now use relative URLs: `{asset_url}@vite/client`

### Python (`src/py/litestar_vite/handler/_app.py`)

1. **Pass `asset_url`** to `inject_vite_dev_scripts()` calls (lines ~344, ~372)
   - Uses `self._config.asset_url` from ViteConfig
