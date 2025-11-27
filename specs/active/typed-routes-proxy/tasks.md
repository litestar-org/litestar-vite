# Tasks: Single-Source Typed Routes & One-Port Vite Proxy

## Phase 1: Planning & Research ✓
- [x] Create PRD
- [x] Identify affected components

## Phase 2: Expert Research
- [ ] Confirm minimal proxy path set for Vite HMR (HTTP + WS)
- [ ] Decide default openapi-ts client/plugins (types-only vs fetch + zod)
- [ ] Define internal Vite port selection strategy and env overrides

## Phase 3: Core Implementation
- [ ] Export routes/openapi to `src/generated` on startup (sync/async lifespan)
- [ ] Add proxy mode in VitePlugin (HTTP + WS) with auto/internal port and hotfile discovery
- [ ] Keep direct/two-port mode as opt-in
- [ ] Align defaults (assetUrl `/static/`, generated paths, envs)
- [ ] Remove duplicate route/type inference in JS; trim `_python_type_to_typescript` if unused

## Phase 4: Integration
- [ ] JS plugin: watch generated artifacts; emit `routes.ts`; run openapi-ts with debounce
- [ ] Wire proxy mode into dev startup/health checks; clear logging

## Phase 5: Testing (auto-invoked)
- [ ] Unit tests (routes export, proxy resolver, watcher triggers)
- [ ] Integration tests (startup writes artifacts; proxy HMR path; direct mode regression)
- [ ] Edge cases (missing openapi-ts, port conflict, custom asset base)

## Phase 6: Documentation (auto-invoked)
- [ ] Update README and docs/usage for proxy vs direct and new defaults
- [ ] Note migration (old paths removed; no backward compat)

## Phase 7: Quality Gate & Archive
- [ ] All quality gates pass
- [ ] Archive workspace
