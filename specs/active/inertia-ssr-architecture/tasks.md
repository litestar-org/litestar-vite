# Tasks: Inertia Proxy Bug Fix & Dev Server Mode

## Phase 1: Planning ✓

- [x] Create PRD
- [x] Research Laravel/Inertia SSR architecture
- [x] Identify all affected code locations
- [x] Understand httpx AsyncClient context manager behavior
- [x] **REVISED**: Identify actual root cause (httpx `__aexit__` cleanup after response)

## Phase 2: Bug 1 - Proxy Fix ✓

### ViteProxyMiddleware._proxy_http()

- [x] Declare response variables before context manager
- [x] Capture response status, headers, body inside context manager
- [x] Move exception handling to set error response variables
- [x] Send ASGI response OUTSIDE context manager
- [x] Add explanatory comment
- [x] Add `content-length` and `content-encoding` to filtered headers (httpx auto-decompresses)

### ExternalDevServerProxyMiddleware._proxy_request()

- [x] Apply same pattern as ViteProxyMiddleware
- [x] Handle ConnectError and HTTPError separately
- [x] Send ASGI response OUTSIDE context manager
- [x] Add explanatory comment

## Phase 3: Bug 2 - Inertia Index Mode ✓

### Python Changes

- [x] Verify `mode` is already written to `.litestar.json` (confirmed - already present)

### TypeScript Changes

- [x] Add `inertiaMode?: boolean` to `PluginConfig` interface
- [x] Add `inertiaMode: boolean` to `ResolvedPluginConfig` interface
- [x] Update `resolvePluginConfig()` to auto-detect `inertiaMode` from `.litestar.json` mode
- [x] Update `findIndexHtmlPath()` to return `null` when `inertiaMode` is true
- [x] Update console logging to show "Index Mode: Inertia" when applicable

## Phase 4: Testing ✓

### Unit Tests

- [x] All 264 JS tests pass
- [x] All Python tests pass

### Linting

- [x] All pre-commit checks pass
- [x] Mypy passes (0 issues)
- [x] Pyright passes (0 errors)
- [x] Slots check passes

## Phase 5: Quality Gate ✓

- [x] `make test` passes
- [x] `make lint` passes
- [ ] Manual verification with reference app (litestar-fullstack-inertia)
- [ ] Archive workspace after verification
