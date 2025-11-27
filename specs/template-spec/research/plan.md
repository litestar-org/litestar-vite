# Research Plan: {Feature Name}

**Slug**: {slug}
**Created**: {YYYY-MM-DD}

---

## Research Objectives

1. {Primary research objective}
2. {Secondary objective}
3. {Tertiary objective}

---

## Research Questions

### Architecture & Design

- [ ] How should {feature} integrate with existing VitePlugin?
- [ ] What's the best pattern for {specific concern}?
- [ ] Are there similar implementations in other frameworks?

### Library/Framework Specific

- [ ] How does Litestar handle {specific functionality}?
  - Context7: `/litestar-org/litestar` - topic: {topic}
- [ ] What Vite APIs are available for {need}?
  - Context7: `/vitejs/vite` - topic: {topic}

### Best Practices

- [ ] What's the current best practice for {pattern}?
  - WebSearch: "{framework} {pattern} best practices 2025"
- [ ] How do other projects solve {problem}?

---

## Research Sources

### Priority 1: Internal

| Source | Purpose | Status |
|--------|---------|--------|
| `specs/guides/architecture.md` | Current patterns | [ ] |
| `src/py/litestar_vite/plugin.py` | Existing plugin pattern | [ ] |
| `src/py/litestar_vite/inertia/` | Inertia implementation | [ ] |

### Priority 2: Context7

| Library | Topic | Tokens | Status |
|---------|-------|--------|--------|
| Litestar | {topic} | 5000 | [ ] |
| Vite | {topic} | 5000 | [ ] |
| Inertia.js | {topic} | 3000 | [ ] |

### Priority 3: WebSearch

| Query | Purpose | Status |
|-------|---------|--------|
| "{query 1}" | {why} | [ ] |
| "{query 2}" | {why} | [ ] |

---

## Findings

### {Topic 1}

**Source**: {where this came from}

**Key Insights**:
- {insight 1}
- {insight 2}

**Code Example**:
```python
# Example code from research
```

**Implications for Implementation**:
- {how this affects the implementation}

---

### {Topic 2}

**Source**: {where this came from}

**Key Insights**:
- {insight 1}

---

## Patterns Discovered

### Pattern: {Name}

**Use When**: {scenario}

**Implementation**:
```python
# Pattern code
```

**Notes**: {additional context}

---

## Decisions Based on Research

| Question | Decision | Rationale |
|----------|----------|-----------|
| {question} | {decision} | {why based on research} |

---

## Unresolved Questions

- {Question that research didn't answer}
- {Question requiring human input}

---

## Next Steps

Based on research:

1. {Implementation step informed by research}
2. {Another step}

---

## Research Log

| Timestamp | Action | Finding |
|-----------|--------|---------|
| {datetime} | Read Litestar docs | Found {x} |
| {datetime} | WebSearch for patterns | Best practice is {y} |
