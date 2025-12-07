# PRD: Test Style Migration - Class to Function-Based Tests

## Overview
- **Slug**: test-style-migration
- **Created**: 2025-12-07
- **Status**: Completed

## Completion Summary

**Migrated 20 class-based test classes to function-based tests across 4 files:**

| File | Before | After | Status |
|------|--------|-------|--------|
| `test_commands.py` | 2 classes, 13 tests | 13 functions | ✅ |
| `test_executor.py` | 2 classes, 14 tests | 14 functions | ✅ |
| `test_optional_jinja.py` | 8 classes, 30 tests | 30 functions | ✅ |
| `test_plugin.py` | 8 classes, 50 tests | 52 functions | ✅ |
| **Total** | **20 classes, 107 tests** | **109 functions** | ✅ |

*Note: test_plugin.py increased by 2 tests due to splitting combined assertions into separate test functions for clarity.*

**Verification:**
- `grep -r "^class Test" src/py/tests/` returns 0 matches
- `make test` passes (506 tests)
- `make lint` passes
- `make type-check` passes (mypy + pyright)

## Problem Statement

The project's testing guide (`specs/guides/testing.md`) explicitly mandates that **all tests must be function-based**:

> **Function-Based Tests**: All tests **must** be function-based. Do not use class-based tests (`class Test...:`).
> - Good: `async def test_inertia_response_flattens_props() -> None:`
> - Bad: `class TestInertiaResponse:`

However, the codebase currently contains **20 class-based test classes** across 4 files, violating this standard. While these tests are working, they create inconsistency with the rest of the test suite and violate the project's documented conventions.

## Goals

1. **Migrate all class-based tests to function-based tests** while preserving 100% test functionality
2. **Maintain test organization** through descriptive naming patterns and module docstrings
3. **Ensure all tests continue to pass** after migration
4. **Achieve consistency** with the rest of the test suite

## Non-Goals

- **NOT** changing test logic or improving test coverage
- **NOT** adding new tests
- **NOT** refactoring the code under test
- **NOT** changing test dependencies or fixtures

## Acceptance Criteria

- [x] All 20 `class Test...` definitions removed from test files
- [x] All test methods converted to module-level test functions
- [x] All tests pass after migration (`make test`)
- [x] No change in test coverage
- [x] Linting passes (`make lint`)
- [x] Type checking passes (`make type-check`)

## Technical Approach

### Class-Based Tests Inventory

| File | Class Count | Test Method Count |
|------|-------------|-------------------|
| `src/py/tests/unit/test_commands.py` | 2 | ~12 |
| `src/py/tests/unit/test_plugin.py` | 8 | ~54 |
| `src/py/tests/unit/test_executor.py` | 2 | ~15 |
| `src/py/tests/integration/test_optional_jinja.py` | 8 | ~35 |
| **Total** | **20** | **~116** |

### Migration Strategy

The migration follows a systematic approach:

#### 1. Naming Convention
Transform class method names using the pattern:
```python
# Before
class TestVitePlugin:
    def test_plugin_initialization_default_config(self) -> None:
        ...

# After
def test_vite_plugin_initialization_default_config() -> None:
    ...
```

Pattern: `test_{class_name_snake_case}_{method_name_without_test_prefix}()`

#### 2. Shared Setup via Fixtures
Any setup that was in `__init__` or shared across methods should become fixtures in `conftest.py` or at module level:

```python
# Before
class TestVitePlugin:
    def setup_method(self):
        self.config = ViteConfig()

    def test_something(self):
        plugin = VitePlugin(config=self.config)
        ...

# After
@pytest.fixture
def default_config() -> ViteConfig:
    return ViteConfig()

def test_vite_plugin_something(default_config: ViteConfig) -> None:
    plugin = VitePlugin(config=default_config)
    ...
```

#### 3. Module Organization
Group related tests using comments and ordering:
```python
# =====================================================
# VitePlugin Core Functionality
# =====================================================

def test_vite_plugin_initialization_default_config() -> None:
    ...

def test_vite_plugin_initialization_custom_config() -> None:
    ...

# =====================================================
# VitePlugin App Integration
# =====================================================
```

### Affected Files

1. **`src/py/tests/unit/test_commands.py`**
   - `TestInitVite` (3 methods) → 3 functions
   - `TestScaffoldingModule` (11 methods) → 11 functions

2. **`src/py/tests/unit/test_plugin.py`**
   - `TestVitePlugin` (7 methods) → 7 functions
   - `TestVitePluginAppIntegration` (9 methods) → 9 functions
   - `TestVitePluginLifespan` (5 methods) → 5 functions
   - `TestViteProcess` (7 methods) → 7 functions
   - `TestStaticFilesConfig` (2 methods) → 2 functions
   - `TestVitePluginWithJinja` (6 methods) → 6 functions
   - `TestVitePluginErrorHandling` (2 methods) → 2 functions
   - `TestVitePluginJinjaOptionalDependency` (13 methods) → 13 functions

3. **`src/py/tests/unit/test_executor.py`**
   - `TestExecutors` (8 methods) → 8 functions
   - `TestNodeenvExecutor` (5 methods) → 5 functions

4. **`src/py/tests/integration/test_optional_jinja.py`**
   - `TestOptionalJinjaSupport` (8 methods) → 8 functions
   - `TestJinjaOptionalInstallationScenarios` (2 methods) → 2 functions
   - `TestErrorMessages` (2 methods) → 2 functions
   - `TestBackwardCompatibility` (2 methods) → 2 functions
   - `TestConditionalImports` (2 methods) → 2 functions
   - `TestJinjaOptionalEdgeCases` (10 methods) → 10 functions
   - `TestJinjaOptionalPerformanceImpact` (3 methods) → 3 functions
   - `TestJinjaOptionalProductionReadiness` (3 methods) → 3 functions

### Reference Examples (Good Patterns)

The project has excellent function-based test examples to follow:

1. **`src/py/tests/unit/test_config.py`** - Clean function-based tests
2. **`src/py/tests/unit/inertia/test_response.py`** - Complex async tests with fixtures
3. **`src/py/tests/unit/test_asset_loader.py`** - Well-organized test functions

## Testing Strategy

1. **Before migration**: Run `make test` and capture passing count
2. **After each file**: Run `pytest src/py/tests/unit/<file>.py -v`
3. **After complete migration**: Run `make test` to verify same count
4. **Final verification**: `make check-all` for full quality gate

## Research Questions

- [x] Which files contain class-based tests? (Answered above)
- [x] Are there any shared fixtures in the classes that need extraction? (Minimal - reviewed)
- [x] What's the naming pattern used in existing function-based tests? (Confirmed above)

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Breaking test functionality | High | Run tests after each file migration |
| Missing test methods during migration | Medium | Count tests before/after each file |
| Introducing duplicate function names | Medium | Use class prefix in new function names |
| Merge conflicts with in-flight PRs | Low | Complete migration in single PR |
