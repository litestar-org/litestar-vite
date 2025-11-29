# PRD: ViteSPAHandler HTML Transformation Integration

## Overview

- **Slug**: spa-html-transform
- **Created**: 2025-11-28
- **Status**: Draft

This feature integrates the existing `HtmlTransformer` utility into `ViteSPAHandler` to enable automatic route metadata injection and template-less Inertia.js SPA mode. The `HtmlTransformer` class already exists in `html_transform.py` but is not used internally - it's only exported as a public API for manual use. This integration fills an architectural gap, enabling SPAs to receive runtime data (routes, page props) without requiring Jinja2 templates.

## Problem Statement

Currently, developers using litestar-vite in SPA mode face several friction points:

1. **Route Metadata Gap**: The `generate_routes_json()` function exports routes to a file, but there's no automatic way to inject route metadata into the served HTML at runtime. Developers who want client-side routing helpers (like Ziggy's `route()` function) must manually transform HTML or set up additional build steps.

2. **Inertia.js Template Requirement**: The Inertia.js integration requires Jinja2 templates to render the initial HTML response with `data-page` props. This forces developers to:
   - Install and configure Jinja2 even for simple SPAs
   - Create and maintain template files
   - Learn template syntax for a single use case (injecting page data)

3. **Unused Utility Code**: The `HtmlTransformer` class in `html_transform.py` provides robust HTML transformation capabilities but sits unused in the codebase. It's exported as public API but serves no internal purpose - a clear architectural gap.

4. **Manual Integration Burden**: Developers who want route metadata or template-less rendering must manually:
   - Read the Vite-built `index.html`
   - Use `HtmlTransformer` to inject data
   - Handle caching and performance themselves

## Goals

1. **Primary**: Automatically inject route metadata into SPA HTML via `ViteSPAHandler` using the existing `HtmlTransformer`

2. **Secondary**: Enable template-less Inertia.js SPA mode where `InertiaResponse` uses `HtmlTransformer` instead of Jinja2 templates

3. **Tertiary**: Implement production caching for transformed HTML to minimize runtime overhead

## Non-Goals

- **Not replacing templates**: Template-based rendering remains the default for Inertia. SPA mode is opt-in.
- **Not implementing SSR**: Server-side rendering of JavaScript components is out of scope.
- **Not modifying API routes**: This only affects HTML responses from the SPA handler, not JSON APIs.
- **Not changing HtmlTransformer API**: The public API remains unchanged; we're adding internal usage.

## Acceptance Criteria

### Phase 1: Core Integration

- [ ] **AC-1**: `ViteSPAHandler` injects route metadata into HTML when `spa.inject_routes=True`
- [ ] **AC-2**: Route metadata is available as `window.__LITESTAR_ROUTES__` (configurable via `routes_var_name`)
- [ ] **AC-3**: Route filtering works via `routes_include` and `routes_exclude` patterns
- [ ] **AC-4**: Custom app selector works for data attribute injection (`app_selector` option)
- [ ] **AC-5**: New `SPAConfig` dataclass added to `config.py` with all configuration options

### Phase 2: Inertia SPA Mode

- [ ] **AC-6**: `InertiaResponse` renders without template engine when `spa_mode=True`
- [ ] **AC-7**: `data-page` attribute is correctly injected on the app element per Inertia.js protocol
- [ ] **AC-8**: Page props are properly JSON serialized with configured type encoders
- [ ] **AC-9**: Optional CSRF token injection works when configured
- [ ] **AC-10**: SPA mode gracefully coexists with template mode (non-breaking)

### Phase 3: Production Optimization

- [ ] **AC-11**: Transformed HTML is cached in production when `cache_transformed_html=True`
- [ ] **AC-12**: Cache is invalidated when routes are re-extracted (startup only)
- [ ] **AC-13**: Development mode always transforms fresh (no caching for HMR compatibility)

### Backward Compatibility

- [ ] **AC-14**: Existing template-based Inertia applications work unchanged
- [ ] **AC-15**: Default `spa` config is `False` (opt-in feature)
- [ ] **AC-16**: `HtmlTransformer` public API remains unchanged

## Technical Approach

### Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                              VitePlugin                                  │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  on_app_init()                                                   │   │
│  │  - Creates ViteSPAHandler with SPAConfig                        │   │
│  │  - Registers catch-all route                                     │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  server_lifespan() / async_server_lifespan()                    │   │
│  │  - Extracts route metadata via generate_routes_json()            │   │
│  │  - Passes routes to ViteSPAHandler.set_routes_metadata()        │   │
│  └─────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                           ViteSPAHandler                                 │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  get_html(request, page_data=None)                              │   │
│  │  - Gets raw HTML (dev: proxy, prod: cached file)                │   │
│  │  - Calls _transform_html() if transformations needed            │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  _transform_html(html, page_data)                               │   │
│  │  - Uses HtmlTransformer.inject_json_script() for routes         │   │
│  │  - Uses HtmlTransformer.set_data_attribute() for page data      │   │
│  │  - Returns transformed HTML                                      │   │
│  └─────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                          InertiaResponse                                 │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  to_asgi_response()                                              │   │
│  │  - If spa_mode=True: calls _render_spa()                        │   │
│  │  - Else: calls _render_template() (existing)                    │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  _render_spa()  [NEW]                                           │   │
│  │  - Gets HTML from ViteSPAHandler.get_html(page_data=props)      │   │
│  │  - Returns rendered HTML bytes                                   │   │
│  └─────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
```

### Affected Files

| File | Changes |
|------|---------|
| `src/py/litestar_vite/config.py` | Add `SPAConfig` dataclass, add `spa` field to `ViteConfig` |
| `src/py/litestar_vite/spa.py` | Add `_transform_html()`, modify `get_html()`, add route metadata storage |
| `src/py/litestar_vite/plugin.py` | Wire route metadata extraction to SPA handler in lifespan |
| `src/py/litestar_vite/inertia/config.py` | Add `spa_mode` and `app_selector` options to `InertiaConfig` |
| `src/py/litestar_vite/inertia/response.py` | Add `_render_spa()` method, modify rendering path selection |
| `tests/unit/test_spa_config.py` | New tests for SPAConfig |
| `tests/unit/test_spa_handler_transform.py` | New tests for transformation logic |
| `tests/unit/test_inertia_spa_mode.py` | New tests for Inertia SPA rendering |
| `tests/integration/test_spa_routes_injection.py` | Integration tests for full flow |

### API Changes

#### New Configuration: SPAConfig

```python
@dataclass
class SPAConfig:
    """Configuration for SPA HTML transformations.

    Attributes:
        inject_routes: Inject route metadata into HTML.
        routes_var_name: Global variable name for routes.
        routes_include: Whitelist patterns for route filtering.
        routes_exclude: Blacklist patterns for route filtering.
        app_selector: CSS selector for data attribute injection.
        cache_transformed_html: Cache transformed HTML in production.
    """

    inject_routes: bool = True
    routes_var_name: str = "__LITESTAR_ROUTES__"
    routes_include: list[str] | None = None
    routes_exclude: list[str] | None = None
    app_selector: str = "#app"
    cache_transformed_html: bool = True
```

#### ViteConfig Extension

```python
@dataclass
class ViteConfig:
    # ... existing fields ...

    # NEW: SPA transformation settings
    spa: SPAConfig | bool = False  # False = disabled, True = defaults, SPAConfig = custom
```

#### InertiaConfig Extension

```python
@dataclass
class InertiaConfig:
    # ... existing fields ...

    # NEW: Template-less SPA mode
    spa_mode: bool = False  # Use HtmlTransformer instead of Jinja2
    app_selector: str = "#app"  # Selector for data-page attribute
```

#### ViteSPAHandler New Methods

```python
class ViteSPAHandler:
    def set_routes_metadata(self, routes: dict[str, Any]) -> None:
        """Set route metadata for injection."""
        ...

    async def get_html(
        self,
        request: Request[Any, Any, Any],
        *,
        page_data: dict[str, Any] | None = None,  # NEW parameter
    ) -> str:
        """Get HTML with optional transformations."""
        ...
```

### Code Samples

#### Usage: Route Injection Only

```python
from litestar import Litestar
from litestar_vite import VitePlugin, ViteConfig, SPAConfig

app = Litestar(
    plugins=[
        VitePlugin(
            config=ViteConfig(
                mode="spa",
                spa=SPAConfig(
                    inject_routes=True,
                    routes_var_name="__ROUTES__",
                    routes_exclude=["_internal_*"],
                ),
            )
        )
    ],
)
# Result: index.html includes <script>window.__ROUTES__ = {...};</script>
```

#### Usage: Inertia Without Templates

```python
from litestar import Litestar
from litestar_vite import VitePlugin, ViteConfig, InertiaConfig
from litestar_vite.inertia import InertiaPlugin

app = Litestar(
    plugins=[
        VitePlugin(
            config=ViteConfig(
                mode="spa",
                spa=True,  # Enable with defaults
                inertia=InertiaConfig(
                    enabled=True,
                    spa_mode=True,  # No Jinja2 needed!
                ),
            )
        ),
        InertiaPlugin(),
    ],
)
# Result: InertiaResponse renders without template engine
```

### Database Changes

None - this feature creates configuration files only.

## Testing Strategy

### Unit Tests

| Test File | Coverage |
|-----------|----------|
| `test_spa_config.py` | SPAConfig defaults, validation, bool shortcut |
| `test_spa_handler_transform.py` | `_transform_html()` with various inputs |
| `test_inertia_spa_mode.py` | `_render_spa()` JSON serialization, attribute injection |

### Integration Tests

| Test | Description |
|------|-------------|
| `test_spa_routes_injection` | Full app with routes injected into HTML |
| `test_inertia_spa_full_flow` | Inertia request/response without Jinja2 |
| `test_production_caching` | Cache behavior verification |
| `test_dev_mode_no_cache` | HMR compatibility in dev mode |

### Edge Cases

- Empty routes (no routes match filter)
- Missing `#app` element in HTML
- Very large page props (>1MB JSON)
- Unicode in route names and props
- Concurrent requests during cache population
- Malformed index.html (missing head/body tags)

### Performance Requirements

- Transformation adds <5ms overhead per request in dev mode
- Production caching eliminates repeat transformation cost
- Memory usage for cached HTML <10MB for typical apps

## Security Considerations

- **XSS Prevention**: `HtmlTransformer._escape_attr()` already handles HTML escaping for attribute values. JSON data is escaped to prevent injection.
- **CSRF**: Optional CSRF token injection uses the same escaping mechanisms.
- **No Secrets**: Route metadata contains only public route information (paths, methods, parameters). No credentials or sensitive data.

## Risks & Mitigations

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| Breaking existing Inertia apps | HIGH | LOW | `spa_mode` defaults to `False`, template path unchanged |
| Performance regression | MEDIUM | LOW | Production caching, lazy transformation |
| Incorrect HTML output | MEDIUM | LOW | Use existing HtmlTransformer (already tested) |
| Route metadata size | LOW | MEDIUM | Filtering options, minified JSON |
| XSS via JSON injection | HIGH | LOW | HtmlTransformer escaping already handles this |
| Cache staleness in dev | LOW | LOW | Dev mode never caches |

## Dependencies

- **External**: None (uses existing stdlib and project code)
- **Internal**:
  - `html_transform.py` - HtmlTransformer class
  - `codegen.py` - generate_routes_json()
  - `spa.py` - ViteSPAHandler
  - `inertia/response.py` - InertiaResponse

## References

- [Inertia.js Protocol Documentation](https://inertiajs.com/the-protocol)
- `src/py/litestar_vite/html_transform.py` - Existing transformer implementation
- `src/py/litestar_vite/codegen.py` - Route metadata generation
- `tests/unit/test_html.py` - Existing transformer tests
- `specs/guides/architecture.md` - System architecture
