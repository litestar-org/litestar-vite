# Pattern Library

This directory contains reusable patterns extracted from the litestar-vite codebase.

## Purpose

Agents should consult this library **before** implementing new features to:
1. Follow established conventions
2. Reuse proven patterns
3. Maintain consistency across the codebase

## Pattern Categories

### Plugin Patterns (`plugin-patterns.md`)
- Litestar plugin structure (VitePlugin, InertiaPlugin)
- Hook registration and lifecycle
- Configuration dataclass patterns

### Type Handling Patterns (`type-patterns.md`)
- PEP 604 union types (`T | None`, not `Optional[T]`)
- Explicit string annotations for forward references
- msgspec/Pydantic model patterns

### Testing Patterns (`testing-patterns.md`)
- Function-based pytest (no class-based tests)
- Fixture organization
- Async test patterns with pytest-asyncio

### Error Handling Patterns (`error-patterns.md`)
- Exception hierarchy design
- Context managers for cleanup
- Flat error handling (no nested try/except)

### Configuration Patterns (`config-patterns.md`)
- Dataclass configuration with defaults
- Runtime vs build-time configuration
- Environment variable handling

## How Patterns Are Captured

1. **During PRD**: Research phase identifies similar implementations
2. **During Implementation**: New patterns documented in `tmp/new-patterns.md`
3. **During Review**: Patterns extracted and added to this library

## Using This Library

```python
# In PRD phase:
# 1. Search for related patterns
# 2. Read pattern files
# 3. Reference in technical approach

# In Implementation phase:
# 1. Follow identified patterns
# 2. Document deviations with rationale
# 3. Add new patterns if discovered
```

## Pattern File Format

Each pattern file should contain:

```markdown
# Pattern Name

## When to Use
Describe the scenario where this pattern applies.

## Structure
Show the canonical implementation.

## Examples
Link to 2-3 real examples in the codebase.

## Anti-patterns
What NOT to do.
```
