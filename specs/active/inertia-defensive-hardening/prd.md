# PRD: Inertia Defensive Hardening

## Overview
- **Slug**: inertia-defensive-hardening
- **Created**: 2025-12-07
- **Status**: In Progress
- **Priority**: P0 (Critical - Security Issues)
- **Parent PRD**: inertia-protocol-compliance
- **GitHub Issues**: #122, #123, #124, #125, #126

## Problem Statement

The Inertia integration in litestar-vite has several defensive programming and security vulnerabilities identified in a comprehensive code audit. While the protocol compliance work (version mismatch, V2 features) has been addressed, the **exception handling and redirect logic** contain critical issues that must be fixed before production use.

### GitHub Issues Summary

| Issue | Title | Severity | Status |
|-------|-------|----------|--------|
| [#122](https://github.com/litestar-org/litestar-vite/issues/122) | HTTPException converted to 500 for non-Inertia requests | High | ✅ **FIXED** |
| [#123](https://github.com/litestar-org/litestar-vite/issues/123) | Security: Open redirect vulnerability in InertiaBack via Referer header | **Critical (Security)** | ❌ NOT FIXED |
| [#124](https://github.com/litestar-org/litestar-vite/issues/124) | Exception handler crashes on empty extras list (IndexError) | High | ❌ NOT FIXED |
| [#125](https://github.com/litestar-org/litestar-vite/issues/125) | InertiaPlugin lookup crashes if plugin not registered | Medium | ❌ NOT FIXED |
| [#126](https://github.com/litestar-org/litestar-vite/issues/126) | Request cookies incorrectly passed to redirect responses | **High (Security)** | ❌ NOT FIXED |

### Additional Issues (Not Filed as GitHub Issues)

| Issue | Location | Severity |
|-------|----------|----------|
| Flash function insufficient exception handling | exception_handler.py:111-114 | Medium |
| Missing X-Inertia header on exception responses | exception_handler.py | Medium |
| Unsafe scheme in URL construction | response.py:527 | Medium |
| Handle None `__cause__` attribute | exception_handler.py:87 | Low |
| Fragile validation error regex | exception_handler.py:119 | Low |

## Root Cause Analysis

All issues stem from **insufficient defensive programming in the exception path**. Exception handlers must be bulletproof because:

1. If an exception handler crashes, it masks the original error
2. Users see generic 500 responses instead of helpful error messages
3. Security vulnerabilities in error paths are often overlooked
4. Debugging becomes much harder when exception handling fails

## Goals

### P0 - Critical (Security Fixes)
1. **Fix #123**: Implement safe redirect URL validation for `InertiaBack` and `InertiaRedirect`
2. **Fix #126**: Remove `cookies=request.cookies` from all redirect classes

### P1 - High Priority (Robustness Fixes)
3. **Fix #124**: Add type-safe handling for `extras` attribute
4. **Fix #125**: Add null check before accessing `InertiaPlugin.config`

### P2 - Medium Priority (Hardening)
5. Broaden exception handling in `flash()` calls
6. Add `X-Inertia: true` header to exception responses
7. Validate URL schemes (whitelist http/https only)
8. Handle `None` `__cause__` attribute gracefully

## Non-Goals

- Redesigning the exception handler architecture
- Breaking changes to public API
- Removing regex-based validation error parsing (would require significant refactoring)

## Acceptance Criteria

### P0 - Security
- [ ] `InertiaBack` validates Referer header is same-origin before redirect
- [ ] `InertiaRedirect` validates redirect target is safe (no open redirect)
- [ ] No redirect response contains `Set-Cookie` headers from request cookies
- [ ] Security tests verify open redirect prevention
- [ ] Security tests verify no cookie echo in redirects

### P1 - Robustness
- [ ] Exception handler does not crash when `extras` is empty string, empty list, or non-dict
- [ ] Exception handler gracefully handles missing InertiaPlugin
- [ ] All exception handler code paths are tested

### P2 - Hardening
- [ ] Flash errors don't crash exception handler
- [ ] Exception responses include required Inertia headers
- [ ] URL schemes are validated in redirect construction

## Technical Approach

### Issue #123: Open Redirect Vulnerability (CRITICAL)

**Problem**: `InertiaBack` uses Referer header without validation, allowing attackers to redirect users to malicious sites.

**Current Code** (`response.py:548`):
```python
class InertiaBack(Redirect):
    def __init__(self, request: "Request[Any, Any, Any]", **kwargs: "Any") -> None:
        super().__init__(
            path=request.headers.get("Referer", str(request.base_url)),  # VULNERABLE
            ...
        )
```

**Fix**: Replace existing redirect logic with `_get_redirect_url()`:
```python
def _get_redirect_url(request: "Request[Any, Any, Any]", url: str | None) -> str:
    """Get a validated redirect URL, ensuring same-origin to prevent open redirect attacks.

    Args:
        request: The request object for base URL comparison.
        url: The URL to validate (e.g., Referer header or redirect_to parameter).

    Returns:
        The validated URL, or base_url if validation fails or URL is invalid.
    """
    if not url:
        return str(request.base_url)

    parsed = urlparse(url)
    base = urlparse(str(request.base_url))

    # Allow relative URLs (no scheme or netloc)
    if not parsed.scheme and not parsed.netloc:
        return url

    # Validate same-origin for absolute URLs
    if parsed.netloc == base.netloc and parsed.scheme in ('http', 'https'):
        return url

    return str(request.base_url)
```

**Apply to**:
- `InertiaBack.__init__` - validate Referer header
- `InertiaRedirect.__init__` - validate redirect_to parameter

---

### Issue #124: IndexError on Empty Extras (HIGH)

**Problem**: Exception handler assumes `extras` is a list with dict items.

**Current Code** (`exception_handler.py:115-122`):
```python
extras = getattr(exc, "extra", "")  # Defaults to empty string!
if extras and len(extras) >= 1:
    message = extras[0]  # IndexError if extras is []
    default_field = f"root.{message.get('key')}"  # AttributeError if not dict
```

**Fix**: Type-safe handling:
```python
extras = getattr(exc, "extra", None)
if extras and isinstance(extras, (list, tuple)) and len(extras) >= 1:
    message = extras[0]
    if isinstance(message, dict):
        key_value = message.get("key")
        default_field = f"root.{key_value}" if key_value is not None else "root"
        error_detail = cast("str", message.get("message", detail))
        # ... continue with safe operations
```

---

### Issue #125: InertiaPlugin None Check (MEDIUM)

**Problem**: `cast()` doesn't validate at runtime; if plugin not registered, code crashes.

**Current Code** (`exception_handler.py:107`):
```python
inertia_plugin = cast("InertiaPlugin", request.app.plugins.get("InertiaPlugin"))
# Later: inertia_plugin.config.redirect_unauthorized_to  # AttributeError!
```

**Fix**: Add guard clause:
```python
inertia_plugin = request.app.plugins.get("InertiaPlugin")
if inertia_plugin is None:
    # Fall back to standard response without Inertia-specific behavior
    return InertiaResponse[Any](
        media_type=preferred_type,
        content=content,
        status_code=status_code,
    )
# Now safe to access inertia_plugin.config
```

---

### Issue #126: Cookie Leak in Redirects (HIGH - Security)

**Problem**: `cookies=request.cookies` echoes incoming cookies as `Set-Cookie` headers.

**Current Code** (`response.py:509, 531, 550`):
```python
cookies=request.cookies,  # WRONG: These are request cookies, not response cookies
```

**Fix**: Remove the parameter entirely from all three classes:
- `InertiaExternalRedirect.__init__`
- `InertiaRedirect.__init__`
- `InertiaBack.__init__`

Browsers persist cookies automatically; responses should only set cookies explicitly when needed.

---

### Additional Fixes

#### Broaden Flash Exception Handling
```python
# Current (too narrow):
except (AttributeError, ImproperlyConfiguredException):
    ...

# Fixed (catch all exceptions in non-critical path):
except Exception:
    request.logger.warning("Unable to set flash message", exc_info=True)
```

#### Add X-Inertia Header to Exception Responses
```python
# When returning InertiaResponse for exceptions, include header:
headers = {"X-Inertia": "true"}
return InertiaResponse[Any](
    media_type=preferred_type,
    content=content,
    status_code=status_code,
    headers=headers,
)
```

#### Safe `__cause__` Handling
```python
# Current:
detail=str(exc.__cause__)  # Returns "None" if __cause__ is None

# Fixed:
detail=str(exc.__cause__) if exc.__cause__ else str(exc)
```

## Affected Files

| File | Changes |
|------|---------|
| `src/py/litestar_vite/inertia/response.py` | Add `_get_redirect_url()` with validation, remove `cookies=request.cookies` from redirects |
| `src/py/litestar_vite/inertia/exception_handler.py` | Type-safe extras, plugin null check, broad exception handling, X-Inertia header |
| `src/py/tests/unit/inertia/test_response.py` | Security tests for redirect validation |
| `src/py/tests/unit/inertia/test_exception_handler.py` | New test file for exception handler edge cases |

## Testing Strategy

### Security Tests
1. Open redirect prevention: Test various malicious URLs
   - `//evil.com/path` (protocol-relative)
   - `javascript:alert(1)` (scheme injection)
   - `https://evil.com` (cross-origin)
   - `https://evil.com@legitimate.com` (userinfo attack)

2. Cookie leak prevention: Verify no `Set-Cookie` headers in redirects

### Robustness Tests
1. Empty extras: `extra=[]`, `extra=""`, `extra=None`
2. Non-dict extras: `extra=["string"]`, `extra=[123]`
3. Missing plugin: App without InertiaPlugin registered
4. Missing config fields: Plugin with partial config

### Edge Cases
1. Referer header missing entirely
2. Referer header with only path (no host)
3. Exception with no `detail` or `extra` attributes

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Breaking redirect behavior | Medium | Keep fallback to base_url for invalid redirects |
| Flash messages not working | Low | Logged warning, non-blocking |
| Plugin detection too strict | Low | Graceful degradation, not crash |

## Implementation Order

### Phase 1: Security Fixes (P0)
1. Add `_get_redirect_url()` function with same-origin validation
2. Update `InertiaBack` to use `_get_redirect_url()`
3. Update `InertiaRedirect` to use `_get_redirect_url()`
4. Remove `cookies=request.cookies` from all redirects
5. Add security tests

### Phase 2: Robustness Fixes (P1)
6. Fix type-safe extras handling
7. Add InertiaPlugin null check
8. Add robustness tests

### Phase 3: Hardening (P2)
9. Broaden exception handling in flash()
10. Add X-Inertia header to exception responses
11. Safe __cause__ handling
12. Scheme validation in URL construction

### Phase 4: Verification
13. Run full test suite
14. Manual security testing
15. Close GitHub issues with PR link

## Success Metrics

- All 5 GitHub issues closed
- No security vulnerabilities in redirect handling
- Exception handler never crashes, always returns valid response
- 90%+ test coverage for modified code

## References

- [OWASP Open Redirect](https://owasp.org/www-project-web-security-testing-guide/latest/4-Web_Application_Security_Testing/11-Client-side_Testing/04-Testing_for_Client-side_URL_Redirect)
- [CWE-601: URL Redirection to Untrusted Site](https://cwe.mitre.org/data/definitions/601.html)
- [Django's is_safe_url](https://github.com/django/django/blob/main/django/utils/http.py) - Reference implementation
- [Inertia.js Protocol](https://inertiajs.com/the-protocol)
