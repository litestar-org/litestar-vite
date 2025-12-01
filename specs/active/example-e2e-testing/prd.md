# PRD: End-to-End Example Testing Framework

## Overview
- **Slug**: example-e2e-testing
- **Created**: 2025-12-01
- **Status**: Draft

## Problem Statement

The `examples/` directory contains 17 framework integration examples (React, Vue, Svelte, Angular, Nuxt, SvelteKit, Astro, HTMX, etc.) that demonstrate litestar-vite capabilities. Currently, these examples are only tested for:
- Module import success
- Configuration validation
- Basic TestClient endpoint responses

**What's missing:**
1. No actual server startup testing in dev mode
2. No production build and serve testing
3. No reverse proxy verification
4. No HTML rendering validation
5. No verification that assets are served correctly

Users and CI have no way to know if examples actually work end-to-end until they manually run them.

## Goals

1. **Verify Dev Mode Works**: Each example can start Vite dev server + Litestar and serve requests with HMR
2. **Verify Production Mode Works**: Each example can build assets and serve them correctly
3. **Verify Reverse Proxy**: Litestar correctly proxies requests to Vite/Node servers
4. **Automate in CI**: Tests run automatically on PR and push to main
5. **Fast Feedback**: Tests complete within reasonable time (< 5 min total)

## Non-Goals

- Visual regression testing
- Performance benchmarking
- Testing all browser combinations
- Testing WebSocket/HMR functionality beyond server availability
- Testing user interactions (clicking, forms, etc.)

## Acceptance Criteria

### Core Functionality
- [ ] Each example starts successfully in dev mode (Vite + Litestar)
- [ ] Each example builds and runs in production mode
- [ ] GET `/` returns valid HTML (200 status, contains DOCTYPE)
- [ ] GET `/api/summary` returns valid JSON (200 status, expected structure)
- [ ] Static assets are accessible (CSS, JS bundles)
- [ ] For SSR examples: Node server starts and serves HTML

### Infrastructure
- [ ] Tests can run in parallel without port conflicts
- [ ] Processes are cleaned up after each test
- [ ] Timeouts prevent hanging tests
- [ ] Clear error messages on failure

### CI Integration
- [ ] Tests run via `make test-examples-e2e`
- [ ] Tests run in GitHub Actions
- [ ] Matrix strategy tests multiple examples in parallel
- [ ] Test failures block PR merge

### Coverage
- [ ] All 17 examples tested
- [ ] Both dev and production modes tested for each example
- [ ] Tests pass on Python 3.10-3.13
- [ ] Tests pass on Node 18 and 20

## Technical Approach

### Architecture

```
src/py/tests/e2e/
├── __init__.py
├── conftest.py           # Fixtures for server management
├── server_manager.py     # ExampleServer class for process lifecycle
├── port_allocator.py     # Unique port assignment
├── health_check.py       # HTTP polling utilities
├── test_dev_mode.py      # Dev mode tests for all examples
├── test_production_mode.py # Production mode tests
└── assertions.py         # Common test assertions
```

### Key Components

#### 1. ExampleServer Class
```python
class ExampleServer:
    """Manages lifecycle of example application servers."""

    def __init__(self, example_name: str, vite_port: int, litestar_port: int):
        self.example_name = example_name
        self.example_dir = EXAMPLES_DIR / example_name
        self.vite_port = vite_port
        self.litestar_port = litestar_port
        self._processes: list[subprocess.Popen] = []

    def start_dev_mode(self) -> None:
        """Start Vite dev server and Litestar with proxy."""
        env = {
            **os.environ,
            "VITE_PORT": str(self.vite_port),
            "VITE_DEV_MODE": "true",
        }
        # Start Vite
        self._processes.append(subprocess.Popen(
            ["npm", "run", "dev", "--", "--port", str(self.vite_port)],
            cwd=self.example_dir,
            env=env,
        ))
        # Start Litestar
        self._processes.append(subprocess.Popen(
            ["uv", "run", "litestar", "--app-dir", str(self.example_dir),
             "run", "--port", str(self.litestar_port)],
            env=env,
        ))

    def start_production_mode(self) -> None:
        """Build assets and start production servers."""
        # Build first
        subprocess.run(
            ["npm", "run", "build"],
            cwd=self.example_dir,
            check=True,
        )
        env = {
            **os.environ,
            "VITE_DEV_MODE": "false",
        }
        # Start Litestar
        self._processes.append(subprocess.Popen(
            ["uv", "run", "litestar", "--app-dir", str(self.example_dir),
             "run", "--port", str(self.litestar_port)],
            env=env,
        ))
        # For SSR examples, also start Node server
        if self._is_ssr_example():
            self._processes.append(subprocess.Popen(
                ["npm", "run", "serve"],
                cwd=self.example_dir,
                env=env,
            ))

    def wait_until_ready(self, timeout: float = 30.0) -> None:
        """Wait until servers respond to health checks."""
        wait_for_http(f"http://localhost:{self.litestar_port}/api/summary", timeout)

    def stop(self) -> None:
        """Terminate all processes."""
        for proc in self._processes:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
```

#### 2. Port Allocation Strategy
```python
# Each example gets a range of 10 ports
# Example index 0 (angular) -> Vite: 5000, Litestar: 8000
# Example index 1 (angular-cli) -> Vite: 5010, Litestar: 8010
# etc.

EXAMPLE_NAMES = [
    "angular", "angular-cli", "astro", "basic", "flash",
    "fullstack-typed", "jinja", "nuxt", "react", "react-inertia",
    "react-inertia-jinja", "svelte", "sveltekit", "template-htmx",
    "vue", "vue-inertia", "vue-inertia-jinja"
]

def get_ports_for_example(example_name: str) -> tuple[int, int]:
    """Get unique ports for an example."""
    idx = EXAMPLE_NAMES.index(example_name)
    vite_port = 5000 + (idx * 10)
    litestar_port = 8000 + (idx * 10)
    return vite_port, litestar_port
```

#### 3. Health Check Utilities
```python
def wait_for_http(url: str, timeout: float = 30.0) -> None:
    """Poll URL until it responds with 200 or timeout."""
    start = time.time()
    while time.time() - start < timeout:
        try:
            response = httpx.get(url, timeout=1.0)
            if response.status_code == 200:
                return
        except httpx.RequestError:
            pass
        time.sleep(0.5)
    raise TimeoutError(f"Server at {url} not ready after {timeout}s")
```

### Example Categories

| Category | Examples | Dev Mode | Prod Mode | Node Server |
|----------|----------|----------|-----------|-------------|
| **SPA** | react, vue, svelte, angular, basic, flash, fullstack-typed | Vite HMR | Static files | No |
| **SSR** | sveltekit, nuxt | Vite proxy | Node serves HTML | Yes |
| **SSG** | astro | Vite proxy | Static files | No |
| **Template** | jinja, template-htmx | Vite HMR | Static + Jinja | No |
| **Inertia** | react-inertia, vue-inertia, *-jinja variants | Vite HMR | Static + Inertia | No |
| **CLI** | angular-cli | ng serve | ng build → static | No |

### Test Implementation

```python
# test_dev_mode.py
import pytest
import httpx
from .conftest import ExampleServer

EXAMPLES = [
    "angular", "basic", "flash", "fullstack-typed", "jinja",
    "react", "react-inertia", "react-inertia-jinja", "svelte",
    "template-htmx", "vue", "vue-inertia", "vue-inertia-jinja"
]

SSR_EXAMPLES = ["astro", "nuxt", "sveltekit"]

@pytest.fixture
def server(request, example_name):
    """Start example server for the test."""
    vite_port, litestar_port = get_ports_for_example(example_name)
    server = ExampleServer(example_name, vite_port, litestar_port)
    server.start_dev_mode()
    server.wait_until_ready()
    yield server
    server.stop()

@pytest.mark.parametrize("example_name", EXAMPLES + SSR_EXAMPLES)
def test_dev_mode_homepage(server, example_name):
    """Test that homepage renders in dev mode."""
    response = httpx.get(f"http://localhost:{server.litestar_port}/")
    assert response.status_code == 200
    assert "<!DOCTYPE html>" in response.text or "<!doctype html>" in response.text.lower()

@pytest.mark.parametrize("example_name", EXAMPLES + SSR_EXAMPLES)
def test_dev_mode_api(server, example_name):
    """Test that API endpoint works in dev mode."""
    response = httpx.get(f"http://localhost:{server.litestar_port}/api/summary")
    assert response.status_code == 200
    data = response.json()
    assert "app" in data or "headline" in data
```

### Affected Files

**New Files:**
- `src/py/tests/e2e/__init__.py`
- `src/py/tests/e2e/conftest.py` - Server fixtures
- `src/py/tests/e2e/server_manager.py` - ExampleServer class
- `src/py/tests/e2e/port_allocator.py` - Port management
- `src/py/tests/e2e/health_check.py` - HTTP utilities
- `src/py/tests/e2e/test_dev_mode.py` - Dev mode tests
- `src/py/tests/e2e/test_production_mode.py` - Production tests

**Modified Files:**
- `Makefile` - Add `test-examples-e2e` target
- `.github/workflows/ci.yml` - Add E2E test job
- `pyproject.toml` - Add pytest markers

### API Changes

No public API changes. This is a testing infrastructure addition.

## Testing Strategy

### Unit Tests
- Test `ExampleServer` start/stop lifecycle
- Test port allocation uniqueness
- Test health check timeout behavior

### Integration Tests
- Test each example in dev mode (parametrized)
- Test each example in production mode (parametrized)
- Test API endpoints in both modes
- Test static asset serving

### Edge Cases
- Server fails to start (missing dependencies)
- Port already in use
- Build failure
- Timeout during startup

## CI/CD Integration

### GitHub Actions Workflow

```yaml
test_examples_e2e:
  name: "E2E Examples (${{ matrix.example }})"
  runs-on: ubuntu-latest
  needs: [validate]
  strategy:
    fail-fast: false
    matrix:
      example:
        - react
        - vue
        - svelte
        - angular
        - sveltekit
        - nuxt
        - astro
  steps:
    - uses: actions/checkout@v6

    - name: Set up Node
      uses: actions/setup-node@v4
      with:
        node-version: 20
        cache: npm

    - name: Install uv
      uses: astral-sh/setup-uv@v7

    - name: Set up Python
      run: uv python install 3.12

    - name: Install dependencies
      run: |
        npm ci --ignore-scripts
        uv sync --all-extras --dev

    - name: Install example dependencies
      run: |
        cd examples/${{ matrix.example }}
        npm ci

    - name: Run E2E tests
      run: |
        uv run pytest src/py/tests/e2e/ -k "${{ matrix.example }}" -v --timeout=120
```

### Makefile Target

```makefile
.PHONY: test-examples-e2e
test-examples-e2e: install-examples  ## Run E2E tests for all examples
	@echo "${INFO} Running E2E example tests... 🧪"
	@uv run pytest src/py/tests/e2e/ -v --timeout=300
	@echo "${OK} E2E tests passed"
```

## Research Questions

- [x] How to handle port conflicts in parallel test runs? → Use example-indexed port allocation
- [x] Should we test all examples or subset in CI? → Matrix strategy with key examples
- [ ] Should we skip slow examples (nuxt, sveltekit) in fast CI? → TBD based on timing
- [ ] Do we need to test on Windows/macOS? → Start with Linux only

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Flaky tests due to timing | High | Generous timeouts, retry logic |
| Port conflicts | Medium | Indexed port allocation |
| CI timeout | Medium | Matrix strategy, parallel jobs |
| npm install failures | Medium | Cache dependencies, retry |
| Process cleanup failures | Medium | Always terminate in finally block |
| Large CI time increase | Medium | Run subset in PR, full in main |

## Performance Budget

| Metric | Target | Rationale |
|--------|--------|-----------|
| Single example E2E | < 60s | npm install + build + test |
| Full E2E suite | < 10min | Parallel matrix |
| CI job overhead | < 2min | Setup Node, Python, deps |

## Rollout Plan

1. **Phase 1**: Implement infrastructure (ExampleServer, fixtures)
2. **Phase 2**: Add dev mode tests for SPA examples
3. **Phase 3**: Add production mode tests
4. **Phase 4**: Add SSR example tests (nuxt, sveltekit)
5. **Phase 5**: CI integration
6. **Phase 6**: Documentation and cleanup
