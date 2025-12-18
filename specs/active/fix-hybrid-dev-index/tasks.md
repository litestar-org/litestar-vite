# Tasks: Fix Hybrid/Inertia Dev Mode HTML Serving

## Phase 1: Planning
- [x] Create PRD
- [x] Identify affected components
- [x] Analyze root cause

## Phase 2: Implementation

### 2.1 Add Vite Dev Script Injection Utility
- [ ] Add `inject_vite_dev_scripts()` function to `html_transform.py`
  - Parameters: `html: str, vite_url: str, is_react: bool = False, csp_nonce: str | None = None`
  - Inject `<script type="module" src="{vite_url}/@vite/client"></script>` into `<head>`
  - If `is_react`, inject React refresh preamble before `@vite/client`
  - Support CSP nonce for script tags

### 2.2 Update AppHandler for Hybrid Dev Mode
- [ ] Add `mode` parameter to `AppHandler.__init__()` (from ViteConfig.mode)
- [ ] Modify `get_html()` method:
  - If `mode == "hybrid"` AND dev mode:
    - Read local index.html (reuse `_load_index_html_async` logic)
    - Inject Vite dev scripts using new utility
    - Apply existing transformations (page_data, csrf)
    - Return result WITHOUT proxying to Vite
  - Otherwise, continue existing proxy behavior
- [ ] Modify `get_html_sync()` method with same logic

### 2.3 Wire Up VitePlugin
- [ ] Pass `config.mode` to `AppHandler` constructor in VitePlugin
- [ ] Ensure `config.is_react` is accessible for React preamble injection

## Phase 3: Testing

### 3.1 Unit Tests
- [ ] Test `inject_vite_dev_scripts()` correctly injects scripts
- [ ] Test `inject_vite_dev_scripts()` with React preamble
- [ ] Test `inject_vite_dev_scripts()` with CSP nonce
- [ ] Test `AppHandler.get_html()` in hybrid dev mode returns local HTML with scripts
- [ ] Test `AppHandler.get_html_sync()` in hybrid dev mode

### 3.2 Integration Tests
- [ ] Test `react-inertia` example serves correct HTML
- [ ] Test `vue-inertia` example serves correct HTML
- [ ] Verify HMR functionality works

### 3.3 Regression Tests
- [ ] Verify SPA mode still proxies correctly
- [ ] Verify production mode unchanged
- [ ] Run full test suite: `make test`

## Phase 4: Quality Gate
- [ ] `make lint` passes
- [ ] `make test` passes
- [ ] Manual verification with examples
- [ ] Update recovery.md

## Implementation Notes

### Vite Dev Script Format

```html
<!-- For non-React apps -->
<script type="module" src="http://localhost:5173/@vite/client"></script>

<!-- For React apps with Fast Refresh -->
<script type="module">
import RefreshRuntime from 'http://localhost:5173/@react-refresh'
RefreshRuntime.injectIntoGlobalHook(window)
window.$RefreshReg$ = () => {}
window.$RefreshSig$ = () => (type) => type
window.__vite_plugin_react_preamble_installed__ = true
</script>
<script type="module" src="http://localhost:5173/@vite/client"></script>
```

### File Locations
- `src/py/litestar_vite/html_transform.py` - New injection function
- `src/py/litestar_vite/handler/_app.py` - Main logic change
- `src/py/litestar_vite/plugin/__init__.py` - Wire up mode to handler
- `src/py/tests/unit/test_html_transform.py` - Unit tests for injection
- `src/py/tests/unit/test_handler.py` - Unit tests for handler changes
