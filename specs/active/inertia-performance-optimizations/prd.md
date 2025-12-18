# PRD: Inertia Performance Optimizations

## Overview
- **Slug**: inertia-performance-optimizations
- **Created**: 2025-12-18
- **Status**: Draft
- **Priority**: High

## Problem Statement

The current litestar-vite Inertia implementation has several performance issues related to HTTP client lifecycle management and sync/async bridging:

1. **Per-Request HTTP Client Creation**: SSR rendering creates a new `httpx.AsyncClient()` for every request (`response.py:158-160`), losing connection pooling, TLS session reuse, and HTTP/2 multiplexing benefits.

2. **Event Loop Blocking in Hybrid Mode**: `_render_spa()` calls `get_html_sync()` which blocks the event loop when serving hybrid/Inertia pages.

3. **DeferredProp Portal Overhead**: `DeferredProp.render()` creates a new `BlockingPortal` if none provided, even when the plugin already has one available.

4. **Proxy Per-Request Client**: The Vite proxy creates new httpx clients per request instead of reusing a shared client.

## Goals

1. **Primary**: Eliminate per-request HTTP client creation for SSR calls
2. **Secondary**: Defer SSR rendering to async context to avoid blocking
3. **Tertiary**: Optimize DeferredProp to reuse existing portal

## Non-Goals

- HTTP/3 support (not widely deployed)
- Custom connection pool sizing (use sensible defaults)

## Acceptance Criteria

### Feature 1: Shared httpx.AsyncClient (Priority 1)

- [ ] Add `_ssr_client: httpx.AsyncClient` to `InertiaPlugin`
- [ ] Initialize client in plugin lifespan with connection limits
- [ ] Use shared client in `_render_inertia_ssr()`
- [ ] Properly close client on app shutdown
- [ ] Add tests verifying client reuse

### Feature 2: LazyInertiaASGIResponse (Priority 2)

- [ ] Create `LazyInertiaASGIResponse` class that defers SSR to `__call__`
- [ ] Return lazy response from `InertiaResponse.to_response()`
- [ ] Perform SSR rendering in async `__call__` method
- [ ] Maintain backward compatibility with existing tests
- [ ] Add benchmark comparing sync vs async rendering

### Feature 3: DeferredProp Portal Optimization (Priority 3)

- [ ] Modify type encoder in `InertiaPlugin` to pass portal
- [ ] Update `DeferredProp.render()` signature to accept optional portal
- [ ] Avoid portal creation when plugin portal is available
- [ ] Add tests verifying portal reuse

## Technical Approach

### Architecture

```
InertiaPlugin (lifespan)
    ├── _ssr_client: httpx.AsyncClient (shared)
    ├── _portal: BlockingPortal (for sync-to-async)
    └── type_encoders (pass portal to DeferredProp)

InertiaResponse.to_response()
    └── LazyInertiaASGIResponse
            └── __call__(scope, receive, send)
                    └── _render_inertia_ssr(client=shared_client)
```

### Affected Files

| File | Changes |
|------|---------|
| `src/py/litestar_vite/inertia/plugin.py` | Add shared client lifespan, update type encoders |
| `src/py/litestar_vite/inertia/response.py` | Create LazyInertiaASGIResponse, refactor SSR |
| `src/py/litestar_vite/inertia/helpers.py` | Update DeferredProp.render() signature |
| `tests/unit/inertia/test_plugin.py` | Add client lifecycle tests |
| `tests/unit/inertia/test_response.py` | Add lazy response tests |

### API Changes

#### InertiaPlugin (plugin.py)

```python
class InertiaPlugin:
    _ssr_client: httpx.AsyncClient | None = None
    _portal: BlockingPortal | None = None

    @asynccontextmanager
    async def lifespan(self, app: Litestar) -> AsyncIterator[None]:
        async with BlockingPortal() as portal:
            self._portal = portal
            # Initialize shared SSR client with connection pooling
            self._ssr_client = httpx.AsyncClient(
                limits=httpx.Limits(max_keepalive_connections=10, max_connections=20),
                timeout=httpx.Timeout(10.0),
            )
            try:
                yield
            finally:
                await self._ssr_client.aclose()
                self._ssr_client = None
                self._portal = None
```

#### LazyInertiaASGIResponse (response.py)

```python
class LazyInertiaASGIResponse(ASGIResponse):
    """ASGI response that defers SSR rendering to async __call__."""

    def __init__(
        self,
        page_props: PageProps[Any],
        ssr_url: str,
        ssr_timeout: float,
        template: str,
        client: httpx.AsyncClient,
        # ... other params
    ) -> None:
        self._page_props = page_props
        self._ssr_url = ssr_url
        self._ssr_timeout = ssr_timeout
        self._client = client
        # Don't render body yet - defer to __call__

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        # Now we're in async context - safe to do SSR
        ssr_result = await _render_inertia_ssr(
            page=self._page_props.to_dict(),
            url=self._ssr_url,
            timeout_seconds=self._ssr_timeout,
            client=self._client,  # Use shared client
        )
        body = self._build_html(ssr_result)
        # ... send response
```

#### DeferredProp (helpers.py)

```python
class DeferredProp(Generic[T]):
    def render(self, portal: BlockingPortal | None = None) -> T:
        """Render the deferred prop, resolving async if needed.

        Args:
            portal: Optional BlockingPortal for sync-to-async. If None
                    and value is async, creates a new portal (slower).
        """
        if asyncio.iscoroutinefunction(self._callable):
            if portal is not None:
                return portal.call(self._callable)
            # Fallback: create portal (less efficient)
            with BlockingPortal() as new_portal:
                return new_portal.call(self._callable)
        return self._callable()
```

## Testing Strategy

### Unit Tests

1. **Shared Client Tests**
   - Verify client created once in lifespan
   - Verify client closed on shutdown
   - Verify SSR uses shared client

2. **Lazy Response Tests**
   - Verify body not rendered until `__call__`
   - Verify SSR happens in async context
   - Verify response content matches eager rendering

3. **DeferredProp Tests**
   - Verify portal reuse when provided
   - Verify fallback works when no portal

### Benchmark Tests

```python
async def test_ssr_performance():
    """Benchmark SSR with shared vs per-request client."""
    # Run 100 SSR requests, compare timing
```

## Performance Impact

| Optimization | Expected Improvement |
|--------------|---------------------|
| Shared httpx.AsyncClient | 30-50% latency reduction for SSR |
| Connection pooling | Eliminates TLS handshake per request |
| Lazy SSR rendering | Prevents event loop blocking |
| Portal reuse | ~5-10ms saved per DeferredProp |

## Multi-Model Consensus

**Models Consulted**: gemini-3-pro-preview, openai/gpt-5.2

**Unanimous Agreement On**:

1. Shared httpx.AsyncClient is the highest-priority fix
2. LazyInertiaASGIResponse pattern is architecturally sound
3. DeferredProp optimization is worth doing but lower priority
4. All optimizations are backward compatible
5. Implementation complexity rated as low-medium

**Confidence Score**: High (8-9/10)

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Client exhaustion under load | Medium | Configure sensible connection limits |
| Lazy response breaks tests | Low | Ensure backward compat in test setup |
| Portal not available in edge cases | Low | Keep fallback portal creation |

## Implementation Notes

### Connection Limits

Based on httpx defaults and SSR workload:

```python
limits = httpx.Limits(
    max_keepalive_connections=10,  # Per-host keep-alive
    max_connections=20,            # Total concurrent
    keepalive_expiry=30.0,         # 30s idle timeout
)
```

### Thread Safety

The shared `httpx.AsyncClient` is thread-safe and designed for concurrent use. No additional synchronization needed.

### Graceful Degradation

If plugin is not properly initialized (edge case), fall back to per-request client:

```python
async def _render_inertia_ssr(..., client: httpx.AsyncClient | None = None):
    if client is None:
        async with httpx.AsyncClient() as fallback:
            return await _do_ssr(fallback, ...)
    return await _do_ssr(client, ...)
```
