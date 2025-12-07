# Recovery Guide: Inertia Typed Page Props

## Current State

**Status**: PRD Complete, Ready for Implementation (after inertia-protocol-compliance)

The comprehensive PRD and task breakdown have been created based on architectural analysis of the existing type generation system and Inertia integration.

## Files Created

| File | Status | Description |
|------|--------|-------------|
| `specs/active/inertia-typed-page-props/prd.md` | Complete | Full PRD with all requirements |
| `specs/active/inertia-typed-page-props/tasks.md` | Complete | Detailed task breakdown by phase |
| `specs/active/inertia-typed-page-props/recovery.md` | Complete | This file |
| `specs/active/inertia-typed-page-props/research/` | Created | Empty, for research artifacts |
| `specs/active/inertia-typed-page-props/tmp/` | Created | Empty, for temp files |

## Files To Be Modified (Implementation)

### Phase 2: Python Metadata Export

| File | Changes Required |
|------|------------------|
| `src/py/litestar_vite/config.py` | Add `generate_page_props`, `page_props_path` to TypeGenConfig |
| `src/py/litestar_vite/codegen.py` | Add `export_inertia_pages()` function |
| `src/py/litestar_vite/commands.py` | Wire into `generate-types` command |

### Phase 3: TypeScript Generation

| File | Changes Required |
|------|------------------|
| `src/js/src/index.ts` | Add file watching for `inertia-pages.json` |
| `src/js/src/inertia-helpers/page-props-generator.ts` | NEW: Generate `page-props.ts` |
| `src/js/src/inertia-helpers/index.ts` | Export new helpers |

### Phase 4: Framework Helpers

| File | Changes Required |
|------|------------------|
| `src/js/src/inertia-helpers/vue.ts` | NEW: Vue `definePageProps` helper |
| `src/js/src/inertia-helpers/react.ts` | NEW: React props type helper |
| `src/js/src/inertia-helpers/svelte.ts` | NEW: Svelte props helper |

### Phase 5: Example Updates

| Directory | Changes Required |
|-----------|------------------|
| `examples/vue-inertia/` | Use generated types, remove manual definitions |
| `examples/react-inertia/` | Use generated types, remove manual definitions |
| `examples/vue-inertia-jinja/` | Use generated types, remove manual definitions |
| `examples/react-inertia-jinja/` | Use generated types, remove manual definitions |

## Next Steps

1. **Wait for Prerequisite**: Complete `inertia-protocol-compliance` PRD first
2. **Start Implementation**: Run `/implement inertia-typed-page-props`
3. **Begin with Phase 2**: Python metadata export
4. **Test After Each Phase**: Run `make test` and `npm test`
5. **Quality Gate**: Run full `make check-all` before marking complete

## Context for Resumption

### Key Design Decisions

1. **Leverage Existing Infrastructure**: Build on @hey-api/openapi-ts for type generation
2. **New Metadata File**: `inertia-pages.json` contains component→type mapping
3. **SharedProps Injection**: All page props include flash, errors, csrf_token
4. **Framework-Agnostic**: Core `page-props.ts` works with Vue, React, Svelte

### Architecture Summary

```
Python Handlers → OpenAPI Schema → openapi.json
                                        │
                                        ▼
                              @hey-api/openapi-ts
                                        │
                                        ▼
                                 api/types.ts
                                        │
Python Handlers → inertia-pages.json ───┼───▶ page-props.ts
(component opt)                         │
                                        ▼
                              Frontend Components
```

### Generated Output Example

```typescript
// src/generated/page-props.ts
import type { Message, BooksPageProps } from './api/types'

export interface SharedProps {
  flash?: { success?: string; error?: string }
  errors?: Record<string, string[]>
  csrf_token?: string
}

export interface PageProps {
  Home: Message & SharedProps
  Books: BooksPageProps & SharedProps
}

export type ComponentName = keyof PageProps
export type InertiaPageProps<C extends ComponentName> = PageProps[C]
```

### Frontend Usage Example

```typescript
// Vue 3
import { PageProps } from '@/generated/page-props'
defineProps<PageProps['Books']>()

// React
import { PageProps } from '@/generated/page-props'
function Books(props: PageProps['Books']) { ... }

// Svelte 5
import type { PageProps } from '$lib/generated/page-props'
const { books, summary }: PageProps['Books'] = $props()
```

### Test Commands

```bash
# Run all tests
make test

# Run only codegen tests
uv run pytest src/py/tests/unit/test_codegen.py -v

# Run TypeScript tests
npm test

# Build TypeScript
npm run build

# Lint check
make lint
```

## Dependencies

### Prerequisite PRD

- `specs/active/inertia-protocol-compliance/` - Must be completed first
  - Ensures `share()` helper works correctly
  - Ensures InertiaConfig is properly integrated
  - Fixes version mismatch and header issues

### External Dependencies

- @hey-api/openapi-ts (existing) - OpenAPI to TypeScript
- msgspec (existing) - Python type introspection
- Vite (existing) - File watching and plugin system

## Related PRDs

- `specs/active/inertia-protocol-compliance/` - Prerequisite (P0)
- `specs/archive/inertia-integration-fixes/` - Previous Inertia work

## Key Files to Study

Before implementing, review these files:

1. `src/py/litestar_vite/codegen.py` - Existing type generation
2. `src/js/src/index.ts` - Vite plugin structure
3. `examples/vue-inertia/app.py` - Example handler patterns
4. `examples/vue-inertia/resources/pages/Books.vue` - Current manual typing
