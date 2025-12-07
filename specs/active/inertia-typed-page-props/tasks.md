# Tasks: Inertia Typed Page Props

## Overview

This task list covers automatic TypeScript type generation for Inertia.js page props, organized by implementation phase.

---

## Phase 1: Planning

- [x] Create PRD with comprehensive analysis
- [x] Identify all affected components
- [x] Define acceptance criteria
- [x] Design architecture and data flow

---

## Phase 2: Python Metadata Export (P0)

### Task 2.1: Add TypeGenConfig Options

**File**: `src/py/litestar_vite/config.py`

- [ ] Add `generate_page_props: bool = True` to TypeGenConfig
- [ ] Add `page_props_path: Path | None = None` to TypeGenConfig
- [ ] Add `__post_init__` logic to compute default page_props_path
- [ ] Update docstrings
- [ ] Write unit tests for new config options

### Task 2.2: Implement export_inertia_pages()

**File**: `src/py/litestar_vite/codegen.py`

- [ ] Create `InertiaPageMeta` dataclass:
  ```python
  @dataclass
  class InertiaPageMeta:
      route: str
      props_type: str
      schema_ref: str | None
  ```
- [ ] Implement `_get_component_from_route()` helper
- [ ] Implement `_get_return_type_name()` for type extraction
- [ ] Implement `_get_schema_ref()` to link to OpenAPI schema
- [ ] Implement `_extract_shared_props_types()` from InertiaConfig
- [ ] Implement main `export_inertia_pages()` function
- [ ] Export function in `__init__.py`

### Task 2.3: Handle Various Return Types

**File**: `src/py/litestar_vite/codegen.py`

- [ ] Support msgspec Struct return types
- [ ] Support Pydantic BaseModel return types
- [ ] Support TypedDict return types
- [ ] Support dict[str, T] return types
- [ ] Support union types (T | None)
- [ ] Handle untyped returns (warn and skip)

### Task 2.4: Wire into CLI Command

**File**: `src/py/litestar_vite/commands.py`

- [ ] Update `generate_types_command()` to call `export_inertia_pages()`
- [ ] Add `--skip-page-props` flag for opt-out
- [ ] Ensure proper error handling and messaging
- [ ] Update command help text

### Task 2.5: Unit Tests for Python Changes

**File**: `src/py/tests/unit/test_codegen.py`

- [ ] Test `export_inertia_pages()` with simple Struct
- [ ] Test with Pydantic model
- [ ] Test with TypedDict
- [ ] Test with dict literal return
- [ ] Test shared props extraction
- [ ] Test handler without component annotation (should skip)
- [ ] Test handler with multiple components on same route
- [ ] Test error handling for untyped handlers

### Phase 2 Verification

- [ ] Run `make test` - all tests pass
- [ ] Run `make lint` - no linting errors
- [ ] Manual test: `litestar assets generate-types` creates `inertia-pages.json`

---

## Phase 3: TypeScript Type Generation (P0)

### Task 3.1: Create Page Props Generator

**File**: `src/js/src/inertia-helpers/page-props-generator.ts` (NEW)

- [ ] Define `InertiaPagesMeta` interface matching JSON format
- [ ] Implement `parseInertiaPagesMeta()` to read JSON
- [ ] Implement `generateSharedPropsInterface()`
- [ ] Implement `generatePagePropsInterface()`
- [ ] Implement `generateTypeImports()` for OpenAPI types
- [ ] Implement `emitPagePropsTs()` main function
- [ ] Export from `inertia-helpers/index.ts`

### Task 3.2: Integrate with Vite Plugin

**File**: `src/js/src/index.ts`

- [ ] Add `inertiaPages` option to `PluginOptions`
- [ ] Add `watchPageProps()` function for file watching
- [ ] Call `generatePagePropsTypes()` on `inertia-pages.json` change
- [ ] Add to `configureServer()` hook
- [ ] Ensure proper error handling

### Task 3.3: TypeScript Generation Tests

**File**: `src/js/tests/page-props-generator.test.ts` (NEW)

- [ ] Test `emitPagePropsTs()` basic output
- [ ] Test SharedProps generation
- [ ] Test multiple pages
- [ ] Test type imports
- [ ] Test empty pages object
- [ ] Test special characters in component names

### Phase 3 Verification

- [ ] Run `npm test` - all tests pass
- [ ] Run `npm run build` - TypeScript compiles
- [ ] Manual test: Vite dev server regenerates types on change

---

## Phase 4: Framework-Specific Helpers (P1)

### Task 4.1: Vue 3 Helper

**File**: `src/js/src/inertia-helpers/vue.ts` (NEW)

- [ ] Create `definePageProps<C>()` type helper
- [ ] Add TypeScript overloads for type inference
- [ ] Export from `inertia-helpers/index.ts`
- [ ] Document usage in JSDoc

### Task 4.2: React Helper

**File**: `src/js/src/inertia-helpers/react.ts` (NEW)

- [ ] Create `ReactPageProps<C>` type alias
- [ ] Export from `inertia-helpers/index.ts`
- [ ] Document usage in JSDoc

### Task 4.3: Svelte Helper

**File**: `src/js/src/inertia-helpers/svelte.ts` (NEW)

- [ ] Create `SveltePageProps<C>` type alias
- [ ] Ensure compatibility with `$props()` rune
- [ ] Export from `inertia-helpers/index.ts`
- [ ] Document usage in JSDoc

### Phase 4 Verification

- [ ] All framework helpers compile
- [ ] Type inference works in VS Code
- [ ] JSDoc comments render correctly

---

## Phase 5: Example App Updates (P1)

### Task 5.1: Update vue-inertia Example

**File**: `examples/vue-inertia/`

- [ ] Remove manual type definitions from pages
- [ ] Import `PageProps` from generated file
- [ ] Use `defineProps<PageProps['Books']>()`
- [ ] Verify app still works correctly

### Task 5.2: Update react-inertia Example

**File**: `examples/react-inertia/`

- [ ] Remove manual interface definitions
- [ ] Import `PageProps` from generated file
- [ ] Use `PageProps['Books']` in component
- [ ] Verify app still works correctly

### Task 5.3: Update vue-inertia-jinja Example

**File**: `examples/vue-inertia-jinja/`

- [ ] Remove manual type definitions from pages
- [ ] Import `PageProps` from generated file
- [ ] Verify app still works correctly

### Task 5.4: Update react-inertia-jinja Example

**File**: `examples/react-inertia-jinja/`

- [ ] Remove manual interface definitions
- [ ] Import `PageProps` from generated file
- [ ] Verify app still works correctly

### Phase 5 Verification

- [ ] All example apps compile without errors
- [ ] All example apps run correctly
- [ ] No manual type duplications remain

---

## Phase 6: Testing & Validation

### Unit Tests

- [ ] All new Python code has 90%+ test coverage
- [ ] All new TypeScript code has tests
- [ ] Edge cases tested (empty, special chars, etc.)

### Integration Tests

- [ ] Test full pipeline: Python → JSON → TypeScript
- [ ] Test file watcher triggers regeneration
- [ ] Test with real example app

### E2E Tests

- [ ] Add E2E test for type generation workflow
- [ ] Verify generated types pass TypeScript compilation
- [ ] Verify VS Code IntelliSense works

---

## Phase 7: Documentation & Quality Gate

### Documentation Updates

- [ ] Update `specs/guides/architecture.md` with type generation flow
- [ ] Add inline docstrings for all new functions
- [ ] Update README with type generation instructions
- [ ] Add example usage to JSDoc

### Quality Gate Checklist

- [ ] `make test` passes
- [ ] `make lint` passes
- [ ] `make type-check` passes
- [ ] `make coverage` shows 90%+ for modified files
- [ ] All example apps compile and run
- [ ] No breaking changes to public API

### Archive

- [ ] Move workspace to `specs/archive/inertia-typed-page-props/`
- [ ] Create completion summary

---

## Progress Tracking

| Phase | Status | Completion |
|-------|--------|------------|
| Phase 1: Planning | Complete | 100% |
| Phase 2: Python Export | Not Started | 0% |
| Phase 3: TS Generation | Not Started | 0% |
| Phase 4: Framework Helpers | Not Started | 0% |
| Phase 5: Example Updates | Not Started | 0% |
| Phase 6: Testing | Not Started | 0% |
| Phase 7: Quality Gate | Not Started | 0% |

---

## Dependencies

```
inertia-protocol-compliance (P0)
         │
         ▼
inertia-typed-page-props (P1)
    Phase 2: Python Export
         │
         ▼
    Phase 3: TS Generation
         │
         ├───────────────┐
         ▼               ▼
    Phase 4: Helpers   Phase 5: Examples
         │               │
         └───────┬───────┘
                 ▼
         Phase 6: Testing
                 │
                 ▼
         Phase 7: Quality Gate
```

**Note**: This PRD should be implemented AFTER `inertia-protocol-compliance` is complete, as it depends on the `share()` helper and InertiaConfig working correctly.
