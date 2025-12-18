# Recovery Guide: Inertia.js v2.3+ Protocol Features

## Current State

**Phase**: Planning Complete, Ready for Implementation

The PRD has been created based on analysis of two merged Inertia.js PRs:
- PR #2757: Flash Data Support (top-level `page.flash` property)
- PR #2687: Script Element Optimization (`useScriptElementForInitialPage`)

A multi-model consensus was built using gemini-3-pro-preview and openai/gpt-5.2, with both models agreeing on the implementation approach.

## Files Modified

| File | Status |
|------|--------|
| `specs/active/inertia-v2-flash-script-element/prd.md` | Created |
| `specs/active/inertia-v2-flash-script-element/tasks.md` | Created |
| `specs/active/inertia-v2-flash-script-element/recovery.md` | Created |

## Implementation Files (Not Yet Modified)

| File | Changes Needed |
|------|----------------|
| `src/py/litestar_vite/inertia/types.py` | Add `flash` field to `PageProps` |
| `src/py/litestar_vite/inertia/response.py` | Extract flash to top-level |
| `src/py/litestar_vite/config/_spa.py` | Add `use_script_element` option |
| `src/py/litestar_vite/html_transform.py` | Add `inject_page_script()` |
| `src/py/litestar_vite/handler/_app.py` | Branch on injection mode |

## Next Steps

1. **Start with Flash Data** (Phase 2):
   - Modify `PageProps` in `types.py` to add `flash` field
   - Update `_build_page_props()` in `response.py`
   - Add unit tests

2. **Then Script Element** (Phase 3):
   - Add config option to `SPAConfig`
   - Implement `inject_page_script()` in `html_transform.py`
   - Update `AppHandler._transform_html()`

## Context for Resumption

### Key Decisions Made

1. **Flash Data**: Add as top-level property BUT keep in `props.flash` for backward compatibility
2. **Script Element**: Opt-in config option, NOT auto-detect
3. **XSS Safety**: Escape `</` to `<\/` in JSON content
4. **CSP**: Support nonce attribute on script element

### Reference PRs

- [Inertia #2757](https://github.com/inertiajs/inertia/pull/2757) - Flash Data
- [Inertia #2687](https://github.com/inertiajs/inertia/pull/2687) - Script Element
- [inertia-laravel #797](https://github.com/inertiajs/inertia-laravel/pull/797) - Server-side Flash

### Current Code Locations

- Flash serialization: `helpers.py:747` (`props["flash"] = flash`)
- Page props building: `response.py:357-427` (`_build_page_props()`)
- HTML transformation: `handler/_app.py:149-171` (`_transform_html()`)
- Data attribute injection: `html_transform.py:250-263` (`set_data_attribute()`)

## Commands to Resume

```bash
# Check current state
cd /home/cody/code/litestar/litestar-vite
cat specs/active/inertia-v2-flash-script-element/tasks.md

# Run tests to verify nothing broken
make test

# Start implementation
/implement inertia-v2-flash-script-element
```
