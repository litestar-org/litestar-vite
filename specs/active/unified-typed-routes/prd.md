# PRD: Inertia-Compatible Route Objects

## Overview
- **Slug**: unified-typed-routes
- **Created**: 2025-12-18
- **Status**: Draft

## Problem Statement

1. **Non-deterministic output**: Route handler names toggle between runs when multiple handlers share a component
2. **No Inertia router integration**: Current `route()` returns URL strings, but Inertia v2.1.2+ accepts `{ url, method }` objects for seamless integration with `router.visit()`, `form.submit()`, etc.

## Goals

1. Fix non-deterministic route generation (done)
2. Return `{ url, method }` objects compatible with Inertia's router
3. Maintain backward compatibility with URL string usage
4. Keep it simple - each handler name maps to exactly one method

## Key Insight

Each Litestar handler has a **unique name** that determines its HTTP method:

```python
@get("/login", name="show_login")
async def show_login() -> InertiaResponse: ...  # GET

@post("/login", name="login")
async def login(data: LoginForm) -> InertiaResponse: ...  # POST
```

So the API is simply:

```typescript
route('show_login')                    // "/login" (string)
route('login')                         // "/login" (string)
routeDefinitions.show_login.method     // "get"
routeDefinitions.login.method          // "post"
```

The `route()` function returns a **string** (the URL) for maximum compatibility with `<Link href>`, `fetch()`, etc. The HTTP method is available on `routeDefinitions` when needed.

## Inertia Integration

```typescript
// Page navigation - route() returns URL string
router.visit(route('show_login'))     // GET /login (default)

// Form submission with explicit method
router.visit(route('login'), { method: routeDefinitions.login.method })

// Links - works directly since route() returns string
<Link href={route('show_login')}>Login</Link>
<Link href={route('login')} method={routeDefinitions.login.method}>Submit</Link>
```

## Technical Approach

### 1. Update Route Data Generation

Add `method` to each route in the generated data:

```typescript
// Current
'show_login': {
  uri: '/login',
  methods: ['GET', 'HEAD'],
  parameters: [],
}

// New - add primary method for Inertia
'show_login': {
  uri: '/login',
  methods: ['GET', 'HEAD'],
  method: 'get',  // Primary method for router.visit()
  parameters: [],
}
```

### 2. route() Function

Returns a URL string (unchanged from original behavior):

```typescript
export function route(name: RouteName, params?: RouteParams<T>): string
```

### 3. Accessing HTTP Method

When you need the HTTP method, access it from the route definition:

```typescript
routeDefinitions.login.method  // "post"
routeDefinitions.show_login.method  // "get"
```

## Affected Files

### Python

1. **`src/py/litestar_vite/codegen/_routes.py`**
   - `generate_routes_json()`: Add `method` field (pick primary method from methods list)
   - `generate_routes_ts()`: Update route() to return `{ url, method }`

### TypeScript

2. **`src/js/src/helpers/routes.ts`**
   - Update `RouteDefinition` interface
   - Update helper functions if needed

## Implementation

### Step 1: Add `method` to Route Data

In `_routes.py`, when building route data:

```python
def pick_primary_method(methods: list[str]) -> str:
    """Pick the primary HTTP method for Inertia router integration."""
    # Prefer in order: GET, POST, PUT, PATCH, DELETE
    for preferred in ['GET', 'POST', 'PUT', 'PATCH', 'DELETE']:
        if preferred in methods:
            return preferred.lower()
    return methods[0].lower() if methods else 'get'
```

### Step 2: Update TypeScript route() Function

```typescript
interface RouteLocation {
  url: string
  method: 'get' | 'post' | 'put' | 'patch' | 'delete'
}

export function route<T extends RouteName>(
  name: T,
  params?: RouteParams<T>
): RouteLocation {
  const def = routeDefinitions[name]
  return {
    url: buildUrl(def.path, params),
    method: def.method,
  }
}

```

## Usage Examples

```typescript
// Navigation - route() returns string
<Link href={route('dashboard')}>Dashboard</Link>
<Link href={route('users.show', { id: 1 })}>View User</Link>

// With explicit method when needed
<Link href={route('logout')} method={routeDefinitions.logout.method}>Logout</Link>

// Forms with method from definition
const form = useForm({ email: '', password: '' })
form.submit(routeDefinitions.login.method, route('login'))

// Fetch API - route() returns string directly
fetch(route('api.users'))
```

## Acceptance Criteria

- [x] `route()` returns URL string (backward compatible)
- [x] Works with `<Link href>`, `fetch()`, `router.visit()`
- [x] `routeDefinitions[name].method` provides HTTP method
- [x] Method is derived from handler's HTTP methods
- [x] All existing tests pass

## Non-Goals

- Typed return values for handlers (future work)
- Custom router wrapper (Inertia handles it natively)
- Complex method chaining API
