# Recovery Guide: Inertia Documentation Redesign

## Current State

**Phase**: Planning Complete (Updated with inertia-typed-page-props integration)

The PRD and task breakdown have been created. No implementation has started yet.

**Dependency**: This PRD depends on `inertia-typed-page-props` being completed first.

## Files Created

- `specs/active/inertia-docs-redesign/prd.md` - Full PRD with structure and requirements
- `specs/active/inertia-docs-redesign/tasks.md` - Detailed task breakdown with Phase 0 verification
- `specs/active/inertia-docs-redesign/recovery.md` - This file

## Files To Be Modified

### New Files (to create)

```
docs/inertia/
  index.rst
  installation.rst
  configuration.rst
  how-it-works.rst
  pages.rst
  responses.rst
  redirects.rst
  forms.rst
  links.rst
  shared-data.rst
  partial-reloads.rst
  deferred-props.rst
  merging-props.rst
  csrf-protection.rst
  history-encryption.rst
  templates.rst
  error-handling.rst
  asset-versioning.rst

  # TypeScript Integration (from inertia-typed-page-props)
  typescript.rst
  type-generation.rst
  typed-page-props.rst
  shared-props-typing.rst

  fullstack-example.rst
```

### Existing Files (to update)

- `docs/index.rst` - Add Inertia section to main toctree
- `docs/frameworks/inertia.rst` - Convert to quick overview pointing to new section
- `docs/usage/inertia.rst` - Archive or convert to redirect

## Next Steps

1. **Wait for inertia-typed-page-props completion**
   - Check if `specs/active/inertia-typed-page-props/` is moved to archive
   - If still active, complete that PRD first

2. **Start Phase 0: Pre-Implementation Verification**
   - Re-evaluate API consistency against actual implementation
   - Verify TypeGenConfig has typed page props features
   - Document any deviations

3. **Start Phase 2: Setup**
   - Create `docs/inertia/` directory
   - Create `docs/inertia/index.rst` with section toctree
   - Update `docs/index.rst` to include new section

4. **Start Phase 3: Core Documentation**
   - Begin with `installation.rst` and `configuration.rst`
   - Work through each topic in order
   - TypeScript section depends on inertia-typed-page-props being complete

## Context for Resumption

### Related PRDs

| PRD | Location | Status |
|-----|----------|--------|
| `inertia-typed-page-props` | `specs/active/inertia-typed-page-props/` | **Must complete first** |
| `inertia-protocol-compliance` | `specs/archive/` (likely) | Complete |
| `inertia-defensive-hardening` | `specs/archive/` (likely) | Complete |

### Key Reference Files

- **Current docs**: `docs/usage/inertia.rst` (504 lines - content to split)
- **Config source**: `src/py/litestar_vite/config.py` (InertiaConfig class)
- **Helpers source**: `src/py/litestar_vite/inertia/helpers.py` (all Python helpers)
- **Response source**: `src/py/litestar_vite/inertia/response.py` (response classes)
- **Fullstack example**: `/home/cody/code/litestar/litestar-fullstack-inertia`
- **Typed page props PRD**: `specs/active/inertia-typed-page-props/prd.md`

### Official Inertia.js Documentation Structure

```
Getting Started
- Introduction
- Demo Application
- Upgrade Guide

Installation
- Server-Side Setup
- Client-Side Setup

Core Concepts
- Who Is Inertia.js For?
- How It Works
- The Protocol

The Basics
- Pages, Responses, Redirects, Routing
- Title & Meta, Links, Manual Visits
- Forms, File Uploads, Validation, View Transitions

Data & Props
- Shared Data, Partial Reloads
- Deferred Props, Merging Props
- Polling, Prefetching, Load When Visible
- Infinite Scroll, Remembering State

Security
- Authentication, Authorization
- CSRF Protection, History Encryption

Advanced
- Asset Versioning, Code Splitting
- Error Handling, Events, Progress Indicators
- Scroll Management, SSR, Testing
```

### Key Python Components to Document

1. **InertiaConfig** - All 11 configuration options
2. **TypeGenConfig** - Type generation options (from inertia-typed-page-props):
   - `generate_page_props` - Auto-generate PageProps types
   - `page_props_path` - Output path for page-props.ts
   - `include_default_auth` - Include AuthData/User defaults
   - `include_default_flash` - Include FlashMessages default
3. **Response classes** - InertiaResponse, InertiaRedirect, InertiaBack, InertiaExternalRedirect
4. **Helper functions** - lazy, defer, merge, share, error, flash, clear_history, scroll_props, only, except_
5. **Template helpers** - vite(), vite_hmr(), inertia, js_routes, csrf_input

### TypeScript Types to Document (from inertia-typed-page-props)

- `GeneratedSharedProps` - Built-in props (flash, errors, csrf_token)
- `User` - Default user interface (extensible)
- `AuthData` - Default auth interface (Laravel Jetstream pattern)
- `FlashMessages` - Default flash messages interface
- `SharedProps` - User-extensible interface for share() calls
- `FullSharedProps` - Combined GeneratedSharedProps & SharedProps
- `PageProps` - Map of component name → typed props

### Patterns from litestar-fullstack-inertia

The preferred pattern is using `component` kwarg in route decorator:

```python
@get("/", component="Home")
async def home() -> dict:
    return {"message": "Hello"}
```

Rather than explicit InertiaResponse:

```python
@get("/")
async def home() -> InertiaResponse:
    return InertiaResponse(component="Home", props={"message": "Hello"})
```

### TypeScript Usage Pattern (from inertia-typed-page-props)

```typescript
// Import generated types
import type { PageProps } from '@/generated/page-props'

// Vue
defineProps<PageProps['Books']>()

// React
export default function Books(props: PageProps['Books']) { ... }

// Svelte
const { books }: PageProps['Books'] = $props()
```

## Implementation Command

To resume implementation:

```bash
/implement inertia-docs-redesign
```

Or manually start with:

1. Verify `inertia-typed-page-props` PRD is complete
2. Read `specs/active/inertia-docs-redesign/tasks.md`
3. Complete Phase 0 verification tasks
4. Begin with Phase 2 setup tasks
5. Create documentation files in order

## API Verification Checklist

Before writing documentation, verify these match the actual implementation:

### InertiaConfig Parameters
- [ ] `root_template` - str, default "index.html"
- [ ] `component_opt_keys` - tuple[str, ...], default ("component", "page")
- [ ] `exclude_from_js_routes_key` - str, default "exclude_from_routes"
- [ ] `redirect_unauthorized_to` - str | None, default None
- [ ] `redirect_404` - str | None, default None
- [ ] `extra_static_page_props` - dict[str, Any], default {}
- [ ] `extra_session_page_props` - set[str], default set()
- [ ] `spa_mode` - bool, default False
- [ ] `app_selector` - str, default "#app"
- [ ] `encrypt_history` - bool, default False

### TypeGenConfig Parameters (from inertia-typed-page-props)
- [ ] `generate_page_props` - bool, default True
- [ ] `page_props_path` - Path | None, default None
- [ ] `include_default_auth` - bool, default True
- [ ] `include_default_flash` - bool, default True

### Helper Functions
- [ ] `lazy(key, value_or_callable)` - exists and documented correctly
- [ ] `defer(key, callback, group)` - exists and documented correctly
- [ ] `merge(key, value, strategy, match_on)` - exists and documented correctly
- [ ] `scroll_props(...)` - exists and documented correctly
- [ ] `share(connection, key, value)` - exists and documented correctly
- [ ] `error(connection, key, message)` - exists and documented correctly
- [ ] `flash(connection, message, category)` - exists and documented correctly
- [ ] `clear_history(connection)` - exists and documented correctly
- [ ] `only(*keys)` - exists and documented correctly
- [ ] `except_(*keys)` - exists and documented correctly

### Response Classes
- [ ] `InertiaResponse` - exists with documented parameters
- [ ] `InertiaRedirect` - exists with documented parameters
- [ ] `InertiaBack` - exists with documented parameters
- [ ] `InertiaExternalRedirect` - exists with documented parameters
