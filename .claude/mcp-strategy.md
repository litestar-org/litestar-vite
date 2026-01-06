# MCP Tool Strategy

This document guides intelligent tool selection based on task requirements.

## Tool Selection by Task Type

### Complex Architectural Decisions

1. **Primary**: `mcp__pal__thinkdeep`
   - Use for: Architecture reviews, performance analysis, security assessment
   - Multi-step investigation with hypothesis testing
2. **Fallback**: `mcp__sequential-thinking__sequentialthinking`
   - Use when: Need structured step-by-step reasoning

### Library Documentation Lookup

1. **Primary**: `mcp__context7__query-docs`
   - First resolve library ID with `mcp__context7__resolve-library-id`
   - Use for: API references, best practices, code examples
2. **Fallback**: `WebSearch`
   - Use when: Context7 doesn't have the library

### Multi-Phase Planning

1. **Primary**: `mcp__pal__planner`
   - Use for: Feature planning, migration strategies, refactoring plans
   - Supports branching and revision
2. **Fallback**: Manual structured thinking with checkpoints

### Code Analysis

1. **Primary**: `mcp__pal__analyze`
   - Use for: Code quality, pattern detection, tech debt assessment
   - Provides systematic investigation with expert validation
2. **Fallback**: Manual code review with Read/Grep tools

### Debugging

1. **Primary**: `mcp__pal__debug`
   - Use for: Complex bugs, race conditions, performance issues
   - Hypothesis-driven investigation
2. **Fallback**: Manual investigation with logging

### Multi-Model Consensus

1. **Primary**: `mcp__pal__consensus`
   - Use for: Important architectural decisions, technology choices
   - Consults multiple models with different stances

### General Chat / Brainstorming

1. **Primary**: `mcp__pal__chat`
   - Use for: Quick questions, validation, exploring ideas
   - Supports continuation for multi-turn discussions

---

## Complexity-Based Selection

### Simple Features (6 checkpoints)

- Use basic Read/Write/Edit tools
- Manual analysis acceptable
- No MCP tools required
- Focus on speed

### Medium Features (8 checkpoints)

- Use `mcp__sequential-thinking__sequentialthinking` (12-15 steps)
- Pattern analysis with Grep/Glob
- Moderate depth research

### Complex Features (10+ checkpoints)

- Use `mcp__pal__thinkdeep` or `mcp__pal__planner`
- Deep pattern analysis with codebase exploration
- Comprehensive research with Context7
- Consider `mcp__pal__consensus` for key decisions

---

## Tool Usage Patterns

### Context7 for Library Docs

```python
# Step 1: Resolve library ID
mcp__context7__resolve-library-id(
    libraryName="litestar",
    query="how to create plugins"
)

# Step 2: Query documentation
mcp__context7__query-docs(
    libraryId="/litestar-org/litestar",
    query="plugin development InitPluginProtocol"
)
```

### Sequential Thinking for Analysis

```python
mcp__sequential-thinking__sequentialthinking(
    thought="Step 1: Identify the current architecture pattern",
    thoughtNumber=1,
    totalThoughts=10,  # Adjust based on complexity
    nextThoughtNeeded=True
)
```

### ThinkDeep for Investigation

```python
mcp__pal__thinkdeep(
    step="Investigating the authentication flow",
    step_number=1,
    total_steps=5,
    next_step_required=True,
    findings="Found that auth middleware...",
    relevant_files=["/path/to/auth.py"],
    confidence="medium"
)
```

### Debug for Bug Hunting

```python
mcp__pal__debug(
    step="Investigating the race condition in connection pool",
    step_number=1,
    total_steps=4,
    next_step_required=True,
    findings="The issue manifests when...",
    hypothesis="Connection not properly returned to pool",
    relevant_files=["/path/to/pool.py"],
    confidence="exploring"
)
```

---

## When NOT to Use MCP Tools

- Simple file reads/writes (use Read/Write)
- Quick searches (use Grep/Glob)
- Running commands (use Bash)
- Single-file changes (direct Edit)

---

## Tool Availability Fallbacks

| Primary Tool | Fallback              | When to Fallback      |
| ------------ | --------------------- | --------------------- |
| context7     | WebSearch             | Library not indexed   |
| thinkdeep    | sequential_thinking   | Need lighter weight   |
| planner      | Manual checkpoints    | Simple planning       |
| consensus    | Single model + review | Time-sensitive        |
