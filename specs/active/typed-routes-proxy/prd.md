# PRD: Single-Source Typed Routes & One-Port Vite Proxy

## Overview
- **Slug**: typed-routes-proxy
- **Created**: 2025-11-27
- **Status**: Draft

## Problem Statement
Developers need Litestar and Vite to work together with zero manual setup: typed routes and API helpers should be generated automatically, and HMR should work even when only the ASGI port is exposed. The current setup splits responsibility between Python and JS, requires two open ports, and duplicates route/type logic.

## Goals
1. Export canonical route and OpenAPI artifacts from Litestar at startup with no user action.
2. Generate TypeScript helpers/types (Ziggy-style routes + API client/types) automatically when those artifacts change.
3. Enable a default single-port dev experience by proxying Vite dev traffic (HTTP + WS/HMR) through the Litestar ASGI server, while retaining a direct two-port option.
4. Remove redundant/legacy type-generation code paths and unify defaults (paths, asset bases).

## Non-Goals
- Maintaining backward compatibility with prior type-gen paths or env defaults.
- Supporting frameworks beyond existing Vite/Litestar stack.
- Redesigning build/release pipelines.

## Acceptance Criteria
- [ ] On app startup, `src/generated/routes.json` is written (and `src/generated/openapi.json` when OpenAPI enabled) without user intervention.
- [ ] Vite plugin auto-generates `src/generated/routes.ts` and API types/client using `@hey-api/openapi-ts` from the exported artifacts on change; no manual CLI needed. If `@hey-api/openapi-ts` is missing, it should warn but not fail startup.
- [ ] Proxy mode (default) serves HMR via the ASGI port only; direct two-port mode remains opt-in.
- [ ] Asset base defaults match (`/static/` with trailing slash) across Python and JS.
- [ ] Duplicate route/type inference code removed or minimized; docs updated to new defaults.

## Technical Approach

### Architecture
- Python side:
  - In VitePlugin lifespan, always export routes/OpenAPI to `src/generated/`.
  - Keep `generate_routes_json` as single source; trim/remove `_python_type_to_typescript` duplication if unused after JS consumption.
  - Add proxy middleware (or extend VitePlugin) to forward HTTP+WS HMR paths to internal Vite dev server bound to 127.0.0.1 on an auto port; retain current direct mode via config/env.
- JS side (Vite plugin):
  - Watch `src/generated/routes.json` and `src/generated/openapi.json`.
  - Run `@hey-api/openapi-ts` (optional fetch client and zod plugins) and generate `routes.ts` helpers from `routes.json`.
  - Align defaults: assetUrl `/static/`; generated output `src/generated`.
- Config UX:
  - Env `VITE_PROXY_MODE=proxy|direct` (default proxy when `VITE_ALLOW_REMOTE` false).
  - Hotfile remains `public/hot`; used for proxy target discovery.

### Existing patterns to reuse or retire
- Current `ViteSPAHandler` proxies only root HTML via httpx to the external Vite dev server; it still requires an exposed Vite port. We will supersede it with the new internal proxy but can reuse its cached-prod-index flow.
- JS framework helpers (`src/js/src/astro.ts`, `sveltekit.ts`, `nuxt.ts`) already set up API dev proxies and logging; align their defaults with the new single-port mode to avoid duplicate proxy config paths.
- Fullstack and fullstack-inertia reference apps used the `hot` file + external Vite port for Jinja HMR; maintain the hotfile contract while defaulting to internal proxy.
- `_python_type_to_typescript` overlaps with `@hey-api/openapi-ts`; keep only minimal param mapping or remove once `routes.json` drives generation.
- Remove legacy root-level defaults (`openapi.json`, `routes.json` in project root) after migrating to `src/generated/*`.

### Affected Files
- `src/py/litestar_vite/plugin.py` - export pipeline, proxy mode.
- `src/py/litestar_vite/loader.py` (if needed for proxy/static alignment).
- `src/py/litestar_vite/codegen.py` - routes export cleanup.
- `src/js/src/index.ts` - watch paths, type generation, routes.ts emitter, proxy config defaults.
- `docs/usage/*`, `README.md` - new defaults, proxy/direct guidance.
- Tests: `src/py/tests/...`, `src/js/tests/...` for new behaviors.

### API Changes
- New/updated config flags:
  - `VITE_PROXY_MODE` (proxy|direct), default proxy unless remote allowed.
  - Paths for generated artifacts fixed to `src/generated/*`.
  - Possibly remove/ignore old `openapiPath`/`routesPath` defaults pointing to project root.

## Testing Strategy
- Unit: routes export function, proxy path resolution, type-gen trigger logic.
- Integration: app startup writes artifacts; proxy mode serves HMR over ASGI port; direct mode unchanged.
- JS: routes.ts generator and openapi-ts runner mocked; watcher tests.
- Edge: missing openapi-ts dependency warns not fails; proxy target down → clear error; asset base with custom env.

## Research Questions
- [ ] Best minimal proxy path set for Vite HMR (HTTP + WS) to ensure compatibility across frameworks?
- [ ] Should `@hey-api/openapi-ts` client default to fetch or remain types-only for tree-shaking?
- [ ] How to reliably pick a free internal port for Vite dev server on constrained platforms?

## Risks & Mitigations
| Risk | Impact | Mitigation |
|------|--------|------------|
| Proxy breaks HMR for some Vite plugins | M | Provide direct mode fallback and targeted proxy path list with tests |
| openapi-ts not installed | M | Emit warning, skip type-gen, keep routes.ts generation functional |
| Port conflicts for internal Vite | M | Auto-pick free port; allow override via env |
| Misaligned paths cause stale types | M | Single-source paths (`src/generated/*`) enforced in both Python and JS |
