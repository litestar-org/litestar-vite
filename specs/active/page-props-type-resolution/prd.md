# PRD: Page Props Type Resolution Fix

## Overview
- **Slug**: page-props-type-resolution
- **Created**: 2025-12-16
- **Status**: Ready for Implementation
- **Issue**: [#160](https://github.com/litestar-org/litestar-vite/issues/160)
- **Reporter**: litestar-fullstack-inertia team

## Problem Statement

When running `litestar assets generate-types`, the generated `page-props.ts` file contains TypeScript errors due to:

1. **Missing imports**: Types like `Message`, `Team` exist in `types.gen.ts` but aren't imported
2. **Mangled type names**: Python module paths like `app_lib_schema_NoProps` appear instead of clean type names
3. **Missing type definitions**: Some types like `EmailSent` don't exist anywhere
4. **Invalid module augmentation**: `declare module "litestar-vite-plugin/inertia"` references a non-existent export

### Reproduction (from litestar-fullstack-inertia)

```bash
cd /home/cody/code/litestar/litestar-fullstack-inertia
npx tsc --noEmit resources/lib/generated/page-props.ts
```

**Current errors:**
```
page-props.ts(84,24): error TS2304: Cannot find name 'app_lib_schema_NoProps'.
page-props.ts(85,33): error TS2304: Cannot find name 'app_domain_accounts_schemas_PasswordResetToken'.
page-props.ts(86,27): error TS2304: Cannot find name 'EmailSent'.
page-props.ts(87,19): error TS2304: Cannot find name 'Message'.
page-props.ts(91,16): error TS2304: Cannot find name 'Team'.
page-props.ts(110,16): error TS2664: Invalid module name in augmentation...
```

## Root Cause Analysis

### 1. Critical Bug: Broken Regex in TypeScript Generator

**File**: `src/js/src/shared/emit-page-props-types.ts:212`

```typescript
// BUG: Double-escaped backslash prevents matching
for (const match of content.matchAll(/export (?:type|interface|enum|class) (\\w+)/g)) {
```

The regex `\\w+` (escaped backslash) looks for literal `\w+` instead of word characters. This means `availableApiTypes` is **always empty**, so no types from `types.gen.ts` are ever imported.

### 2. Python Type Name Mangling

When the OpenAPI schema doesn't include a type (internal schemas excluded from API), the Python codegen falls back to using Litestar's `_get_normalized_schema_key()` which produces module-prefixed names like:
- `app_lib_schema_NoProps` (from `app.lib.schema.NoProps`)
- `app_domain_accounts_schemas_PasswordResetToken` (from `app.domain.accounts.schemas.PasswordResetToken`)

These mangled names don't exist in `types.gen.ts` which uses OpenAPI schema naming.

### 3. Missing Module Export for Augmentation

The `package.json` exports don't include `./inertia`:

```json
"exports": {
  ".": { ... },
  "./helpers": { ... },
  "./inertia-helpers": { ... },
  // Missing: "./inertia": { ... }
}
```

TypeScript module augmentation with `declare module "litestar-vite-plugin/inertia"` fails because the module path doesn't resolve.

### 4. Empty `typeImportPaths`

The JSON output shows `typeImportPaths: {}` because:
- Users haven't configured `TypeGenConfig.type_import_paths`
- The system doesn't auto-populate import paths from the OpenAPI schema

## Goals

1. Fix the regex bug to enable type imports from `types.gen.ts`
2. Improve Python type name resolution to use clean OpenAPI names
3. Add `./inertia` export for proper module augmentation
4. Provide clear guidance for unresolved types via warnings and documentation

## Non-Goals

- Auto-generating type definitions for schemas excluded from OpenAPI (user should configure)
- Supporting non-standard OpenAPI type generators (focus on @hey-api/openapi-ts)
- Breaking changes to existing `TypeGenConfig` API
- Removing or limiting existing extensibility mechanisms

## Extensibility Preservation (Critical)

The current system provides several extensibility points that MUST be preserved:

### 1. Module Augmentation for User/AuthData/SharedProps

Users can extend the generated types via TypeScript module augmentation:

```typescript
// This pattern MUST continue to work
declare module "litestar-vite-plugin/inertia" {
  interface User {
    avatarUrl?: string
    roles: Role[]
  }
  interface SharedProps {
    locale?: string
    currentTeam?: Team
  }
}
```

### 2. TypeGenConfig.type_import_paths

Users can specify import paths for custom types not in OpenAPI:

```python
# This configuration MUST continue to work
TypeGenConfig(
    type_import_paths={
        "CustomUser": "@/types/user",
        "OffsetPagination": "@/types/pagination",
    }
)
```

### 3. InertiaTypeGenConfig Settings

Users can customize default type generation:

```python
# These settings MUST continue to work
InertiaConfig(
    type_gen=InertiaTypeGenConfig(
        include_default_auth=False,  # Disable built-in User/AuthData
        include_default_flash=False, # Disable built-in FlashMessages
    )
)
```

### 4. Custom sharedProps via extra_static_page_props

Users can add static shared props with custom types:

```python
# This MUST continue to work
InertiaConfig(
    extra_static_page_props={
        "locale": "en",
        "currentTeam": None,  # Type inferred from value
    }
)
```

### Compatibility Requirements

All fixes MUST:

- Preserve existing `TypeGenConfig.type_import_paths` functionality
- Not change the structure of generated interfaces in breaking ways
- Maintain module augmentation as the primary extension mechanism
- Keep `SharedProps` as an empty interface for user extension
- Automatically normalize mangled type names when short name exists in OpenAPI

## Acceptance Criteria

- [ ] `npx tsc --noEmit page-props.ts` passes with no errors in litestar-fullstack-inertia
- [ ] Types from `types.gen.ts` are properly imported
- [ ] Module augmentation resolves correctly
- [ ] Unresolved types produce clear console warnings with actionable guidance
- [ ] All existing tests pass
- [ ] New tests cover the fixed functionality

## Technical Approach

### Phase 1: Fix TypeScript Regex Bug (Critical)

**File**: `src/js/src/shared/emit-page-props-types.ts`

```typescript
// Line 212: Fix the regex
// Before:
for (const match of content.matchAll(/export (?:type|interface|enum|class) (\\w+)/g)) {

// After:
for (const match of content.matchAll(/export (?:type|interface|enum|class) (\w+)/g)) {
```

### Phase 2: Add `./inertia` Export

**File**: `package.json`

Add a new export that provides the types for module augmentation:

```json
"exports": {
  // ... existing exports ...
  "./inertia": {
    "types": "./dist/js/inertia-types.d.ts",
    "import": "./dist/js/inertia-types.js"
  }
}
```

Create `src/js/src/inertia-types.ts`:
```typescript
// Re-exports for module augmentation
// The actual interfaces are generated per-project in page-props.ts
// This module provides the augmentation target

export interface User {}
export interface AuthData {}
export interface FlashMessages {}
export interface SharedProps {}
export interface GeneratedSharedProps {}
export type FullSharedProps = GeneratedSharedProps & SharedProps
export interface PageProps {}
export type ComponentName = keyof PageProps
export type InertiaPageProps<C extends ComponentName> = PageProps[C]
export type PagePropsFor<C extends ComponentName> = PageProps[C]
```

### Phase 3: Improve Type Name Resolution in Python

**File**: `src/py/litestar_vite/_codegen/inertia.py`

Add logic to strip module prefixes from mangled names when the clean name matches an OpenAPI schema:

```python
def _normalize_type_name(type_name: str, openapi_schemas: set[str]) -> str:
    """Strip module prefix from mangled type names.

    Always converts 'app_lib_schema_NoProps' -> 'NoProps' because:
    1. If 'NoProps' exists in OpenAPI, it will be imported correctly
    2. If 'NoProps' doesn't exist, the error message is clearer for users
       (they can add it to OpenAPI or configure type_import_paths)

    The mangled name 'app_lib_schema_NoProps' will NEVER work - it doesn't
    exist anywhere. The short name is always preferable.
    """
    if type_name in openapi_schemas:
        return type_name

    # Check if this looks like a mangled module path (contains underscores)
    if '_' not in type_name:
        return type_name

    # Try progressively shorter suffixes to find the class name
    parts = type_name.split('_')
    for i in range(len(parts)):
        short_name = '_'.join(parts[i:])
        # Prefer OpenAPI match, but if we get to the last part, use it anyway
        if short_name in openapi_schemas:
            return short_name

    # Use the last part as the class name (e.g., 'NoProps' from 'app_lib_schema_NoProps')
    # This is always better than the mangled name for error messages
    return parts[-1] if parts else type_name
```

### Phase 4: Improve Warning Messages

**File**: `src/js/src/shared/emit-page-props-types.ts`

Enhance the warning to provide actionable guidance:

```typescript
if (unresolvedTypes.length > 0) {
  console.warn(
    `litestar-vite: Unresolved Inertia props types: ${unresolvedTypes.join(", ")}.\n` +
    `  To fix:\n` +
    `  1. Add to OpenAPI by including in route return types\n` +
    `  2. Or configure TypeGenConfig.type_import_paths:\n` +
    `     types=TypeGenConfig(type_import_paths={"${unresolvedTypes[0]}": "@/types/custom"})`
  );
}
```

### Phase 5: Testing with litestar-fullstack-inertia

**Pre-test setup**:
1. Update `litestar-fullstack-inertia/package.json` to use local build:
   ```json
   "litestar-vite-plugin": "file:../litestar-vite"
   ```
2. Rebuild litestar-vite: `npm run build`
3. Regenerate types: `litestar assets generate-types`
4. Verify: `npx tsc --noEmit resources/lib/generated/page-props.ts`

## Affected Files

### TypeScript (fixes)
- `src/js/src/shared/emit-page-props-types.ts` - Regex fix + warning improvement
- `src/js/src/inertia-types.ts` - NEW: Module augmentation target
- `package.json` - Add `./inertia` export

### Python (improvements)
- `src/py/litestar_vite/_codegen/inertia.py` - Type name normalization
- `src/py/litestar_vite/_codegen/openapi.py` - Expose schema name lookup

### Tests (new)
- `src/js/tests/page-props-generator.test.ts` - Add type import tests
- `src/py/tests/unit/test_codegen_page_props.py` - Add type normalization tests

### Validation
- `/home/cody/code/litestar/litestar-fullstack-inertia` - Real-world test project

## Testing Strategy

### Unit Tests
1. Test regex correctly matches type exports
2. Test type name normalization strips prefixes correctly
3. Test import generation includes matched types

### Integration Tests
1. Generate page-props.ts with various type scenarios
2. Verify TypeScript compilation succeeds
3. Verify module augmentation resolves

### E2E Validation
1. Link local litestar-vite build to litestar-fullstack-inertia
2. Run `litestar assets generate-types`
3. Verify `npx tsc --noEmit` passes

## Implementation Order

1. **Fix regex bug** (immediate impact, low risk)
2. **Add ./inertia export** (fixes module augmentation)
3. **Improve warning messages** (better DX)
4. **Python type name normalization** (addresses root cause)
5. **Test with litestar-fullstack-inertia** (validation)
6. **Add comprehensive tests** (prevent regression)

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Regex fix changes import behavior | M | Test with multiple projects before release |
| New export breaks existing code | L | Export is additive, no breaking changes |
| Type normalization produces wrong names | M | Only normalize when exact match exists in OpenAPI |
| litestar-fullstack-inertia has other issues | M | Fix one issue at a time, document remaining |

## Success Metrics

- Zero TypeScript errors in generated `page-props.ts`
- Clear warning messages for unresolved types
- All tests pass in CI
- litestar-fullstack-inertia validates the fix

## Additional Issue: InertiaProps Type Compatibility

### Problem

The `global.d.ts` in litestar-fullstack-inertia has a type architecture issue:

```typescript
// Current (broken)
interface InertiaProps extends Page<PageProps>, FullSharedProps {
  flash: FlashMessages
  errors: Errors & ErrorBag  // Conflicts with FullSharedProps.errors!
  csrf_token: string
  auth?: AuthData
  currentTeam?: CurrentTeam
}
```

This causes two TypeScript errors:
1. **Index signature missing**: `PageProps` from `@inertiajs/core` has `[key: string]: unknown`, but `InertiaProps` doesn't inherit this
2. **Type incompatibility**: `errors: Errors & ErrorBag` conflicts with `errors?: Record<string, string[]>` from `GeneratedSharedProps`

### Root Cause

The user is mixing two incompatible type hierarchies:
- `Page<PageProps>` - Inertia's full page structure (has `component`, `url`, `props`, etc.)
- `FullSharedProps` - Just the props interface (doesn't have page structure)

### Solution for litestar-fullstack-inertia

Use Inertia's recommended module augmentation pattern instead:

```typescript
// resources/types/global.d.ts - FIXED

import type { FullSharedProps, PageProps as LitestarPageProps } from "@/lib/generated/page-props"

// Option 1: Augment Inertia's config (recommended)
declare module '@inertiajs/core' {
  interface InertiaConfig {
    sharedPageProps: FullSharedProps
    errorValueType: string[]
  }
}

// Then use in components:
// const { auth, flash } = usePage().props  // Fully typed!

// Option 2: Create a simple type alias (simpler)
type AppPageProps = FullSharedProps & {
  [key: string]: unknown  // Add index signature for compatibility
}

// Then use as:
// usePage<{ props: AppPageProps }>().props

declare global {
  interface Window {
    axios: AxiosInstance
  }
}
```

### Changes to Generated `page-props.ts`

To support easier integration, add an index signature to `FullSharedProps`:

```typescript
export type FullSharedProps = GeneratedSharedProps & SharedProps & {
  [key: string]: unknown  // Allow additional props
}
```

Or provide a separate type for use with `usePage<T>()`:

```typescript
/** Use with usePage<InertiaAppPage>() for full typing */
export type InertiaAppPage = {
  props: FullSharedProps & { [key: string]: unknown }
}
```

## Follow-up Tasks (Post-Fix)

1. Document `TypeGenConfig.type_import_paths` usage in migration guide
2. Add example of custom type configuration in docs
3. Consider auto-populating import paths from OpenAPI schema analysis
4. Document the correct Inertia.js typing pattern for module augmentation
5. Update litestar-fullstack-inertia's global.d.ts with working types
