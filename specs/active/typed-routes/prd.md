# PRD: Typed Routes Generation (Ziggy-style)

**Status**: Draft
**Author**: AI Assistant
**Created**: 2024-12-04
**Priority**: High

## Problem Statement

Currently, litestar-vite has **two overlapping systems** for route handling:

1. **Runtime Injection** (`window.__LITESTAR_ROUTES__`): Server injects routes JSON into HTML at request time
2. **Static File** (`routes.json`): Generated at build/startup but not imported by frontend
3. **Runtime Helper** (`helpers/routes.ts`): Reads from window globals, no type safety

This creates:
- Two sources of truth (build-time file vs runtime injection)
- No compile-time type checking for route names or parameters
- HTML bloat from injected JSON on every page
- No tree-shaking possible
- Missing query parameter support in the route helper

## Goals

1. **Single source of truth**: One generated `routes.ts` file
2. **Type-safe route names**: Autocomplete and compile-time validation
3. **Type-safe parameters**: Path params AND query params with correct types
4. **Zero HTML bloat**: Routes in cacheable static assets, not per-page scripts
5. **Seamless dev/prod**: HMR in dev, optimized builds in prod
6. **Framework agnostic**: Works with React, Vue, Svelte, Angular, HTMX

## Non-Goals

- Replacing `@hey-api/openapi-ts` SDK generation (complementary feature)
- Supporting truly runtime-added routes (rare edge case, can be opt-in extension)
- Server-side route resolution (Python side)

## Architecture Decision

### Consensus: Pure Build-Time Generation

After evaluating hybrid vs pure build-time approaches:

| Approach | Pros | Cons |
|----------|------|------|
| **Hybrid** (build-time + runtime) | Flexibility for dynamic base URLs | Two systems to maintain, test, debug |
| **Pure Build-Time** | Single source of truth, simpler mental model, tree-shakeable | Must handle base URL via env vars |

**Decision**: Pure build-time generation with relative paths by default.

**Rationale**:
- Routes rarely change at runtime; they're defined in code and deployed together
- Relative paths work for most scenarios (integrated dev, production)
- Vite proxy handles dev mode when running integrated (`litestar assets serve`)
- For separate dev servers, optional `VITE_API_URL` can override
- HMR works via Vite's file watching, no runtime injection needed
- Eliminates entire class of bugs from mismatched build-time vs runtime routes

**Dev Server Modes**:
| Mode | Setup | URL Handling |
|------|-------|--------------|
| Integrated | `litestar assets serve` + `litestar run` | Relative paths (Vite proxies to Litestar) |
| Separate | `npm run dev` + `litestar run` | `VITE_API_URL=http://localhost:8000` |
| Production | Built assets served by Litestar | Relative paths |

## Migration Plan

### What Gets Removed

1. **`window.__LITESTAR_ROUTES__`** injection in `spa.py` - DELETE (not released yet)
2. **`SPAConfig.inject_routes`** config option - DELETE (not released yet)
3. **`helpers/routes.ts`** runtime helper - DELETE in favor of generated routes

### What Gets Added

1. **`routes.ts` generation** in `codegen.py`
2. **`generate_routes: bool`** config option (default: `True`)
3. **Query parameter support** in generated `route()` function

### What Stays

1. **CSRF token injection** (`window.__LITESTAR_CSRF__`) - still needed per-request
2. **`routes.json` generation** - useful for tooling/debugging
3. **Inertia page data injection** - different concern

## User Stories

### Story 1: React Developer with Inertia
```tsx
import { route } from '@/generated/routes'
import { Link } from '@inertiajs/react'

// Full autocomplete for route names
<Link href={route('book_detail', { book_id: 123 })}>View Book</Link>

// TypeScript error: Property 'book_id' is missing
<Link href={route('book_detail')}>View Book</Link>

// TypeScript error: 'boook_detail' is not a valid route
<Link href={route('boook_detail', { book_id: 123 })}>View Book</Link>
```

### Story 2: Vue Developer with Query Params
```vue
<script setup lang="ts">
import { route } from '@/generated/routes'

// Query params are type-safe too!
const searchUrl = route('api:search', { q: 'typescript', limit: 10 })
// → '/api/search?q=typescript&limit=10'

// TypeScript error: 'q' is required
const badUrl = route('api:search', { limit: 10 })
</script>
```

### Story 3: HTMX Developer
```typescript
import { route } from '@/generated/routes'

// Type-safe URL generation for HTMX attributes
const btn = document.createElement('button')
btn.setAttribute('hx-get', route('api:search', { q: 'test' }))
btn.setAttribute('hx-target', '#results')
```

### Story 4: Separate Dev Servers
```bash
# Integrated dev (default) - no config needed
# Vite proxies API calls to Litestar automatically

# Separate dev servers - set API URL
VITE_API_URL=http://localhost:8000
```

```typescript
import { route } from '@/generated/routes'

// Integrated dev or production (relative paths)
route('books')  // → '/api/books'

// Separate dev servers (with VITE_API_URL set)
route('books')  // → 'http://localhost:8000/api/books'
```

**Note**: The Vite plugin can auto-detect `.litestar.json` and set `VITE_API_URL` automatically when running `npm run dev` separately.

## Technical Design

### Generated Output Structure

For a Litestar app with these routes:
```python
@get("/api/books")
async def books() -> list[Book]: ...

@get("/api/books/{book_id:int}")
async def book_detail(book_id: int) -> Book: ...

@get("/api/search")
async def search(q: str, limit: int = 10) -> list[Book]: ...

@get("/", component="Home")
async def home() -> Message: ...
```

Generate `src/generated/routes.ts`:

```typescript
/**
 * Auto-generated route definitions for litestar-vite.
 * DO NOT EDIT - regenerated on server restart and file changes.
 *
 * @generated
 */

// API base URL - only needed for separate dev servers
// Set VITE_API_URL=http://localhost:8000 when running Vite separately
const API_URL = import.meta.env?.VITE_API_URL ?? '';

/** All available route names */
export type RouteName =
  | 'books'
  | 'book_detail'
  | 'search'
  | 'home';

/** Path parameter definitions per route */
export interface RoutePathParams {
  books: Record<string, never>;
  book_detail: { book_id: number };
  search: Record<string, never>;
  home: Record<string, never>;
}

/** Query parameter definitions per route */
export interface RouteQueryParams {
  books: Record<string, never>;
  book_detail: Record<string, never>;
  search: { q: string; limit?: number };
  home: Record<string, never>;
}

/** Combined parameters (path + query) */
export type RouteParams<T extends RouteName> =
  RoutePathParams[T] & RouteQueryParams[T];

/** Route metadata */
export const routes = {
  books: {
    path: '/api/books',
    methods: ['GET'] as const,
  },
  book_detail: {
    path: '/api/books/{book_id}',
    methods: ['GET'] as const,
    pathParams: ['book_id'] as const,
  },
  search: {
    path: '/api/search',
    methods: ['GET'] as const,
    queryParams: ['q', 'limit'] as const,
  },
  home: {
    path: '/',
    methods: ['GET'] as const,
    component: 'Home',
  },
} as const;

/** Routes that require parameters */
type RoutesWithParams = {
  [K in RouteName]: RouteParams<K> extends Record<string, never> ? never : K
}[RouteName];

/** Routes without required parameters */
type RoutesWithoutParams = Exclude<RouteName, RoutesWithParams>;

/** Routes with only optional parameters */
type RoutesWithOptionalParams = {
  [K in RouteName]: RouteParams<K> extends Record<string, never>
    ? never
    : Partial<RouteParams<K>> extends RouteParams<K>
      ? K
      : never
}[RouteName];

/**
 * Generate a URL for a named route.
 *
 * @example
 * route('books')                              // '/api/books'
 * route('book_detail', { book_id: 123 })      // '/api/books/123'
 * route('search', { q: 'test', limit: 5 })    // '/api/search?q=test&limit=5'
 */
export function route<T extends RoutesWithoutParams>(name: T): string;
export function route<T extends RoutesWithOptionalParams>(
  name: T,
  params?: RouteParams<T>
): string;
export function route<T extends RoutesWithParams>(
  name: T,
  params: RouteParams<T>
): string;
export function route<T extends RouteName>(
  name: T,
  params?: RouteParams<T>
): string {
  const def = routes[name];
  let url = def.path;

  // Replace path parameters
  if (params && 'pathParams' in def) {
    for (const param of def.pathParams) {
      const value = (params as Record<string, unknown>)[param];
      if (value !== undefined) {
        url = url.replace(`{${param}}`, String(value));
      }
    }
  }

  // Add query parameters
  if (params && 'queryParams' in def) {
    const queryParts: string[] = [];
    for (const param of def.queryParams) {
      const value = (params as Record<string, unknown>)[param];
      if (value !== undefined) {
        queryParts.push(`${encodeURIComponent(param)}=${encodeURIComponent(String(value))}`);
      }
    }
    if (queryParts.length > 0) {
      url += '?' + queryParts.join('&');
    }
  }

  // Apply API URL if set (for separate dev servers)
  return API_URL ? API_URL.replace(/\/$/, '') + url : url;
}

/** Check if a route exists */
export function hasRoute(name: string): name is RouteName {
  return name in routes;
}

/** Get all route names */
export function getRouteNames(): RouteName[] {
  return Object.keys(routes) as RouteName[];
}

/** Get route metadata */
export function getRoute<T extends RouteName>(name: T): typeof routes[T] {
  return routes[name];
}
```

### Configuration

Update `TypeGenConfig` in `config.py`:

```python
@dataclass
class TypeGenConfig:
    """Configuration for TypeScript type generation."""

    enabled: bool = False
    output: Path = field(default_factory=lambda: Path("src/generated"))
    openapi_path: Path = field(default_factory=lambda: Path("src/generated/openapi.json"))
    routes_path: Path = field(default_factory=lambda: Path("src/generated/routes.json"))

    # Existing
    generate_zod: bool = False
    generate_sdk: bool = True

    # NEW
    generate_routes: bool = True  # Generate typed routes.ts
    routes_ts_path: Path | None = None  # Default: output / "routes.ts"
```

### HMR Integration (Dev Mode)

1. **Litestar dev server** writes `routes.ts` on startup and route changes
2. **Vite watches** the generated file as a normal dependency
3. **File change → Vite HMR** automatically invalidates the module
4. **Frontend hot-reloads** with new routes

No special HMR events needed - Vite's standard file watching handles it.

### Type Mapping

| Litestar/OpenAPI | TypeScript |
|------------------|------------|
| `int`, `integer` | `number` |
| `float`, `number` | `number` |
| `str`, `string` | `string` |
| `bool`, `boolean` | `boolean` |
| `uuid`, `UUID` | `string` |
| `date`, `datetime` | `string` |
| `list[T]`, `array` | `T[]` |
| `dict`, `object` | `Record<string, unknown>` |
| Optional/has default | `T \| undefined` (or `T?`) |

## Implementation Plan

### Phase 1: Core Generation (Python)

1. Add `generate_routes` and `routes_ts_path` to `TypeGenConfig`
2. Create `generate_routes_ts()` function in `codegen.py`
3. Generate route types, params, and helper functions
4. Call generation in plugin startup

### Phase 2: Cleanup (Delete Unreleased Code)

1. Remove `SPAConfig.inject_routes` config option
2. Remove `window.__LITESTAR_ROUTES__` injection from `spa.py`
3. Remove `helpers/routes.ts` runtime helper
4. Update docs to reference generated routes only

### Phase 3: Query Parameter Support

1. Extract query params from handler signatures (already in `codegen.py`)
2. Include in generated `RouteQueryParams` interface
3. Update `route()` function to append query string

### Phase 4: Framework Integration

1. Update examples to use generated routes
2. Ensure HMR works in all frameworks (React, Vue, Svelte, etc.)
3. Test with Nuxt, SvelteKit (their own build systems)

## Testing Strategy

### Unit Tests (Python)
```python
def test_generate_routes_ts_basic():
    """Test basic route generation."""
    app = create_test_app()
    ts_content = generate_routes_ts(app)

    assert "export type RouteName =" in ts_content
    assert "'book_detail'" in ts_content
    assert "book_id: number" in ts_content

def test_generate_routes_ts_query_params():
    """Test query parameter extraction."""
    # ...

def test_routes_ts_compiles():
    """Verify generated TS is valid."""
    # Write to temp file, run tsc --noEmit
```

### Integration Tests (TypeScript)
```typescript
import { route, hasRoute } from '../src/generated/routes'

describe('route()', () => {
  it('generates URLs without params', () => {
    expect(route('books')).toBe('/api/books')
  })

  it('generates URLs with path params', () => {
    expect(route('book_detail', { book_id: 123 })).toBe('/api/books/123')
  })

  it('generates URLs with query params', () => {
    expect(route('search', { q: 'test', limit: 5 }))
      .toBe('/api/search?q=test&limit=5')
  })

  it('applies API URL for separate dev servers', () => {
    // Mock import.meta.env.VITE_API_URL = 'http://localhost:8000'
    expect(route('books')).toBe('http://localhost:8000/api/books')
  })
})
```

## Success Metrics

1. **Type Coverage**: 100% of routes have typed parameters
2. **DX Improvement**: Route name autocomplete in IDE
3. **Error Prevention**: Compile-time detection of invalid routes
4. **Performance**: No route JSON in HTML (measure payload size reduction)
5. **Adoption**: All examples use generated routes

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Large apps = large types file | Build time | Routes are usually small; monitor |
| SSR compatibility | Runtime errors | Test with Nuxt, SvelteKit SSR |
| Separate dev server setup | User confusion | Auto-detect `.litestar.json` and set `VITE_API_URL` |

## References

- [Ziggy GitHub](https://github.com/tighten/ziggy)
- [Ziggy TypeScript Support](https://github.com/tighten/ziggy#typescript)
- [Inertia.js Routing](https://inertiajs.com/routing)
- [Existing codegen.py](../../../src/py/litestar_vite/codegen.py)
