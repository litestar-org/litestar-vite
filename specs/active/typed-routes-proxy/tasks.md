# Tasks: Single-Source Typed Routes & One-Port Vite Proxy

## Phase 1: Planning & Research ✓
- [x] Create PRD
- [x] Identify affected components

## Phase 2: Expert Research
- [x] Confirm minimal proxy path set for Vite HMR (HTTP + WS)
- [x] Decide default openapi-ts client/plugins (types-only vs fetch + zod)
- [x] Define internal Vite port selection strategy and env overrides
- [ ] Validate proxy/HMR assumptions with Angular Vite (Analog plugin) dev server; document any Angular-specific paths or ws behaviors

## Phase 3: Core Implementation
- [x] Export routes/openapi to `src/generated` on startup (sync/async lifespan)
- [x] Add proxy mode in VitePlugin (HTTP + WS) with auto/internal port and hotfile discovery
- [ ] Keep direct/two-port mode as opt-in
- [ ] Align defaults (assetUrl `/static/`, generated paths, envs)
- [ ] Remove duplicate route/type inference in JS; trim `_python_type_to_typescript` if unused
- [ ] Ensure Angular Vite scaffold uses proxy defaults (hotfile path, asset base) and is covered by single-port mode

## Phase 4: Integration
- [x] JS plugin: watch generated artifacts; emit `routes.ts`; run openapi-ts with debounce
- [x] Wire proxy mode into dev startup/health checks; clear logging
- [ ] Add integration checks for Angular Vite scaffold (dev + build) with new proxy/type-gen defaults

## Phase 5: Testing (auto-invoked)
- [x] Unit tests (proxy path matcher; hotfile/port selection)
- [x] Integration-ish tests for proxy HTTP + WS forwarding
- [ ] Unit tests (routes export, watcher triggers)
- [ ] Integration tests (startup writes artifacts; proxy HMR path; direct mode regression)
- [ ] Edge cases (missing openapi-ts, port conflict, custom asset base)
- [ ] Scaffold tests for Angular Vite template to ensure hotfile/proxy + asset base alignment

## Phase 6: Documentation (auto-invoked)
- [x] Update README and docs/usage for proxy vs direct and new defaults
- [ ] Note migration (old paths removed; no backward compat)
- [ ] Document Angular Vite compatibility and Angular-CLI exception (no litestar-vite plugin)

## Phase 7: Quality Gate & Archive
- [ ] All quality gates pass
- [ ] Archive workspace
