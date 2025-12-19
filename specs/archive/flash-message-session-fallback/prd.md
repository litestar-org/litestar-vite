# PRD: Flash Message Session Fallback

## Overview
- **Slug**: flash-message-session-fallback
- **Created**: 2025-12-19
- **Status**: Implemented (Pending Tests)
- **Issue**: https://github.com/litestar-org/litestar-vite/issues/164

## Problem Statement

When an unauthenticated user tries to access a protected route, they are redirected to the login page but **no error message is displayed**. The user sees a blank login form with no indication of why they were redirected.

### Root Cause

The `create_inertia_exception_response` function tries to flash an error message when handling `NotAuthorizedException`. However, for unauthenticated users, **no session exists yet**, so the flash fails silently.

The `flash()` function was catching the exception internally and logging a warning, but not re-raising it. Since no exception propagated, the exception handler incorrectly assumed the flash succeeded and redirected without any error indication.

### Impact

- **User confusion**: Users redirected to login don't know why
- **Poor UX**: No feedback on authentication failures
- **Silent failures**: Developers may not notice the issue in logs (warning level)

## Goals

1. Ensure error messages are always displayed when users are redirected to login
2. Provide a fallback mechanism when session-based flash messages fail
3. Maintain backward compatibility with existing session-based flash behavior
4. Change logging from `warning` to `debug` level (expected behavior, not an error)

## Non-Goals

- Changing the flash message storage mechanism
- Supporting multiple fallback methods (query param is sufficient)
- Modifying frontend components (documented as recommendation)

## Acceptance Criteria

- [x] `flash()` returns `bool` indicating success/failure
- [x] Exception handler uses query parameter fallback when flash fails
- [x] Logging level changed from `warning` to `debug` for missing session
- [x] Unit tests for `flash()` return value (success and failure cases)
- [x] Unit tests for query parameter fallback in unauthorized redirects
- [x] Documentation for frontend handling of `error` query parameter

## Technical Approach

### Architecture

The fix introduces a two-tier fallback mechanism:

```
┌─────────────────────────────────────────────────────────────┐
│  NotAuthorizedException raised                              │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│  Try flash(request, detail, "error")                        │
└─────────────────────────────────────────────────────────────┘
                          │
           ┌──────────────┴──────────────┐
           │                             │
     flash_succeeded=True          flash_succeeded=False
           │                             │
           ▼                             ▼
┌─────────────────────┐    ┌─────────────────────────────────┐
│ Redirect: /login    │    │ Redirect: /login?error=message  │
│ (flash in session)  │    │ (fallback query param)          │
└─────────────────────┘    └─────────────────────────────────┘
```

### Affected Files

- [src/py/litestar_vite/inertia/helpers.py](src/py/litestar_vite/inertia/helpers.py) - `flash()` returns `bool`
- [src/py/litestar_vite/inertia/exception_handler.py](src/py/litestar_vite/inertia/exception_handler.py) - Query param fallback

### API Changes

All three session helper functions now return `bool` indicating success/failure:

#### `flash()` function signature change

**Before:**
```python
def flash(connection: ASGIConnection, message: str, category: str = "info") -> None:
```

**After:**
```python
def flash(connection: ASGIConnection, message: str, category: str = "info") -> bool:
```

#### `share()` function signature change

**Before:**
```python
def share(connection: ASGIConnection, key: str, value: Any) -> None:
```

**After:**
```python
def share(connection: ASGIConnection, key: str, value: Any) -> bool:
```

#### `error()` function signature change

**Before:**
```python
def error(connection: ASGIConnection, key: str, message: str) -> None:
```

**After:**
```python
def error(connection: ASGIConnection, key: str, message: str) -> bool:
```

All functions return `True` if the operation succeeded, `False` otherwise.

#### Redirect URL change (when flash fails)

**Before:**
```
Location: /login
```

**After (when no session):**
```
Location: /login?error=User%20not%20authenticated
```

## Testing Strategy

### Unit Tests

1. **`flash()` return value tests** ([test_helpers.py](src/py/tests/unit/inertia/test_helpers.py))
   - Test `flash()` returns `True` with valid session
   - Test `flash()` returns `False` without session (mocked)

2. **Exception handler query param fallback** ([test_response.py](src/py/tests/unit/inertia/test_response.py))
   - Test redirect includes query param when flash fails (no session middleware)
   - Test redirect does NOT include query param when flash succeeds (with session)
   - Test URL encoding of special characters in error message
   - Test redirect with existing query params preserves them

### Integration Tests

- Test full flow: protected route → redirect to login with error param → login page displays error

### Edge Cases

- Empty detail message (should not add query param)
- Special characters in error message (URL encoding)
- Redirect URL already has query params (append with `&`)
- Login page is already current path (InertiaBack, no redirect)

## Frontend Guidance

Frontend applications should read the `error` query parameter as a fallback when flash messages are empty:

### React Example

```tsx
import { usePage } from '@inertiajs/react'
import { useMemo } from 'react'

function Login() {
  const { url, flash } = usePage().props

  const errorMessage = useMemo(() => {
    // v2.3+ protocol: flash is top-level
    if (flash?.error?.length) {
      return flash.error[0]
    }
    // Fallback: check query param
    try {
      const urlObj = new URL(url, window.location.origin)
      return urlObj.searchParams.get('error')
    } catch {
      return null
    }
  }, [url, flash])

  return (
    <div>
      {errorMessage && <div className="error">{errorMessage}</div>}
      {/* login form */}
    </div>
  )
}
```

### Vue Example

```vue
<script setup>
import { usePage } from '@inertiajs/vue3'
import { computed } from 'vue'

const page = usePage()

const errorMessage = computed(() => {
  if (page.props.flash?.error?.length) {
    return page.props.flash.error[0]
  }
  try {
    const urlObj = new URL(page.props.url, window.location.origin)
    return urlObj.searchParams.get('error')
  } catch {
    return null
  }
})
</script>
```

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Breaking change in `flash()` return type | Low | Return value was `None`, now `bool`. Callers ignoring return are unaffected. |
| Query param visible in URL | Low | Standard practice; cleared on subsequent navigation |
| URL length limits | Low | Error messages are typically short; browser limits ~2KB are sufficient |

## Implementation Status

### Completed

- [x] `flash()` returns `bool` indicating success/failure
- [x] Exception handler checks `flash_succeeded` return value
- [x] Query parameter fallback for unauthorized redirects when flash fails
- [x] Logging level changed from `warning` to `debug`
- [x] URL encoding using `urllib.parse.quote()`
- [x] Preserves existing query params in redirect URL
- [x] Unit tests for `flash()` return value (3 tests)
- [x] Unit tests for query parameter fallback (4 tests)
- [x] Documentation (this PRD)

### Test Coverage

| Test File | New Tests | Total |
|-----------|-----------|-------|
| `test_helpers.py` | 7 | 28 |
| `test_response.py` | 4 | 74 |

All 98 tests in affected modules pass.

---

## Completion Metadata

- **Completed**: 2025-12-19
- **Status**: Completed
- **Related Issue**: https://github.com/litestar-org/litestar-vite/issues/164

### Lessons Learned

- Session helpers should return success indicators to allow fallback mechanisms
- Debug-level logging is appropriate for expected failures (like unauthenticated users)
- Query parameter fallbacks provide graceful degradation for session-less scenarios

### Files Modified

- `src/py/litestar_vite/inertia/helpers.py` - `share()`, `error()`, `flash()` return `bool`
- `src/py/litestar_vite/inertia/exception_handler.py` - Query param fallback for auth redirects
- `src/py/tests/unit/inertia/test_helpers.py` - 7 new tests for helper return values
- `src/py/tests/unit/inertia/test_response.py` - 4 new tests for query param fallback
