# Recovery Guide: Inertia Integration Fixes

## Current State

**PRD Created**: 2025-12-06
**Status**: Ready for implementation
**Decision**: Use synchronous `initialize()` - portal pattern rejected as over-engineering

All research and analysis is complete, including consensus analysis on async/sync approaches.

## Key Decisions

### Decision 1: ViteSPAHandler - Follow ViteAssetLoader Pattern

After comprehensive review of ALL async/sync patterns in `src/py/litestar_vite/`:

**Rejected**: Portal pattern (sqlspec's `portal.py` and `sync_tools.py`)
- Adds ~300 lines of vendored code
- Background thread management complexity
- Disproportionate for one-time file read

**Chosen**: Follow `ViteAssetLoader` pattern (dual sync/async methods)

**Naming Convention**: Methods with both async and sync versions MUST use `_async` and `_sync` suffixes.

- `ViteAssetLoader` already has `_load_manifest_async()` and `_load_manifest_sync()`
- ViteSPAHandler should have `_load_index_html_async()` and `_load_index_html_sync()`
- ViteSPAHandler should have `initialize_async()` and `initialize_sync()`
- Consistent with existing codebase patterns
- Keep `anyio` import for `*_async` methods

### Decision 2: Keep InertiaPlugin.portal

The InertiaPlugin portal is a DIFFERENT use case:

| ViteSPAHandler | InertiaPlugin.portal |
|----------------|---------------------|
| Simple file I/O | User async callables |
| Can use sync pathlib | Must call user async functions |
| One-time init | Per-request prop evaluation |

**Conclusion**: Keep `InertiaPlugin.portal` as-is - it's the correct pattern for `DeferredProp` async execution.

## Files to Modify

### Issue 3 (ViteSPAHandler Initialization) - Priority

| File | Status | Change |
|------|--------|--------|
| `src/py/litestar_vite/spa.py` | Pending | Make `initialize()` sync, replace `anyio.Path` with `pathlib.Path`, add lazy init fallback |
| `src/py/litestar_vite/plugin.py` | Pending | Remove `await` from `initialize()` call in lifespan |
| `src/py/litestar_vite/config.py` | Pending | Fix `_detect_mode()` to default hybrid when InertiaConfig present |

### Issue 1 (Flash Messages)

| File | Status | Change |
|------|--------|--------|
| `src/py/litestar_vite/inertia/helpers.py` | Pending | Verify/add `flash()` helper |
| `src/py/litestar_vite/inertia/__init__.py` | Pending | Export `flash` function |

### Issue 2 (Dev Server Index)

| File | Status | Change |
|------|--------|--------|
| `src/js/src/index.ts` | Pending | Serve placeholder for hybrid mode at "/" |

## Implementation Steps

### Step 1: Fix ViteSPAHandler (Issue 3)

1. In `spa.py`:
   - Rename `_load_index_html()` → `_load_index_html_async()` (keep async with `anyio.Path`)
   - Add `_load_index_html_sync()` using `pathlib.Path`
   - Rename `initialize()` → `initialize_async()` (keep async)
   - Add `initialize_sync()` that calls `_load_index_html_sync()`
   - Add lazy init in `get_html_sync()`:

     ```python
     if not self._initialized:
         logger.warning("ViteSPAHandler lazy init - lifespan may not have run")
         self.initialize_sync()
     ```

2. In `plugin.py`:
   - Change `await self._spa_handler.initialize()` to `self._spa_handler.initialize_sync()`

3. In `config.py`:
   - Fix `_detect_mode()` to return "hybrid" when InertiaConfig is present (unless `spa_mode=False`)

### Step 2: Flash Messages (Issue 1)

1. Verify `flash()` helper exists in `helpers.py`
2. Export from `__init__.py`

### Step 3: Dev Server Index (Issue 2)

1. Modify TypeScript plugin middleware to serve `dev-server-index.html` at "/" for hybrid mode

## Context for Resumption

### Why the Bug Occurs

1. `mode="hybrid"` creates `ViteSPAHandler` in `on_app_init()` (plugin.py:1818-1821)
2. Initialization happens in async lifespan hook (plugin.py:2094-2097)
3. In some complex setups, lifespan doesn't run before first request
4. `get_html_sync()` throws if not initialized (spa.py:357-359)

### Why Sync is Correct

The `initialize()` method was async only because of `anyio.Path`. However:
- HTTP client constructors are synchronous (only methods are async)
- File reading is one-time at startup
- `to_asgi_response()` runs ON the event loop thread - any blocking there affects all requests
- But microsecond file reads during init are negligible

### Flash Messages Context

Flash messages already work via:
1. `request.session["_messages"]` stores flash messages
2. `get_shared_props()` extracts them (helpers.py:532-533)
3. They're returned as `props["flash"]` (helpers.py:544)

Users just need a convenient `flash()` helper exported.

### Dev Server Index Context

TypeScript plugin already serves `dev-server-index.html` for `/index.html` when no index exists. For hybrid mode, we need to also serve it at `/` (root path).

## Test Commands

```bash
# Quick test of SPA handler
uv run pytest tests/test_spa.py -v

# Full test suite
make test

# Run react-inertia example to verify
cd examples/react-inertia
litestar assets serve
```

## References

- PRD: `specs/active/inertia-integration-fixes/prd.md`
- Tasks: `specs/active/inertia-integration-fixes/tasks.md`
- Consensus analysis: Documented in PRD under Issue 3
