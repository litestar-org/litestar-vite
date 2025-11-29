# Recovery Guide: {Feature Name}

**Slug**: {slug}
**Last Updated**: {YYYY-MM-DD HH:MM}

---

## Quick Resume

To resume work on this feature:

1. Read the PRD: `specs/active/{slug}/prd.md`
2. Check current progress: `specs/active/{slug}/tasks.md`
3. Review research: `specs/active/{slug}/research/`

---

## Current State

| Aspect | Status |
|--------|--------|
| **Phase** | {current phase} |
| **Last Action** | {what was just completed} |
| **Next Action** | {what needs to happen next} |
| **Blockers** | {any blockers or None} |

---

## Files Modified

### Python

| File | Status | Notes |
|------|--------|-------|
| `src/py/litestar_vite/{file}.py` | In Progress | {what's done, what's left} |

### TypeScript

| File | Status | Notes |
|------|--------|-------|
| `src/js/src/{file}.ts` | Not Started | |

### Tests

| File | Status | Notes |
|------|--------|-------|
| `src/py/tests/unit/test_{module}.py` | Not Started | |

---

## Research Completed

### Context7 Lookups

- **Litestar**: {topic researched}
  - Finding: {key insight}
- **Vite**: {topic researched}
  - Finding: {key insight}

### WebSearch Results

- Query: "{search query}"
  - Finding: {key insight}

---

## Decisions Made

| Decision | Rationale | Date |
|----------|-----------|------|
| {decision 1} | {why this approach} | {date} |
| {decision 2} | | |

---

## Open Questions

- [ ] {Question still needing answer}
- [x] {Resolved question} → Answer: {answer}

---

## Context for Next Session

{Free-form notes about what the next session should know}

### Key Files to Read First

1. `src/py/litestar_vite/{key_file}.py` - {why}
2. `specs/active/{slug}/research/plan.md` - {research findings}

### Potential Issues

- {Known issue to watch for}
- {Edge case discovered but not yet handled}

### Testing Notes

- Local test command: `pytest src/py/tests/unit/test_{module}.py -v`
- Current test status: {passing/failing}

---

## Checkpoint History

| Timestamp | Checkpoint | Agent |
|-----------|------------|-------|
| {datetime} | PRD created | PRD |
| {datetime} | Research complete | Expert |
| {datetime} | Implementation 50% | Expert |
| | | |

---

## How to Continue

### If Resuming Implementation

```python
# Read current state
Read("specs/active/{slug}/prd.md")
Read("specs/active/{slug}/tasks.md")

# Check what's modified
Read("src/py/litestar_vite/{current_file}.py")

# Continue from {specific line/function}
```

### If Resuming Testing

```python
# Read implementation
Read("src/py/litestar_vite/{implemented_file}.py")

# Check existing tests
Read("src/py/tests/unit/test_{module}.py")

# Run tests
Bash("pytest src/py/tests/unit/test_{module}.py -v")
```

### If Resuming Documentation

```python
# Check what needs documenting
Read("specs/active/{slug}/tasks.md")  # Phase 6 items

# Read guides to update
Read("specs/guides/architecture.md")
```
