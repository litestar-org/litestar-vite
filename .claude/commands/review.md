---
description: Run quality gates and documentation review
allowed-tools: Read, Write, Edit, Glob, Grep, Bash
---

# Quality Review Workflow

You are reviewing the feature from: **specs/active/$ARGUMENTS**

## Phase 1: Quality Gate

Run all quality checks:

```bash
# Tests
make test

# Linting
make lint

# Type checking (if available)
make type-check

# Coverage
make coverage
```

All must pass before proceeding.

## Phase 2: Anti-Pattern Scan

Check for prohibited patterns:

```bash
# Check for future annotations (should be 0)
rg "from __future__ import annotations" src/py/litestar_vite/ --count

# Check for class-based tests (should be 0)
rg "class Test" src/py/tests/ --count
```

If any violations found, report them for fixing before continuing.

## Phase 3: Documentation Review

### Check Docstrings

All new public APIs must have Google-style docstrings:

```python
def my_function(arg: str) -> str:
    """Brief description.

    Args:
        arg: Description of argument.

    Returns:
        Description of return value.

    Raises:
        ValueError: When argument is invalid.
    """
```

### Check Guide Updates

If new patterns were introduced:
- [ ] Update `specs/guides/architecture.md`
- [ ] Update `specs/guides/code-style.md`
- [ ] Add examples for new APIs

## Phase 4: Knowledge Capture

Document any lessons learned or new patterns in `specs/guides/`.

## Phase 5: Archive Workspace

After all checks pass:

```bash
# Create archive
mkdir -p specs/archive/$ARGUMENTS

# Move files
mv specs/active/$ARGUMENTS/* specs/archive/$ARGUMENTS/

# Clean up
rm -rf specs/active/$ARGUMENTS
```

Add completion metadata to archived PRD:

```markdown
---
## Completion Metadata

- **Completed**: {date}
- **Status**: Completed
- **Test Coverage**: {percentage}%

### Lessons Learned
- {lesson}

### Patterns Introduced
- {pattern added to guides}

### Files Modified
- `src/py/litestar_vite/{file}.py`
---
```

## Success Criteria

- [ ] All quality gates pass
- [ ] No anti-patterns in code
- [ ] Documentation updated if needed
- [ ] Knowledge captured in guides
- [ ] Workspace archived
