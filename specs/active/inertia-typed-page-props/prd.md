# PRD: Inertia Typed Page Props

## Overview

- **Slug**: inertia-typed-page-props
- **Created**: 2025-12-06
- **Status**: Draft
- **Priority**: P1 (High)
- **Depends On**:
  - `inertia-protocol-compliance` (P0) - Core Inertia fixes
  - `inertia-defensive-hardening` (P0 Security) - Security fixes for redirects and exception handling
- **Consensus Sources**: Gemini 3 Pro (9/10 confidence), GPT 5.1 (8/10 confidence)

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
- Global TypeScript augmentation of `@inertiajs/core` PageProps (opt-in only in v2)

---

## Consensus Design Decisions

Based on multi-model consensus review (Gemini 3 Pro + GPT 5.1), the following design principles ensure graceful simplification:

### 1. Smart Defaults with Easy Escape Hatches

```python
# When BOTH types AND inertia are enabled, page props generation is automatic
ViteConfig(
    types=TypeGenConfig(),       # Enables type generation
    inertia=InertiaConfig(),     # Enables Inertia
    # generate_page_props defaults to True when both are present
)

# Explicit opt-out if unwanted
ViteConfig(
    types=TypeGenConfig(generate_page_props=False),  # Disable page props only
    inertia=InertiaConfig(),
)

# No types at all - Inertia works exactly as today
ViteConfig(
    inertia=InertiaConfig(),  # No types config = no generated files
)
```

### 2. Three Graceful Degradation Layers

```
┌─────────────────────────────────────────────────────────────────────┐
│ LAYER 1: No Types At All                                            │
│ - User doesn't enable `types` or never runs `generate-types`        │
│ - Inertia works exactly as today, no extra files                    │
│ - Zero impact on existing workflows                                 │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│ LAYER 2: Types Enabled, Page Props Ignored                          │
│ - User enables `types` but doesn't care about Inertia props         │
│ - `page-props.ts` is generated but:                                 │
│   - Never imported anywhere by default code                         │
│   - Does NOT change any global TS declarations                      │
│ - User experiences ZERO breakage (can simply ignore the file)       │
│ - If they dislike the extra file: `generate_page_props=False`       │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│ LAYER 3: Full Type Safety (Explicit Import)                         │
│ - User imports generated types in their components                  │
│ - Full IntelliSense, compile-time type checking                     │
│ - Can adopt incrementally (typed + untyped pages can coexist)       │
└─────────────────────────────────────────────────────────────────────┘
```

### 3. Passive Artifacts (Key Principle)

**Critical Rule**: Generated files are **passive** - they never affect runtime behavior.

- `inertia-pages.json` and `page-props.ts` are **dev-time only**
- Inertia runtime NEVER depends on these files
- Users who don't use TypeScript experience zero impact
- Files can be safely ignored, deleted, or gitignored

### 4. Incremental Adoption Support

```typescript
// OPTION A: Fully typed page
import type { PageProps } from '@/generated/page-props'
export default function Home(props: PageProps['Home']) {
  return <div>{props.message}</div>  // Fully typed
}

// OPTION B: Legacy page (not yet migrated)
export default function LegacyPage(props: any) {
  return <div>{props.whatever}</div>  // Works fine
}

// OPTION C: Manual types (user preference)
interface MyCustomProps {
  // ... manually defined
}
export default function CustomPage(props: MyCustomProps) {
  return <div>{props.custom}</div>
}
```

### 5. No Global TS Augmentation (v1)

**Decision**: Do NOT auto-augment `@inertiajs/core` PageProps.

```typescript
// v1: Explicit imports only (safe, predictable)
import type { PageProps } from '@/generated/page-props'
defineProps<PageProps['Books']>()

// v2 (future, opt-in): Global augmentation
// Only if user explicitly enables `inertia_global_page_props=True`
declare module '@inertiajs/core' {
  interface PageProps extends import('./page-props').PageProps {}
}
```

### 6. Fallback for Untyped Python Handlers

When a handler has no return type annotation:

```python
# No return type annotation
@get("/legacy", component="Legacy")
async def legacy_page():
    return {"data": "whatever"}
```

Generated TypeScript uses safe fallback:

```typescript
export interface PageProps {
  Home: HomeProps & SharedProps        // Typed handler
  Books: BooksProps & SharedProps      // Typed handler
  Legacy: Record<string, unknown> & SharedProps  // Fallback for untyped
}
```

---

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
| Complex dict literals without type hints | Medium | Use `Record<string, unknown>` fallback; warn on untyped handlers |
| Breaking existing type generation workflows | Low | Auto-on only when BOTH `types` AND `inertia` enabled; easy opt-out |
| Performance impact on app startup | Low | Only runs on `generate-types` command, not at runtime |
| Type name collisions between pages | Low | Use component name as prefix; warn on collisions |
| Circular type dependencies | Low | Let @hey-api/openapi-ts handle; it's battle-tested |
| Users confused by extra generated file | Low | File is passive; can be ignored or disabled with one flag |
| Global TS pollution breaking builds | None | v1 uses explicit imports only; no global augmentation |

## Dependencies

### Prerequisites

1. **inertia-protocol-compliance PRD** must be completed first to ensure:
   - `share()` helper works correctly (for shared props)
   - InertiaConfig is properly integrated
   - Middleware correctly processes requests
   - Pagination integration (`PaginationContainer` protocol) completed

2. **inertia-defensive-hardening PRD** (P0 Security) must be completed:
   - Fixes open redirect vulnerability (#123)
   - Fixes cookie leak in redirects (#126)
   - Fixes exception handler crashes (#124, #125)
   - Security issues must be resolved before adding new features

### External Dependencies

- @hey-api/openapi-ts (existing) - OpenAPI to TypeScript conversion
- msgspec or Pydantic - Python type introspection
- Vite (existing) - File watching and plugin system

### .litestar.json Integration

The `.litestar.json` file (generated during project setup) already has infrastructure for type generation config. Current structure includes `types: null`. We can extend this:

```json
{
  "assetUrl": "/static/",
  "bundleDir": "...",
  "types": {
    "enabled": true,
    "output": "./src/generated",
    "generatePageProps": true,
    "pagePropsPath": "./src/generated/page-props.ts"
  },
  // ... other fields
}
```

**Benefits of .litestar.json integration:**
1. **IDE Tooling**: VS Code extensions can read settings without parsing Python
2. **CI/CD Portability**: Config readable from any language (Node.js build scripts, etc.)
3. **Consistency**: Matches existing pattern used for other settings
4. **Single Source of Truth**: Avoids duplication between Python config and env vars

**Implementation note:** The TypeScript Vite plugin should read `types` config from `.litestar.json` to determine output paths for `page-props.ts`.

## Implementation Order

```
inertia-protocol-compliance (P0) ──▶ inertia-defensive-hardening (P0) ──▶ inertia-typed-page-props (P1)
         │                                      │
         │                                      └── #122, #123, #124, #125, #126 fixes
         │
         └── Phase 3.5 Pagination (PaginationContainer protocol)
                                                           │
                                                           ▼
                                              ┌────────────────────────────┐
                                              │ inertia-typed-page-props   │
                                              └────────────────────────────┘
                                                           │
         ├── Phase 1: Python Metadata Export
         │   ├── Add export_inertia_pages() to codegen.py
         │   ├── Add TypeGenConfig options
         │   ├── Wire into CLI command
         │   └── Update .litestar.json schema with types config
         │
         ├── Phase 2: TypeScript Generation
         │   ├── Add page-props-generator.ts
         │   ├── Integrate with Vite plugin
         │   ├── Read config from .litestar.json
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

### Related PRDs

| PRD | Status | Relationship |
|-----|--------|--------------|
| `inertia-protocol-compliance` | ~95% complete | Prerequisite - provides share(), middleware fixes, pagination integration |
| `inertia-defensive-hardening` | New | Prerequisite - security fixes must be done before new features |
| `openapi-ts-migration` | Draft | Related - migrates to new @hey-api plugin names we depend on |
| `example-e2e-testing` | Draft | Related - E2E tests should verify type generation works in examples |

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

---

## Consensus Summary

### Multi-Model Review (2025-12-06)

**Models Consulted:**
- Gemini 3 Pro (Advocate stance) - 9/10 confidence
- GPT 5.1 (Critical stance) - 8/10 confidence

### Points of Agreement

Both models agreed on the following key design decisions:

1. **Default Behavior**: Auto-enable `generate_page_props=True` when BOTH `types` AND `inertia` are configured. Users who want type safety shouldn't hunt for flags.

2. **Passive Artifacts**: Generated files (`inertia-pages.json`, `page-props.ts`) are passive dev-time artifacts. They never affect runtime behavior.

3. **No Global Augmentation**: Do NOT auto-augment `@inertiajs/core` PageProps in v1. Require explicit imports for predictable behavior.

4. **Incremental Adoption**: TypeScript's nature allows mixing typed and untyped pages. Users adopt at their own pace.

5. **Simple API Surface**: One config flag, one JSON, one TS file. Document "ignore, partial, full" adoption paths.

6. **Industry Alignment**: Modern meta-frameworks (Remix, Next.js, tRPC) all offer similar patterns. This positions litestar-vite as a premium choice.

### Key Insight from Gemini 3 Pro

> "The generated `page-props.ts` is a passive file. Its existence doesn't break existing code, enabling perfect graceful degradation."

### Key Insight from GPT 5.1

> "The most important rule: Do not make any Inertia runtime, or any generated runtime code, depend on `page-props.ts`. These must be purely dev-time artifacts."

### Resulting Design Principle

**"Batteries included for those who want them, invisible for those who don't."**

Users get type safety automatically when they enable the right configs, but the feature degrades gracefully at every level - from "full types" to "ignore the file" to "no types at all" - with zero breakage at any layer.
