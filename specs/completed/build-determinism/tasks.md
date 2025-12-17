# Tasks: Deterministic Build Output and Write-on-Change

## Phase 1: Planning ✓
- [x] Create PRD
- [x] Identify affected components
- [x] Analyze root causes

## Phase 2: Core Infrastructure ✓

### 2.1 Create deterministic serialization utilities ✓
- [x] Create `_codegen/utils.py` with `_deep_sort_dict()` helper
- [x] Add `encode_deterministic_json()` function for sorted JSON output
- [x] Add unit tests for sorting utilities

### 2.2 Enhance `_write_if_changed` pattern ✓
- [x] Add `normalize_for_comparison` callback parameter to `_write_if_changed`
- [x] Create `strip_timestamp_for_comparison()` helper
- [x] Extract `_write_if_changed` to shared module (`_codegen/utils.py`)
- [x] Add unit tests for conditional write with normalization

## Phase 3: Deterministic Generation ✓

### 3.1 Inertia pages JSON ✓
- [x] Sort `pages_dict` by component name in `generate_inertia_pages_json()`
- [x] Sort `sharedProps` by prop name
- [x] Sort `customTypes` lists (already using `sorted()`, verified)
- [x] Sort root keys for deterministic JSON structure
- [x] Add test verifying repeated generation produces identical output

### 3.2 Routes JSON and TypeScript ✓
- [x] Sort routes by name in `generate_routes_json()`
- [x] Sort params and query_params dicts
- [x] Sort routes by name in `generate_routes_ts()`
- [x] Sort HTTP methods for consistency
- [x] Add tests for repeated generation

### 3.3 OpenAPI schema export ✓
- [x] OpenAPI export uses msgspec.json.format (deterministic)
- [x] Applied write_if_changed to OpenAPI export

## Phase 4: CLI Integration ✓

### 4.1 Apply write-on-change to CLI commands ✓
- [x] Refactor `_export_inertia_pages_metadata()` to use `write_if_changed`
- [x] Update to use timestamp-aware content comparison
- [x] Refactor `export_routes_cmd()` TypeScript export to use `write_if_changed`
- [x] Refactor `_export_routes_metadata()` to use `write_if_changed`
- [x] Refactor `_export_routes_typescript()` to use `write_if_changed`
- [x] Refactor `_export_openapi_schema()` to use `write_if_changed`

### 4.2 Update CLI output messages ✓
- [x] Show "✓ {file} (unchanged)" when file content matches
- [x] Show "✓ {file} (updated)" when file was written
- [x] Maintain backward-compatible output format

## Phase 5: Fix .litestar.json ✓

### 5.1 Apply write-on-change to runtime config ✓
- [x] Update `_write_runtime_config_file()` in plugin.py to use `write_if_changed`
- [x] Note: The "client" field issue from PRD was from older schema version; current TypeScript schema is valid

## Phase 6: Testing ✓

### 6.1 Unit tests (90%+ coverage) ✓
- [x] Test `_deep_sort_dict()` with nested dicts
- [x] Test `_write_if_changed` with normalization
- [x] Test `generate_inertia_pages_json` determinism
- [x] Test `generate_routes_json` determinism
- [x] Test `generate_routes_ts` determinism
- [x] All 496 unit tests passing

### 6.2 Integration tests
- [ ] Test `litestar assets generate-types` produces stable output (manual verification recommended)
- [ ] Test `litestar assets export-routes` produces stable output (manual verification recommended)
- [ ] Test `litestar assets build` type artifacts are stable (manual verification recommended)

### 6.3 Edge cases ✓
- [x] Test with empty pages/routes
- [x] Test primitive values preservation
- [x] Test repeated generation produces byte-identical output

## Phase 7: Documentation ✓

- [x] Update docstrings for modified functions (all functions have Google-style docstrings)
- [x] Add inline comments explaining determinism requirements

## Phase 8: Quality Gate ✓

- [x] All unit tests pass (496/496)
- [x] Linting clean (`make lint` - all checks pass)
- [x] 22 new tests for determinism in `test_codegen_determinism.py`
- [ ] Manual verification of deterministic builds (recommended)
- [ ] Archive workspace (after review)

## Implementation Summary

### Files Created
- `src/py/litestar_vite/_codegen/utils.py` - New utility module with:
  - `_deep_sort_dict()` - Recursive dict key sorting
  - `strip_timestamp_for_comparison()` - Removes generatedAt for content comparison
  - `write_if_changed()` - Conditional write with hash comparison
  - `encode_deterministic_json()` - Sorted JSON encoding

- `src/py/tests/unit/test_codegen_determinism.py` - 22 new tests for determinism

### Files Modified
- `src/py/litestar_vite/_codegen/__init__.py` - Export new utilities
- `src/py/litestar_vite/_codegen/inertia.py` - Sorted pages and shared props
- `src/py/litestar_vite/_codegen/routes.py` - Sorted routes, params, and methods
- `src/py/litestar_vite/codegen.py` - Export new utilities
- `src/py/litestar_vite/cli.py` - Apply write_if_changed to all exports
- `src/py/litestar_vite/plugin.py` - Apply write_if_changed to runtime config

### Key Changes
1. All JSON output now has deterministically sorted keys
2. Files are only written when content actually changes
3. Timestamp fields are excluded from content comparison
4. CLI shows "(updated)" or "(unchanged)" status for each file
