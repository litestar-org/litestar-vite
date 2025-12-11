# Recovery Guide: Python Code Cleanup

## Current State

**Status**: PRD Complete - Ready for Implementation

The analysis phase is complete. All code smells have been documented:
- 25+ nested imports identified in cli.py
- 2 duplicate comment blocks in executor.py
- 2 import consolidations needed in helpers.py
- No breaking changes required

## Files to Modify

| File | Status | Priority |
|------|--------|----------|
| cli.py | Not started | High |
| executor.py | Not started | Medium |
| helpers.py | Not started | Medium |
| doctor.py | Not started | Low |

## Next Steps

1. **Start with cli.py** - Has the most nested imports
2. **Test after each file** - Run `make lint && make test`
3. **Keep httpx nested** - It's an optional dependency check
4. **Preserve behavior comments** - Only remove obvious/redundant ones

## Key Decisions Made

1. **Keep nested imports for optional dependencies** (httpx, fsspec)
2. **Keep defensive exception handling** - Protects against missing session middleware
3. **Keep section divider comments** - Useful for navigation in large files
4. **Remove duplicate comment blocks** - Same explanation in multiple places

## Context for Resumption

The user wants to remove the beta tag. This cleanup addresses:
- Nested imports that aren't conditional/circular-avoiding
- Inline comments that explain obvious code
- Minor code smells

**Critical constraint**: No breaking changes to public API.

## Validation Commands

```bash
# After each file change
make lint
make test

# Final validation
make check-all
```

## Rollback Plan

All changes are pure refactoring. If any issues arise:
1. `git checkout -- <file>` to revert individual files
2. `git stash` to save work in progress
3. All tests should continue to pass throughout
