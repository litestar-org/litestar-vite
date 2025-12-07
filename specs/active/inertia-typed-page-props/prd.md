# PRD: Inertia Typed Page Props

## Overview

- **Slug**: inertia-typed-page-props
- **Created**: 2025-12-06
- **Status**: Draft
- **Priority**: P1 (High)
- **Depends On**: inertia-protocol-compliance (P0)

## Problem Statement

Currently, Inertia.js page components in litestar-vite must manually define TypeScript interfaces for their props, leading to:

1. **Code Duplication**: Types are defined twice - once in Python (msgspec Struct, Pydantic models) and again in TypeScript (interfaces)
2. **Type Drift**: Manual TypeScript types can become out of sync with backend Python types
3. **Maintenance Burden**: Every change to a handler's return type requires updating the frontend type definition
4. **Lost Context**: Shared props (flash messages, errors, CSRF tokens) must be manually added to every component

### Current Pain Point

```python
# Python handler (app.py)
class Book(Struct):
    id: int
    title: str

@get("/books", component="Books")
async def books_page() -> dict[str, object]:
    return {"books": BOOKS}
```

```typescript
// Frontend (Books.vue) - MANUALLY DUPLICATED!
interface Book {
  id: number
  title: string
}
defineProps<{ books: Book[] }>()
```

### Desired State

```typescript
// Frontend (Books.vue) - AUTOMATICALLY TYPED!
import { PageProps } from '@/generated/page-props'
defineProps<PageProps['Books']>()
```

## Goals

### P0 - Core Type Generation

1. Automatically generate TypeScript types for Inertia page props from Python handler return types
2. Create a mapping of component names to their corresponding prop types
3. Include shared props (flash, errors, csrf_token) in all page prop types

### P1 - Developer Experience

4. Integrate with existing `litestar assets generate-types` command
5. Provide framework-specific helpers for Vue, React, and Svelte
6. Support hot-reload of types during development

### P2 - Advanced Features

7. Support for lazy/deferred props typing
8. TypeScript module augmentation for @inertiajs types
9. JSON Schema export for page props (for validation tooling)

## Non-Goals

- Replacing @hey-api/openapi-ts (we build on top of it)
- Runtime type validation (TypeScript is compile-time only)
- Supporting non-Inertia routes in page props
- Automatic prop destructuring or code generation for components

## Acceptance Criteria

### P0 - Core Functionality

- [ ] New `export_inertia_pages()` function in `codegen.py`
- [ ] `inertia-pages.json` metadata file generated with component→type mapping
- [ ] `page-props.ts` generated with `PageProps` interface
- [ ] SharedProps interface includes flash, errors, csrf_token
- [ ] Works with msgspec Struct, Pydantic BaseModel, TypedDict, and dict return types

### P1 - Integration

- [ ] `litestar assets generate-types` includes page props generation
- [ ] Vite plugin watches `inertia-pages.json` for changes
- [ ] Types regenerate automatically on file change in dev mode
- [ ] Example apps updated to use generated types

### P2 - Framework Helpers

- [ ] Vue: `definePageProps<'Books'>()` type helper
- [ ] React: `PageProps['Books']` works with component props
- [ ] Svelte: Compatible with `$props()` rune typing
- [ ] TypeScript IntelliSense works for all frameworks

## Technical Approach

### Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           TYPE GENERATION PIPELINE                          │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐       │
│  │  Python Types   │     │   OpenAPI Schema │     │  TypeScript     │       │
│  │  (msgspec/      │────▶│   (openapi.json) │────▶│  (api/types.ts) │       │
│  │   Pydantic)     │     │                 │     │                 │       │
│  └─────────────────┘     └─────────────────┘     └─────────────────┘       │
│                                                           │                 │
│  ┌─────────────────┐     ┌─────────────────┐             │                 │
│  │  Route Handlers │     │  Inertia Pages  │             │                 │
│  │  (component=    │────▶│  Metadata       │             │                 │
│  │   "Books")      │     │  (inertia-      │             ▼                 │
│  └─────────────────┘     │   pages.json)   │     ┌─────────────────┐       │
│                          └────────┬────────┘     │  Page Props     │       │
│                                   │              │  (page-props.ts)│       │
│                                   └─────────────▶│                 │       │
│                                                  └─────────────────┘       │
│                                                           │                 │
│                                                           ▼                 │
│                                                  ┌─────────────────┐       │
│                                                  │  Frontend       │       │
│                                                  │  Components     │       │
│                                                  │  (Vue/React/    │       │
│                                                  │   Svelte)       │       │
│                                                  └─────────────────┘       │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Data Flow

1. **Python Build Time**: Route handlers are introspected for:
   - Component name from `@get("/path", component="Name")`
   - Return type annotation
   - Shared props from InertiaConfig

2. **Metadata Export**: `inertia-pages.json` created with structure:
   ```json
   {
     "pages": {
       "Books": {
         "route": "/books",
         "propsType": "BooksPageProps",
         "schemaRef": "#/components/schemas/BooksPageProps"
       }
     },
     "sharedProps": {
       "flash": { "type": "object", "optional": true },
       "errors": { "type": "Record<string, string[]>", "optional": true },
       "csrf_token": { "type": "string", "optional": true }
     }
   }
   ```

3. **TypeScript Generation**: Vite plugin reads metadata and emits:
   ```typescript
   // page-props.ts
   import type { BooksPageProps } from './api/types'

   export interface SharedProps {
     flash?: { success?: string; error?: string }
     errors?: Record<string, string[]>
     csrf_token?: string
   }

   export interface PageProps {
     Books: BooksPageProps & SharedProps
   }
   ```

### Affected Files

#### Python (src/py/litestar_vite/)

| File | Changes |
|------|---------|
| `codegen.py` | Add `export_inertia_pages()` function |
| `config.py` | Add `generate_page_props` and `page_props_path` to `TypeGenConfig` |
| `commands.py` | Wire page props export into `generate-types` command |
| `inertia/helpers.py` | Add type extraction utilities |

#### TypeScript (src/js/src/)

| File | Changes |
|------|---------|
| `index.ts` | Add `inertia-pages.json` watching and generation |
| `inertia-helpers/page-props-generator.ts` | NEW: Generate `page-props.ts` |
| `inertia-helpers/index.ts` | Export type helpers |

### API Changes

#### New TypeGenConfig Options

```python
@dataclass
class TypeGenConfig:
    # ... existing fields ...
    generate_page_props: bool = True
    page_props_path: Path | None = None  # Default: output / "page-props.json"
```

#### New CLI Behavior

```bash
# Existing command now also generates page props
litestar assets generate-types

# Generates:
# - src/generated/openapi.json
# - src/generated/routes.json
# - src/generated/routes.ts
# - src/generated/inertia-pages.json  (NEW)
# - src/generated/page-props.ts       (NEW - from Vite plugin)
```

#### Generated TypeScript API

```typescript
// src/generated/page-props.ts

/** Shared props available on every Inertia page */
export interface SharedProps {
  flash?: { success?: string; error?: string }
  errors?: Record<string, string[]>
  csrf_token?: string
}

/** Page props mapped by component name */
export interface PageProps {
  Home: HomeProps & SharedProps
  Books: BooksProps & SharedProps
  // ... auto-generated for each Inertia route
}

/** Component name union type */
export type ComponentName = keyof PageProps

/** Type-safe props for a specific component */
export type InertiaPageProps<C extends ComponentName> = PageProps[C]
```

## Testing Strategy

### Unit Tests

1. **codegen.py tests** (`test_codegen.py`):
   - Test `export_inertia_pages()` with various return types
   - Test msgspec Struct extraction
   - Test Pydantic BaseModel extraction
   - Test TypedDict extraction
   - Test plain dict return types
   - Test shared props extraction from InertiaConfig

2. **TypeScript generation tests** (`page-props-generator.test.ts`):
   - Test `emitPagePropsTs()` output format
   - Test SharedProps generation
   - Test type imports from api/types.ts
   - Test edge cases (no pages, many pages, special characters)

### Integration Tests

1. **Full pipeline test**:
   - Start example app
   - Trigger type generation
   - Verify all expected files created
   - Verify TypeScript compilation passes

2. **Hot reload test**:
   - Modify Python handler return type
   - Run generate-types
   - Verify page-props.ts updates correctly

### Edge Cases

- Handler returning `Any` type
- Handler with no return annotation
- Nested complex types (dict of lists of objects)
- Circular type references
- Unicode in component names
- Very long type names

## Research Questions

- [x] Can we reuse existing OpenAPI schema refs for page props?
  - **Answer**: Yes, handlers already generate OpenAPI schemas for return types
- [ ] Should we support multiple components per route?
  - Needs investigation of use case
- [ ] How to handle `lazy()` and `defer()` prop types?
  - These wrap values; need to extract inner type
- [ ] Should `usePage()` be typed via module augmentation?
  - Could provide better DX but adds complexity

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Complex dict literals without type hints | Medium | Require explicit return type annotations; warn on untyped returns |
| Breaking existing type generation workflows | Low | Feature is opt-in via `generate_page_props=True` |
| Performance impact on app startup | Low | Only runs on `generate-types` command, not at runtime |
| Type name collisions between pages | Low | Use component name as prefix; warn on collisions |
| Circular type dependencies | Low | Let @hey-api/openapi-ts handle; it's battle-tested |

## Dependencies

### Prerequisites

1. **inertia-protocol-compliance PRD** must be completed first to ensure:
   - `share()` helper works correctly (for shared props)
   - InertiaConfig is properly integrated
   - Middleware correctly processes requests

### External Dependencies

- @hey-api/openapi-ts (existing) - OpenAPI to TypeScript conversion
- msgspec or Pydantic - Python type introspection
- Vite (existing) - File watching and plugin system

## Implementation Order

```
inertia-protocol-compliance (P0) ──▶ inertia-typed-page-props (P1)
         │
         ├── Phase 1: Python Metadata Export
         │   ├── Add export_inertia_pages() to codegen.py
         │   ├── Add TypeGenConfig options
         │   └── Wire into CLI command
         │
         ├── Phase 2: TypeScript Generation
         │   ├── Add page-props-generator.ts
         │   ├── Integrate with Vite plugin
         │   └── Add file watcher
         │
         ├── Phase 3: Framework Helpers
         │   ├── Vue definePageProps helper
         │   ├── React props type helper
         │   └── Svelte $props typing
         │
         └── Phase 4: Testing & Examples
             ├── Unit tests
             ├── Integration tests
             └── Update example apps
```

## Success Metrics

1. All Inertia example apps use generated types (no manual duplication)
2. Type changes in Python reflect in TypeScript within seconds (dev mode)
3. Zero manual intervention required after initial setup
4. TypeScript compilation passes for all example apps
5. Full IntelliSense support in VS Code for page props

## References

- [Inertia.js TypeScript Guide](https://inertiajs.com/typescript)
- [Laravel Inertia TypeScript](https://github.com/inertiajs/inertia-laravel/blob/master/stubs/typescript.ts)
- [@hey-api/openapi-ts Documentation](https://heyapi.vercel.app/)
- Existing litestar-vite type generation in `codegen.py`
