# PRD: Fix Hybrid/Inertia Dev Mode HTML Serving

## Overview
- **Slug**: fix-hybrid-dev-index
- **Created**: 2025-12-18
- **Status**: Draft
- **Type**: Bug Fix

## Problem Statement

In hybrid/Inertia mode (`mode="hybrid"` or `mode="inertia"`), when running in development mode with the Vite dev server, the Litestar backend incorrectly serves the Vite placeholder page (`dev-server-index.html`) instead of the application's actual `index.html` with Inertia page props injected.

### Current Behavior

1. User runs `litestar assets serve` and `litestar run` for a hybrid/Inertia app
2. User accesses `http://localhost:8000/` (Litestar port)
3. Instead of seeing the React/Vue app with Inertia props, they see "Litestar Vite Dev Server" placeholder page

### Expected Behavior

1. Accessing the Vite port directly (e.g., `http://localhost:5173/`) should show the placeholder page (this works correctly)
2. Accessing the Litestar port should serve the application's `index.html` with:
   - Vite HMR scripts injected
   - Inertia page props injected via `data-page` attribute
   - React/Vue app loads correctly

### Who is Affected

All users of `mode="hybrid"` or `mode="inertia"` (template-less Inertia applications) are affected when running in development mode.

## Root Cause Analysis

### Flow Diagram

```
[Browser → Litestar:8000]
    ↓
[InertiaResponse.to_asgi_response()]
    ↓
[mode=="hybrid" → _render_spa()]
    ↓
[spa_handler.get_html_sync(page_data)]
    ↓
[dev_mode + hot_reload → _proxy_to_dev_server_sync()]
    ↓
[HTTP GET {vite_url}/]
    ↓
[Vite: inertiaMode=true → findIndexHtmlPath() returns null]
    ↓
[Vite serves dev-server-index.html ← BUG]
```

### Key Files Involved

1. **[src/js/src/index.ts](src/js/src/index.ts)** (lines 719-735)
   - The Vite plugin serves `dev-server-index.html` at `/` when no index.html is found
   - In Inertia mode, `findIndexHtmlPath()` returns `null` by design

2. **[src/py/litestar_vite/handler/_app.py](src/py/litestar_vite/handler/_app.py)** (lines 405-463)
   - `_proxy_to_dev_server()` and `_proxy_to_dev_server_sync()` request `{vite_url}/` from Vite
   - This is correct for SPA mode but wrong for hybrid/Inertia mode

3. **[src/py/litestar_vite/inertia/response.py](src/py/litestar_vite/inertia/response.py)** (lines 453-515)
   - `_render_spa()` calls `spa_handler.get_html_sync()` for hybrid mode
   - It expects to receive the app's index.html but gets the placeholder instead

### Design Issue

The Vite placeholder page behavior is **correct** for direct Vite port access - it guides users to the backend. However, when the Python backend proxies to Vite for HTML, it receives this placeholder instead of the actual index.html because Vite doesn't know the request is from the backend.

## Goals

1. Fix dev mode HTML serving for hybrid/Inertia applications
2. Maintain correct behavior: Vite port shows placeholder, Litestar port shows app
3. Preserve HMR functionality in dev mode
4. Keep backward compatibility with SPA mode (which works correctly)

## Non-Goals

- Changing how SPA mode works (it's not affected)
- Modifying the Vite placeholder page design
- Changing production mode behavior

## Acceptance Criteria

- [ ] `mode="hybrid"` apps show correct application UI on Litestar port in dev mode
- [ ] Inertia page props are correctly injected into the HTML
- [ ] HMR works correctly (changes trigger browser reload/update)
- [ ] Vite port still shows placeholder page for direct access
- [ ] `react-inertia` example works correctly in dev mode
- [ ] `vue-inertia` example works correctly in dev mode
- [ ] `react-inertia-jinja` example works correctly in dev mode
- [ ] `vue-inertia-jinja` example works correctly in dev mode
- [ ] Tests pass: `make test`
- [ ] Linting passes: `make lint`

## Technical Approach

### Option A: Fix in Python - Read Local index.html in Hybrid Dev Mode (Recommended)

In hybrid/Inertia mode, the backend should serve HTML directly from the filesystem rather than proxying to Vite. The Vite dev scripts should be injected programmatically.

**Changes Required:**

1. **[src/py/litestar_vite/handler/_app.py](src/py/litestar_vite/handler/_app.py)**
   - Add a `mode` parameter to `AppHandler.__init__()` or pass it from config
   - In `get_html()` and `get_html_sync()`, when `mode=="hybrid"`:
     - Read local index.html from disk (reuse `_load_index_html_*` methods)
     - Inject Vite client script: `<script type="module" src="{vite_url}/@vite/client"></script>`
     - Inject React refresh preamble if `is_react=True`
     - Return transformed HTML
   - For non-hybrid modes, continue proxying to Vite as before

2. **[src/py/litestar_vite/html_transform.py](src/py/litestar_vite/html_transform.py)** (may need new function)
   - Add `inject_vite_dev_scripts(html, vite_url, is_react)` function
   - Handles proper script injection for dev mode

**Pros:**
- Clean separation: Vite handles assets/HMR, Python handles HTML
- Consistent with Inertia's design philosophy (backend serves HTML)
- No changes needed on JS side

**Cons:**
- More complex logic in Python side

### Option B: Fix in Vite - Recognize Backend Requests

Have Vite return the actual index.html when the request comes from the Python backend (via a header or query parameter).

**Changes Required:**

1. **[src/js/src/index.ts](src/js/src/index.ts)**
   - Check for a special header (e.g., `X-Litestar-Backend: true`)
   - When present and index.html exists, serve it instead of placeholder

2. **[src/py/litestar_vite/handler/_app.py](src/py/litestar_vite/handler/_app.py)**
   - Add the special header when proxying to Vite

**Pros:**
- Minimal changes to Python side
- Vite handles HTML transformation

**Cons:**
- Violates Inertia's design (backend should own HTML)
- Adds protocol coupling between Python and JS
- Harder to test/debug

### Recommendation: Option A

Option A is recommended because:
1. Aligns with Inertia's philosophy that the backend controls HTML rendering
2. Cleaner architecture - Vite focuses on assets, Python focuses on HTML
3. No new protocol between Python and JS
4. More testable

## Affected Files

- `src/py/litestar_vite/handler/_app.py` - Main fix: hybrid dev mode HTML serving
- `src/py/litestar_vite/html_transform.py` - Potential new function for dev script injection
- `src/py/tests/unit/test_handler.py` - Unit tests for the fix
- `src/py/tests/e2e/test_inertia_examples.py` - E2E verification

## Testing Strategy

### Unit Tests
- Test `AppHandler.get_html()` returns correct HTML in hybrid dev mode
- Test Vite scripts are injected correctly
- Test React preamble injection when `is_react=True`

### Integration Tests
- Test `react-inertia` example serves correct HTML on Litestar port
- Test `vue-inertia` example serves correct HTML on Litestar port
- Test HMR still works after the fix

### Manual Testing
1. `cd examples/react-inertia && litestar assets serve` (in one terminal)
2. `cd examples/react-inertia && litestar run` (in another terminal)
3. Open `http://localhost:8000/` - should show React app with "Welcome to React Inertia!"
4. Edit `resources/pages/Home.tsx` - should trigger HMR update

## Research Questions

- [x] Is there an existing function to inject Vite dev scripts? (Not directly - need to add)
- [ ] How does Laravel's vite-plugin handle this for Inertia? (For reference)

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Breaking SPA mode | High | Add mode check, only change hybrid behavior |
| HMR breaks in hybrid mode | High | Test HMR thoroughly after fix |
| Performance regression in dev | Low | Caching already exists, minimal impact |
| Cache staleness in hybrid dev | Medium | Disable caching in dev mode for hybrid |
