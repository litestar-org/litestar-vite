# Recovery Guide: ViteSPAHandler HTML Transformation Integration

**Slug**: spa-html-transform
**Created**: 2025-11-28
**Last Updated**: 2025-11-28
**Status**: Implementation Complete - Testing Passed

## Current State

Core implementation complete. All 204 unit tests passing. Linting, mypy, and pyright clean.

### Completed Checkpoints

- [x] **Checkpoint 0**: Context loaded (CLAUDE.md, architecture, code-style guides)
- [x] **Checkpoint 1**: Existing code analyzed (html_transform.py, spa.py, config.py, plugin.py, inertia/response.py)
- [x] **Checkpoint 2**: Inertia.js protocol researched (data-page attribute, page object structure)
- [x] **Checkpoint 3**: Deep analysis via sequential thinking (12 steps)
- [x] **Checkpoint 4**: PRD workspace created at `specs/active/spa-html-transform/`
- [x] **Checkpoint 5**: Comprehensive PRD written (3200+ words, 16 acceptance criteria)
- [x] **Checkpoint 6**: Task breakdown created (44 tasks across 9 phases)
- [x] **Checkpoint 7**: SPAConfig implemented in config.py
- [x] **Checkpoint 8**: ViteSPAHandler enhanced with transformations
- [x] **Checkpoint 9**: Plugin wired for route extraction
- [x] **Checkpoint 10**: Inertia SPA mode implemented
- [x] **Checkpoint 11**: Unit tests written and passing

### Files Created/Modified

| File | Status | Changes |
|------|--------|---------|
| `specs/active/spa-html-transform/prd.md` | Complete | Full PRD with technical approach |
| `specs/active/spa-html-transform/tasks.md` | Complete | Detailed task breakdown |
| `specs/active/spa-html-transform/recovery.md` | Complete | This file |
| `src/py/litestar_vite/config.py` | ✅ Complete | SPAConfig, spa field, spa_config property |
| `src/py/litestar_vite/spa.py` | ✅ Complete | Route metadata, _transform_html, get_html_sync |
| `src/py/litestar_vite/plugin.py` | ✅ Complete | _inject_routes_to_spa_handler, lifespan wiring |
| `src/py/litestar_vite/inertia/config.py` | ✅ Complete | spa_mode, app_selector fields |
| `src/py/litestar_vite/inertia/response.py` | ✅ Complete | _render_spa method, to_asgi_response routing |
| `src/py/tests/unit/test_config.py` | ✅ Complete | SPAConfig unit tests |
| `src/py/tests/unit/test_spa.py` | ✅ Complete | Transformation tests |

## Test Results

```
collected 204 items
204 passed in 2.49s
```

Linting:
```
Ruff: All checks passed
Mypy: no issues found in 67 source files
Pyright: 0 errors, 0 warnings
Slots check: All OK
```

## Next Steps

### Phase 8: Quality Gate (Pending)
- [ ] Verify all 16 acceptance criteria from PRD
- [ ] Integration test for full route injection flow
- [ ] Inertia SPA mode integration test
- [ ] Code review

### Phase 9: Archive (Pending)
- [ ] Move to `specs/archive/`
- [ ] Create completion summary

## Context for Resumption

### Key Design Decisions

1. **Opt-in Feature**: `spa` config defaults to `False` for backward compatibility
2. **Use Existing HtmlTransformer**: No new HTML parsing, reuse tested code
3. **Production Caching**: Transform once per routes update, cache for all requests
4. **Separate SPAConfig**: Clean organization, doesn't bloat RuntimeConfig
5. **Coexistence with Templates**: Inertia can use either templates or SPA mode
6. **msgspec for JSON**: Uses Litestar's optimized JSON serialization

### Implementation Summary

```python
# Enable route injection in SPA
from litestar_vite.config import ViteConfig, SPAConfig

config = ViteConfig(
    spa=True,  # Enable with defaults
    # or:
    spa=SPAConfig(
        routes_var_name="__ROUTES__",
        routes_exclude=["_internal*"],
    )
)
```

```python
# Enable Inertia SPA mode (no Jinja2 needed)
from litestar_vite.inertia.config import InertiaConfig

inertia_config = InertiaConfig(
    spa_mode=True,
    app_selector="#app",
)
```

### Route Injection Flow

1. Plugin lifespan calls `_inject_routes_to_spa_handler(app)`
2. Routes extracted via `generate_routes_json()`
3. Routes stored in SPA handler via `set_routes_metadata()`
4. HTML transformed on first `get_html()` call
5. Cached for subsequent requests (production only)
6. Page data injected per-request when provided

### Code Patterns Followed

```python
# Type hints: Union style (not PEP 604 | syntax)
spa: "Union[SPAConfig, bool]" = False

# Docstrings: Google style
def set_routes_metadata(self, routes: dict[str, Any]) -> None:
    """Set route metadata for injection.

    Args:
        routes: Route metadata dictionary from generate_routes_json().
    """

# Tests: Function-based, no class-based tests
def test_spa_config_defaults() -> None:
    config = SPAConfig()
    assert config.inject_routes is True
```

### New Public APIs

1. **SPAConfig** - Configuration dataclass for SPA transformations
2. **ViteConfig.spa** - Enable/configure SPA transformations
3. **ViteConfig.spa_config** - Property to access SPAConfig (or None)
4. **ViteSPAHandler.set_routes_metadata()** - Store routes for injection
5. **ViteSPAHandler.get_html(page_data=...)** - Enhanced with page data injection
6. **ViteSPAHandler.get_html_sync(page_data=...)** - Synchronous version for production
7. **InertiaConfig.spa_mode** - Enable template-less rendering
8. **InertiaConfig.app_selector** - CSS selector for data-page injection

## Verification Checklist

Before marking implementation complete:

- [x] `make test` passes (204/204)
- [x] `make lint` passes
- [x] Mypy passes
- [x] Pyright passes
- [x] Slots check passes
- [x] Docstrings updated
- [ ] All 16 acceptance criteria verified
- [ ] Integration tests for route injection
- [ ] Inertia SPA mode integration tests
- [ ] 90%+ coverage on modified modules (needs verification)

## Research References

- Inertia.js Protocol: https://inertiajs.com/the-protocol
- Context7 docs ID: `/inertiajs/docs`
- Existing transformer tests: `tests/unit/test_html.py`
