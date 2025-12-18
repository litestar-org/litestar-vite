# Tasks: Inertia.js v2.3+ Protocol Features Support

## Phase 1: Planning
- [x] Review Inertia.js PR #2757 (Flash Data)
- [x] Review Inertia.js PR #2687 (Script Element)
- [x] Analyze current litestar-vite flash implementation
- [x] Build consensus with gemini-3-pro and gpt-5.2
- [x] Create PRD

## Phase 2: Flash Data Implementation (High Priority)

### 2.1 Protocol Types
- [x] Add `flash: dict[str, list[str]] | None = None` to `PageProps` in `types.py`
- [x] Ensure `to_dict()` serializes flash at top level
- [x] Verify camelCase conversion for `flash` (should stay `flash`)

### 2.2 Response Assembly
- [x] Modify `_build_page_props()` in `response.py`:
  - Pop flash from `shared_props` for top-level property
  - Handle empty flash dict (convert to `None`)
- [x] Ensure flash is not in props (top-level only)

### 2.3 Tests
- [x] Add unit test: top-level flash in serialized output
- [x] Add unit test: flash NOT in props (removed)
- [x] Add unit test: empty flash becomes `null`
- [x] Add unit test: multiple flash categories
- [x] Update existing flash tests to use `page.flash`
- [x] Replace Litestar FlashPlugin with our own `flash` helper in tests

## Phase 3: Script Element Implementation (Medium Priority)

### 3.1 Configuration
- [x] Add `use_script_element: bool = True` to `SPAConfig` (default True for performance)
- [x] Document in config docstring
- [x] Add `spa` config to `.litestar.json` bridge file (`_utils.py`)
- [x] Update TypeScript bridge schema (`BridgeSpaConfig` in `bridge-schema.ts`)

### 3.2 HTML Transform
- [x] Create `inject_page_script()` function in `html_transform.py`:
  - Insert before `</body>`
  - Set `type="application/json"` and `id="app_page"`
  - Support optional `nonce` attribute
- [x] Implement XSS escaping (escape `</` to `<\/`)
- [x] Add unit tests for script injection (8 new tests)
- [x] Add unit tests for `</script>` escaping

### 3.3 Handler Integration
- [x] Modify `AppHandler._transform_html()` to branch:
  - If `use_script_element`: use `inject_page_script()`
  - Otherwise: use existing `set_data_attribute()`
- [x] Pass nonce from `self._config.csp_nonce`
- [ ] Add integration test for script element mode

## Phase 4: Documentation
- [ ] Add note about Inertia v2.3+ compatibility
- [ ] Document `page.flash` vs `props.flash` (deprecation notice)
- [ ] Document `use_script_element` config option
- [ ] Document client-side `useScriptElementForInitialPage` requirement

## Phase 5: Quality Gate
- [ ] All tests pass (`make test`)
- [ ] Linting clean (`make lint`)
- [ ] Type checking passes (`make type-check`)
- [ ] Coverage maintained at 90%+
- [ ] Archive workspace

## Implementation Summary

### Files Modified

| File | Changes |
|------|---------|
| `src/py/litestar_vite/inertia/types.py` | Added `flash` field to `PageProps` |
| `src/py/litestar_vite/inertia/response.py` | Extract flash to top-level in `_build_page_props()` |
| `src/py/litestar_vite/config/_spa.py` | Added `use_script_element = True` option |
| `src/py/litestar_vite/html_transform.py` | Added `inject_page_script()` function |
| `src/py/litestar_vite/handler/_app.py` | Branch on injection mode in `_transform_html()` |
| `src/py/litestar_vite/plugin/_utils.py` | Added `spa` config to bridge file payload |
| `src/py/litestar_vite/inertia/exception_handler.py` | Use our flash helper instead of Litestar's |
| `src/js/src/shared/bridge-schema.ts` | Added `BridgeSpaConfig` interface and parsing |
| `src/py/tests/unit/inertia/test_response.py` | Updated flash tests for v2.3+ protocol |
| `src/py/tests/unit/test_html.py` | Added 8 tests for `inject_page_script()` |

### Key Decisions

1. **Flash at top-level only**: Using `.pop()` to remove from props entirely (no backward compatibility needed - library unreleased)
2. **Script element default True**: Better performance (~37% smaller payloads)
3. **XSS escaping**: Replace `</` with `<\/` in JSON content
4. **Bridge config**: Added `spa.useScriptElement` to `.litestar.json` for TypeScript plugin
