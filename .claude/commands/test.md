---
description: Run comprehensive tests for a feature
allowed-tools: Read, Write, Edit, Glob, Grep, Bash, mcp__context7__get-library-docs
---

# Testing Workflow

You are testing the feature from: **specs/active/$ARGUMENTS**

## Phase 1: Load Context

1. Read the PRD and understand acceptance criteria:
   - `specs/active/$ARGUMENTS/prd.md`
   - `specs/active/$ARGUMENTS/tasks.md`

2. Read testing guide:
   - `specs/guides/testing.md`

3. Find modified files:
   ```bash
   git diff --name-only HEAD~10
   ```

## Phase 2: Analyze Test Requirements

For each acceptance criterion in the PRD:
- [ ] Identify what needs to be tested
- [ ] Plan unit tests
- [ ] Plan integration tests
- [ ] Identify edge cases

## Phase 3: Write Tests

### Python Tests (Function-Based ONLY)

```python
import pytest
from unittest.mock import AsyncMock, MagicMock

@pytest.fixture
def mock_config() -> ViteConfig:
    """Create mock ViteConfig."""
    return ViteConfig(...)

async def test_feature_happy_path(mock_config: ViteConfig) -> None:
    """Test normal operation."""
    # Arrange
    # Act
    # Assert

async def test_feature_error_case(mock_config: ViteConfig) -> None:
    """Test error handling."""
    with pytest.raises(ExpectedError):
        ...

@pytest.mark.parametrize(("input", "expected"), [...])
def test_feature_variations(...) -> None:
    """Test multiple scenarios."""
    ...
```

### TypeScript Tests

```typescript
import { describe, it, expect, vi } from 'vitest';

describe('feature', () => {
  it('should work normally', () => {
    // ...
  });

  it('should handle errors', () => {
    // ...
  });
});
```

## Phase 4: Test Categories

Ensure coverage for:

### Unit Tests
- [ ] Each public function/method
- [ ] Each class behavior

### Integration Tests
- [ ] Components working together
- [ ] With real dependencies

### Edge Cases
- [ ] Empty input
- [ ] None/null values
- [ ] Boundary values
- [ ] Invalid input

### Error Handling
- [ ] Missing dependencies
- [ ] Invalid configuration
- [ ] Network failures (if applicable)

### Async Behavior (if applicable)
- [ ] Concurrent access
- [ ] Race conditions

## Phase 5: Run Tests and Check Coverage

```bash
# Run all tests
make test

# Run with coverage
make coverage

# Check specific module coverage
pytest --cov=src/py/litestar_vite/{module} src/py/tests/ --cov-report=term-missing

# Ensure tests run in parallel
pytest -n auto src/py/tests/
```

## Phase 6: Update Progress

Update `specs/active/$ARGUMENTS/tasks.md` with testing completion status.

## Success Criteria

- [ ] 90%+ coverage for modified modules
- [ ] All acceptance criteria tested
- [ ] Edge cases covered
- [ ] Tests run in parallel (`pytest -n auto`)
- [ ] All tests pass
- [ ] Function-based tests only (no `class Test...`)
