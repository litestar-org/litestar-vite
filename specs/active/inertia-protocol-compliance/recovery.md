# Recovery Guide: Inertia Protocol Compliance

## Current State

**Status**: PRD Complete, Ready for Implementation

The comprehensive PRD and task breakdown have been created based on a multi-model consensus review (Gemini 3 Pro + GPT 5.1) of the Inertia.js protocol compliance in litestar-vite.

### Key Design Decisions

1. **`lazy()` static value support**: KEEP as Pythonic DX enhancement (per Gemini 3 Pro consultation)
   - Static values optimize bandwidth (don't send until partial reload)
   - Callables optimize bandwidth + CPU (deferred execution)
   - Both are valid; protocol is agnostic to server implementation

2. **History encryption**: Server only sends `encryptHistory`/`clearHistory` flags; all crypto is client-side

## Files Created

| File | Status | Description |
|------|--------|-------------|
| `specs/active/inertia-protocol-compliance/prd.md` | ✅ Complete | Full PRD with all requirements |
| `specs/active/inertia-protocol-compliance/tasks.md` | ✅ Complete | Detailed task breakdown by phase |
| `specs/active/inertia-protocol-compliance/recovery.md` | ✅ Complete | This file |
| `specs/active/inertia-protocol-compliance/research/` | ✅ Created | Empty, for research artifacts |
| `specs/active/inertia-protocol-compliance/tmp/` | ✅ Created | Empty, for temp files |

## Files To Be Modified (Implementation)

### P0 - Critical (First Priority)

| File | Changes Required |
|------|------------------|
| `src/py/litestar_vite/inertia/middleware.py` | Use `InertiaRequest`; return `InertiaExternalRedirect` on version mismatch |
| `src/py/litestar_vite/inertia/response.py` | Add `X-Inertia-Version` header to responses |

### P1 - V2 Features

| File | Changes Required |
|------|------------------|
| `src/py/litestar_vite/inertia/response.py` | Add `encrypt_history`, `clear_history` params |
| `src/py/litestar_vite/inertia/helpers.py` | Add `scroll_props()`, improve `should_render()` |

### P2 - DX Polish

| File | Changes Required |
|------|------------------|
| `src/py/litestar_vite/inertia/helpers.py` | Deprecate static `lazy()`, add `only()`/`except_()` |
| `src/py/litestar_vite/inertia/request.py` | Make component keys configurable |

## Next Steps

1. **Start Implementation**: Run `/implement inertia-protocol-compliance`
2. **Begin with P0**: Fix the three critical protocol issues first
3. **Test After Each Phase**: Run `make test` after completing each phase
4. **Quality Gate**: Run full `make check-all` before marking complete

## Context for Resumption

### Key Findings from Consensus Review

1. **Middleware Bug**: `InertiaMiddleware.__call__()` at line 43 creates `Request[Any, Any, Any](scope=scope)` - must use `InertiaRequest(scope=scope)` instead

2. **Version Mismatch Response**: Line 29 returns `InertiaRedirect` - must return `InertiaExternalRedirect` for 409 + X-Inertia-Location

3. **Missing Header**: In `response.py` lines 375-378, the `get_headers()` call only passes `enabled=True` but should also pass `version=vite_plugin.asset_loader.version_id`

4. **Both Models Agree**: BlockingPortal pattern is correct and should not be changed

5. **DX Insight**: `lazy()` helper differs from Laravel - it accepts static values, but Laravel's `lazy()` is callable-only

### Important Code Patterns

```python
# Current (WRONG):
request = Request[Any, Any, Any](scope=scope)

# Correct:
from litestar_vite.inertia.request import InertiaRequest
request = InertiaRequest(scope=scope)

# Current (WRONG):
return InertiaRedirect(request, redirect_to=str(request.url))

# Correct:
return InertiaExternalRedirect(request, redirect_to=str(request.url))

# Current (MISSING version header):
headers.update({"Vary": "Accept", **get_headers(InertiaHeaderType(enabled=True))})

# Correct:
headers.update({
    "Vary": "Accept",
    **get_headers(InertiaHeaderType(
        enabled=True,
        version=vite_plugin.asset_loader.version_id,
    ))
})
```

### Test Commands

```bash
# Run all tests
make test

# Run only Inertia tests
uv run pytest src/py/tests/unit/test_inertia*.py -v

# Run with coverage
make coverage

# Lint check
make lint
```

## Dependencies

- No external dependencies needed
- All changes are internal to `litestar_vite.inertia` module
- Existing test infrastructure (pytest, pytest-asyncio) is sufficient

## Related PRDs

- `specs/archive/inertia-integration-fixes/` - Previous Inertia fixes (ViteSPAHandler, flash messages, mode auto-detect)

## Consensus Sources

This PRD is based on analysis from:
- **Gemini 3 Pro** (9/10 confidence) - Advocate stance
- **GPT 5.1** (8/10 confidence) - Critical stance

Both models agreed on the critical issues and most of the recommended fixes. The task breakdown reflects their combined recommendations.
