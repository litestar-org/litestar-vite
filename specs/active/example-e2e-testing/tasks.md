# Tasks: End-to-End Example Testing Framework

## Phase 1: Planning
- [x] Create PRD
- [x] Identify affected components
- [x] Research process management approaches
- [x] Define test architecture

## Phase 2: Infrastructure Implementation

### 2.1 Core Utilities
- [ ] Create `src/py/tests/e2e/__init__.py`
- [ ] Create `src/py/tests/e2e/port_allocator.py`
  - [ ] Implement `get_ports_for_example()` function
  - [ ] Implement port uniqueness validation
  - [ ] Add constant for example names list
- [ ] Create `src/py/tests/e2e/health_check.py`
  - [ ] Implement `wait_for_http()` function
  - [ ] Implement `check_html_response()` helper
  - [ ] Implement `check_api_response()` helper
  - [ ] Add configurable timeout and retry logic

### 2.2 Server Manager
- [ ] Create `src/py/tests/e2e/server_manager.py`
  - [ ] Implement `ExampleServer` class
  - [ ] Implement `start_dev_mode()` method
  - [ ] Implement `start_production_mode()` method
  - [ ] Implement `wait_until_ready()` method
  - [ ] Implement `stop()` method with cleanup
  - [ ] Add SSR detection logic
  - [ ] Add process monitoring
  - [ ] Add logging for debugging

### 2.3 Test Fixtures
- [ ] Create `src/py/tests/e2e/conftest.py`
  - [ ] Create `example_server` fixture
  - [ ] Create `dev_mode_server` fixture
  - [ ] Create `production_server` fixture
  - [ ] Add autouse cleanup fixture
  - [ ] Add pytest markers for example categories

## Phase 3: Dev Mode Tests

### 3.1 SPA Examples
- [ ] Create `src/py/tests/e2e/test_dev_mode.py`
- [ ] Test `basic` example dev mode
- [ ] Test `react` example dev mode
- [ ] Test `vue` example dev mode
- [ ] Test `svelte` example dev mode
- [ ] Test `angular` example dev mode
- [ ] Test `flash` example dev mode
- [ ] Test `fullstack-typed` example dev mode

### 3.2 Template Examples
- [ ] Test `jinja` example dev mode
- [ ] Test `template-htmx` example dev mode

### 3.3 Inertia Examples
- [ ] Test `react-inertia` example dev mode
- [ ] Test `vue-inertia` example dev mode
- [ ] Test `react-inertia-jinja` example dev mode
- [ ] Test `vue-inertia-jinja` example dev mode

### 3.4 SSR Examples
- [ ] Test `astro` example dev mode
- [ ] Test `nuxt` example dev mode
- [ ] Test `sveltekit` example dev mode
- [ ] Test `angular-cli` example dev mode

## Phase 4: Production Mode Tests

### 4.1 SPA Examples
- [ ] Create `src/py/tests/e2e/test_production_mode.py`
- [ ] Test `basic` example production mode
- [ ] Test `react` example production mode
- [ ] Test `vue` example production mode
- [ ] Test `svelte` example production mode
- [ ] Test `angular` example production mode
- [ ] Test `flash` example production mode
- [ ] Test `fullstack-typed` example production mode

### 4.2 Template Examples
- [ ] Test `jinja` example production mode
- [ ] Test `template-htmx` example production mode

### 4.3 Inertia Examples
- [ ] Test `react-inertia` example production mode
- [ ] Test `vue-inertia` example production mode
- [ ] Test `react-inertia-jinja` example production mode
- [ ] Test `vue-inertia-jinja` example production mode

### 4.4 SSR Examples (with Node server)
- [ ] Test `astro` example production mode (static)
- [ ] Test `nuxt` example production mode (Node SSR)
- [ ] Test `sveltekit` example production mode (Node SSR)
- [ ] Test `angular-cli` example production mode (static)

## Phase 5: Test Assertions

- [ ] Create `src/py/tests/e2e/assertions.py`
  - [ ] `assert_html_response()` - Valid HTML document
  - [ ] `assert_api_response()` - Valid JSON with expected keys
  - [ ] `assert_asset_accessible()` - Static assets load
  - [ ] `assert_no_server_errors()` - No 500 errors in logs

## Phase 6: CI/CD Integration

### 6.1 Makefile
- [ ] Add `test-examples-e2e` target
- [ ] Add `test-examples-e2e-quick` target (subset)
- [ ] Update `check-all` to optionally include E2E

### 6.2 GitHub Actions
- [ ] Create `.github/workflows/e2e-examples.yml`
  - [ ] Matrix strategy for examples
  - [ ] Node.js setup
  - [ ] Python/uv setup
  - [ ] Example dependency installation
  - [ ] Test execution
  - [ ] Artifact upload on failure

### 6.3 pytest Configuration
- [ ] Add `e2e` marker to `pyproject.toml`
- [ ] Configure test timeout
- [ ] Add xdist group markers

## Phase 7: Testing & QA

- [ ] Run all tests locally
- [ ] Verify cleanup (no zombie processes)
- [ ] Test on CI
- [ ] Verify parallel execution
- [ ] Check timing and optimize
- [ ] Add retry logic for flaky scenarios

## Phase 8: Documentation

- [ ] Update `CLAUDE.md` with E2E test info
- [ ] Add README in `src/py/tests/e2e/`
- [ ] Document how to add tests for new examples
- [ ] Document troubleshooting steps

## Phase 9: Quality Gate

- [ ] All tests pass locally
- [ ] All tests pass in CI
- [ ] 100% example coverage
- [ ] No zombie processes after test run
- [ ] < 10 minute total CI time
- [ ] Clear failure messages

## Dependencies

- pytest (existing)
- pytest-xdist (existing)
- httpx (existing)
- subprocess (stdlib)

## Estimated Effort

| Phase | Effort |
|-------|--------|
| Phase 2: Infrastructure | 2-3 hours |
| Phase 3: Dev Mode Tests | 2-3 hours |
| Phase 4: Production Tests | 2-3 hours |
| Phase 5: Assertions | 1 hour |
| Phase 6: CI/CD | 1-2 hours |
| Phase 7: Testing & QA | 2-3 hours |
| Phase 8: Documentation | 1 hour |
| **Total** | **11-16 hours** |
