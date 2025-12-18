# Recovery Guide: Inertia URL Query Parameter Preservation

## Current State
PRD complete. Ready for implementation.

## Issue Summary
Query parameters are stripped from the Inertia page object URL, causing filter state to be lost on page refresh.

## Root Cause
Line 396 in `src/py/litestar_vite/inertia/response.py`:
```python
url=request.url.path,  # Missing query string
```

## The Fix
```python
url=(request.url.path + ('?' + request.url.query if request.url.query else '')),
```

Or with helper function:
```python
def _get_relative_url(request: "Request[Any, Any, Any]") -> str:
    """Get relative URL including query string."""
    path = request.url.path
    query = request.url.query
    return f"{path}?{query}" if query else path
```

## Files to Modify
- `src/py/litestar_vite/inertia/response.py` - Line 396 in `_build_page_props()`

## Next Steps
1. Open `src/py/litestar_vite/inertia/response.py`
2. Add helper function or inline fix
3. Write tests in `tests/test_inertia_response.py`
4. Run `make test` to verify
5. Run `make lint` to verify code quality

## Context for Resumption
- Inertia protocol requires URL with query string
- All other adapters (Laravel, Rails, Django) include query params
- This is a low-risk, high-impact bug fix
- Litestar URL object: `.path` = path only, `.query` = query string
