# Testing Guide for litestar-vite

This guide provides instructions and best practices for writing and running tests in the `litestar-vite` project.

## Overview

The project uses a dual testing strategy for its Python backend and TypeScript frontend.

-   **Backend (Python)**: [pytest](https://docs.pytest.org/) is the primary framework for all Python tests.
-   **Frontend (TypeScript)**: [Vitest](https://vitest.dev/) is used for tests related to the core JavaScript/TypeScript library.

The full test suite can be run with a single command: `make test`.

## Backend Testing (pytest)

Python tests are located in `src/py/tests/`.

### Test Types

1.  **Unit Tests (`src/py/tests/unit/`)**: These tests focus on individual components (functions, classes) in isolation. Dependencies, especially I/O-bound ones like databases or network calls, must be mocked.
    -   **Framework**: `pytest`
    -   **Mocks**: `unittest.mock` (especially `AsyncMock` for async code).

2.  **Integration Tests (`src/py/tests/integration/`)**: These tests verify the interaction between multiple components. They may use real dependencies like a test database or a live Vite dev server process.

### Key Practices

-   **Function-Based Tests**: All tests **must** be function-based. Do not use class-based tests (`class Test...:`).
-   **Fixtures**: Use `pytest` fixtures (`@pytest.fixture`) to provide reusable setup and teardown logic, such as creating mock objects or database sessions.
-   **Async Tests**: Mark `async` test functions with `@pytest.mark.asyncio`.
-   **Coverage**: Aim for at least 90% test coverage for any new or modified code. The full coverage report can be generated with `make coverage`.

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

-   **Modern Syntax**: Use modern ES module syntax (`import`, `export`).
-   **Mocking**: Use Vitest's built-in mocking capabilities (`vi.mock`, `vi.fn`).

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
