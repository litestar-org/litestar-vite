# Recovery Guide: Test Style Migration

## Current State

PRD and task breakdown complete. Ready for implementation.

## Files to be Modified

| File | Status | Notes |
|------|--------|-------|
| `src/py/tests/unit/test_commands.py` | Pending | 2 classes, ~14 tests |
| `src/py/tests/unit/test_executor.py` | Pending | 2 classes, ~13 tests |
| `src/py/tests/unit/test_plugin.py` | Pending | 8 classes, ~51 tests |
| `src/py/tests/integration/test_optional_jinja.py` | Pending | 8 classes, ~32 tests |

## Next Steps

1. Run baseline test count verification
2. Start with `test_commands.py` migration
3. Proceed through files in order of complexity

## Context for Resumption

### Key Pattern to Follow

```python
# Before (class-based):
class TestVitePlugin:
    """Test VitePlugin core functionality."""

    def test_plugin_initialization_default_config(self) -> None:
        """Test plugin initialization with default configuration."""
        plugin = VitePlugin()
        assert plugin._config is not None

# After (function-based):
# =====================================================
# VitePlugin Core Functionality
# =====================================================


def test_vite_plugin_initialization_default_config() -> None:
    """Test plugin initialization with default configuration."""
    plugin = VitePlugin()
    assert plugin._config is not None
```

### Naming Convention

- Class: `TestVitePlugin` → prefix: `vite_plugin`
- Method: `test_plugin_initialization_default_config`
- Result: `test_vite_plugin_initialization_default_config`

### Important Constraints

1. **DO NOT change test logic** - only restructure
2. **Preserve all docstrings** - copy them to functions
3. **Run tests after each file** - verify nothing breaks
4. **Keep imports unchanged** - same dependencies
5. **Use section comments** - for organization

### Reference Files (Good Examples)

- `src/py/tests/unit/test_config.py` - Function-based pattern
- `src/py/tests/unit/inertia/test_response.py` - Async tests with fixtures
- `src/py/tests/unit/test_asset_loader.py` - Well-organized

### Commands to Verify

```bash
# Before migration - record count
pytest src/py/tests/unit/test_commands.py --collect-only -q

# After migration - verify same count
pytest src/py/tests/unit/test_commands.py -v

# Full suite after all files
make test
make lint
make type-check
```
