# Tasks: Inertia Defensive Hardening

## Overview

This task list covers all security and robustness fixes for GitHub issues #122-#126 and related hardening.

**Branch**: `feat/inertia-specific`
**Parent Work**: inertia-protocol-compliance

---

## GitHub Issues Tracking

| Issue | Title | Task | Status |
|-------|-------|------|--------|
| [#122](https://github.com/litestar-org/litestar-vite/issues/122) | HTTPException converted to 500 | Task 1.0 | ✅ Already Fixed |
| [#123](https://github.com/litestar-org/litestar-vite/issues/123) | Open redirect in InertiaBack | Task 2.1, 2.2 | ❌ TODO |
| [#124](https://github.com/litestar-org/litestar-vite/issues/124) | IndexError on empty extras | Task 3.1 | ❌ TODO |
| [#125](https://github.com/litestar-org/litestar-vite/issues/125) | InertiaPlugin lookup crashes | Task 3.2 | ❌ TODO |
| [#126](https://github.com/litestar-org/litestar-vite/issues/126) | Cookie leak in redirects | Task 2.3 | ❌ TODO |

---

## Phase 1: Issue #122 (Already Fixed) ✅

### Task 1.0: HTTPException Preservation
**Status**: ✅ Complete (in current branch)

**File**: `src/py/litestar_vite/inertia/exception_handler.py`

The fix was implemented as part of the protocol compliance work:
```python
if not inertia_enabled:
    # If it's already an HTTPException, use it directly with its original status code
    if isinstance(exc, HTTPException):
        return cast("Response[Any]", create_exception_response(request, exc))
```

- [x] HTTPException checked first
- [x] Original status code preserved
- [x] Tests pass

---

## Phase 2: Security Fixes (P0 - Critical)

### Task 2.1: Add _get_redirect_url() with Validation (Issue #123)

**File**: `src/py/litestar_vite/inertia/response.py`

**Add** `_get_redirect_url()` function at module level:
- [ ] Create function with signature `_get_redirect_url(request, url: str | None) -> str`
- [ ] Parse URL with `urlparse()`
- [ ] Allow relative URLs (no scheme/netloc)
- [ ] Validate absolute URLs are same-origin
- [ ] Whitelist schemes to `http`, `https` only
- [ ] Return base_url as fallback for invalid URLs
- [ ] Handle edge cases:
  - [ ] Protocol-relative URLs (`//evil.com`)
  - [ ] Userinfo attacks (`https://evil@good.com`)
  - [ ] javascript: scheme
  - [ ] Empty/None URL
  - [ ] URL with only path

### Task 2.2: Update InertiaBack to Use _get_redirect_url (Issue #123)

**File**: `src/py/litestar_vite/inertia/response.py`

**Modify** `InertiaBack.__init__`:
- [ ] Use `_get_redirect_url()` for Referer validation

**Before**:
```python
path=request.headers.get("Referer", str(request.base_url)),
```

**After**:
```python
path=_get_redirect_url(request, request.headers.get("Referer")),
```

### Task 2.2b: Update InertiaRedirect to Use _get_redirect_url (Issue #123)

**File**: `src/py/litestar_vite/inertia/response.py`

**Modify** `InertiaRedirect.__init__`:

- [ ] Use `_get_redirect_url()` for redirect_to validation

### Task 2.3: Remove Cookie Echo from Redirects (Issue #126)

**File**: `src/py/litestar_vite/inertia/response.py`

**Remove** `cookies=request.cookies` from:
- [ ] `InertiaExternalRedirect.__init__` (line ~509)
- [ ] `InertiaRedirect.__init__` (line ~531)
- [ ] `InertiaBack.__init__` (line ~550)

### Task 2.4: Security Tests

**File**: `src/py/tests/unit/inertia/test_response.py`

- [ ] Test: InertiaBack rejects cross-origin Referer
- [ ] Test: InertiaBack allows same-origin Referer
- [ ] Test: InertiaBack falls back to base_url for invalid Referer
- [ ] Test: InertiaBack handles protocol-relative URLs
- [ ] Test: InertiaBack rejects javascript: URLs
- [ ] Test: InertiaRedirect validates redirect_to parameter
- [ ] Test: No Set-Cookie header in redirect responses

### Phase 2 Verification

- [ ] Run `make test` - all tests pass
- [ ] Run `make lint` - no linting errors
- [ ] Manual test: Verify redirect behavior in browser

---

## Phase 3: Robustness Fixes (P1 - High Priority)

### Task 3.1: Type-Safe Extras Handling (Issue #124)

**File**: `src/py/litestar_vite/inertia/exception_handler.py`

**Modify** `create_inertia_exception_response()`:
- [ ] Change `extras = getattr(exc, "extra", "")` to `getattr(exc, "extra", None)`
- [ ] Add `isinstance(extras, (list, tuple))` check
- [ ] Add `len(extras) >= 1` check
- [ ] Add `isinstance(message, dict)` before using `.get()`
- [ ] Handle `message.get("key")` returning None

**Before**:
```python
extras = getattr(exc, "extra", "")
if extras and len(extras) >= 1:
    message = extras[0]
    default_field = f"root.{message.get('key')}"
```

**After**:
```python
extras = getattr(exc, "extra", None)
if extras and isinstance(extras, (list, tuple)) and len(extras) >= 1:
    message = extras[0]
    if isinstance(message, dict):
        key_value = message.get("key")
        default_field = f"root.{key_value}" if key_value is not None else "root"
```

### Task 3.2: InertiaPlugin Null Check (Issue #125)

**File**: `src/py/litestar_vite/inertia/exception_handler.py`

**Modify** `create_inertia_exception_response()`:
- [ ] Remove `cast()` wrapper
- [ ] Add explicit null check
- [ ] Return basic response if plugin not found

**Before**:
```python
inertia_plugin = cast("InertiaPlugin", request.app.plugins.get("InertiaPlugin"))
```

**After**:
```python
inertia_plugin = request.app.plugins.get("InertiaPlugin")
if inertia_plugin is None:
    return InertiaResponse[Any](
        media_type=preferred_type,
        content=content,
        status_code=status_code,
    )
```

### Task 3.3: Robustness Tests

**File**: `src/py/tests/unit/inertia/test_exception_handler.py` (NEW)

- [ ] Test: Empty extras string doesn't crash
- [ ] Test: Empty extras list doesn't crash
- [ ] Test: None extras doesn't crash
- [ ] Test: Non-dict extras[0] doesn't crash
- [ ] Test: Missing InertiaPlugin returns basic response
- [ ] Test: Normal exception flow still works

### Phase 3 Verification

- [ ] Run `make test` - all tests pass
- [ ] Run `make lint` - no linting errors
- [ ] Verify exception handler never raises secondary exceptions

---

## Phase 4: Hardening (P2 - Medium Priority)

### Task 4.1: Broaden Flash Exception Handling

**File**: `src/py/litestar_vite/inertia/exception_handler.py`

**Modify** flash() try/except:
- [ ] Catch `Exception` instead of specific types
- [ ] Log with `exc_info=True` for debugging

**Before**:
```python
except (AttributeError, ImproperlyConfiguredException):
```

**After**:
```python
except Exception:
    request.logger.warning("Unable to set flash message", exc_info=True)
```

### Task 4.2: Add X-Inertia Header to Exception Responses

**File**: `src/py/litestar_vite/inertia/exception_handler.py`

- [ ] Add `X-Inertia: true` header to `InertiaResponse` returns
- [ ] Verify Inertia client receives JSON, not HTML

### Task 4.3: Safe __cause__ Handling

**File**: `src/py/litestar_vite/inertia/exception_handler.py`

**Modify** line ~87:
- [ ] Check if `__cause__` is None before converting to string

**Before**:
```python
detail=str(exc.__cause__)
```

**After**:
```python
detail=str(exc.__cause__) if exc.__cause__ else str(exc)
```

### Task 4.4: Validate URL Scheme in InertiaRedirect

**File**: `src/py/litestar_vite/inertia/response.py`

**Modify** `InertiaRedirect.__init__`:
- [ ] Validate `redirect_to` with `_get_safe_redirect_url()`
- [ ] Ensure scheme replacement preserves same-origin

### Task 4.5: Hardening Tests

- [ ] Test: Flash failure doesn't crash handler
- [ ] Test: Exception response includes X-Inertia header
- [ ] Test: None __cause__ handled gracefully

### Phase 4 Verification

- [ ] Run `make test` - all tests pass
- [ ] Run `make lint` - no linting errors
- [ ] All edge cases covered

---

## Phase 5: PR Preparation

### Task 5.1: Close GitHub Issues

When PR is ready:
- [ ] Verify issue #122 is already fixed (link to commit)
- [ ] Verify issue #123 is fixed by Task 2.1, 2.2
- [ ] Verify issue #124 is fixed by Task 3.1
- [ ] Verify issue #125 is fixed by Task 3.2
- [ ] Verify issue #126 is fixed by Task 2.3

### Task 5.2: PR Description

Create PR with:
- [ ] Summary of all fixes
- [ ] Link to each closed issue
- [ ] Test plan
- [ ] Security notes

### Task 5.3: Quality Gate

- [ ] `make test` passes
- [ ] `make lint` passes
- [ ] `make type-check` passes
- [ ] 90%+ coverage for modified files
- [ ] No security vulnerabilities

---

## Progress Tracking

| Phase | Status | Completion |
|-------|--------|------------|
| Phase 1: Issue #122 | ✅ Complete | 100% |
| Phase 2: Security (P0) | ❌ Not Started | 0% |
| Phase 3: Robustness (P1) | ❌ Not Started | 0% |
| Phase 4: Hardening (P2) | ❌ Not Started | 0% |
| Phase 5: PR | ❌ Not Started | 0% |

---

## Quick Reference

### Files to Modify

1. `src/py/litestar_vite/inertia/response.py`
   - Add `_get_safe_redirect_url()`
   - Fix `InertiaBack`, `InertiaRedirect`, `InertiaExternalRedirect`

2. `src/py/litestar_vite/inertia/exception_handler.py`
   - Type-safe extras
   - Plugin null check
   - Broader exception handling
   - X-Inertia header
   - Safe __cause__

### New Test Files

1. `src/py/tests/unit/inertia/test_exception_handler.py` (NEW)
   - Edge case tests for exception handling

2. `src/py/tests/unit/inertia/test_response.py` (EXTEND)
   - Security tests for redirect validation
