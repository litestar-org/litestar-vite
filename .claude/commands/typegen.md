---
description: Generate and verify litestar-vite TypeScript artifacts (routes, schemas, page props)
allowed-tools: Read, Write, Edit, Glob, Grep, Bash
---

# Type Generation Workflow

Generating types for: **$ARGUMENTS**

## Phase 1: Load Context

- Read `ViteConfig` and `TypeGenConfig` definitions
- Confirm output paths and feature flags

## Phase 2: Generate Artifacts

```bash
litestar assets generate-types
litestar assets export-routes
```

## Phase 3: Verify Outputs

Check for:
- `src/generated/openapi.json`
- `src/generated/routes.json`
- `src/generated/routes.ts`
- `src/generated/schemas.ts`
- `src/generated/inertia-pages.json`

Suggested checks:

```
Glob(pattern="src/generated/*")
```

## Phase 4: Report

Summarize:
- Generated files
- Any missing or stale outputs
- Required config adjustments (TypeGenConfig / InertiaTypeGenConfig)
