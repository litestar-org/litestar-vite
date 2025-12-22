# Testing Guide for litestar-vite

**Version**: 0.15.0-rc.5 | **Updated**: 2025-12-22

This guide provides instructions and best practices for writing and running tests in the `litestar-vite` project.

## Overview

The project uses a dual testing strategy for its Python backend and TypeScript frontend.

- **Backend (Python)**: [pytest](https://docs.pytest.org/) is the primary framework for all Python tests.
- **Frontend (TypeScript)**: [Vitest](https://vitest.dev/) is used for tests related to the core JavaScript/TypeScript library.

The full test suite can be run with a single command: `make test`.

## Backend Testing (pytest)

Python tests are located in `src/py/tests/`.

### Test Types

1. **Unit Tests (`src/py/tests/unit/`)**: These tests focus on individual components (functions, classes) in isolation. Dependencies, especially I/O-bound ones like databases or network calls, must be mocked.
    - **Framework**: `pytest`
    - **Mocks**: `unittest.mock` (especially `AsyncMock` for async code).

2. **Integration Tests (`src/py/tests/integration/`)**: These tests verify the interaction between multiple components. They may use real dependencies like a test database or a live Vite dev server process.

### Key Practices

- **Function-Based Tests**: All tests **must** be function-based. Do not use class-based tests (`class Test...:`).
    - Good: `async def test_inertia_response_flattens_props() -> None:`
    - Bad: `class TestInertiaResponse:`
- **Fixtures**: Use `pytest` fixtures (`@pytest.fixture`) to provide reusable setup and teardown logic, such as creating mock objects or database sessions.
- **Async Tests**: Mark `async` test functions with `@pytest.mark.asyncio`.
- **Coverage**: Aim for at least 90% test coverage for any new or modified code. The full coverage report can be generated with `make coverage`.

### Test Organization

Tests mirror the source structure:

```
src/py/tests/
├── unit/              # Fast, isolated tests
│   ├── inertia/       # Inertia-specific unit tests
│   ├── test_config.py
│   └── test_asset_loader.py
├── integration/       # Tests with real dependencies
│   ├── cli/           # CLI command integration tests
│   └── test_examples.py
└── conftest.py        # Shared fixtures
```

### Recent Test Patterns

The inertia-props-top-level feature introduced these test patterns:

1. **Props flattening tests**: Verify dict props are merged at top-level
2. **Content wrapping tests**: Verify non-dict content goes under `content` key
3. **Inertia protocol tests**: Test v2 protocol features (deferred, merge, prepend props)

### Running Python Tests

```bash
# Run all python tests
pytest src/py/tests/

# Run tests in parallel for speed
pytest -n auto src/py/tests/

# Run a specific test file
pytest src/py/tests/unit/test_config.py

# Run tests with coverage for a specific module
pytest --cov=src/py/litestar_vite/config src/py/tests/unit/test_config.py
```

## Frontend Testing (Vitest)

The core TypeScript library tests are located in `src/js/tests/`.

### Key Practices

- **Modern Syntax**: Use modern ES module syntax (`import`, `export`).
- **Mocking**: Use Vitest's built-in mocking capabilities (`vi.mock`, `vi.fn`).

### Running Frontend Tests

The frontend tests are typically run as part of the `make test` command. To run them in isolation:

```bash
# Navigate to the JS directory
cd src/js

# Run the tests
npm run test
```

## Full Suite

To ensure the entire project is working correctly, always run the full test and quality suite before submitting changes.

```bash
# Run all tests (Python + JS)
make test

# Run all linting, type-checking, and tests
make check-all

# Run with coverage report
make coverage

# Run only linting (includes pre-commit, type-check, slotscheck)
make lint

# Run only type checking (mypy + pyright)
make type-check
```

## Type Checking

The project uses multiple type checkers for comprehensive type safety:

```bash
# Run mypy (with cache)
make mypy

# Run mypy without cache
make mypy-nocache

# Run pyright
make pyright

# Run basedpyright (stricter variant)
make basedpyright

# Run all type checkers
make type-check
```

## Example Testing

Test all example applications to ensure integrations work correctly:

```bash
# Install dependencies for all examples
make install-examples

# Build all examples
make build-examples

# Run example integration tests
make test-examples
```

## End-to-End (E2E) Testing

E2E tests validate the complete developer experience by running actual servers.

### Critical: Use Litestar CLI Commands

**ALWAYS use `litestar assets` commands instead of npm/node directly in tests!**

```python
# CORRECT - Uses Litestar CLI
def start_dev_mode():
    # Start Vite dev server via Litestar
    subprocess.Popen(["litestar", "assets", "serve"], cwd=example_dir, env=env)
    # Start Litestar backend
    subprocess.Popen(["litestar", "run", "--port", str(port)], cwd=example_dir, env=env)

def start_production_mode():
    # Build assets via Litestar
    subprocess.run(["litestar", "assets", "build"], cwd=example_dir, env=env, check=True)
    # Start Litestar backend (serves static files)
    subprocess.Popen(["litestar", "run", "--port", str(port)], cwd=example_dir, env=env)
    # For SSR: also start production Node server
    subprocess.Popen(["litestar", "assets", "serve", "--production"], cwd=example_dir, env=env)

# WRONG - Bypasses Litestar integration
def start_dev_mode_wrong():
    subprocess.Popen(["npm", "run", "dev"])  # NO! Use litestar assets serve
    subprocess.Popen(["npm", "run", "build"])  # NO! Use litestar assets build
```

**Why this matters:**
- The Litestar CLI manages port allocation, environment variables, and process coordination
- Direct npm commands bypass the Python-JS integration layer
- Tests must validate the real developer experience, not just that npm works

### E2E Test Structure

```
src/py/tests/e2e/
├── __init__.py
├── conftest.py           # Server fixtures with caching and process cleanup
├── server_manager.py     # ExampleServer class using litestar CLI and port management
├── health_check.py       # HTTP polling utilities
├── assertions.py         # HTML/API validation helpers
├── test_dev_mode.py      # Dev mode tests for all examples
└── test_production_mode.py  # Production mode tests
```

### Running E2E Tests

```bash
# Run all E2E tests
make test-examples-e2e

# Run E2E tests for specific example
uv run pytest src/py/tests/e2e/ -k "react" -v

# Run with verbose output for debugging
uv run pytest src/py/tests/e2e/ -v -s
```
