# Recovery Guide: Page Props Type Resolution Fix

## Current State

PRD and tasks have been created. Ready for implementation.

## Files to Modify

### TypeScript (Critical Fixes)

| File | Status | Changes |
|------|--------|---------|
| `src/js/src/shared/emit-page-props-types.ts` | Pending | Fix regex, add index signature, improve warnings |
| `src/js/src/inertia-types.ts` | NEW | Module augmentation target |
| `package.json` | Pending | Add `./inertia` export |

### Python (Enhancements)

| File | Status | Changes |
|------|--------|---------|
| `src/py/litestar_vite/inertia/schema.py` | NEW | NoProps, Message, EmailSent schemas |
| `src/py/litestar_vite/inertia/__init__.py` | Pending | Export new schemas |
| `src/py/litestar_vite/_codegen/inertia.py` | Pending | Type name normalization |

### Tests

| File | Status | Changes |
|------|--------|---------|
| `src/js/tests/page-props-generator.test.ts` | Pending | Add type import tests |
| `src/py/tests/unit/test_codegen_page_props.py` | Pending | Add normalization tests |

### Validation

| File | Status | Changes |
|------|--------|---------|
| `/home/cody/code/litestar/litestar-fullstack-inertia/package.json` | Pending | Link to local build |
| `/home/cody/code/litestar/litestar-fullstack-inertia/resources/types/global.d.ts` | Pending | Fix type pattern |

## Next Steps

1. Start with the regex fix in `emit-page-props-types.ts` (Phase 1)
2. Build and test locally
3. Link to litestar-fullstack-inertia for validation
4. Continue through remaining phases

## Key Context

### The Regex Bug (Most Critical)

Line 212 of `emit-page-props-types.ts`:

```typescript
// BROKEN - looks for literal \w+ instead of word characters
/export (?:type|interface|enum|class) (\\w+)/g

// FIXED - matches word characters correctly
/export (?:type|interface|enum|class) (\w+)/g
```

### litestar-fullstack-inertia Location

```
/home/cody/code/litestar/litestar-fullstack-inertia
```

### Test Commands

```bash
# In litestar-vite
npm run build
make test

# In litestar-fullstack-inertia
npm install
litestar assets generate-types
npx tsc --noEmit resources/lib/generated/page-props.ts
```

## Issue Reference

GitHub Issue: [#160](https://github.com/litestar-org/litestar-vite/issues/160)

Do NOT update the issue - report findings back to user for relay.
