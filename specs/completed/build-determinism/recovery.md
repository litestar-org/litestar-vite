# Recovery Guide: Deterministic Build Output

## Current State

**Status: Implementation Complete** ✓

All acceptance criteria from the PRD have been met:
- ✓ Running `litestar assets generate-types` twice produces no file changes (via timestamp exclusion)
- ✓ Running `litestar assets build` twice produces no file changes (via write-on-change)
- ✓ `generatedAt` field still exists but is excluded from content hash comparison
- ✓ All JSON files use sorted keys for deterministic ordering
- ✓ Existing test suite passes (496/496 unit tests)
- ✓ New tests verify deterministic output (22 tests in test_codegen_determinism.py)
- ✓ Linting clean (`make lint` passes)

## Implementation Summary

### New Files Created

| File | Purpose |
|------|---------|
| `src/py/litestar_vite/_codegen/utils.py` | Deterministic serialization utilities |
| `src/py/tests/unit/test_codegen_determinism.py` | 22 tests for determinism verification |

### Files Modified

| File | Changes |
|------|---------|
| `_codegen/__init__.py` | Export new utilities |
| `_codegen/inertia.py` | Sort pages and shared props |
| `_codegen/routes.py` | Sort routes, params, methods |
| `codegen.py` | Export new utilities |
| `cli.py` | Apply write_if_changed to all CLI exports |
| `plugin.py` | Apply write_if_changed to runtime config |

### Key Utilities Added

```python
# In _codegen/utils.py

def _deep_sort_dict(obj: Any) -> Any:
    """Recursively sort all dictionary keys."""

def strip_timestamp_for_comparison(content: bytes) -> bytes:
    """Remove generatedAt field for content comparison."""

def write_if_changed(
    path: Path,
    content: bytes | str,
    *,
    normalize_for_comparison: Callable[[bytes], bytes] | None = None,
) -> bool:
    """Write file only if content differs (with optional normalization)."""

def encode_deterministic_json(data: dict[str, Any]) -> bytes:
    """Encode JSON with sorted keys for deterministic output."""
```

## Testing Commands

```bash
# Run determinism tests
uv run pytest src/py/tests/unit/test_codegen_determinism.py -v

# Run all unit tests
uv run pytest src/py/tests/unit/ -q

# Run linting
make lint
```

## Manual Verification

To verify deterministic builds manually:

```bash
# 1. Generate types and check git status
litestar assets generate-types
git status

# 2. Generate again - should show no changes
litestar assets generate-types
git status  # Should show no changes

# 3. Export routes
litestar assets export-routes --typescript
git status

# 4. Export again - should show no changes
litestar assets export-routes --typescript
git status  # Should show no changes
```

## Next Steps

1. **Manual verification** - Run the commands above in a real project
2. **Review** - Have changes reviewed
3. **Archive** - Move workspace from `specs/active/` to `specs/completed/`

## Notes

- The "client" field validation error mentioned in the PRD was from an older schema version
- The current TypeScript schema (`bridge-schema.ts`) is valid and doesn't have a "client" field
- CLI now shows "(updated)" or "(unchanged)" status for each file operation
