# PRD: Inertia.js v2.3+ Protocol Features Support

## Overview
- **Slug**: inertia-v2-flash-script-element
- **Created**: 2025-12-18
- **Status**: Draft
- **Inertia.js Version**: v2.3.0+
- **Source PRs**:
  - [#2757](https://github.com/inertiajs/inertia/pull/2757) - Flash Data Support (MERGED)
  - [#2687](https://github.com/inertiajs/inertia/pull/2687) - Script Element Optimization (MERGED)

## Problem Statement

The Inertia.js client has introduced two new protocol features in v2.3.x that litestar-vite needs to support:

1. **Flash Data Protocol Change**: The official Inertia adapters now send flash data as a top-level `page.flash` property (not inside `props`). This enables flash messages to NOT persist in browser history, improving UX by preventing flash messages from reappearing on back/forward navigation.

2. **Script Element for Page Data**: A new performance optimization that embeds page data in a `<script type="application/json" id="app_page">` element instead of a `data-page` attribute. This provides ~37% payload size reduction for large pages by avoiding HTML entity escaping.

Currently, litestar-vite places flash messages inside `props.flash`, which causes them to persist in browser history (incorrect behavior with new Inertia clients).

## Goals

1. **Primary**: Align with Inertia.js v2.3+ protocol by adding top-level `flash` property
2. **Secondary**: Support script element optimization for large payload scenarios

## Non-Goals

- Auto-detecting client capabilities for script element feature
- Per-response override for script element (adds unnecessary complexity)

## Acceptance Criteria

### Feature 1: Flash Data Protocol (High Priority)

- [ ] Add `flash: dict[str, list[str]] | None` field to `PageProps` dataclass
- [ ] Modify `_build_page_props()` to extract flash for top-level property
- [ ] Remove flash from `props` (move to top-level only)
- [ ] Flash messages appear correctly on frontend via `page.flash`
- [ ] Flash messages do NOT reappear on browser back/forward navigation
- [ ] Update existing Inertia tests to use `page.flash`
- [ ] Add new tests for top-level flash behavior

### Feature 2: Script Element Optimization (Medium Priority)

- [ ] Add `use_script_element: bool = False` config option to `SPAConfig`
- [ ] Implement `inject_page_script()` function in `html_transform.py`
- [ ] Handle CSP nonce attribute on script element
- [ ] Escape `</script>` sequences as `<\/script>` in JSON for XSS safety
- [ ] Modify `AppHandler._transform_html()` to support both injection modes
- [ ] Add tests for script element injection and escaping
- [ ] Document client-side configuration requirement (`useScriptElementForInitialPage`)

## Technical Approach

### Architecture

Both features affect the server-side page serialization and HTML rendering:

```
InertiaResponse._build_page_props()
    └── PageProps (add flash field)
            └── to_dict() (serialize top-level flash)

AppHandler._transform_html()
    ├── set_data_attribute() [existing path]
    └── inject_page_script() [new path when enabled]
```

### Affected Files

| File | Changes |
|------|---------|
| `src/py/litestar_vite/inertia/types.py` | Add `flash` field to `PageProps` |
| `src/py/litestar_vite/inertia/response.py` | Extract flash to top-level in `_build_page_props()` |
| `src/py/litestar_vite/config/_spa.py` | Add `use_script_element` option |
| `src/py/litestar_vite/html_transform.py` | Add `inject_page_script()` function |
| `src/py/litestar_vite/handler/_app.py` | Branch on injection mode |
| `src/py/tests/unit/inertia/test_response.py` | Add flash protocol tests |
| `src/py/tests/unit/test_html.py` | Add script element tests |

### API Changes

#### PageProps (types.py)

```python
@dataclass
class PageProps(Generic[T]):
    component: str
    url: str
    version: str
    props: dict[str, Any]

    # Existing v2 fields...
    encrypt_history: bool = False
    clear_history: bool = False
    # ... merge_props, deferred_props, etc.

    # NEW: Top-level flash for v2.3+ protocol
    flash: dict[str, list[str]] | None = None
```

#### SPAConfig (config/_spa.py)

```python
@dataclass
class SPAConfig:
    # Existing fields...

    # NEW: Use script element instead of data-page attribute
    # Requires client-side: createInertiaApp({ useScriptElementForInitialPage: true })
    use_script_element: bool = False
```

#### html_transform.py

```python
def inject_page_script(
    html: str,
    json_data: str,
    nonce: str | None = None
) -> str:
    """Inject page data as a script element.

    The script element is inserted before </body> with:
    - type="application/json" (non-executable)
    - id="app_page" (Inertia's expected ID)
    - Optional nonce for CSP compliance

    The JSON is escaped to prevent XSS via </script> injection.
    """
```

## Testing Strategy

### Unit Tests

1. **Flash Protocol Tests**
   - Verify `page.flash` in serialized output
   - Verify `props.flash` still present for backward compatibility
   - Verify empty flash results in `flash: null` (not included)
   - Test flash with multiple categories

2. **Script Element Tests**
   - Verify script element injection before `</body>`
   - Verify `id="app_page"` and `type="application/json"` attributes
   - Verify nonce attribute when CSP enabled
   - Verify `</script>` escaping in JSON content
   - Verify `</` becomes `<\/` in output

### Integration Tests

1. **Flash E2E**
   - Flash message appears on frontend
   - Flash does not persist on back navigation (requires Inertia v2.3+ client)

2. **Script Element E2E**
   - App hydrates correctly from script element
   - Works with SSR mode

## Research Questions

- [x] Does `page.flash` need to be at top level or inside props? → **Top level confirmed**
- [x] What ID does Inertia expect for script element? → **`app_page`**
- [x] How should `</script>` be escaped? → **`<\/script>` (escape forward slash)**

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Client not configured for script element | High | Make config opt-in, document client setup |
| CSP blocking script element | Medium | Support nonce attribute |
| XSS via `</script>` in props | High | Escape forward slashes in JSON |

## Multi-Model Consensus

**Models Consulted**: gemini-3-pro-preview, openai/gpt-5.2

**Unanimous Agreement On**:

1. Both features should be implemented
2. Flash should be top-level only (no backward compatibility needed - library unreleased)
3. Script element should be opt-in config, NOT auto-detect
4. Priority: Flash first (correctness), Script Element second (optimization)
5. Implementation complexity rated as low

**Confidence Score**: High (8-10/10)

## Implementation Notes

### Flash Data Implementation Detail

In `response.py`:

```python
def _build_page_props(...) -> PageProps[T]:
    shared_props = get_shared_props(request, partial_data=partial_data, partial_except=partial_except)

    # Extract flash for top-level (v2.3+ protocol)
    # Remove from props - flash should only be at top-level
    flash_data = shared_props.pop("flash", None)
    if flash_data == {}:  # Empty dict becomes None
        flash_data = None

    # ... rest of method ...

    return PageProps[T](
        component=...,
        props=shared_props,  # No longer contains flash
        flash=flash_data,    # Top-level only
        # ...
    )
```

### Script Element Escaping

```python
def _escape_script_content(json_str: str) -> str:
    """Escape sequences that could break out of script element."""
    # Escape </script> to prevent premature tag closure
    # Use <\/ which is valid JSON and prevents HTML parser issues
    return json_str.replace("</", "<\\/")
```
