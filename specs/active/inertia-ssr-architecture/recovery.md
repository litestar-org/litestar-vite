# Recovery Guide: Inertia Proxy Bug Fix & Dev Server Mode

## Current State

**Status**: ✅ IMPLEMENTATION COMPLETE - Ready for manual verification

Both bugs have been fixed and all automated tests pass:

1. **Bug 1**: ✅ Fixed - Proxy middleware restructured to send ASGI response OUTSIDE httpx context manager
2. **Bug 2**: ✅ Fixed - Inertia mode auto-detection disables index.html auto-detection

## Changes Made

### Bug 1 (Python) - [plugin.py](src/py/litestar_vite/plugin.py)

1. **Updated `_HOP_BY_HOP_HEADERS`** (lines 417-430):
   - Added `content-length` and `content-encoding` to the filter
   - These headers become invalid because httpx auto-decompresses responses

2. **Fixed `ViteProxyMiddleware._proxy_http()`** (lines 560-596):
   - Declared response variables with defaults before context manager
   - Added `got_full_body` flag to distinguish cleanup errors from real failures
   - Wrapped entire `async with` in `try/except`
   - Moved `send()` calls OUTSIDE context manager

3. **Fixed `ExternalDevServerProxyMiddleware._proxy_request()`** (lines 795-835):
   - Applied same pattern as ViteProxyMiddleware
   - Handles `ConnectError` (503) and `HTTPError` (502) separately

### Bug 2 (TypeScript) - [index.ts](src/js/src/index.ts)

1. Added `inertiaMode?: boolean` to `PluginConfig` interface (lines 155-166)
2. Added `inertiaMode: boolean` to `ResolvedPluginConfig` interface (lines 243-244)
3. Updated `resolvePluginConfig()` to auto-detect from `.litestar.json` mode (lines 950-951, 966)
4. Updated `findIndexHtmlPath()` to return `null` for Inertia mode (lines 313-317)
5. Updated console logging to show "Index Mode: Inertia" (lines 593-594)

### Other Changes

- Added `te` to codespell ignore list in `pyproject.toml` (valid HTTP header)

## Test Results

- ✅ All 264 JS tests pass
- ✅ All Python tests pass
- ✅ Mypy: 0 issues
- ✅ Pyright: 0 errors
- ✅ All pre-commit checks pass

## Next Steps

1. **Manual Verification** with reference app:
   ```bash
   cd /home/cody/code/litestar/litestar-fullstack-inertia
   unset VITE_PORT && LITESTAR_DEBUG=False VITE_DEV_MODE=True uv run app run -p 8088

   # Test proxy - should return JS content, not "Internal server error"
   curl http://localhost:8088/static/@vite/client
   ```

2. **Archive workspace** after verification passes

## Key Files Reference

- Bug report: `/home/cody/code/litestar/litestar-vite/new_inertia_bug.md`
- PRD: `/home/cody/code/litestar/litestar-vite/specs/active/inertia-ssr-architecture/prd.md`
- Tasks: `/home/cody/code/litestar/litestar-vite/specs/active/inertia-ssr-architecture/tasks.md`
- Proxy middleware: `/home/cody/code/litestar/litestar-vite/src/py/litestar_vite/plugin.py`
- Vite plugin: `/home/cody/code/litestar/litestar-vite/src/js/src/index.ts`
