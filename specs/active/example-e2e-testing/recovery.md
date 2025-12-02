# Recovery Guide: End-to-End Example Testing Framework

## Current State

**Status**: Implementation in progress – core E2E scaffolding, fixtures, and tests added.

## Files Created

| File | Status | Description |
|------|--------|-------------|
| `specs/active/example-e2e-testing/prd.md` | Complete | Full requirements document |
| `specs/active/example-e2e-testing/tasks.md` | Complete | Detailed task breakdown |
| `specs/active/example-e2e-testing/recovery.md` | Complete | This file |

## Files To Be Created

| File | Description |
|------|-------------|
| `src/py/tests/e2e/__init__.py` | Package marker |
| `src/py/tests/e2e/conftest.py` | pytest fixtures |
| `src/py/tests/e2e/server_manager.py` | ExampleServer class |
| `src/py/tests/e2e/port_allocator.py` | Port management |
| `src/py/tests/e2e/health_check.py` | HTTP utilities |
| `src/py/tests/e2e/assertions.py` | Test assertions |
| `src/py/tests/e2e/test_dev_mode.py` | Dev mode tests |
| `src/py/tests/e2e/test_production_mode.py` | Production tests |
| `.github/workflows/e2e-examples.yml` | CI workflow |

## Files To Be Modified

| File | Changes |
|------|---------|
| `Makefile` | Add `test-examples-e2e` target |
| `pyproject.toml` | Add pytest markers |
| `specs/active/example-e2e-testing/tasks.md` | Progress updates |

## Next Steps

## Latest Findings (2025-12-02)

- Added process monitoring/cleanup and xdist grouping; port collisions still occur because examples sometimes spawn extra processes (vite port auto-increments when busy). Litestar ports (36xxx) also collide when a previous run leaves a bound process; need enforced cleanup and/or broader port spacing.
- Angular CLI: dev HTML now passes via shell-marker assertion; initial 503s handled. However suite-wide reruns can fail when ports are occupied.
- Template HTMX: Jinja `include ... with` fixed to use `set` + include. Prod homepage now passes.
- Nuxt/SvelteKit prod: now pass when using SSR port for HTML fetch.
- Remaining failures (full suite): timeouts/port-in-use for basic, fullstack-typed, angular, svelte, sveltekit, react-inertia; prod astro still 404/timeout; some API 404s due to Litestar startup while Vite auto-changes port.

## Next Steps

1. Increase port spacing and lock per-example ports (e.g., jump by 50 or random free port search) and free stray processes before each fixture.
2. Treat Vite auto-port bump as signal to update litestar target or force --strictPort to fail fast; consider passing VITE_STRICT_PORT=1 or Vite flag.
3. Add retries for dev/prod startup when ports busy; kill listeners detected on target ports before starting.
4. Add pytest-timeout/longer waits for SSR build-heavy examples.
5. Stabilize astro (prod) homepage 404 by aligning request to SSR/static host and ensuring build/serve path.
6. Rerun full E2E; then proceed to testing agent → docs-vision agent → archive.

## Context for Resumption

### Key Design Decisions Made

1. **Port Allocation**: Each example gets a unique port range based on index
   - Vite: 5000 + (idx * 10)
   - Litestar: 8000 + (idx * 10)

2. **Server Categories**:
   - SPA: react, vue, svelte, angular, basic, flash, fullstack-typed
   - SSR: sveltekit, nuxt (need Node server in production)
   - SSG: astro (static files)
   - Template: jinja, template-htmx
   - Inertia: react-inertia, vue-inertia, *-jinja variants
   - CLI: angular-cli (uses ng serve/build)

3. **Process Management**: Use subprocess.Popen with context manager pattern

4. **Health Checks**: Poll HTTP endpoint until 200 response

5. **CI Strategy**: Matrix jobs for parallel example testing

### Reference Commands

```bash
# Run single example manually
cd examples/react
npm run dev &
VITE_DEV_MODE=true uv run litestar --app-dir . run

# Build and run production
cd examples/react
npm run build
VITE_DEV_MODE=false uv run litestar --app-dir . run

# Test API endpoint
curl http://localhost:8000/api/summary
```

### Example App Structure

All examples follow the same pattern:
- `app.py` - Litestar application with VitePlugin
- `package.json` - npm scripts (dev, build, serve, preview)
- API endpoints: `/api/summary`, `/api/books`, `/api/books/{id}`

### Environment Variables

- `VITE_DEV_MODE`: "true" for dev, "false" for production
- `VITE_PORT`: Vite dev server port
- `LITESTAR_PORT`: Litestar server port (via CLI `--port`)

## Blockers / Questions

None currently identified. Ready to proceed with implementation.

## Related Documentation

- `CLAUDE.md` - Project conventions
- `specs/guides/testing.md` - Testing patterns
- `src/py/tests/integration/test_examples.py` - Existing example tests
- `Makefile` - Build targets
