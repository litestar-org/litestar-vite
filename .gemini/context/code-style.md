# Code Style Context

Quick reference for code style standards in litestar-vite. Reference for all code modifications.

## Python Standards

### Type Hints (CRITICAL)

```python
# ✅ CORRECT - PEP 604 syntax
def process(data: str | None) -> dict[str, Any]:
    ...

def get_items() -> list[Item]:
    ...

async def fetch(id: int) -> Item | None:
    ...

# ❌ WRONG - Never use future annotations
from __future__ import annotations  # NO!
```

### No Future Annotations (CRITICAL)

```python
# ❌ NEVER DO THIS
from __future__ import annotations

# ✅ Use explicit string quotes if needed for forward refs
def method(self) -> "MyClass":
    ...
```

### Async/Await

```python
# ✅ All I/O operations must be async
async def get_item(id: int) -> Item:
    result = await db.fetch_one(query)
    return Item.model_validate(result)

# ✅ Use asyncio.gather for concurrent operations
results = await asyncio.gather(
    fetch_user(user_id),
    fetch_items(user_id),
)
```

### Docstrings (Google Style)

```python
async def create_item(
    self,
    data: ItemCreate,
    user_id: int,
) -> Item:
    """Create a new item for a user.

    Args:
        data: The item data to create.
        user_id: The ID of the user creating the item.

    Returns:
        The created item with generated ID.

    Raises:
        ValidationError: If the data is invalid.
        PermissionError: If user cannot create items.
    """
    ...
```

### Error Handling

```python
# ✅ CORRECT - Specific exceptions with context
try:
    result = await external_api.call()
except ExternalAPIError as e:
    logger.error("API call failed: %s", e)
    raise ProcessingError("Failed to process request") from e

# ❌ WRONG - Bare except
try:
    result = await something()
except Exception:  # Too broad!
    pass
```

### Imports Order

```python
# 1. Standard library
import asyncio
from pathlib import Path

# 2. Third-party
from litestar import get, post
from pydantic import BaseModel

# 3. Local
from litestar_vite.config import ViteConfig
from litestar_vite.exceptions import ViteError
```

## TypeScript Standards

### Type Definitions

```typescript
// ✅ Use interfaces for objects
interface PluginOptions {
  input: string | string[];
  bundleDirectory?: string;
  hotFile?: string;
}

// ✅ Use type for unions/aliases
type EntryPoint = string | string[];
```

### Strict Mode

```typescript
// tsconfig.json should have
{
  "compilerOptions": {
    "strict": true,
    "noImplicitAny": true,
    "strictNullChecks": true
  }
}
```

### Async/Await

```typescript
// ✅ Always use async/await over .then()
async function fetchData(): Promise<Data> {
  const response = await fetch('/api/data');
  return response.json();
}
```

## Testing Standards

### Function-Based Tests Only

```python
# ✅ CORRECT
async def test_something() -> None:
    result = await function_under_test()
    assert result == expected

# ❌ WRONG - No class-based tests
class TestSomething:  # Never do this!
    def test_method(self):
        ...
```

### Coverage Target: 90%+

All modified modules must achieve 90%+ test coverage.

## Anti-Patterns to Avoid

| Anti-Pattern | Correct Pattern |
|--------------|-----------------|
| `from __future__ import annotations` | Explicit string quotes |
| `class TestFoo:` | Function-based tests |
| `hasattr()` / `getattr()` | Type guards |
| Bare `except Exception` | Specific exceptions |
| Nested try/except | Flat error handling |
| Mutable default args | `None` with conditional |

## Commands

```bash
# Format and lint
make fix      # Auto-fix formatting
make lint     # Check for errors
make type-check  # Run type checkers

# Full check
make check-all
```

## Related Files

- `specs/guides/code-style.md` - Full code style guide
- `pyproject.toml` - Ruff/mypy configuration
- `biome.json` - Biome configuration for TypeScript
