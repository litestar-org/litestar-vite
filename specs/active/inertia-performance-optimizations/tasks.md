# Tasks: Inertia Performance Optimizations

## Phase 1: Planning
- [x] Analyze current SSR and HTTP client usage
- [x] Identify performance bottlenecks
- [x] Build consensus with gemini-3-pro and gpt-5.2
- [x] Create PRD

## Phase 2: Shared httpx.AsyncClient (Priority 1)

### 2.1 Plugin Lifespan
- [ ] Add `_ssr_client: httpx.AsyncClient | None` attribute to `InertiaPlugin`
- [ ] Initialize client in `lifespan()` with connection limits
- [ ] Close client in lifespan cleanup
- [ ] Store client reference for SSR functions

### 2.2 SSR Client Integration
- [ ] Modify `_render_inertia_ssr()` to accept optional client parameter
- [ ] Pass shared client from plugin when available
- [ ] Keep fallback for per-request client (graceful degradation)
- [ ] Update all SSR call sites

### 2.3 Tests
- [ ] Add test: client created once in lifespan
- [ ] Add test: client closed on shutdown
- [ ] Add test: SSR reuses shared client
- [ ] Add test: fallback works without plugin

## Phase 3: LazyInertiaASGIResponse (Priority 2)

### 3.1 Response Class
- [ ] Create `LazyInertiaASGIResponse` class in `response.py`
- [ ] Store page props, SSR config, client reference
- [ ] Defer body rendering until `__call__`

### 3.2 SSR in Async Context
- [ ] Move SSR call to `__call__` method
- [ ] Build HTML after SSR completes
- [ ] Send response headers and body

### 3.3 Integration
- [ ] Update `InertiaResponse.to_response()` to return lazy response
- [ ] Ensure SPA mode (no SSR) still works
- [ ] Ensure partial responses still work

### 3.4 Tests
- [ ] Add test: body not rendered until `__call__`
- [ ] Add test: SSR happens in async context
- [ ] Add test: content matches eager rendering
- [ ] Add benchmark: compare lazy vs eager timing

## Phase 4: DeferredProp Portal Optimization (Priority 3)

### 4.1 Type Encoder Update
- [ ] Modify type encoder lambda in `InertiaPlugin._configure_app_for_inertia()`
- [ ] Pass `self._portal` to `DeferredProp.render()`
- [ ] Handle case where portal is None

### 4.2 DeferredProp Changes
- [ ] Update `DeferredProp.render()` signature to accept `portal` parameter
- [ ] Use provided portal when available
- [ ] Keep fallback portal creation for standalone usage

### 4.3 Tests
- [ ] Add test: portal reused when provided by plugin
- [ ] Add test: fallback works when no portal available
- [ ] Add test: async callable resolved correctly

## Phase 5: Quality Gate
- [ ] All tests pass (`make test`)
- [ ] Linting clean (`make lint`)
- [ ] Type checking passes (`make type-check`)
- [ ] Coverage maintained at 90%+
- [ ] Run performance benchmark
- [ ] Archive workspace

## Estimated Effort

| Task Group | Complexity | Estimate |
|------------|------------|----------|
| Phase 2 (Shared Client) | Low | 2-3 hours |
| Phase 3 (Lazy Response) | Medium | 4-5 hours |
| Phase 4 (Portal Opt) | Low | 1-2 hours |
| Phase 5 (QA) | Low | 1 hour |

**Total**: ~8-11 hours

## Dependencies

- Phase 2 should be completed before Phase 3 (lazy response needs shared client)
- Phase 4 is independent and can be done in parallel with Phase 3
