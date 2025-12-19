# PRD: Fix Hybrid/Inertia Dev Mode Asset URLs

## Overview
- **Slug**: fix-hybrid-dev-asset-urls
- **Created**: 2025-12-18
- **Status**: Draft
- **Priority**: High (blocking issue for Inertia users)

## Problem Statement

In hybrid/Inertia dev mode, Vite returns 404 for `@vite/client` and other internal modules because the JS plugin tells Vite there's no index.html, which prevents Vite from registering these routes.

### Current Behavior

1. User starts dev server with `litestar assets serve`
2. Accessing `http://localhost:5173/` shows the placeholder page ✓
3. Accessing `http://localhost:5173/@vite/client` says "did you mean /static/@vite/client?"
4. Accessing `http://localhost:5173/static/@vite/client` returns **404** ✗

Even with the correct base-prefixed URL, Vite doesn't serve `@vite/client`.

### Expected Behavior

- `http://localhost:5173/` → Placeholder page (for users who accidentally visit Vite directly)
- `http://localhost:5173/static/@vite/client` → Vite client JavaScript
- `http://localhost:8000/` (Litestar) → Full app with working HMR

## Root Cause Analysis

### PRIMARY ISSUE: Vite doesn't register `@vite/client` without index.html

**Reference**: [Vite GitHub Discussion #2418](https://github.com/vitejs/vite/discussions/2418)

> "When using Vite for serving only scripts for development without caring about the index.html, deleting it causes `/@vite/client` to return a 404. This problem appeared since Vite 2.0.2"

In our JS plugin, `findIndexHtmlPath()` returns `null` for Inertia mode:

**File**: `src/js/src/index.ts:328-333`
```typescript
async function findIndexHtmlPath(server: ViteDevServer, pluginConfig: ResolvedPluginConfig): Promise<string | null> {
  // In Inertia mode, never auto-detect index.html - the backend serves all HTML
  if (pluginConfig.inertiaMode) {
    return null  // <-- THIS BREAKS @vite/client REGISTRATION!
  }
  // ...
}
```

When `findIndexHtmlPath` returns `null`, Vite doesn't know about any HTML entry point, so it doesn't register the `@vite/client` virtual module route.

### SECONDARY ISSUE: `inject_vite_dev_scripts()` uses wrong URLs

**File**: `src/py/litestar_vite/html_transform.py:384-437`

```python
def inject_vite_dev_scripts(html: str, vite_url: str, *, is_react: bool = False, csp_nonce: str | None = None) -> str:
    # ...
    scripts.append(f'<script type="module" src="{vite_url}/@vite/client"{nonce_attr}></script>')
```

The function uses `vite_url` (e.g., `http://localhost:5173`) directly, which:
- Bypasses Litestar's proxy middleware
- Doesn't include Vite's `base` prefix (`/static/`)

### 2. React preamble also uses absolute URLs

```python
if is_react:
    react_preamble = f"""import RefreshRuntime from '{vite_url}/@react-refresh'
    # ...
```

### 3. Entry point scripts in index.html may need transformation

The `resources/index.html` contains:
```html
<script type="module" src="/resources/main.tsx"></script>
```

While the proxy handles `/resources/*` paths correctly (prepending the base prefix), this only works when accessed through the Litestar port. The current implementation doesn't transform these URLs in the served HTML.

## Goals

1. **Fix Vite `@vite/client` registration** - Let Vite see an index.html so it registers internal module routes
2. **Still serve placeholder for direct Vite port access** - Intercept `/` requests in middleware
3. **Fix Python script injection** - Use relative URLs with the correct `base` prefix
4. **Maintain backward compatibility** - Don't break existing SPA or template modes

## Non-Goals

- Changing how production mode works (manifest-based URL transformation is fine)
- Adding new configuration options (this should "just work")

## Acceptance Criteria

- [ ] `http://localhost:5173/static/@vite/client` returns Vite client JS (not 404)
- [ ] `http://localhost:5173/` shows placeholder page
- [ ] `http://localhost:8000/` loads the full Inertia app
- [ ] Vite HMR works (file changes trigger hot reload)
- [ ] React Fast Refresh works (for React apps)
- [ ] No 404 errors for Vite assets
- [ ] All existing tests pass

## Technical Approach

### Two-Part Fix Required

#### Part 1: JS Plugin - Let Vite See index.html (PRIMARY FIX)

**Problem**: `findIndexHtmlPath()` returns `null` in Inertia mode, which prevents Vite from registering `@vite/client`.

**Solution**: Let Vite find and use the index.html for internal setup, but intercept `/` requests to serve our placeholder instead.

**File**: `src/js/src/index.ts`

```typescript
// BEFORE: Returns null, breaks @vite/client
async function findIndexHtmlPath(server: ViteDevServer, pluginConfig: ResolvedPluginConfig): Promise<string | null> {
  if (pluginConfig.inertiaMode) {
    return null  // <-- PROBLEM: Vite won't register @vite/client
  }
  // ...
}

// AFTER: Let Vite see index.html, use separate flag for placeholder
async function findIndexHtmlPath(server: ViteDevServer, pluginConfig: ResolvedPluginConfig): Promise<string | null> {
  // REMOVED: Don't return null for inertiaMode
  // Vite needs to see index.html to register @vite/client
  // ...normal path resolution...
}

// In middleware, use pluginConfig.inertiaMode directly:
server.middlewares.use(async (req, res, next) => {
  if (pluginConfig.inertiaMode && (req.url === "/" || req.url === "/index.html")) {
    // Serve placeholder even though index.html exists
    // (because backend should serve the real app)
    const placeholderPath = path.join(dirname(), "dev-server-index.html")
    // ...serve placeholder...
    return
  }
  next()
})
```

#### Part 2: Python - Use Relative URLs with Base Prefix (SECONDARY FIX)

**Problem**: `inject_vite_dev_scripts()` injects absolute URLs without the base prefix.

**Solution**: Use relative URLs that go through Litestar's proxy.

**File**: `src/py/litestar_vite/html_transform.py`

```python
# BEFORE: Absolute URL without base
scripts.append(f'<script type="module" src="{vite_url}/@vite/client">')

# AFTER: Relative URL with base prefix
scripts.append(f'<script type="module" src="{asset_url}@vite/client">')
```

### Affected Files

| File | Changes |
| ---- | ------- |
| `src/js/src/index.ts` | Remove early `return null` in `findIndexHtmlPath`, check `inertiaMode` in middleware instead |
| `src/py/litestar_vite/html_transform.py` | Add `asset_url` parameter, use relative URLs |
| `src/py/litestar_vite/handler/_app.py` | Pass `asset_url` to `inject_vite_dev_scripts()` |

### Request Flow After Fix

```
Vite Port Direct Access:
http://localhost:5173/ → Our middleware → Placeholder page
http://localhost:5173/static/@vite/client → Vite → 200 OK (JS)

Litestar Port (Normal Flow):
http://localhost:8000/ → Litestar → HTML with <script src="/static/@vite/client">
Browser requests /static/@vite/client → Litestar Proxy → Vite → 200 OK
```

## Testing Strategy

### Manual Testing (Primary)

1. Run `litestar assets serve` in `examples/react-inertia/`
2. Test Vite port directly:
   - `http://localhost:5173/` → Should show placeholder
   - `http://localhost:5173/static/@vite/client` → Should return JS (not 404)
3. Test Litestar port:
   - `http://localhost:8000/` → Should load full app
   - Check browser Network tab for 404s
4. Test HMR: Edit a component, verify hot reload works

### Unit Tests

1. Test JS plugin `findIndexHtmlPath` doesn't return null for Inertia mode
2. Test Python `inject_vite_dev_scripts()` with various `asset_url` values

## Risks & Mitigations

| Risk | Impact | Mitigation |
| ---- | ------ | ---------- |
| Breaking existing SPA mode | High | Test all modes; middleware only intercepts in inertiaMode |
| Vite transforming index.html when we don't want it | Medium | Our middleware intercepts before Vite serves |
| Entry point scripts not working | Low | Proxy already handles resource_dir paths |

## Related Issues

- [Vite GitHub Discussion #2418](https://github.com/vitejs/vite/discussions/2418) - @vite/client 404 without index.html
- Previous fix attempt: commit `4651f18`

## References

- [Vite Server Options](https://vite.dev/config/server-options)
- [Vite Backend Integration Guide](https://vite.dev/guide/backend-integration)
