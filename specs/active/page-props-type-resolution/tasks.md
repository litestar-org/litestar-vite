# Tasks: Page Props Type Resolution Fix

## Phase 1: Critical Bug Fix (Regex)

- [ ] Fix regex in `src/js/src/shared/emit-page-props-types.ts:212`
  - Change `(\\w+)` to `(\w+)` in the type export matching regex
- [ ] Add unit test to verify type export matching works

## Phase 2: Add `./inertia` Module Export

- [ ] Create `src/js/src/inertia-types.ts` with base type interfaces
- [ ] Update `package.json` exports to include `"./inertia"`
- [ ] Update build scripts to compile the new module
- [ ] Add test for module resolution

## Phase 3: Python Type Name Resolution (Key Fix)

- [ ] Add `_normalize_type_name()` helper to `src/py/litestar_vite/_codegen/inertia.py`
- [ ] Integrate normalization into `_finalize_inertia_pages()`
- [ ] Add tests for module-prefixed name stripping

## Phase 4: Improve Warning Messages

- [ ] Update console warning in `emit-page-props-types.ts` with actionable guidance
- [ ] Include example of `TypeGenConfig.type_import_paths` in warning

## Phase 5: Add Index Signature to FullSharedProps

- [ ] Update `emit-page-props-types.ts` to add index signature to `FullSharedProps`
- [ ] Update test expectations

## Phase 6: Testing with litestar-fullstack-inertia

- [ ] Update `litestar-fullstack-inertia/package.json` to use local build:
  ```json
  "litestar-vite-plugin": "file:../litestar-vite"
  ```
- [ ] Run `npm run build` in litestar-vite
- [ ] Run `npm install` in litestar-fullstack-inertia
- [ ] Run `litestar assets generate-types`
- [ ] Verify `npx tsc --noEmit resources/lib/generated/page-props.ts` passes
- [ ] Fix `global.d.ts` to use correct type pattern
- [ ] Verify full TypeScript compilation passes

## Phase 7: Documentation

- [ ] Update migration guide with `TypeGenConfig.type_import_paths` usage
- [ ] Document automatic type name normalization behavior
- [ ] Document correct Inertia.js typing pattern for `usePage<T>()`

## Phase 8: Quality Gate

- [ ] All existing tests pass (`make test`)
- [ ] Linting passes (`make lint`)
- [ ] New tests have 90%+ coverage for modified modules
- [ ] E2E validation with litestar-fullstack-inertia passes

## Implementation Priority

1. **Phase 1** - Critical regex fix (immediate impact)
2. **Phase 3** - Type name normalization (addresses root cause for mangled names)
3. **Phase 5** - Index signature (fixes type compatibility)
4. **Phase 2** - Module export (fixes augmentation)
5. **Phase 4** - Better warnings (improves DX)
6. **Phase 6** - Validation (ensures fix works)
7. **Phase 7** - Documentation
8. **Phase 8** - Quality gate
