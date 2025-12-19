# Recovery Guide: Fix Hybrid/Inertia Dev Mode Asset URLs

## Current State

**Phase**: PRD Complete, Ready for Implementation

## Problem Summary

In hybrid/Inertia dev mode:

1. `http://localhost:5173/static/@vite/client` returns **404**
2. This breaks HMR because Vite's client module isn't available

## Root Cause (IMPORTANT)

**Vite doesn't register `@vite/client` when there's no index.html detected!**

Reference: [Vite GitHub Discussion #2418](https://github.com/vitejs/vite/discussions/2418)

Our JS plugin explicitly returns `null` from `findIndexHtmlPath()` in Inertia mode:

```typescript
// src/js/src/index.ts:328-333
if (pluginConfig.inertiaMode) {
  return null  // <-- THIS BREAKS @vite/client REGISTRATION!
}
```

This was intended to prevent Vite from serving index.html (since Litestar should serve it). But it also prevents Vite from registering internal modules like `@vite/client`.

## Two-Part Fix Required

### Part 1: JS Plugin (PRIMARY - fixes the 404)

**File**: `src/js/src/index.ts`

1. Remove the early `return null` for `inertiaMode` in `findIndexHtmlPath()`
2. Let Vite see the index.html (so it registers `@vite/client`)
3. In middleware, check `pluginConfig.inertiaMode` directly to serve placeholder

```typescript
// In middleware:
if (pluginConfig.inertiaMode && (req.url === "/" || req.url === "/index.html")) {
  // Serve placeholder even though index.html exists
  // ...
}
```

### Part 2: Python (SECONDARY - fixes URL format)

**File**: `src/py/litestar_vite/html_transform.py`

1. Add `asset_url` parameter to `inject_vite_dev_scripts()`
2. Use relative URLs: `{asset_url}@vite/client` instead of `{vite_url}/@vite/client`

## Files to Modify

| File | Line | Change |
| ---- | ---- | ------ |
| `src/js/src/index.ts` | ~328 | Remove `return null` for inertiaMode |
| `src/js/src/index.ts` | ~696 | Check `pluginConfig.inertiaMode` in middleware |
| `src/py/litestar_vite/html_transform.py` | ~384 | Add `asset_url` param, use relative URLs |
| `src/py/litestar_vite/handler/_app.py` | ~344, ~366 | Pass `asset_url` to inject function |

## Testing Commands

```bash
# After making changes:
cd examples/react-inertia
litestar assets serve

# Test in browser:
# 1. http://localhost:5173/ → Should show placeholder
# 2. http://localhost:5173/static/@vite/client → Should return JS (not 404)
# 3. http://localhost:8000/ → Should load full app
```

## Context for Resumption

- The JS fix is PRIMARY - it's what makes `/static/@vite/client` work
- The Python fix is SECONDARY - it makes the URLs correct in injected HTML
- Both are needed for full functionality
- Test the JS fix first to verify `@vite/client` is accessible
