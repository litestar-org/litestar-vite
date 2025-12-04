# PRD: OpenAPI-TS Configuration Migration and SDK Generation Fix

## Overview
- **Slug**: openapi-ts-migration
- **Created**: 2025-12-04
- **Status**: Draft

## Problem Statement

The litestar-vite project has three critical issues with its @hey-api/openapi-ts integration:

1. **Config File Naming Convention**: The project uses `hey-api.config.ts` across all examples and templates, but the upstream @hey-api/openapi-ts project has standardized on `openapi-ts.config.ts` as the configuration filename convention (since v0.57.0+).

2. **CLI Fallback Uses Deprecated Plugin Names**: The `litestar assets generate-types` CLI command's fallback path (when no config file is found) uses deprecated plugin names:
   - `@hey-api/types` should be `@hey-api/typescript` (renamed in v0.57.0)
   - `@hey-api/services` should be `@hey-api/sdk` (renamed in v0.57.0)

3. **Path Mismatches in Config Files**: Several example config files have incorrect input/output paths that don't match the actual project structure:
   - **Inertia examples** (react-inertia, react-inertia-jinja, vue-inertia, vue-inertia-jinja): Config points to `./src/generated/` but actual files are at `./resources/generated/`
   - **Nuxt example**: Config points to `./src/generated/` but actual files are at `./generated/`
   - **Sveltekit example**: `src/generated/` directory doesn't exist at all

Additionally, there's inconsistency: one template (`react-tanstack`) already uses `openapi-ts.config.ts.j2` while all others use `hey-api.config.ts`.

### Idiomatic Generated File Paths by Framework

Each framework has its own idiomatic location for generated files:

| Framework | Idiomatic Path | Reason |
|-----------|---------------|--------|
| **React/Vue/Svelte** (Vite) | `./src/generated/` | Standard Vite `src/` convention |
| **Angular** (Vite) | `./src/generated/` | Angular with Vite uses `src/` |
| **Angular-CLI** | `./src/generated/` | Angular CLI uses `src/` |
| **Inertia** (all variants) | `./resources/generated/` | Laravel-style resources directory |
| **Nuxt** | `./generated/` | Nuxt uses root-level directories |
| **SvelteKit** | `./src/lib/generated/` | SvelteKit convention for shared libs |
| **Astro** | `./src/generated/` | Astro uses `src/` convention |
| **HTMX** | **NO CONFIG** | Server-rendered, no SDK generation needed |

### SDK Generation Status by Example

| Example | Has sdk.gen.ts | Current openapi.json | Correct Path | Status |
|---------|---------------|---------------------|--------------|--------|
| angular | 45 lines | src/generated/ | `./src/generated/` | Working |
| angular-cli | NO | src/generated/ | `./src/generated/` | **Needs SDK gen** |
| astro | NO | src/generated/ | `./src/generated/` | **Needs SDK gen** |
| jinja-htmx | 64 lines | src/generated/ | **REMOVE CONFIG** | Should not have SDK |
| nuxt | NO | generated/ | `./generated/` | **PATH MISMATCH** |
| react | 46 lines | src/generated/ | `./src/generated/` | Working |
| react-inertia | NO | resources/generated/ | `./resources/generated/` | **PATH MISMATCH** |
| react-inertia-jinja | NO | resources/generated/ | `./resources/generated/` | **PATH MISMATCH** |
| svelte | 46 lines | src/generated/ | `./src/generated/` | Working |
| sveltekit | NO | src/lib/generated/ | `./src/lib/generated/` | **PATH MISMATCH** |
| vue | 46 lines | src/generated/ | `./src/generated/` | Working |
| vue-inertia | NO | resources/generated/ | `./resources/generated/` | **PATH MISMATCH** |
| vue-inertia-jinja | NO | resources/generated/ | `./resources/generated/` | **PATH MISMATCH** |

## Goals
1. Rename all config files from `hey-api.config.ts` to `openapi-ts.config.ts` in examples (except htmx)
2. Rename all config template files from `hey-api.config.ts.j2` to `openapi-ts.config.ts.j2` in templates
3. Update CLI code to use correct plugin names in the fallback path
4. Update CLI config file detection to prioritize `openapi-ts.config.ts` over `hey-api.config.ts`
5. Update package.json scripts in examples to reference the new config filename
6. Ensure all templates use modern plugin names (`@hey-api/typescript`, `@hey-api/sdk`)
7. **Fix path mismatches** in example config files to use idiomatic framework paths
8. **Remove SDK/openapi config from HTMX** - it's server-rendered and doesn't need client SDK

## Non-Goals
- Changing the overall hey-api/openapi-ts library version requirements
- Adding new features to the SDK generation
- Changing the plugin configuration options (just the names)

## Acceptance Criteria
- [ ] All `hey-api.config.ts` files renamed to `openapi-ts.config.ts` in examples (13 files)
- [ ] All `hey-api.config.ts.j2` templates renamed to `openapi-ts.config.ts.j2` (6 files)
- [ ] CLI `_run_openapi_ts` function uses `@hey-api/typescript` and `@hey-api/sdk` instead of deprecated names
- [ ] CLI config file detection order updated: `openapi-ts.config.ts` checked first
- [ ] Package.json scripts updated to use `--config openapi-ts.config.ts`
- [ ] Template file mapping in `templates.py` updated for new filenames
- [ ] `make test` passes
- [ ] `make lint` passes
- [ ] SDK generation works correctly when running `litestar assets generate-types`

## Technical Approach

### Architecture
The changes affect three layers:
1. **Examples** - Static config files used as reference implementations
2. **Templates** - Jinja2 templates for scaffolding new projects
3. **CLI** - Python code that runs the type generation

### Affected Files

#### Examples (rename `hey-api.config.ts` to `openapi-ts.config.ts`)
- `examples/react-inertia-jinja/hey-api.config.ts`
- `examples/jinja-htmx/hey-api.config.ts`
- `examples/angular/hey-api.config.ts`
- `examples/vue/hey-api.config.ts`
- `examples/vue-inertia/hey-api.config.ts`
- `examples/angular-cli/hey-api.config.ts`
- `examples/sveltekit/hey-api.config.ts`
- `examples/astro/hey-api.config.ts`
- `examples/nuxt/hey-api.config.ts`
- `examples/react-inertia/hey-api.config.ts`
- `examples/svelte/hey-api.config.ts`
- `examples/react/hey-api.config.ts`
- `examples/vue-inertia-jinja/hey-api.config.ts`

#### Templates (rename `hey-api.config.ts.j2` to `openapi-ts.config.ts.j2`)
- `src/py/litestar_vite/templates/base/hey-api.config.ts.j2`
- `src/py/litestar_vite/templates/angular/hey-api.config.ts.j2`
- `src/py/litestar_vite/templates/angular-cli/hey-api.config.ts.j2`
- `src/py/litestar_vite/templates/nuxt/hey-api.config.ts.j2`
- `src/py/litestar_vite/templates/sveltekit/hey-api.config.ts.j2`
- `src/py/litestar_vite/templates/astro/hey-api.config.ts.j2`

#### Python Code
- `src/py/litestar_vite/cli.py` - Update `_run_openapi_ts` function:
  - Line 996-1001: Update config file detection order
  - Line 1015-1017: Update plugin names from `@hey-api/types` and `@hey-api/services` to `@hey-api/typescript` and `@hey-api/sdk`

#### Package.json Updates
All examples with `generate-types` script need updating:
- `examples/react/package.json` - line 10: `--config hey-api.config.ts` -> `--config openapi-ts.config.ts`
- (Check all other examples for similar scripts)

#### Template Registration
- `src/py/litestar_vite/scaffolding/templates.py` - Update file mappings if present

### Implementation Notes

1. The CLI already checks for both `hey-api.config.ts` and `openapi-ts.config.ts` (lines 996-1001), but the order should prioritize the new convention.

2. The `react-tanstack` template already uses `openapi-ts.config.ts.j2` - this is the correct pattern to follow.

3. The `react-tanstack/openapi-ts.config.ts.j2` uses `@hey-api/types` which should also be updated to `@hey-api/typescript`.

## Testing Strategy
- Unit tests: Verify CLI correctly detects config files in both naming conventions
- Integration tests: Run `litestar assets generate-types` in example projects
- Manual testing: Scaffold a new project and verify SDK generation works

## Research Questions
- [x] What is the new config file convention? Answer: `openapi-ts.config.ts`
- [x] What are the current plugin names? Answer: `@hey-api/typescript`, `@hey-api/sdk`, `@hey-api/schemas`
- [x] What version introduced these changes? Answer: v0.57.0

## Risks & Mitigations
| Risk | Impact | Mitigation |
|------|--------|------------|
| Breaking existing projects that use `hey-api.config.ts` | Medium | CLI still checks for old filename as fallback |
| Template mapping changes could break scaffolding | Medium | Test `litestar assets init` after changes |
| Package.json scripts reference old config name | Low | Simple find-replace operation |
