# Recovery Guide: Inertia Defensive Hardening

## Current State

**Date**: 2025-12-07
**Branch**: `feat/inertia-specific`
**Status**: PRD and tasks created, implementation not started

### Work Completed

1. ✅ Deep analysis of GitHub issues #122-#126
2. ✅ Comparison against current branch state
3. ✅ Identified which issues are fixed vs unfixed
4. ✅ Created comprehensive PRD (`prd.md`)
5. ✅ Created detailed task breakdown (`tasks.md`)

### GitHub Issue Status

| Issue | Status in Branch | Notes |
|-------|-----------------|-------|
| #122 | ✅ Fixed | HTTPException check added in exception_handler.py:76-77 |
| #123 | ❌ Not Fixed | Open redirect vulnerability in InertiaBack |
| #124 | ❌ Not Fixed | IndexError on empty extras |
| #125 | ❌ Not Fixed | InertiaPlugin null check missing |
| #126 | ❌ Not Fixed | Cookie leak in redirect responses |

## Files Modified (Protocol Compliance - Already Done)

These files were modified as part of the parent `inertia-protocol-compliance` work:

- `src/py/litestar_vite/inertia/middleware.py` - Version mismatch detection
- `src/py/litestar_vite/inertia/response.py` - X-Inertia-Version header, V2 features
- `src/py/litestar_vite/inertia/helpers.py` - scroll_props, pagination helpers
- `src/py/litestar_vite/inertia/exception_handler.py` - Issue #122 fix (HTTPException)
- `src/py/litestar_vite/config.py` - encrypt_history config
- `src/py/tests/unit/inertia/*` - New tests

## Next Steps

### Immediate (P0 Security)

1. **Task 2.1**: Add `_get_safe_redirect_url()` to `response.py`
   - Location: After imports, before class definitions
   - Reference: Django's `is_safe_url` implementation

2. **Task 2.2**: Update `InertiaBack` to use safe redirect
   - Location: `response.py:548`
   - Change: Validate Referer header

3. **Task 2.3**: Remove `cookies=request.cookies` from redirects
   - Locations: `response.py` lines 509, 531, 550
   - Simple removal

4. **Task 2.4**: Add security tests
   - Location: `tests/unit/inertia/test_response.py`

### Then (P1 Robustness)

5. **Task 3.1**: Fix type-safe extras handling
   - Location: `exception_handler.py:115-122`

6. **Task 3.2**: Add InertiaPlugin null check
   - Location: `exception_handler.py:107`

### Finally (P2 Hardening)

7. Tasks 4.1-4.5: Various hardening fixes

## Context for Resumption

### Key Insight from Analysis

The `feat/inertia-specific` branch has substantial protocol compliance work completed (V2 features, version mismatch, pagination). The **security and robustness issues** (#123, #124, #125, #126) were filed against the `main` branch's alpha 6 release and were **not part of the original protocol compliance scope**.

### Implementation Notes

1. **_get_safe_redirect_url()** should handle:
   - Protocol-relative URLs (`//evil.com`)
   - Userinfo attacks (`https://evil@legitimate.com`)
   - javascript: scheme injection
   - Empty/None URLs

2. **Cookie removal** is straightforward - just delete the parameter

3. **Type-safe extras** needs careful attention to maintain backward compatibility

4. **Plugin null check** should gracefully degrade, not crash

### Testing Approach

- Add tests BEFORE implementing fixes (TDD for security)
- Cover all edge cases listed in tasks.md
- Verify existing tests still pass

## PR Preparation

When all fixes are complete, create PR with:

```markdown
## Summary

Closes #122, #123, #124, #125, #126

### Security Fixes
- [x] Fixed open redirect vulnerability in InertiaBack (Closes #123)
- [x] Fixed cookie leak in redirect responses (Closes #126)

### Robustness Fixes
- [x] HTTPException now preserves original status code (Closes #122)
- [x] Type-safe handling of exception extras (Closes #124)
- [x] Graceful handling when InertiaPlugin not registered (Closes #125)

### Additional Hardening
- [x] Broader exception handling in flash()
- [x] X-Inertia header on exception responses
- [x] Safe URL scheme validation

## Test Plan
- [ ] All unit tests pass
- [ ] Security tests verify no open redirects
- [ ] Robustness tests verify no crashes on edge cases
```

## Related Specs

- Parent PRD: `specs/active/inertia-protocol-compliance/prd.md`
- Parent Tasks: `specs/active/inertia-protocol-compliance/tasks.md`

## Commands

```bash
# Run tests
make test

# Run linting
make lint

# Check specific test file
uv run pytest src/py/tests/unit/inertia/test_response.py -v

# Check coverage
make coverage
```
