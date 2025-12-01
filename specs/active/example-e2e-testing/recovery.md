# Recovery Guide: End-to-End Example Testing Framework

## Current State

**Status**: PRD and task breakdown complete. Ready for implementation.

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

## Next Steps

1. **Start implementation** by creating the e2e test directory:
   ```bash
   mkdir -p src/py/tests/e2e
   ```

2. **Implement port allocator** first as it has no dependencies:
   ```python
   # port_allocator.py
   EXAMPLE_NAMES = ["angular", "angular-cli", "astro", ...]
   def get_ports_for_example(name: str) -> tuple[int, int]: ...
   ```

3. **Implement health check** utilities:
   ```python
   # health_check.py
   def wait_for_http(url: str, timeout: float = 30.0) -> None: ...
   ```

4. **Implement ExampleServer** class:
   ```python
   # server_manager.py
   class ExampleServer:
       def start_dev_mode(self) -> None: ...
       def start_production_mode(self) -> None: ...
       def stop(self) -> None: ...
   ```

5. **Create fixtures** in conftest.py

6. **Write first test** for `basic` example to validate infrastructure

7. **Expand tests** to all examples

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
