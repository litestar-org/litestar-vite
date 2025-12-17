# PRD: Deterministic Build Output and Write-on-Change

## Overview
- **Slug**: build-determinism
- **Created**: 2025-12-17
- **Status**: Completed
- **Completed**: 2025-12-17

## Problem Statement

When running `litestar assets build` or `litestar assets generate-types`, the generated files change on every run even when the underlying application code hasn't changed. This causes:

1. **Unnecessary git diffs**: Files like `inertia-pages.json` and `routes.json` show changes on every build, polluting version control and making code reviews harder
2. **Build cache invalidation**: File watchers (Vite, etc.) trigger rebuilds unnecessarily
3. **CI/CD instability**: Deterministic builds are required for reproducible deployments

### Root Causes Identified

1. **`generatedAt` timestamp in `inertia-pages.json`** (line 527 in `_codegen/inertia.py`)
   - Every generation includes `datetime.datetime.now().isoformat()` which always differs

2. **Potential dict ordering issues**
   - Python dicts are insertion-ordered (3.7+), but the order depends on route registration order
   - Currently uses `sorted()` in some places but not consistently

3. **Missing `_write_if_changed` in CLI exports**
   - The `_write_if_changed` helper exists in `plugin.py` but CLI commands in `cli.py` (line 1013) use direct `write_bytes()` without content comparison
   - CLI always writes even when content is identical (after removing non-deterministic fields)

4. **Secondary Issue: `.litestar.json` validation error**
   - Error: `"client" must be a non-empty string`
   - This appears when TypeGenConfig types section is malformed
   - Occurs because `.litestar.json` is written without proper type config when types are partially configured

## Goals

1. **Make all generated file content deterministic** - same input produces byte-identical output
2. **Only write files when actual content changes** - reduce unnecessary file system churn
3. **Fix `.litestar.json` validation** - ensure TypeGenConfig writes valid configurations

## Non-Goals

- Removing the `generatedAt` field entirely (useful for debugging/auditing)
- Adding compression or minification to generated files
- Changing the overall structure of generated files

## Acceptance Criteria

- [x] Running `litestar assets generate-types` twice in a row produces no file changes
- [x] Running `litestar assets build` twice in a row produces no file changes (for type artifacts)
- [x] Git status shows no changes after repeated builds on unchanged code
- [x] `generatedAt` field still exists but is excluded from content hash comparison
- [x] All JSON files use sorted keys for deterministic ordering
- [x] `.litestar.json` validates successfully after `export-routes` or `generate-types`
- [x] Existing test suite passes (496/496)
- [x] New tests verify deterministic output (22 new tests)

## Technical Approach

### Architecture

The solution involves three coordinated changes:

```
┌─────────────────────────────────────────────────────────────────┐
│                     Code Generation Flow                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  1. Generate Content (deterministic)                             │
│     ├─ Sort dict keys consistently                               │
│     ├─ Sort lists where order is semantic                        │
│     └─ Exclude/normalize timestamps                              │
│                                                                  │
│  2. Compare Content (hash-based)                                 │
│     ├─ Strip non-deterministic fields for comparison             │
│     └─ Use MD5/SHA256 hash for efficiency                        │
│                                                                  │
│  3. Conditional Write (only on change)                           │
│     └─ Write file with full content (including timestamp)        │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Affected Files

#### Python (src/py/litestar_vite/)

- `_codegen/inertia.py` - Make `generate_inertia_pages_json` output deterministic
  - Sort `pages_dict` keys
  - Sort `sharedProps` keys
  - Move `generatedAt` handling to allow comparison without it

- `_codegen/routes.py` - Verify/ensure `generate_routes_json` determinism
  - Sort route entries consistently

- `plugin.py` - Already has `_write_if_changed`, ensure it's used everywhere
  - Refactor to handle "compare without timestamp" pattern

- `cli.py` - Use `_write_if_changed` pattern for CLI exports
  - `_export_inertia_pages_metadata()` - lines 1011-1013
  - `export_routes_cmd()` - lines 975-976
  - All `generate-types` exports

- `config.py` - Ensure TypeGenConfig validation for `.litestar.json`

#### TypeScript (src/js/src/shared/)

- `emit-page-props-types.ts` - Verify TypeScript generation is deterministic
- `bridge-schema.ts` - Fix "client" validation error handling

### API Changes

No public API changes. Internal refactoring only.

### Proposed Implementation

#### 1. Create deterministic JSON encoder utility

```python
# In _codegen/utils.py or similar
def encode_deterministic_json(
    data: dict[str, Any],
    *,
    exclude_keys: set[str] | None = None,
) -> bytes:
    """Encode JSON with sorted keys for deterministic output.

    Args:
        data: Dictionary to encode.
        exclude_keys: Keys to exclude from comparison (e.g., 'generatedAt').

    Returns:
        Formatted JSON bytes.
    """
    import msgspec
    from litestar.serialization import encode_json

    # Deep-sort all dict keys
    sorted_data = _deep_sort_dict(data)
    return msgspec.json.format(encode_json(sorted_data), indent=2)
```

#### 2. Modify `_write_if_changed` to support content normalization

```python
def _write_if_changed(
    path: Path,
    content: bytes | str,
    *,
    normalize_for_comparison: Callable[[bytes], bytes] | None = None,
    encoding: str = "utf-8",
) -> bool:
    """Write file only if normalized content differs."""
    content_bytes = content.encode(encoding) if isinstance(content, str) else content

    if path.exists():
        existing = path.read_bytes()
        # Normalize both for comparison (e.g., strip timestamps)
        if normalize_for_comparison:
            existing_normalized = normalize_for_comparison(existing)
            new_normalized = normalize_for_comparison(content_bytes)
        else:
            existing_normalized = existing
            new_normalized = content_bytes

        if hashlib.md5(existing_normalized).hexdigest() == hashlib.md5(new_normalized).hexdigest():
            return False  # No change

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content_bytes)
    return True
```

#### 3. Sort inertia pages output

```python
# In generate_inertia_pages_json()
root: dict[str, Any] = {
    "pages": dict(sorted(pages_dict.items())),  # Sort by component name
    "sharedProps": dict(sorted(shared_props.items())),  # Sort by prop name
    "typeGenConfig": {...},
    "generatedAt": datetime.datetime.now(tz=datetime.timezone.utc).isoformat(),
}
```

## Testing Strategy

### Unit Tests

- Test `_write_if_changed` with content normalization
- Test `generate_inertia_pages_json` produces sorted output
- Test `generate_routes_json` produces sorted output
- Test repeated calls produce identical output

### Integration Tests

- Test full `litestar assets generate-types` produces stable output
- Test full `litestar assets build` produces stable type artifacts

### Edge Cases

- Empty pages/routes
- Unicode component names
- Very large route sets (ensure performance is acceptable)

## Research Questions

- [ ] Should `generatedAt` be moved to a separate metadata file?
- [ ] Should we add a `--force` flag to bypass content comparison?
- [ ] Should the JS plugin respect the `generatedAt` for file watching?

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Sorting changes component order semantically | Low | Only sort JSON keys, not arrays where order matters |
| Performance impact of content comparison | Low | MD5 is fast; files are typically <100KB |
| Breaking changes to generated file format | Medium | Ensure JSON structure remains backward compatible |
| Edge cases with non-ASCII keys | Low | Test with unicode component/route names |

## Implementation Notes

### Dict ordering in Python 3.10+

Python dicts maintain insertion order, but when serializing to JSON:
- `json.dumps(d, sort_keys=True)` ensures consistent ordering
- msgspec doesn't have `sort_keys`, need to pre-sort dict

### Content normalization for comparison

To compare content while ignoring `generatedAt`:
```python
def strip_generated_at(content: bytes) -> bytes:
    """Remove generatedAt field for content comparison."""
    data = json.loads(content)
    data.pop('generatedAt', None)
    return json.dumps(data, sort_keys=True).encode()
```

### The `.litestar.json` client error

The error `"client" must be a non-empty string` comes from `bridge-schema.ts`:
```typescript
function assertString(val: unknown, field: string): asserts val is string {
  if (typeof val !== 'string' || val === '') {
    fail(`"${field}" must be a non-empty string`)
  }
}
```

This occurs when `types.client` is missing in `.litestar.json`. The fix requires ensuring the Python side always populates required fields even when types config is minimal.

---

## Completion Metadata

- **Completed**: 2025-12-17
- **Status**: Completed
- **Test Coverage**: 96% for utils.py, 92% for routes.py (modified modules)

### Lessons Learned
- Using hash comparison (MD5) for file comparison is efficient and reliable
- Timestamp exclusion via normalization callback is cleaner than modifying the data structure
- Sorting all dict keys recursively is necessary for true determinism

### Patterns Introduced
- `write_if_changed()` utility with optional content normalization
- `encode_deterministic_json()` for sorted key output
- CLI status feedback pattern: "(updated)" / "(unchanged)"

### Files Created
- `src/py/litestar_vite/_codegen/utils.py` - New determinism utilities
- `src/py/tests/unit/test_codegen_determinism.py` - 22 new tests

### Files Modified
- `src/py/litestar_vite/_codegen/__init__.py` - Export new utilities
- `src/py/litestar_vite/_codegen/inertia.py` - Sorted pages and shared props
- `src/py/litestar_vite/_codegen/routes.py` - Sorted routes, params, methods
- `src/py/litestar_vite/codegen.py` - Export new utilities
- `src/py/litestar_vite/cli.py` - Apply write_if_changed to all exports
- `src/py/litestar_vite/plugin.py` - Apply write_if_changed to runtime config
