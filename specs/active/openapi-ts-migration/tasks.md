# Tasks: OpenAPI-TS Configuration Migration

## Phase 1: Planning
- [x] Create PRD
- [x] Identify all affected files
- [x] Research upstream conventions
- [x] Determine idiomatic paths per framework

## Phase 2: Implementation - HTMX Cleanup

### 2.1 Remove SDK from HTMX (Server-rendered, no client SDK needed)
- [ ] Delete `examples/jinja-htmx/hey-api.config.ts`
- [ ] Delete `examples/jinja-htmx/src/generated/` directory
- [ ] Remove `generate-types` script from `examples/jinja-htmx/package.json` (if present)
- [ ] Remove `@hey-api/openapi-ts` from `examples/jinja-htmx/package.json` devDependencies

## Phase 3: Implementation - Templates

### 3.1 Rename Template Files
- [ ] Rename `src/py/litestar_vite/templates/base/hey-api.config.ts.j2` to `openapi-ts.config.ts.j2`
- [ ] Rename `src/py/litestar_vite/templates/angular/hey-api.config.ts.j2` to `openapi-ts.config.ts.j2`
- [ ] Rename `src/py/litestar_vite/templates/angular-cli/hey-api.config.ts.j2` to `openapi-ts.config.ts.j2`
- [ ] Rename `src/py/litestar_vite/templates/nuxt/hey-api.config.ts.j2` to `openapi-ts.config.ts.j2`
- [ ] Rename `src/py/litestar_vite/templates/sveltekit/hey-api.config.ts.j2` to `openapi-ts.config.ts.j2`
- [ ] Rename `src/py/litestar_vite/templates/astro/hey-api.config.ts.j2` to `openapi-ts.config.ts.j2`

### 3.2 Update Template Content - Paths
Update each template to use the idiomatic path for its framework:

- [ ] `base/openapi-ts.config.ts.j2` - `./src/generated/` (default for Vite frameworks)
- [ ] `nuxt/openapi-ts.config.ts.j2` - `./generated/`
- [ ] `sveltekit/openapi-ts.config.ts.j2` - `./src/lib/generated/`
- [ ] Create Inertia-specific templates with `./resources/generated/` path

### 3.3 Update Template Content - Plugin Names
- [ ] Update `react-tanstack/openapi-ts.config.ts.j2` - change `@hey-api/types` to `@hey-api/typescript`
- [ ] Verify all templates use correct plugin names (`@hey-api/typescript`, `@hey-api/sdk`, `@hey-api/schemas`)

### 3.4 Remove HTMX Template SDK Config
- [ ] Remove/skip `hey-api.config.ts.j2` for htmx template in scaffolding

## Phase 4: Implementation - Examples

### 4.1 Rename Config Files (12 files - NOT htmx)
- [ ] `git mv examples/react/hey-api.config.ts examples/react/openapi-ts.config.ts`
- [ ] `git mv examples/react-inertia/hey-api.config.ts examples/react-inertia/openapi-ts.config.ts`
- [ ] `git mv examples/react-inertia-jinja/hey-api.config.ts examples/react-inertia-jinja/openapi-ts.config.ts`
- [ ] `git mv examples/vue/hey-api.config.ts examples/vue/openapi-ts.config.ts`
- [ ] `git mv examples/vue-inertia/hey-api.config.ts examples/vue-inertia/openapi-ts.config.ts`
- [ ] `git mv examples/vue-inertia-jinja/hey-api.config.ts examples/vue-inertia-jinja/openapi-ts.config.ts`
- [ ] `git mv examples/svelte/hey-api.config.ts examples/svelte/openapi-ts.config.ts`
- [ ] `git mv examples/sveltekit/hey-api.config.ts examples/sveltekit/openapi-ts.config.ts`
- [ ] `git mv examples/angular/hey-api.config.ts examples/angular/openapi-ts.config.ts`
- [ ] `git mv examples/angular-cli/hey-api.config.ts examples/angular-cli/openapi-ts.config.ts`
- [ ] `git mv examples/nuxt/hey-api.config.ts examples/nuxt/openapi-ts.config.ts`
- [ ] `git mv examples/astro/hey-api.config.ts examples/astro/openapi-ts.config.ts`

### 4.2 Fix Config Path - Idiomatic Framework Paths
- [ ] `examples/react-inertia/openapi-ts.config.ts` - `./resources/generated/`
- [ ] `examples/react-inertia-jinja/openapi-ts.config.ts` - `./resources/generated/`
- [ ] `examples/vue-inertia/openapi-ts.config.ts` - `./resources/generated/`
- [ ] `examples/vue-inertia-jinja/openapi-ts.config.ts` - `./resources/generated/`
- [ ] `examples/nuxt/openapi-ts.config.ts` - `./generated/`
- [ ] `examples/sveltekit/openapi-ts.config.ts` - `./src/lib/generated/`

### 4.3 Update package.json Scripts
- [ ] Update `examples/react/package.json` - change `--config hey-api.config.ts` to `--config openapi-ts.config.ts`
- [ ] Update all other package.json files with config references

## Phase 5: Implementation - CLI

### 5.1 Update Plugin Names
- [ ] In `src/py/litestar_vite/cli.py` line ~1015: Change `@hey-api/types` to `@hey-api/typescript`
- [ ] In `src/py/litestar_vite/cli.py` line ~1017: Change `@hey-api/services` to `@hey-api/sdk`

### 5.2 Update Config File Detection Order
- [ ] In `src/py/litestar_vite/cli.py` lines 996-1001: Prioritize `openapi-ts.config.ts` over `hey-api.config.ts`

## Phase 6: Update Template Registration
- [ ] Check `src/py/litestar_vite/scaffolding/templates.py` for filename mappings
- [ ] Update any hardcoded references to `hey-api.config.ts`
- [ ] Ensure HTMX template doesn't include openapi config

## Phase 7: Testing
- [ ] Run `make lint`
- [ ] Run `make test`
- [ ] Manual test: `litestar assets init` scaffolding
- [ ] Manual test: `litestar assets generate-types` in react example

## Phase 8: Documentation
- [ ] Update any docs referencing `hey-api.config.ts`

## Phase 9: Quality Gate
- [ ] All tests pass
- [ ] Linting clean
- [ ] Archive workspace

---

## Summary of Path Changes

| Example | Old Path | New Path |
|---------|----------|----------|
| react, vue, svelte, angular, angular-cli, astro | `./src/generated/` | `./src/generated/` (no change) |
| react-inertia, react-inertia-jinja | `./src/generated/` | `./resources/generated/` |
| vue-inertia, vue-inertia-jinja | `./src/generated/` | `./resources/generated/` |
| nuxt | `./src/generated/` | `./generated/` |
| sveltekit | `./src/generated/` | `./src/lib/generated/` |
| jinja-htmx | `./src/generated/` | **REMOVE** |
