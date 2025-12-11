# Recovery Guide: External Mode Static Router Auth Fix

## Current State

**Phase**: Complete
**Status**: Implementation done, tests passing

## Summary of Changes

The fix uses `AppHandler` (same as SPA mode) for external mode in production instead of relying on `html_mode=True` on the static files router:

1. **Static files router** (`plugin.py:1797-1807`):
   - Serves actual static files (JS, CSS, images) only
   - No `html_mode` - just file serving
   - Still has `opt={"exclude_from_auth": True}` for auth bypass

2. **`AppHandler` for external mode in production** (`plugin.py:1935-1941`):
   - External mode now uses `AppHandler` (like SPA mode)
   - Provides proper route exclusion via `is_litestar_route()` check
   - Serves `index.html` for client-side routes

3. **Skip manifest for external mode** (`handler.py:131-133, 162-164`):
   - External frameworks (Angular CLI, etc.) handle their own builds
   - No Vite manifest to load/transform

4. **Angular-cli example** (`app.py:94`):
   - Added `asset_url="/"` since external SPAs typically serve at root

## Files Modified

| File | Line(s) | Change |
|------|---------|--------|
| `src/py/litestar_vite/plugin.py` | 1797-1807 | Removed `html_mode` from static files config |
| `src/py/litestar_vite/plugin.py` | 1935-1941 | Added external mode to `AppHandler` usage |
| `src/py/litestar_vite/handler.py` | 131-133, 162-164 | Skip manifest for external mode |
| `src/py/litestar_vite/__init__.py` | 51 | Fixed import path |
| `src/py/tests/unit/test_handler.py` | multiple | Fixed patch paths from `.spa` to `.handler` |
| `examples/angular-cli/app.py` | 94 | Added `asset_url="/"` |

## Test Results

- All 276 JS tests pass
- All Python tests pass
- All linting checks pass

## Key Design Decisions

1. **Use `AppHandler` for external mode**: Same mechanism as SPA mode provides better route exclusion
2. **Skip manifest for external mode**: External frameworks handle their own asset hashing
3. **Static files router for actual files**: No SPA fallback, just serves real static files
4. **External mode users set `asset_url="/"`**: Required for SPA at root
