---
description: Fix a GitHub issue
allowed-tools: Read, Write, Edit, Glob, Grep, Bash, Task, WebSearch
---

# Fix GitHub Issue: $ARGUMENTS

## Phase 1: Understand the Issue

```bash
gh issue view $ARGUMENTS
```

Read the issue description and identify:
- What is the bug/feature request?
- What is the expected behavior?
- What is the actual behavior?
- Are there reproduction steps?

## Phase 2: Investigate

Search the codebase for relevant code:

```
Grep(pattern="...", path="src/py/litestar_vite")
Glob(pattern="src/py/litestar_vite/**/*.py")
```

Find related tests:

```
Grep(pattern="...", path="src/py/tests")
```

## Phase 3: Implement Fix

Follow project standards:
- Type hints: `T | None`
- Docstrings: Google style
- No `from __future__ import annotations`

## Phase 4: Write Tests

Add tests covering:
- The bug fix / new behavior
- Edge cases
- Error conditions

```python
async def test_fix_for_issue_$ARGUMENTS() -> None:
    """Test fix for GitHub issue #$ARGUMENTS."""
    # ...
```

## Phase 5: Verify

```bash
make test
make lint
```

## Phase 6: Create Commit

```bash
git add -A
git commit -m "fix: [description] (closes #$ARGUMENTS)"
```

## Phase 7: Create PR (if requested)

```bash
gh pr create --title "fix: [description]" --body "Closes #$ARGUMENTS

## Summary
- [changes made]

## Test Plan
- [how to test]"
```
