# PRD: Inertia Protocol Compliance

## Overview
- **Slug**: inertia-protocol-compliance
- **Created**: 2025-12-06
- **Status**: Draft
- **Priority**: P0 (Critical)
- **Consensus Sources**: Gemini 3 Pro (9/10 confidence), GPT 5.1 (8/10 confidence)

## Problem Statement

The current Inertia.js integration in litestar-vite has several protocol compliance issues that prevent proper asset versioning, break client-side refresh behavior, and leave v2 features incomplete. These issues were identified through a comprehensive multi-model consensus review against the official Inertia.js protocol specification (https://inertiajs.com/the-protocol).

### Critical Issues Identified

1. **Version Mismatch Logic Never Fires**: The middleware creates a plain `Request` instead of `InertiaRequest`, so `is_inertia` is always `None` and version mismatch detection is effectively disabled.

2. **Wrong Response for Version Mismatch**: When version mismatch is detected, the code returns `InertiaRedirect` (303/307) instead of `InertiaExternalRedirect` (409 + X-Inertia-Location) as required by the Inertia protocol.

3. **Missing X-Inertia-Version Response Header**: Responses do not include the `X-Inertia-Version` header. The client cannot detect version changes without this header being sent on every Inertia response.

4. **Incomplete V2 Features**: History encryption, infinite scroll, and partial reload filtering are only partially implemented.

5. **DX Inconsistencies**: The `lazy()` helper conflates static and deferred semantics, differing from Laravel's patterns.

## Goals

### P0 - Critical (Must Fix)
1. Fix middleware to use `InertiaRequest` so version mismatch detection actually works
2. Change version mismatch response from `InertiaRedirect` to `InertiaExternalRedirect` (409)
3. Add `X-Inertia-Version` header to all Inertia responses

### P1 - High Priority (Complete V2 Support)
4. Add `encrypt_history` and `clear_history` arguments to `InertiaResponse`
5. Wire `merge_intent` header to response logic for infinite scroll
6. Implement `scroll_props` helper for infinite scroll configuration
7. Improve partial reload filtering to filter all props by key, not just lazy props

### P2 - Medium Priority (DX Polish)
8. Improve `lazy()` documentation (keep static value support - Pythonic DX enhancement)
9. Add `only()` / `except()` helpers for explicit prop filtering
10. Make component option keys configurable via `InertiaConfig` (remove hardcoded keys)
11. Document BlockingPortal behavior for type encoders

### P1.5 - Pagination Integration ✅ (NEW - Completed 2025-12-07)
12. Auto-unwrap pagination containers (`OffsetPagination`, `ClassicPagination`) in props
13. Opt-in infinite scroll support via `infinite_scroll=True` route opt
14. Support direct `OffsetPagination` returns with automatic `items` key assignment
15. (Pending) Route-level `key` opt to customize prop key name for direct pagination returns

## Non-Goals

- Redesigning Litestar's response pipeline for async rendering
- Removing the BlockingPortal pattern (it's the correct architectural solution)
- Breaking changes to the core `InertiaResponse` API beyond additive parameters
- Frontend JavaScript changes (this is backend protocol compliance only)

## Acceptance Criteria

### P0 - Critical
- [ ] Version mismatch detection fires correctly for Inertia XHR requests
- [ ] Version mismatch returns HTTP 409 with `X-Inertia-Location` header
- [ ] All Inertia JSON responses include `X-Inertia-Version` header
- [ ] All Inertia HTML responses include `X-Inertia-Version` header
- [ ] Existing tests continue to pass
- [ ] New tests cover version mismatch scenarios

### P1 - V2 Features
- [ ] `InertiaResponse(encrypt_history=True)` sets `encryptHistory: true` in page props
- [ ] `InertiaResponse(clear_history=True)` sets `clearHistory: true` in page props
- [ ] `merge_intent` header value is accessible and used in response building
- [ ] `scroll_props()` helper creates proper `ScrollPropsConfig` in page response
- [ ] Partial reloads only return requested props (not all non-lazy props)

### P2 - DX Polish
- [ ] `lazy()` docstring improved with bandwidth vs CPU optimization guidance
- [ ] `only(*keys)` helper filters props to specified keys
- [ ] `except_(*keys)` helper excludes specified props
- [ ] Component option keys are configurable via `InertiaConfig.component_opt_keys`
- [ ] Documentation updated for all changes

## Technical Approach

### Architecture

The changes affect the Inertia module (`src/py/litestar_vite/inertia/`) with minimal impact on the core Vite integration. All changes follow existing patterns and maintain backward compatibility where possible.

### Affected Files

#### P0 - Critical Fixes

| File | Changes |
|------|---------|
| `src/py/litestar_vite/inertia/middleware.py` | Use `InertiaRequest` instead of `Request`; return `InertiaExternalRedirect` on version mismatch |
| `src/py/litestar_vite/inertia/response.py` | Add `X-Inertia-Version` header to `get_headers()` call in `to_asgi_response()` |
| `src/py/litestar_vite/inertia/_utils.py` | Ensure `get_version_header()` is used in response header construction |
| `examples/react-inertia/index.html` | Fix template variable: `page` → `inertia` (GitHub #121) |

#### P1 - V2 Features

| File | Changes |
|------|---------|
| `src/py/litestar_vite/inertia/response.py` | Add `encrypt_history`, `clear_history` args to `InertiaResponse.__init__`; wire to `PageProps` |
| `src/py/litestar_vite/inertia/helpers.py` | Add `scroll_props()` helper; improve `should_render()` to accept prop keys for all props |
| `src/py/litestar_vite/inertia/types.py` | Ensure `ScrollPropsConfig` is properly integrated |

#### P2 - DX Polish

| File | Changes |
|------|---------|
| `src/py/litestar_vite/inertia/helpers.py` | Refactor `lazy()` to callable-only; add `only()` and `except_()` helpers |
| `src/py/litestar_vite/inertia/request.py` | Make `_get_route_component()` use configurable keys from `InertiaConfig` |
| `src/py/litestar_vite/inertia/config.py` | Add `component_opt_keys` configuration option |

### API Changes

#### New `InertiaResponse` Parameters

```python
class InertiaResponse(Response[T]):
    def __init__(
        self,
        content: T,
        *,
        # Existing parameters...
        encrypt_history: bool = False,  # NEW: Enable history encryption
        clear_history: bool = False,    # NEW: Clear encrypted history
    ) -> None:
```

#### New Helper Functions

```python
def scroll_props(
    page_name: str = "page",
    current_page: int = 1,
    previous_page: int | None = None,
    next_page: int | None = None,
) -> ScrollPropsConfig:
    """Create scroll props configuration for infinite scroll."""
    ...

def only(*keys: str) -> PropFilter:
    """Filter response to only include specified props."""
    ...

def except_(*keys: str) -> PropFilter:
    """Filter response to exclude specified props."""
    ...
```

#### `lazy()` Behavior (No Breaking Change)

**Decision**: Keep static value support as a Pythonic DX enhancement.

Per Gemini 3 Pro consultation, the Inertia protocol is agnostic to server implementation. Supporting both static values and callables provides better DX without violating the protocol.

```python
# Static value - optimizes BANDWIDTH only
# Value is computed eagerly, but only sent on partial reload
lazy("key", static_value)

# Callable - optimizes BANDWIDTH + CPU
# Value is computed only when actually needed
lazy("key", lambda: expensive_computation())

# v2 deferred props with grouping - use defer() instead
defer("key", lambda: compute_value(), group="default")
```

**Documentation improvement**: Clarify the "False Lazy" pitfall:
```python
# WRONG - expensive_fn() runs immediately, result passed to lazy()
lazy("key", expensive_fn())

# CORRECT - expensive_fn is passed as callable, runs only when needed
lazy("key", expensive_fn)
```

---

## Deep Dive: History Encryption (P1)

### How History Encryption Works

History encryption is an **opt-in security feature** that prevents users from viewing privileged information in browser history after logout. The encryption happens **client-side** using the browser's built-in `window.crypto.subtle` API.

**Key Insight**: The server's role is simple - just tell the client whether to encrypt and when to clear. All cryptographic operations happen in the browser.

### Protocol Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                        SERVER SIDE                               │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  1. Route handler returns InertiaResponse(encrypt_history=True)  │
│                           │                                      │
│                           ▼                                      │
│  2. Response includes: { "encryptHistory": true, ... }           │
│                                                                  │
│  3. On logout: clear_history() sets session flag                 │
│                           │                                      │
│                           ▼                                      │
│  4. Next response includes: { "clearHistory": true, ... }        │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                        CLIENT SIDE                               │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  5. When encryptHistory=true:                                    │
│     - Generate encryption key (stored in sessionStorage)         │
│     - Encrypt page data before pushing to history.state          │
│                                                                  │
│  6. When navigating back:                                        │
│     - Decrypt data using key from sessionStorage                 │
│     - If decryption fails → make fresh server request            │
│                                                                  │
│  7. When clearHistory=true:                                      │
│     - Delete old encryption key from sessionStorage              │
│     - Generate new key (invalidates all previous history)        │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Server-Side Implementation Requirements

#### 1. Response-Level Encryption Flag

```python
# Per-response encryption
@get("/dashboard", component="Dashboard")
async def dashboard(request: InertiaRequest) -> InertiaResponse:
    return InertiaResponse(
        {"sensitive_data": "..."},
        encrypt_history=True,  # This page's history will be encrypted
    )
```

#### 2. Global Encryption via Config

```python
# In ViteConfig
ViteConfig(
    inertia=InertiaConfig(
        encrypt_history=True,  # All Inertia responses encrypt by default
    )
)

# Opt-out per response
@get("/public", component="Public")
async def public_page(request: InertiaRequest) -> InertiaResponse:
    return InertiaResponse(
        {"public_data": "..."},
        encrypt_history=False,  # Override: don't encrypt this page
    )
```

#### 3. Clear History Helper (Session-Based)

```python
from litestar_vite.inertia import clear_history

@post("/logout")
async def logout(request: InertiaRequest) -> InertiaRedirect:
    # Clear session, logout user, etc.
    request.session.clear()

    # Mark that next response should tell client to clear history
    clear_history(request)

    return InertiaRedirect(request, redirect_to="/login")
```

#### 4. Middleware for Route Groups (Optional)

```python
from litestar_vite.inertia import EncryptHistoryMiddleware

# Apply to specific routes
app = Litestar(
    route_handlers=[...],
    middleware=[
        DefineMiddleware(EncryptHistoryMiddleware, path="/admin/*"),
    ],
)
```

### Implementation Details

#### Session Key for Clear History

Following Laravel's pattern, `clear_history()` stores a flag in the session:

```python
def clear_history(connection: "ASGIConnection[Any, Any, Any, Any]") -> None:
    """Mark that the next response should clear client history encryption keys.

    This should be called during logout to invalidate any encrypted history
    states that may contain sensitive information.

    Args:
        connection: The ASGI connection (Request).
    """
    try:
        connection.session["_inertia_clear_history"] = True
    except (AttributeError, ImproperlyConfiguredException):
        connection.logger.warning("Unable to set clear_history flag - session not available")
```

#### Response Building Integration

In `_build_page_props()` or `to_asgi_response()`:

```python
# Check for session-based clear_history flag (consumed on read)
clear_history_flag = False
try:
    clear_history_flag = request.session.pop("_inertia_clear_history", False)
except (AttributeError, ImproperlyConfiguredException):
    pass

# Determine encrypt_history value
# Priority: response param > config default > False
encrypt_history_value = self.encrypt_history
if encrypt_history_value is None:
    encrypt_history_value = inertia_plugin.config.encrypt_history

return PageProps(
    component=...,
    props=...,
    encrypt_history=encrypt_history_value,
    clear_history=clear_history_flag,
    ...
)
```

### Requirements & Constraints

1. **HTTPS Required**: `window.crypto.subtle` only works in secure contexts
2. **Session Required**: `clear_history()` needs session middleware
3. **No Server-Side Encryption**: All crypto happens client-side
4. **One-Way Clear**: Once `clearHistory=true` is sent, old keys are gone

### Files Affected

| File | Changes |
|------|---------|
| `src/py/litestar_vite/inertia/response.py` | Add `encrypt_history` param to `InertiaResponse.__init__` |
| `src/py/litestar_vite/inertia/helpers.py` | Add `clear_history()` function |
| `src/py/litestar_vite/inertia/config.py` | Add `encrypt_history` to `InertiaConfig` |
| `src/py/litestar_vite/inertia/types.py` | Ensure `PageProps` fields are used |
| `src/py/litestar_vite/inertia/__init__.py` | Export `clear_history` |
| `src/py/litestar_vite/inertia/middleware.py` | Add optional `EncryptHistoryMiddleware` |

### References

- [Inertia.js History Encryption](https://inertiajs.com/history-encryption)
- [Laravel ResponseFactory.php](https://github.com/inertiajs/inertia-laravel/blob/master/src/ResponseFactory.php)
- [History Encryption with Inertia (Codecourse)](https://codecourse.com/articles/history-encryption-with-inertia)

---

## Deep Dive: Pagination Integration (P1.5) ✅

### Problem Statement

When using Advanced Alchemy's `to_schema()` pattern with Inertia routes, developers had to manually extract items from pagination containers. The goal is to write pagination once and have it work for both API and Inertia clients seamlessly.

### Solution: Automatic Pagination Container Unwrapping

The response now automatically detects and unwraps pagination containers (`OffsetPagination`, `ClassicPagination`) in props:

1. **Items Extraction**: Pagination containers are unwrapped to just their `items` array
2. **Scroll Props Calculation**: When `infinite_scroll=True` on the route, `scroll_props` are calculated from pagination metadata
3. **Direct Return Support**: Routes can return `OffsetPagination` directly (uses `"items"` as default key)

### Usage Patterns

#### Pattern 1: Wrapped in Dict (Recommended - Explicit Key)

```python
@get("/users", component="Users")
async def list_users(users_service: UserService, filters: list[FilterTypes]) -> InertiaResponse:
    results, total = await users_service.list_and_count(*filters)
    return InertiaResponse({
        "users": users_service.to_schema(data=results, total=total, schema_type=User, filters=filters)
    })
```

**Props Result:** `{"users": [...items...]}`

The pagination container is automatically unwrapped - only items are sent to the client.

#### Pattern 2: Direct OffsetPagination Return (Simpler Route)

```python
@get("/users", component="Users")
async def list_users(users_service: UserService, filters: list[FilterTypes]) -> OffsetPagination[User]:
    results, total = await users_service.list_and_count(*filters)
    return users_service.to_schema(data=results, total=total, schema_type=User, filters=filters)
```

**Props Result:** `{"items": [...items...]}`

When returning `OffsetPagination` directly (not wrapped in a dict), it uses `"items"` as the key.

#### Pattern 3: With Infinite Scroll

```python
@get("/posts", component="Posts", infinite_scroll=True)
async def list_posts(posts_service: PostService, filters: list[FilterTypes]) -> OffsetPagination[Post]:
    results, total = await posts_service.list_and_count(*filters)
    return posts_service.to_schema(data=results, total=total, schema_type=Post, filters=filters)
```

**Props Result:** `{"items": [...items...]}`
**Plus:** `scroll_props` with `current_page`, `next_page`, `previous_page` calculated from pagination metadata

### Implementation Details

#### Pagination Detection (`helpers.py`)

Two new functions detect and extract pagination containers:

```python
def is_pagination_container(value: Any) -> bool:
    """Detect OffsetPagination (items, limit, offset, total) or
    ClassicPagination (items, page_size, current_page, total_pages)."""
    ...

def extract_pagination_scroll_props(
    value: Any,
    page_param: str = "page",
) -> tuple[Any, ScrollPropsConfig | None]:
    """Extract items and calculate scroll props from pagination container."""
    ...
```

#### Response Integration (`response.py`)

In `_build_page_props()`:

```python
# Check if route has infinite_scroll opt enabled
route_handler = request.scope.get("route_handler")
infinite_scroll_enabled = bool(route_handler and route_handler.opt.get("infinite_scroll", False))

for key, value in list(shared_props.items()):
    if is_pagination_container(value):
        items, scroll = extract_pagination_scroll_props(value)
        shared_props[key] = items  # Replace pagination object with just items
        # Only calculate scroll_props if infinite_scroll is enabled
        if extracted_scroll_props is None and scroll is not None and infinite_scroll_enabled:
            extracted_scroll_props = scroll
```

### Supported Pagination Types

| Type | Detection | Scroll Props Calculation |
|------|-----------|--------------------------|
| Litestar `OffsetPagination` | `items`, `limit`, `offset`, `total` | `current_page = (offset // limit) + 1` |
| Litestar `ClassicPagination` | `items`, `page_size`, `current_page`, `total_pages` | Direct from `current_page`, `total_pages` |
| Advanced Alchemy `OffsetPagination` | Same as Litestar | Same as Litestar |
| Any custom type with matching attributes | Same attribute detection | Same calculation |

### Files Affected

| File | Changes |
|------|---------|
| `src/py/litestar_vite/inertia/helpers.py` | Added `is_pagination_container()` and `extract_pagination_scroll_props()` |
| `src/py/litestar_vite/inertia/response.py` | Wired pagination extraction into `_build_page_props()` |
| `src/py/tests/unit/inertia/test_types.py` | Added 17 tests for pagination detection and extraction |

### Key Design Decisions

1. **Unwrapping is Always Done**: Pagination containers are always unwrapped to items - this keeps the frontend simple
2. **Scroll Props are Opt-In**: Only calculated when `infinite_scroll=True` on the route - regular pagination doesn't need scroll props
3. **Default Key is `items`**: When returning pagination directly, uses sensible default
4. **Pending: Custom Key via Route Opt**: Allow `key="users"` on route to customize the prop key name

---

## Testing Strategy

### Unit Tests

1. **Middleware Tests** (`test_middleware.py`):
   - Test version mismatch detection with `InertiaRequest`
   - Test 409 response with `X-Inertia-Location` header
   - Test version match (no redirect)
   - Test non-Inertia requests bypass middleware

2. **Response Tests** (`test_response.py`):
   - Test `X-Inertia-Version` header in JSON responses
   - Test `X-Inertia-Version` header in HTML responses
   - Test `encrypt_history` parameter
   - Test `clear_history` parameter
   - Test partial reload filtering for all props

3. **Helper Tests** (`test_helpers.py`):
   - Test `scroll_props()` helper
   - Test `only()` and `except_()` filters
   - Test `lazy()` deprecation warning for static values

### Integration Tests

1. **Full Request Cycle**:
   - Test initial page load → subsequent XHR with version header
   - Test version mismatch → 409 → client hard refresh
   - Test partial reload with `only` filter

2. **E2E Tests** (if applicable):
   - Test with real Inertia.js client adapter

### Edge Cases

- Version header with special characters
- Empty partial keys
- Conflicting `encrypt_history` and `clear_history`
- Nested lazy props in partial reload

## Research Questions

- [x] Confirm Inertia.js v2 protocol specification for all headers
- [x] Verify Laravel adapter behavior for `lazy()` semantics
- [ ] Check if `X-Inertia-Version` should be in HTML meta tag as well as response header
- [ ] Determine if `scroll_props` should be automatically populated from query params

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Breaking existing `lazy()` usage | Medium | Add deprecation warning first; full removal in next major version |
| Performance impact of key-based filtering | Low | Only applies during partial reloads; minimal overhead |
| Middleware order issues | Medium | Document required middleware ordering; add runtime checks |
| Type encoder portal overhead | Low | Document behavior; consider lazy initialization |

## Implementation Order

### Phase 1: Critical Fixes (P0)
1. Fix middleware request type (`InertiaRequest`)
2. Change version mismatch to 409 response
3. Add `X-Inertia-Version` response header
4. Add comprehensive tests

### Phase 2: V2 Feature Completion (P1)
5. Add `encrypt_history`/`clear_history` to `InertiaResponse`
6. Wire `merge_intent` header
7. Implement `scroll_props()` helper
8. Improve partial reload filtering

### Phase 3: DX Polish (P2)
9. Add deprecation to `lazy()` for static values
10. Add `only()`/`except_()` helpers
11. Make component keys configurable
12. Update documentation

## Dependencies

- No external dependencies required
- All changes are internal to `litestar_vite.inertia` module
- Tests use existing pytest + pytest-asyncio infrastructure

## Success Metrics

- All Inertia protocol compliance tests pass
- No regressions in existing test suite
- Asset versioning works end-to-end with standard Inertia.js client
- Documentation is updated with new features

## References

- [Inertia.js Protocol Specification](https://inertiajs.com/the-protocol)
- [Laravel Inertia Adapter](https://github.com/inertiajs/inertia-laravel)
- [Inertia.js v2 Release Notes](https://inertiajs.com/releases)
- Consensus review from Gemini 3 Pro and GPT 5.1 (2025-12-06)
