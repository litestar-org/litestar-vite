# Implementation Plan: Inertia Defensive Hardening

## Executive Summary

This plan addresses 5 GitHub issues (#122-#126) related to security vulnerabilities and robustness in the Inertia integration. **Issue #122 is already fixed** in the current branch. The remaining 4 issues require implementation.

## Issue Analysis

| Issue | Title | Severity | Current Status | Action Required |
|-------|-------|----------|----------------|-----------------|
| #122 | HTTPException converted to 500 | High | ✅ **FIXED** | Close issue |
| #123 | Open redirect in InertiaBack | **Critical** | ❌ Not Fixed | Implement safe URL validation |
| #124 | IndexError on empty extras | High | ❌ Not Fixed | Add type-safe handling |
| #125 | InertiaPlugin lookup crashes | Medium | ❌ Not Fixed | Add null check |
| #126 | Cookie leak in redirects | High | ❌ Not Fixed | Remove cookie echo |

## Implementation Phases

### Phase 1: Security Fixes (P0 - Critical)

**Files to modify:**
- `src/py/litestar_vite/inertia/response.py`

**Changes:**
1. Add `_get_safe_redirect_url()` helper function
2. Update `InertiaBack` to validate Referer header
3. Update `InertiaRedirect` to validate redirect_to
4. Remove `cookies=request.cookies` from all redirect classes

**Tests:**
- Open redirect prevention tests
- Cookie leak prevention tests

### Phase 2: Robustness Fixes (P1 - High)

**Files to modify:**
- `src/py/litestar_vite/inertia/exception_handler.py`

**Changes:**
1. Type-safe handling of `extras` attribute
2. Add null check for InertiaPlugin

**Tests:**
- Edge case tests for exception handler

### Phase 3: Hardening (P2 - Medium)

**Files to modify:**
- `src/py/litestar_vite/inertia/exception_handler.py`

**Changes:**
1. Broaden flash() exception handling
2. Add X-Inertia header to exception responses
3. Safe __cause__ handling

### Phase 4: PR Preparation

1. Verify all tests pass
2. Update PR description to link all closed issues
3. Request review

## Detailed PRD

See: [prd.md](./prd.md)

## Task Breakdown

See: [tasks.md](./tasks.md)

## Recovery Guide

See: [recovery.md](./recovery.md)

## Acceptance Criteria

- [ ] Issue #123: InertiaBack rejects cross-origin Referer
- [ ] Issue #124: Exception handler handles empty/invalid extras
- [ ] Issue #125: Missing InertiaPlugin doesn't crash
- [ ] Issue #126: No Set-Cookie headers in redirect responses
- [ ] All existing tests pass
- [ ] 90%+ coverage for modified code
