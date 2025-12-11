# Tasks: External Mode Static Router Auth Fix

## Phase 1: Planning
- [x] Create PRD
- [x] Analyze existing code patterns
- [x] Research Litestar static files router API
- [x] Identify affected components

## Phase 2: Implementation
- [x] Update `_configure_static_files()` to use `html_mode=True` for external mode in production
- [x] Skip static files for external mode in dev (proxy handles it)
- [x] Remove duplicate external mode static files block
- [x] Update angular-cli example to set `asset_url="/"`

## Phase 3: Testing
- [x] All existing tests pass
- [x] All linting checks pass

## Phase 4: Quality Gate
- [x] `make test` passes
- [x] `make lint` passes
- [x] No regressions in existing functionality

## Files Modified

| File | Changes |
|------|---------|
| `src/py/litestar_vite/plugin.py:1797-1800` | Added `html_mode` based on mode |
| `src/py/litestar_vite/plugin.py:1925-1929` | Skip static files for external dev mode |
| `examples/angular-cli/app.py:94` | Added `asset_url="/"` |
