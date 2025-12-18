# Recovery Guide: Fix Hybrid/Inertia Dev Mode HTML Serving

## Current State

**Status**: PRD Complete, Ready for Implementation

The bug has been fully analyzed and documented. The implementation has not yet started.

## Bug Summary

In hybrid/Inertia mode during development, the Litestar backend incorrectly serves the Vite placeholder page instead of the application's index.html. This happens because:

1. `AppHandler._proxy_to_dev_server()` requests `{vite_url}/` from Vite
2. Vite's JS plugin returns `dev-server-index.html` in Inertia mode because `findIndexHtmlPath()` returns null
3. The placeholder is returned instead of the actual app HTML

## Fix Strategy

Read local index.html directly in hybrid dev mode instead of proxying to Vite. Inject Vite dev scripts programmatically.

## Key Files to Modify

1. **`src/py/litestar_vite/html_transform.py`**
   - Add `inject_vite_dev_scripts(html, vite_url, is_react, csp_nonce)` function

2. **`src/py/litestar_vite/handler/_app.py`**
   - Add `mode` parameter to `AppHandler.__init__()`
   - Modify `get_html()` and `get_html_sync()` to handle hybrid mode differently:
     - Read local index.html
     - Inject Vite dev scripts
     - Return without proxying

3. **`src/py/litestar_vite/plugin/__init__.py`**
   - Pass `config.mode` to `AppHandler` constructor

## Verification Commands

```bash
# Test the fix manually
cd examples/react-inertia
litestar assets serve  # Terminal 1
litestar run           # Terminal 2
# Open http://localhost:8000/ - should show React app

# Run test suite
make test

# Run linting
make lint
```

## Related Files (Read-Only Context)

- `src/js/src/index.ts:719-735` - Vite placeholder serving logic
- `src/py/litestar_vite/inertia/response.py:453-515` - `_render_spa()` that calls `get_html_sync()`
- `src/py/litestar_vite/config/__init__.py:474-501` - Mode auto-detection logic

## Context for Resumption

The issue was reported as: "dev-server-index is served when accessing the vite port using inertia mode is now working. However, this same index is also being served up on the litestar port instead of my application index."

The root cause is that in hybrid/Inertia mode:
- Vite JS plugin correctly serves placeholder at direct Vite port access
- But Python backend proxies to Vite for HTML, receiving the placeholder
- The fix is to have Python read local HTML in hybrid mode instead of proxying

## Branch Information

**Branch**: `fix/dev-gen` (existing branch with related changes)
**Base Branch**: `main`
