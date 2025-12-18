# Recovery Guide: Inertia Performance Optimizations

## Current State

**Phase**: Planning Complete, Ready for Implementation

The PRD has been created based on performance analysis with multi-model consensus (gemini-3-pro-preview and gpt-5.2).

## Files Modified

| File | Status |
|------|--------|
| `specs/active/inertia-performance-optimizations/prd.md` | Created |
| `specs/active/inertia-performance-optimizations/tasks.md` | Created |
| `specs/active/inertia-performance-optimizations/recovery.md` | Created |

## Implementation Files (Not Yet Modified)

| File | Changes Needed |
|------|----------------|
| `src/py/litestar_vite/inertia/plugin.py` | Add shared client lifespan, update type encoders |
| `src/py/litestar_vite/inertia/response.py` | Create LazyInertiaASGIResponse, refactor SSR |
| `src/py/litestar_vite/inertia/helpers.py` | Update DeferredProp.render() signature |

## Next Steps

1. **Start with Shared httpx.AsyncClient** (Phase 2):
   - Add `_ssr_client` attribute to `InertiaPlugin`
   - Initialize in lifespan with connection limits
   - Modify `_render_inertia_ssr()` to accept client parameter

2. **Then LazyInertiaASGIResponse** (Phase 3):
   - Create lazy response class
   - Defer SSR to async `__call__`
   - Update `InertiaResponse.to_response()`

3. **Finally DeferredProp optimization** (Phase 4):
   - Update type encoder to pass portal
   - Update `DeferredProp.render()` signature

## Context for Resumption

### Key Decisions Made

1. **Shared Client**: Initialize in plugin lifespan with sensible connection limits
2. **Lazy Response**: Defer SSR to async `__call__` method
3. **Portal Reuse**: Pass plugin portal to DeferredProp when available
4. **Graceful Degradation**: Fall back to per-request client if plugin not available

### Performance Issues Identified

| Issue | Location | Impact |
|-------|----------|--------|
| Per-request httpx.AsyncClient | `response.py:158-160` | 30-50% SSR latency |
| Event loop blocking | `_render_spa()` → `get_html_sync()` | Blocks other requests |
| DeferredProp portal creation | `helpers.py` | ~5-10ms per prop |

### Current Code Locations

- SSR client creation: `response.py:158-160` (`async with httpx.AsyncClient()`)
- Plugin lifespan: `plugin.py:193-208` (`lifespan()`)
- Type encoders: `plugin.py:165-167` (`_configure_app_for_inertia()`)
- DeferredProp: `helpers.py:128-165` (`class DeferredProp`)
- SPA rendering: `response.py:238-265` (`_render_spa()`)

### Multi-Model Consensus

Both gemini-3-pro-preview and gpt-5.2 agreed on:
- Priority order: Shared Client > Lazy Response > Portal Optimization
- All changes are backward compatible
- Confidence: 8-9/10

## Commands to Resume

```bash
# Check current state
cd /home/cody/code/litestar/litestar-vite
cat specs/active/inertia-performance-optimizations/tasks.md

# Run tests to verify nothing broken
make test

# Start implementation
/implement inertia-performance-optimizations
```

## Related PRDs

- `specs/active/inertia-v2-flash-script-element/` - Inertia v2.3+ protocol features

## Related Changes Already Implemented

The **Script Element Optimization** from `inertia-v2-flash-script-element` PRD has been implemented:

| Feature | Impact | Files |
|---------|--------|-------|
| `use_script_element = True` (default) | ~37% smaller payloads vs data-page attribute | `config/_spa.py`, `handler/_app.py` |
| `inject_page_script()` | No HTML entity escaping needed (only `</` → `<\/`) | `html_transform.py` |
| Bridge config `spa.useScriptElement` | TypeScript plugin auto-detection | `plugin/_utils.py`, `bridge-schema.ts` |

This is a **client-side** performance optimization (smaller payload, faster parsing). The optimizations in this PRD focus on **server-side** performance (SSR latency, connection pooling, portal reuse).
