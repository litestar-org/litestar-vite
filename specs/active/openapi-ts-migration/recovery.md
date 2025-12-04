# Recovery Guide: OpenAPI-TS Configuration Migration

## Current State
PRD and tasks created with full analysis. Ready to begin implementation.

## Files Modified
- `specs/active/openapi-ts-migration/prd.md` - Created
- `specs/active/openapi-ts-migration/tasks.md` - Created

## Files to Create/Modify
See tasks.md for full list

## Next Steps
1. Remove SDK config from HTMX example (server-rendered, no SDK needed)
2. Update CLI to use correct plugin names
3. Rename template files to `openapi-ts.config.ts.j2`
4. Update template content with idiomatic framework paths
5. Rename example config files to `openapi-ts.config.ts`
6. Fix path mismatches in example configs
7. Update package.json references
8. Run tests

## Context for Resumption

### Key Findings

1. **Config Naming Convention**: The @hey-api/openapi-ts project standardized on `openapi-ts.config.ts` as the config filename

2. **Plugin Name Changes** (v0.57.0):
   - `@hey-api/types` -> `@hey-api/typescript`
   - `@hey-api/services` -> `@hey-api/sdk`

3. **CLI Fallback Uses Deprecated Names**: The CLI fallback path uses outdated plugin names

4. **HTMX Should NOT Have SDK**: Server-rendered apps don't need client SDK generation

5. **Idiomatic Paths by Framework**:

| Framework | Idiomatic Path |
|-----------|---------------|
| React/Vue/Svelte (Vite) | `./src/generated/` |
| Angular (Vite/CLI) | `./src/generated/` |
| Inertia (all variants) | `./resources/generated/` |
| Nuxt | `./generated/` |
| SvelteKit | `./src/lib/generated/` |
| Astro | `./src/generated/` |
| HTMX | **NO CONFIG** |

### Working Examples (5/13)
- angular, react, vue, svelte, jinja-htmx (but htmx shouldn't have it)

### CLI Code Location
`src/py/litestar_vite/cli.py` function `_run_openapi_ts` (lines 960-1036):
- Lines 996-1001: Config file detection order
- Lines 1015-1017: Fallback plugin names (OUTDATED - uses @hey-api/types, @hey-api/services)

### Files to Rename (Templates)
- `base/hey-api.config.ts.j2` -> `openapi-ts.config.ts.j2`
- `angular/hey-api.config.ts.j2` -> `openapi-ts.config.ts.j2`
- `angular-cli/hey-api.config.ts.j2` -> `openapi-ts.config.ts.j2`
- `nuxt/hey-api.config.ts.j2` -> `openapi-ts.config.ts.j2`
- `sveltekit/hey-api.config.ts.j2` -> `openapi-ts.config.ts.j2`
- `astro/hey-api.config.ts.j2` -> `openapi-ts.config.ts.j2`

### Files to Rename (Examples)
12 examples (all except htmx):
- react, react-inertia, react-inertia-jinja
- vue, vue-inertia, vue-inertia-jinja
- svelte, sveltekit
- angular, angular-cli
- nuxt, astro

### Migration Notes from Upstream
- v0.57.0: Plugin renames (@hey-api/types -> @hey-api/typescript, @hey-api/services -> @hey-api/sdk)
- v0.73.0+: Clients are bundled by default
- v0.86.0: Node 18 dropped, minimum is 20.19
- v0.87.0: Legacy clients removed

### Sources
- [Hey API Migration Guide](https://heyapi.dev/openapi-ts/migrating)
- [Hey API Configuration](https://heyapi.dev/openapi-ts/configuration)
- [GitHub Repository](https://github.com/hey-api/openapi-ts)
