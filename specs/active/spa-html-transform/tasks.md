# Tasks: ViteSPAHandler HTML Transformation Integration

## Phase 1: Planning ✓

- [x] Analyze existing HtmlTransformer implementation
- [x] Research Inertia.js protocol requirements
- [x] Review ViteSPAHandler and plugin architecture
- [x] Create PRD with acceptance criteria
- [x] Create task breakdown

## Phase 2: Core Configuration ✓

### 2.1: SPAConfig Implementation ✓

- [x] Create `SPAConfig` dataclass in `config.py`
  - [x] Add `inject_routes: bool = True`
  - [x] Add `routes_var_name: str = "__LITESTAR_ROUTES__"`
  - [x] Add `routes_include: list[str] | None = None`
  - [x] Add `routes_exclude: list[str] | None = None`
  - [x] Add `app_selector: str = "#app"`
  - [x] Add `cache_transformed_html: bool = True`
  - [x] Add Google-style docstrings

- [x] Add `spa` field to `ViteConfig`
  - [x] Type: `Union[SPAConfig, bool] = False`
  - [x] Add bool shortcut normalization in `__post_init__`
  - [x] Add `spa_config` property accessor for convenience

- [x] Write unit tests for `SPAConfig`
  - [x] Test default values
  - [x] Test bool shortcut (True → SPAConfig with defaults)
  - [x] Test custom configuration

## Phase 3: ViteSPAHandler Enhancement ✓

### 3.1: Route Metadata Storage ✓

- [x] Add `_routes_metadata: dict[str, Any] | None` to `__slots__`
- [x] Add `_spa_config: SPAConfig | None` to `__slots__`
- [x] Add `_cached_transformed_html: str | None` to `__slots__`
- [x] Initialize new attributes in `__init__`

### 3.2: Route Metadata Methods ✓

- [x] Implement `set_routes_metadata(routes: dict[str, Any]) -> None`
  - [x] Store routes in `_routes_metadata`
  - [x] Invalidate `_cached_transformed_html`
  - [x] Add docstring

### 3.3: HTML Transformation ✓

- [x] Implement `_transform_html(html: str, page_data: dict | None = None) -> str`
  - [x] Import HtmlTransformer
  - [x] Inject route metadata if configured
  - [x] Inject page data if provided
  - [x] Handle custom selectors
  - [x] Use msgspec for JSON serialization
  - [x] Add docstring

- [x] Modify `get_html()` method
  - [x] Add `page_data: dict[str, Any] | None = None` parameter
  - [x] Call `_transform_html()` when needed
  - [x] Implement production caching logic
  - [x] Update docstring

- [x] Add `get_html_sync()` method
  - [x] Synchronous version for production use
  - [x] Raises error in dev mode (requires async proxy)

### 3.4: Unit Tests ✓

- [x] `test_spa.py` transformation tests
  - [x] Test route metadata injection
  - [x] Test page data injection
  - [x] Test caching behavior
  - [x] Test dev mode (no cache)
  - [x] Test sync method works in production
  - [x] Test sync method fails in dev mode
  - [x] Test no transform when spa=False

## Phase 4: Plugin Integration ✓

### 4.1: Route Extraction Wiring ✓

- [x] Add `_inject_routes_to_spa_handler()` helper method in `plugin.py`
  - [x] Check if SPA handler exists and routes injection enabled
  - [x] Call `generate_routes_json()` with filter options
  - [x] Pass routes to `spa_handler.set_routes_metadata()`
  - [x] Handle errors gracefully with console output

- [x] Modify `server_lifespan()` in `plugin.py`
  - [x] Call `_inject_routes_to_spa_handler()` after SPA handler initialization

- [x] Modify `async_server_lifespan()` in `plugin.py`
  - [x] Same changes as sync version

## Phase 5: Inertia SPA Mode ✓

### 5.1: Inertia Configuration ✓

- [x] Add `spa_mode: bool = False` to `InertiaConfig`
- [x] Add `app_selector: str = "#app"` to `InertiaConfig`
- [x] Update docstrings with Attributes section

### 5.2: SPA Rendering Path ✓

- [x] Add `_render_spa()` method to `InertiaResponse`
  - [x] Get ViteSPAHandler from plugin
  - [x] Convert page props using `to_dict()` for camelCase
  - [x] Call `get_html_sync(page_data=props)`
  - [x] Return encoded HTML bytes
  - [x] Add docstring

- [x] Modify `to_asgi_response()` in `InertiaResponse`
  - [x] Check `spa_mode` flag
  - [x] Route to `_render_spa()` or `_render_template()`

## Phase 6: Production Optimization ✓

### 6.1: Caching Implementation ✓

- [x] Implement cache population in `get_html()`
  - [x] Check `cache_transformed_html` setting
  - [x] Store transformed HTML on first request (routes only)
  - [x] Return cached HTML on subsequent requests
  - [x] Skip caching in dev mode
  - [x] Bypass cache when page_data is provided

- [x] Implement cache invalidation
  - [x] Clear cache when `set_routes_metadata()` called

## Phase 7: Testing & Documentation ✓

### 7.1: Comprehensive Test Coverage ✓

- [x] Run `make test` - all 204 tests pass
- [x] Run `make lint` - zero errors
- [x] Mypy passes
- [x] Pyright passes

### 7.2: Documentation ✓

- [x] Updated docstrings on all modified functions
- [x] Added usage examples to docstrings

## Phase 8: Quality Gate (Pending)

- [ ] All 16 acceptance criteria verified
- [ ] Integration tests for route injection
- [ ] Inertia SPA mode integration test
- [ ] Code review completed

## Phase 9: Archive (Pending)

- [ ] Move `specs/active/spa-html-transform/` to `specs/archive/`
- [ ] Create `COMPLETION-SUMMARY.md`
- [ ] Update cross-references

## Implementation Summary

### Files Modified

1. **src/py/litestar_vite/config.py**
   - Added `SPAConfig` dataclass
   - Added `spa` field to `ViteConfig`
   - Added `spa_config` property

2. **src/py/litestar_vite/spa.py**
   - Added route metadata storage
   - Added `set_routes_metadata()` method
   - Added `_transform_html()` method
   - Enhanced `get_html()` with page_data support
   - Added `get_html_sync()` for synchronous access
   - Uses msgspec for fast JSON serialization

3. **src/py/litestar_vite/plugin.py**
   - Added `_inject_routes_to_spa_handler()` method
   - Wired route injection into both lifespan handlers

4. **src/py/litestar_vite/inertia/config.py**
   - Added `spa_mode` and `app_selector` fields

5. **src/py/litestar_vite/inertia/response.py**
   - Added `_render_spa()` method
   - Modified `to_asgi_response()` to support SPA mode

6. **src/py/tests/unit/test_config.py**
   - Added SPAConfig unit tests

7. **src/py/tests/unit/test_spa.py**
   - Added transformation tests
   - Removed `from __future__ import annotations`

## Estimated vs Actual Effort

| Phase | Estimated | Actual |
|-------|-----------|--------|
| Configuration | 8 tasks | 7 tasks |
| SPA Handler | 12 tasks | 14 tasks |
| Plugin Integration | 4 tasks | 4 tasks |
| Inertia SPA Mode | 10 tasks | 6 tasks |
| Optimization | 4 tasks | 3 tasks |
| Testing & Docs | 6 tasks | 4 tasks |
| **Total** | ~44 tasks | ~38 tasks |
