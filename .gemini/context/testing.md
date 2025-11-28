# Testing Context

Expert knowledge for testing in litestar-vite. Reference when writing pytest tests for Python or Vitest tests for TypeScript.

## Python Testing (pytest)

### Function-Based Tests (Required Pattern)

```python
import pytest
from unittest.mock import AsyncMock, MagicMock
from pathlib import Path

from litestar_vite.config import ViteConfig
from litestar_vite.loader import ViteAssetLoader


@pytest.fixture
def mock_config() -> ViteConfig:
    """Create mock ViteConfig for testing."""
    return ViteConfig(
        bundle_dir=Path("public"),
        hot_reload=False,
    )


@pytest.fixture
def mock_manifest() -> dict[str, Any]:
    """Create mock Vite manifest."""
    return {
        "src/main.ts": {
            "file": "assets/main.abc123.js",
            "css": ["assets/main.def456.css"],
        }
    }


async def test_loader_reads_manifest(
    mock_config: ViteConfig,
    mock_manifest: dict[str, Any],
    tmp_path: Path,
) -> None:
    """Test ViteAssetLoader correctly reads manifest."""
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps(mock_manifest))
    mock_config.bundle_dir = tmp_path

    loader = ViteAssetLoader(config=mock_config)
    await loader.load_manifest()

    assert loader.manifest == mock_manifest


async def test_loader_raises_on_missing_manifest(
    mock_config: ViteConfig,
) -> None:
    """Test missing manifest raises appropriate error."""
    mock_config.bundle_dir = Path("/nonexistent")

    loader = ViteAssetLoader(config=mock_config)

    with pytest.raises(FileNotFoundError):
        await loader.load_manifest()
```

### Parameterized Tests

```python
@pytest.mark.parametrize(
    ("input_value", "expected"),
    [
        ("src/main.ts", "assets/main.abc123.js"),
        ("src/app.ts", None),
    ],
)
def test_resolve_entry(
    input_value: str,
    expected: str | None,
) -> None:
    """Test entry point resolution."""
    # ...
```

### Async Testing

```python
# pytest-asyncio auto mode - no decorator needed
async def test_concurrent_access() -> None:
    """Test concurrent manifest access."""
    tasks = [loader.get_asset("main.js") for _ in range(10)]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    assert all(isinstance(r, (str, Exception)) for r in results)
```

### Litestar Test Client

```python
from litestar.testing import AsyncTestClient

async def test_route_handler() -> None:
    async with AsyncTestClient(app=app) as client:
        response = await client.get("/api/items")
        assert response.status_code == 200
        assert response.json() == [...]
```

## TypeScript Testing (Vitest)

### Basic Tests

```typescript
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { litestarVitePlugin } from '../src/index';

describe('litestarVitePlugin', () => {
  it('creates plugin with default options', () => {
    const plugin = litestarVitePlugin({
      input: 'src/main.ts',
    });
    expect(plugin.name).toBe('litestar-vite-plugin');
  });

  it('respects custom bundle directory', () => {
    const plugin = litestarVitePlugin({
      input: 'src/main.ts',
      bundleDirectory: 'custom/dist',
    });

    const config = plugin.config?.({}, { command: 'build', mode: 'production' });
    expect(config?.build?.outDir).toContain('custom/dist');
  });
});
```

### Mocking

```typescript
import { vi } from 'vitest';

const mockFetch = vi.fn();
vi.stubGlobal('fetch', mockFetch);

beforeEach(() => {
  mockFetch.mockReset();
});

it('fetches data', async () => {
  mockFetch.mockResolvedValue({
    ok: true,
    json: () => Promise.resolve([{ id: 1 }]),
  });

  const result = await fetchItems();
  expect(result).toEqual([{ id: 1 }]);
});
```

## Commands

```bash
# Python tests
make test                    # Run all tests
make coverage               # With coverage
pytest -n auto              # Parallel execution
pytest src/py/tests/unit/test_config.py -v  # Specific file

# TypeScript tests
npm run test                # Run Vitest
npm run test:coverage       # With coverage
```

## Anti-Patterns to Avoid

| Pattern | Use Instead |
|---------|-------------|
| `class TestFoo:` | Function-based tests |
| Hard-coded paths | `tmp_path` fixture |
| Sync tests for async | `async def test_` |
| Missing error tests | Test all error paths |
| `Optional[T]` | `T \| None` |

## Related Files

- `src/py/tests/` - Python tests
- `src/js/tests/` - TypeScript tests
- `src/py/tests/conftest.py` - Shared fixtures
- `specs/guides/testing.md` - Testing guide
