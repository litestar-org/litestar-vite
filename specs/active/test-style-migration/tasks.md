# Tasks: Test Style Migration - Class to Function-Based Tests

## Phase 1: Planning ✓
- [x] Create PRD
- [x] Identify all affected files
- [x] Document migration strategy
- [x] Count tests in each file

## Phase 2: Pre-Migration Verification
- [ ] Run `make test` and record baseline pass count
- [ ] Run `pytest src/py/tests/unit/test_commands.py -v --collect-only` to count tests
- [ ] Run `pytest src/py/tests/unit/test_plugin.py -v --collect-only` to count tests
- [ ] Run `pytest src/py/tests/unit/test_executor.py -v --collect-only` to count tests
- [ ] Run `pytest src/py/tests/integration/test_optional_jinja.py -v --collect-only` to count tests

## Phase 3: Implementation

### 3.1 Migrate `test_commands.py` (~14 tests)
- [ ] Convert `TestInitVite` class (3 methods)
- [ ] Convert `TestScaffoldingModule` class (11 methods)
- [ ] Verify: `pytest src/py/tests/unit/test_commands.py -v`
- [ ] Confirm same test count passes

### 3.2 Migrate `test_executor.py` (~13 tests)
- [ ] Convert `TestExecutors` class (8 methods)
- [ ] Convert `TestNodeenvExecutor` class (5 methods)
- [ ] Verify: `pytest src/py/tests/unit/test_executor.py -v`
- [ ] Confirm same test count passes

### 3.3 Migrate `test_plugin.py` (~51 tests)
- [ ] Convert `TestVitePlugin` class (7 methods)
- [ ] Convert `TestVitePluginAppIntegration` class (9 methods)
- [ ] Convert `TestVitePluginLifespan` class (5 methods)
- [ ] Convert `TestViteProcess` class (7 methods)
- [ ] Convert `TestStaticFilesConfig` class (2 methods)
- [ ] Convert `TestVitePluginWithJinja` class (6 methods)
- [ ] Convert `TestVitePluginErrorHandling` class (2 methods)
- [ ] Convert `TestVitePluginJinjaOptionalDependency` class (13 methods)
- [ ] Verify: `pytest src/py/tests/unit/test_plugin.py -v`
- [ ] Confirm same test count passes

### 3.4 Migrate `test_optional_jinja.py` (~32 tests)
- [ ] Convert `TestOptionalJinjaSupport` class (8 methods)
- [ ] Convert `TestJinjaOptionalInstallationScenarios` class (2 methods)
- [ ] Convert `TestErrorMessages` class (2 methods)
- [ ] Convert `TestBackwardCompatibility` class (2 methods)
- [ ] Convert `TestConditionalImports` class (2 methods)
- [ ] Convert `TestJinjaOptionalEdgeCases` class (10 methods)
- [ ] Convert `TestJinjaOptionalPerformanceImpact` class (3 methods)
- [ ] Convert `TestJinjaOptionalProductionReadiness` class (3 methods)
- [ ] Verify: `pytest src/py/tests/integration/test_optional_jinja.py -v`
- [ ] Confirm same test count passes

## Phase 4: Post-Migration Verification
- [ ] Run `make test` - all tests pass
- [ ] Run `make lint` - no linting errors
- [ ] Run `make type-check` - no type errors
- [ ] Compare baseline vs final test count (should match)

## Phase 5: Quality Gate
- [ ] No `class Test` definitions remain in test files
- [ ] All tests follow function-based pattern
- [ ] Naming convention consistent across files
- [ ] Section comments added for organization

## Phase 6: Cleanup
- [ ] Archive workspace to `specs/archive/test-style-migration/`
- [ ] Update PRD status to "Completed"
- [ ] Delete `specs/active/test-style-migration/`

## Implementation Order Recommendation

Start with simpler files and progress to more complex:

1. **`test_commands.py`** (14 tests, 2 classes) - Smallest, good warmup
2. **`test_executor.py`** (13 tests, 2 classes) - Small, straightforward
3. **`test_optional_jinja.py`** (32 tests, 8 classes) - Medium complexity
4. **`test_plugin.py`** (51 tests, 8 classes) - Largest, most complex

## Notes

- Each class should become a section with a comment header
- Use `test_{class_name_snake}_{method_name}` naming pattern
- Keep method docstrings as function docstrings
- No shared state between tests (pytest ensures this)
