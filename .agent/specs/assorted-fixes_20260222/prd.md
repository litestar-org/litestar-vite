# Flow PRD: Assorted Bug and Docs Fixes

## Context
There are a few open issues in `litestar-org/litestar-vite` that represent bugs or outdated documentation:
1. **Issue 195:** `routes.ts` generates undefined module-prefixed enum types instead of OpenAPI schema names.
2. **Issue 193:** Docs: logo link currently goes to `https://litestar-org.github.io/`, resulting in a 404.
3. **Issue 192:** Docs: Described property `TypeGenConfig.watch_patterns` does not exist.

## North Star Goal
Improve type generation correctness for `routes.ts` by correctly resolving OpenAPI references and keeping the documentation accurate and up-to-date.

## Roadmap
1. **Fix Issue 195:** Ensure `extract_route_metadata` in `src/py/litestar_vite/codegen/_routes.py` correctly uses `openapi_schema` to extract accurate parameter types (resolving module-prefixed names like `app_domain_insight_schemas__base_Granularity` back to their schema names like `Granularity`).
2. **Fix Issue 193:** Update `docs/conf.py` `logo_target` to `/litestar-vite/`.
3. **Fix Issue 192:** Remove `watch_patterns` references from `docs/usage/types.rst` and `docs/inertia/type-generation.rst`.

## Global Constraints
- Pass existing tests in `test_codegen.py`.
- Documentation changes should accurately reflect current configuration options.