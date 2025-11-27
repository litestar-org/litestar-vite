# Tasks: {Feature Name}

**Slug**: {slug}
**PRD**: [prd.md](./prd.md)
**Last Updated**: {YYYY-MM-DD}

---

## Phase 1: Planning & Research

- [x] Create PRD
- [x] Identify affected components
- [x] Define acceptance criteria
- [x] Set up workspace

---

## Phase 2: Expert Research

- [ ] Research {topic 1}
  - Context7: {library} documentation
  - Focus: {specific aspect}
- [ ] Research {topic 2}
  - WebSearch: best practices
- [ ] Review existing patterns in codebase
  - Files: `src/py/litestar_vite/{relevant}*.py`

---

## Phase 3: Core Implementation

### Python Backend

- [ ] Implement {component 1}
  - File: `src/py/litestar_vite/{file}.py`
  - Changes: {description}
- [ ] Implement {component 2}
  - File: `src/py/litestar_vite/{file}.py`
  - Changes: {description}
- [ ] Update configuration
  - File: `src/py/litestar_vite/config.py`
  - Add: {new options}

### TypeScript Frontend (if applicable)

- [ ] Implement {component}
  - File: `src/js/src/{file}.ts`
  - Changes: {description}

---

## Phase 4: Integration

- [ ] Integrate with existing {system/component}
- [ ] Update plugin initialization (if needed)
- [ ] Verify backward compatibility

---

## Phase 5: Testing (Auto-invoked)

### Unit Tests

- [ ] Test {component 1}
  - File: `src/py/tests/unit/test_{module}.py`
  - Coverage target: 90%+
- [ ] Test {component 2}
- [ ] Test edge cases

### Integration Tests

- [ ] Test with Litestar app
  - File: `src/py/tests/integration/test_{feature}.py`
- [ ] Test with real Vite (if applicable)

### Verification

- [ ] `make test` passes
- [ ] `pytest -n auto` works (parallel)
- [ ] Coverage ≥ 90% for new code

---

## Phase 6: Documentation (Auto-invoked)

- [ ] Update docstrings for new APIs
- [ ] Update `specs/guides/architecture.md` (if architecture changed)
- [ ] Update `specs/guides/code-style.md` (if new patterns)
- [ ] Add examples (if new public APIs)

---

## Phase 7: Quality Gate & Archive

### Quality Checks

- [ ] `make test` passes
- [ ] `make lint` passes
- [ ] `make type-check` passes
- [ ] Coverage ≥ 90%

### Anti-Pattern Scan

- [ ] No `Optional[T]` usage
- [ ] No `from __future__ import annotations`
- [ ] No class-based tests
- [ ] All public APIs documented

### Completion

- [ ] All acceptance criteria met
- [ ] Knowledge captured in guides
- [ ] Workspace archived to `specs/archive/{slug}/`

---

## Progress Log

| Date | Phase | Status | Notes |
|------|-------|--------|-------|
| {date} | Planning | Complete | PRD approved |
| | | | |

---

## Blockers

| Blocker | Status | Resolution |
|---------|--------|------------|
| {none yet} | | |
