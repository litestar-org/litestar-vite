# PRD: Inertia URL Query Parameter Preservation

## Overview
- **Slug**: inertia-url-query-params
- **Created**: 2025-12-18
- **Status**: Draft
- **Severity**: Bug (Data Loss)

## Problem Statement

When users filter a report by appending query parameters to the URL (e.g., `/reports?status=active&page=2`), refreshing the page causes those filters to be lost. The page reloads without the query parameters, forcing users to re-apply their filters.

**Root Cause**: In `InertiaResponse._build_page_props()`, the URL is set using only `request.url.path`, which excludes query parameters:

```python
# response.py line 396
url=request.url.path,  # Returns "/reports" instead of "/reports?status=active&page=2"
```

This violates the Inertia.js protocol, which specifies that the `url` property should include query parameters.

## Evidence

### 1. Inertia.js Protocol Documentation
The official [Inertia.js protocol](https://inertiajs.com/the-protocol) shows URLs should include query strings:
```json
{
  "component": "Posts",
  "props": {...},
  "url": "/posts?page=1",
  "version": "..."
}
```

### 2. Laravel Adapter Implementation
The [inertia-laravel Response.php](https://github.com/inertiajs/inertia-laravel/blob/master/src/Response.php) uses `getUrl()` which explicitly preserves query strings:
- Extracts full URL from request
- Removes scheme/host for relative URL
- Preserves query string in final URL

From the docs: "By default, the Laravel adapter resolves this using the `fullUrl()` method on the `Request` instance, but strips the scheme and host so the result is a relative URL."

### 3. Django Pattern
Django's standard pattern uses `request.get_full_path()` which returns the path WITH query parameters, not `request.path` which excludes them.

### 4. Litestar URL Object
Testing confirms Litestar's `URL` object separates these:
- `request.url.path` = `/test` (path only)
- `request.url.query` = `page=1&filter=active` (query string only)

## Goals
1. Preserve query parameters in the Inertia page object URL
2. Maintain compatibility with all existing functionality
3. Follow the same pattern as other official Inertia adapters

## Non-Goals
- Modifying how Litestar parses URLs
- Adding URL manipulation/transformation features
- Changing browser history behavior beyond fixing this bug

## Acceptance Criteria
- [ ] Query parameters are preserved in `PageProps.url` when present
- [ ] Page refresh maintains filter state via URL
- [ ] URLs without query strings work unchanged
- [ ] All existing Inertia tests pass
- [ ] New tests cover query parameter preservation

## Technical Approach

### The Fix

**File**: `src/py/litestar_vite/inertia/response.py`
**Location**: `_build_page_props()` method, line 396

**Current Code**:
```python
return PageProps[T](
    component=request.inertia.route_component,
    props=shared_props,
    version=vite_plugin.asset_loader.version_id,
    url=request.url.path,  # BUG: Missing query string
    ...
)
```

**Fixed Code**:
```python
def _get_relative_url(request: "Request[Any, Any, Any]") -> str:
    """Get relative URL including query string.

    Returns path with query parameters, e.g., "/reports?page=1&status=active".
    This matches the Inertia.js protocol expectation and other adapter implementations.
    """
    path = request.url.path
    query = request.url.query
    return f"{path}?{query}" if query else path

return PageProps[T](
    component=request.inertia.route_component,
    props=shared_props,
    version=vite_plugin.asset_loader.version_id,
    url=_get_relative_url(request),  # Now includes query string
    ...
)
```

### Alternative: Inline Fix
For minimal changes, simply inline the logic:
```python
url=(request.url.path + ('?' + request.url.query if request.url.query else '')),
```

### Affected Files
- `src/py/litestar_vite/inertia/response.py` - Add query string to URL

### API Changes
None - this is a bug fix that corrects existing behavior to match the documented protocol.

## Testing Strategy

### Unit Tests
```python
def test_inertia_response_preserves_query_params() -> None:
    """Query parameters should be included in page props URL."""
    # Setup request with query params
    # Assert page_props["url"] includes query string

def test_inertia_response_url_without_query_params() -> None:
    """URLs without query parameters should work unchanged."""
    # Setup request without query params
    # Assert page_props["url"] is just the path

def test_inertia_page_refresh_maintains_filters() -> None:
    """Page refresh should preserve filter state via URL."""
    # Simulate filtered page load
    # Assert response contains correct URL with params
```

### Edge Cases
- Empty query string
- Query string with special characters (URL encoding)
- Query string with array parameters (`?ids[]=1&ids[]=2`)
- Fragment identifiers (should be excluded per HTTP spec)

## Research Summary

| Adapter | URL Building Method | Query Params Included |
|---------|---------------------|----------------------|
| Laravel | `getUrl()` with `fullUrl()` | Yes |
| Rails | `request.fullpath` | Yes |
| Django | `request.get_full_path()` | Yes |
| litestar-vite | `request.url.path` | **No (bug)** |

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Breaking existing behavior | Low | Change is additive - only adds query string when present |
| URL encoding issues | Low | Use Litestar's built-in URL handling which handles encoding |
| Fragment identifier leakage | Low | Fragments are client-side only; not sent to server |

## Implementation Complexity
**Low** - Single line change with helper function for clarity.

## References
- [Inertia.js Protocol](https://inertiajs.com/the-protocol)
- [Inertia Laravel Response.php](https://github.com/inertiajs/inertia-laravel/blob/master/src/Response.php)
- [Inertia Routing - URL Customization](https://inertiajs.com/routing#customizing-the-page-url)
- [GitHub Discussion #1292](https://github.com/inertiajs/inertia/discussions/1292)
