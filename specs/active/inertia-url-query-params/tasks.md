# Tasks: Inertia URL Query Parameter Preservation

## Phase 1: Planning
- [x] Investigate user-reported issue
- [x] Research Inertia.js protocol for URL handling
- [x] Review other adapter implementations (Laravel, Django)
- [x] Identify root cause in litestar-vite
- [x] Create PRD with findings

## Phase 2: Implementation
- [ ] Add `_get_relative_url()` helper function in `response.py`
- [ ] Update `_build_page_props()` to use new helper
- [ ] Ensure URL encoding is handled correctly

## Phase 3: Testing
- [ ] Write unit test for query parameter preservation
- [ ] Write unit test for URL without query params (no regression)
- [ ] Write test for special characters in query string
- [ ] Write test for array-style query parameters
- [ ] Run full test suite (`make test`)
- [ ] Achieve 90%+ coverage for modified code

## Phase 4: Documentation
- [ ] Update docstring for `_get_relative_url()` helper
- [ ] No user-facing docs needed (internal bug fix)

## Phase 5: Quality Gate
- [ ] All tests pass
- [ ] Linting clean (`make lint`)
- [ ] Type checking passes (`make type-check`)
- [ ] Archive workspace to `specs/archive/`
