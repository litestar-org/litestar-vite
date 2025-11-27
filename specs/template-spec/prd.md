# PRD: {Feature Name}

## Overview

| Field | Value |
|-------|-------|
| **Slug** | {slug} |
| **Created** | {YYYY-MM-DD} |
| **Status** | Draft |
| **Author** | {agent/user} |

---

## Problem Statement

{Describe the problem this feature solves. Be specific about user pain points and current limitations.}

---

## Goals

1. {Primary goal - what must be achieved}
2. {Secondary goal}
3. {Tertiary goal}

---

## Non-Goals

- {What this feature explicitly will NOT do}
- {Scope boundaries}

---

## Acceptance Criteria

- [ ] {Specific, testable criterion 1}
- [ ] {Specific, testable criterion 2}
- [ ] {Specific, testable criterion 3}
- [ ] All tests pass (`make test`)
- [ ] Linting passes (`make lint`)
- [ ] 90%+ test coverage for new code

---

## Technical Approach

### Architecture

{How this feature fits into the existing litestar-vite architecture}

### Affected Files

| File | Change Type | Description |
|------|-------------|-------------|
| `src/py/litestar_vite/{file}.py` | Modify | {what changes} |
| `src/js/src/{file}.ts` | Add | {new file purpose} |

### API Changes

#### New APIs

```python
# Example new function signature
def new_function(param: str, option: bool = False) -> Result:
    """Brief description."""
```

#### Modified APIs

```python
# Before
def existing_function(param: str) -> Result:

# After
def existing_function(param: str, new_option: bool = False) -> Result:
```

### Configuration Changes

```python
@dataclass
class ViteConfig:
    # New field
    new_option: bool = False
```

---

## Testing Strategy

### Unit Tests

- Test {component 1} in isolation
- Test {component 2} with mocked dependencies
- Test error handling paths

### Integration Tests

- Test with real Litestar app
- Test with real Vite build (if applicable)

### Edge Cases

- [ ] Empty input
- [ ] None/null values
- [ ] Invalid configuration
- [ ] {specific edge case}

---

## Research Questions

Questions for Expert agent to investigate:

- [ ] {Research question 1}
- [ ] {Research question 2}
- [ ] How does Litestar handle {specific concern}?
- [ ] What's the best practice for {pattern}?

---

## Dependencies

### Python Dependencies

- {package}: {version} - {why needed}

### TypeScript Dependencies

- {package}: {version} - {why needed}

---

## Risks & Mitigations

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| {risk 1} | High/Medium/Low | High/Medium/Low | {mitigation strategy} |
| {risk 2} | | | |

---

## Timeline Estimate

| Phase | Estimated Effort |
|-------|------------------|
| Research | {effort} |
| Implementation | {effort} |
| Testing | {effort} |
| Documentation | {effort} |

---

## Open Questions

- {Question that needs human input}
- {Decision that requires discussion}

---

## References

- [Litestar Docs]({relevant link})
- [Vite Docs]({relevant link})
- [Related Issue]({github issue link})
