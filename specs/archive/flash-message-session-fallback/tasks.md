# Tasks: Flash Message Session Fallback

## Phase 1: Planning ✓
- [x] Analyze GitHub issue #164
- [x] Review existing code in `helpers.py` and `exception_handler.py`
- [x] Create PRD documentation

## Phase 2: Implementation ✓
- [x] Modify `flash()` to return `bool` indicating success/failure
- [x] Change logging from `warning` to `debug` for missing session
- [x] Update exception handler to check `flash_succeeded` return value
- [x] Add query parameter fallback when flash fails for unauthorized redirects
- [x] URL-encode error message in query parameter
- [x] Preserve existing query parameters when appending error

## Phase 3: Testing ✓
- [x] Write unit tests for `flash()` return value
  - `test_flash_returns_true_with_session`
  - `test_flash_returns_false_when_session_access_fails`
  - `test_flash_returns_false_when_session_setdefault_raises_attribute_error`
- [x] Write unit tests for query parameter fallback
  - `test_unauthenticated_redirect_with_query_param_fallback`
  - `test_unauthenticated_redirect_no_query_param_when_flash_succeeds`
  - `test_unauthenticated_redirect_query_param_with_special_chars`
  - `test_unauthenticated_redirect_preserves_existing_query_params`
- [x] All 94 tests in affected modules pass

## Phase 4: Documentation ✓
- [x] Update PRD with test coverage
- [x] Document frontend handling in PRD
- [x] Create tasks.md with completion status

## Phase 5: Quality Gate
- [ ] Run full `make test` suite
- [ ] Run `make lint`
- [ ] Archive workspace after merge

## Test Results

```
src/py/tests/unit/inertia/test_helpers.py ........................
src/py/tests/unit/inertia/test_response.py ...................................
94 passed in 5.74s
```

## Files Modified

| File | Change |
|------|--------|
| `src/py/litestar_vite/inertia/helpers.py` | `flash()` returns `bool` |
| `src/py/litestar_vite/inertia/exception_handler.py` | Query param fallback |
| `src/py/tests/unit/inertia/test_helpers.py` | 3 new tests for `flash()` |
| `src/py/tests/unit/inertia/test_response.py` | 4 new tests for exception handler |
