# PRD: Inertia Documentation Redesign

## Overview
- **Slug**: inertia-docs-redesign
- **Created**: 2025-12-07
- **Status**: Draft
- **Depends On**: `inertia-typed-page-props` (should be implemented first)

## Prerequisites

Before implementing this PRD:
1. **Re-evaluate API consistency** - Verify `InertiaConfig`, helpers, and response classes match current implementation
2. **Review inertia-typed-page-props completion** - Ensure type generation features are implemented and stable
3. **Check for any API changes** - Run `make test` and review any failing tests that indicate API drift

## Problem Statement

The current Inertia.js documentation in litestar-vite is:
1. **Too dense** - All content is in a single 500+ line page (`docs/usage/inertia.rst`)
2. **Hard to navigate** - Users cannot quickly find specific topics
3. **Different from official docs** - Users familiar with Inertia.js official docs struggle to map concepts
4. **Missing key topics** - Several v2 features are documented but not prominently organized
5. **Lacks real-world examples** - The `litestar-fullstack-inertia` project shows best practices but isn't referenced

## Goals

1. **Mirror Inertia.js official structure** - Reorganize docs to follow the official Inertia.js documentation hierarchy
2. **Concise, focused pages** - Each page covers one topic with minimal content (~100-200 lines max)
3. **Clear references to official docs** - Link to inertiajs.com for client-side concepts
4. **Document all config options** - Complete `InertiaConfig` and template reference
5. **Showcase best practices** - Reference `litestar-fullstack-inertia` as the "gold standard"

## Non-Goals

- Duplicating client-side documentation (React/Vue/Svelte components) - link to official docs
- Writing framework-specific tutorials (React vs Vue vs Svelte) - focus on Python integration
- Documenting Vite configuration in detail - that belongs in Vite docs section

## Acceptance Criteria

- [ ] Documentation structure mirrors official Inertia.js docs hierarchy
- [ ] Each page is concise (<200 lines) and focused on a single topic
- [ ] All `InertiaConfig` options are documented with examples
- [ ] Root template (`index.html`) is fully documented with all available helpers
- [ ] Every Python helper function is documented with examples
- [ ] Links to official Inertia.js docs for client-side concepts
- [ ] References to `litestar-fullstack-inertia` for real-world patterns
- [ ] Cross-references between related pages (See Also sections)

## Technical Approach

### Proposed Documentation Structure

Following the official Inertia.js hierarchy:

```
docs/
  inertia/                        # New Inertia.js section
    index.rst                     # Overview & quick start
    installation.rst              # Installation guide
    configuration.rst             # InertiaConfig reference

    # Core Concepts (mirror official)
    how-it-works.rst              # The protocol explained

    # The Basics (mirror official)
    pages.rst                     # Page components & routing
    responses.rst                 # InertiaResponse & props
    redirects.rst                 # InertiaRedirect, InertiaBack
    links.rst                     # Link to official + route() helper
    forms.rst                     # Link to official + validation handling

    # Data & Props (mirror official)
    shared-data.rst               # share(), extra_static_page_props
    partial-reloads.rst           # only(), except_()
    deferred-props.rst            # defer(), lazy()
    merging-props.rst             # merge() for infinite scroll

    # Security
    csrf-protection.rst           # CSRF setup
    history-encryption.rst        # v2 encrypt_history feature

    # Advanced
    templates.rst                 # Root template reference
    error-handling.rst            # Exception handlers
    asset-versioning.rst          # How version checking works

    # TypeScript Integration (from inertia-typed-page-props)
    typescript.rst                # Overview of TS integration
    type-generation.rst           # TypeGenConfig for routes
    typed-page-props.rst          # PageProps generation & usage
    shared-props-typing.rst       # SharedProps interface extension

    # Examples
    fullstack-example.rst         # Reference to litestar-fullstack-inertia
```

### Content Guidelines

1. **Each page structure**:
   ```rst
   Title
   =====

   Brief 1-2 sentence description.

   .. seealso::
      Official Inertia.js docs: `Topic <https://inertiajs.com/topic>`_

   [Main content - focused, concise]

   Example
   -------
   [Working code example]

   See Also
   --------
   - :doc:`related-topic`
   ```

2. **Python examples use `component` kwarg style** (preferred pattern from fullstack):
   ```python
   @get("/", component="Home")
   async def home() -> dict:
       return {"message": "Hello"}
   ```

3. **Reference fullstack patterns**:
   ```rst
   .. tip::
      See `litestar-fullstack-inertia <https://github.com/litestar-org/litestar-fullstack-inertia>`_
      for a complete production example.
   ```

### Key Files to Document

#### InertiaConfig (from `src/py/litestar_vite/config.py`)

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `root_template` | `str` | `"index.html"` | Root Jinja2 template name |
| `component_opt_keys` | `tuple[str, ...]` | `("component", "page")` | Route handler opt keys for component name |
| `exclude_from_js_routes_key` | `str` | `"exclude_from_routes"` | Key to exclude routes from JS routes |
| `redirect_unauthorized_to` | `str \| None` | `None` | URL for unauthorized redirects |
| `redirect_404` | `str \| None` | `None` | URL for 404 redirects |
| `extra_static_page_props` | `dict[str, Any]` | `{}` | Props shared with every page |
| `extra_session_page_props` | `set[str]` | `set()` | Session keys to include in props |
| `spa_mode` | `bool` | `False` | Use SPA mode (no Jinja templates) |
| `app_selector` | `str` | `"#app"` | CSS selector for app root element |
| `encrypt_history` | `bool` | `False` | Enable history encryption globally |

#### Python Helpers (from `src/py/litestar_vite/inertia/helpers.py`)

- `lazy(key, value_or_callable)` - Create lazy prop (partial reload only)
- `defer(key, callback, group)` - Create deferred prop (v2)
- `merge(key, value, strategy, match_on)` - Create merge prop (v2)
- `scroll_props(...)` - Infinite scroll configuration
- `share(connection, key, value)` - Share data with all pages
- `error(connection, key, message)` - Set error message
- `flash(connection, message, category)` - Add flash message
- `clear_history(connection)` - Clear encrypted history
- `only(*keys)` - Include only specified props
- `except_(*keys)` - Exclude specified props

#### Response Classes (from `src/py/litestar_vite/inertia/response.py`)

- `InertiaResponse` - Main response class
- `InertiaRedirect` - Same-origin redirect
- `InertiaBack` - Redirect to Referer
- `InertiaExternalRedirect` - External redirect (OAuth, etc.)

#### Template Helpers (injected into root template)

- `{{ vite('resources/main.ts') }}` - Include Vite assets
- `{{ vite_hmr() }}` - HMR client (dev mode)
- `{{ inertia }}` - Page props JSON for data-page attribute
- `{{ js_routes }}` - Route definitions script
- `{{ csrf_input }}` - CSRF hidden input

#### TypeGenConfig (for Typed Page Props - from inertia-typed-page-props PRD)

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `generate_page_props` | `bool` | `True` | Auto-generate TypeScript types for page props |
| `page_props_path` | `Path \| None` | `None` | Output path for `page-props.ts` |
| `include_default_auth` | `bool` | `True` | Include default `AuthData` and `User` interfaces |
| `include_default_flash` | `bool` | `True` | Include default `FlashMessages` interface |

#### Generated TypeScript Types (from inertia-typed-page-props PRD)

The typed page props feature generates these key types:

- `GeneratedSharedProps` - Built-in props (flash, errors, csrf_token) + static config props
- `User` - Default user interface (id, email, name) - extensible via module augmentation
- `AuthData` - Default auth interface (isAuthenticated, user) - Laravel Jetstream pattern
- `FlashMessages` - Default flash messages interface ({ [category]: string[] })
- `SharedProps` - User-extensible interface for `share()` calls in guards/middleware
- `FullSharedProps` - Combined `GeneratedSharedProps & SharedProps`
- `PageProps` - Map of component name → typed props (e.g., `PageProps['Books']`)

**Usage in Components:**

```typescript
// Vue
import type { PageProps } from '@/generated/page-props'
defineProps<PageProps['Books']>()

// React
import type { PageProps } from '@/generated/page-props'
export default function Books(props: PageProps['Books']) { ... }

// Svelte
import type { PageProps } from '@/generated/page-props'
const { books }: PageProps['Books'] = $props()
```

**Extending SharedProps:**

```typescript
// src/types/shared-props.ts
declare module 'litestar-vite/inertia' {
  interface User {
    avatarUrl?: string | null
    roles: Role[]
  }
  interface SharedProps {
    locale?: string
    currentTeam?: CurrentTeam
  }
}
```

### Migration Strategy

1. **Phase 1**: Create new `docs/inertia/` directory structure
2. **Phase 2**: Split current `docs/usage/inertia.rst` into focused pages
3. **Phase 3**: Update `docs/frameworks/inertia.rst` to be a quick overview pointing to new section
4. **Phase 4**: Add cross-references and See Also sections
5. **Phase 5**: Update main docs index to feature Inertia section

## Testing Strategy

- Build docs locally (`make docs`) to verify RST syntax
- Verify all internal cross-references resolve
- Check all external links are valid
- Review rendered output for formatting issues

## Research Questions

- [x] What is the official Inertia.js documentation structure? (Researched above)
- [x] What config options exist in InertiaConfig? (Documented above)
- [x] What helpers are available in the Python library? (Documented above)

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Breaking existing doc links | Medium | Keep old pages as redirects initially |
| Missing content during split | Medium | Checklist comparison against current content |
| Inconsistent style across pages | Low | Use template structure for all pages |

## Related PRDs

| PRD | Status | Relationship |
|-----|--------|--------------|
| `inertia-typed-page-props` | Active | **Must complete first** - TypeScript type generation features need to be stable before documenting |
| `inertia-protocol-compliance` | Complete | Prerequisite for typed-page-props |
| `inertia-defensive-hardening` | Complete | Security fixes referenced in redirect/exception docs |

## Reference Materials

- Official Inertia.js docs: https://inertiajs.com/
- Current usage docs: `docs/usage/inertia.rst`
- Current framework docs: `docs/frameworks/inertia.rst`
- Fullstack example: `/home/cody/code/litestar/litestar-fullstack-inertia`
- Config source: `src/py/litestar_vite/config.py` (InertiaConfig)
- Helpers source: `src/py/litestar_vite/inertia/helpers.py`
- Response source: `src/py/litestar_vite/inertia/response.py`
- **Typed page props PRD**: `specs/active/inertia-typed-page-props/prd.md`
