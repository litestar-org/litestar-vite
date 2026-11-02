# Typed Routes (`route` & `toRoute`)

Hardcoding URL strings like `` `/api/users/${userId}/invoices?status=open` `` across frontend components leads to silent 404s whenever a backend route path or parameter name changes.

When `TypeGenConfig(generate_routes=True)` is active (the default whenever `types=True`), Litestar Vite inspects every route on your `Litestar` router and generates `src/generated/routes.ts` with compile-time checked `route()`, `toRoute()`, `currentRoute()`, and `isCurrentRoute()` helpers.

---

## Naming Routes in Litestar

Give your Litestar route handlers semantic `name="..."` identifiers. If `name` is omitted, `extract_route_metadata()` derives a deterministic name from the handler function name:

```python
from typing import Annotated
from uuid import UUID
from litestar import get
from litestar.params import Parameter


@get("/api/organizations/{org_id:uuid}/members", name="orgs:members", sync_to_thread=False)
def list_members(org_id: Annotated[UUID, Parameter()], role: str = "all") -> list[dict[str, str]]:
    """Return members for an organization."""
    return [{"org_id": str(org_id), "role": role}]
```

---

## Semantic Parameter Type Aliases

`routes.ts` emits semantic TypeScript type aliases corresponding to Litestar path and query parameter types:

| Python / OpenAPI Parameter Type | Generated TypeScript Alias | Description |
| --- | --- | --- |
| `uuid.UUID` (`format: "uuid"`) | `type UUID = string` | RFC 4122 UUID string (`"123e4567-e89b-..."`) |
| `datetime.datetime` (`format: "date-time"`) | `type DateTime = string` | ISO 8601 timestamp string |
| `datetime.date` (`format: "date"`) | `type DateOnly = string` | ISO 8601 date string (`"2026-11-02"`) |
| `int` / `float` | `number` | Numeric path or query parameter |
| `bool` | `boolean` | Boolean query flag |

---

## Using `route`, `toRoute`, and `isCurrentRoute` in TypeScript

`route()` accepts the route name and a single combined `params` object containing both required path parameters and optional query parameters (automatically splitting query keys into the `?query` string):

```typescript title="src/navigation.ts"
import {
  currentRoute,
  hasRoute,
  isCurrentRoute,
  route,
  toRoute,
  type RouteParams,
} from "./generated/routes";

type OrgMemberParams = RouteParams<"orgs:members">;

const params: OrgMemberParams = {
  org_id: "123e4567-e89b-12d3-a456-426614174000",
  role: "admin",
};
const membersUrl = route("orgs:members", params);
const fullUrl = toRoute("orgs:members", params);

if (hasRoute("orgs:members") && isCurrentRoute("orgs:*")) {
  console.log("Current route:", currentRoute(), membersUrl, fullUrl);
}
```

### Generated Route Helpers Summary

| Exported Helper | Description |
| --- | --- |
| `route(name, params?)` | Builds a type-safe URL path (plus `?query` string for non-path keys). |
| `toRoute(name, params?)` | Like `route()`, prefixed with `API_URL` when an origin is configured. |
| `hasRoute(name)` | Type guard checking whether `name` exists in `routeDefinitions`. |
| `currentRoute()` | Matches `window.location.pathname` against `routeDefinitions` and returns the active `RouteName | null`. |
| `isCurrentRoute(pattern)` | Checks whether `currentRoute()` matches an exact name or wildcard pattern (e.g. `"orgs:*"`). |
| `isRoute(url, pattern)` | Checks whether an arbitrary URL string or `Location` matches `pattern`. |

---

## Compile-Time Parameter Validation & Global Route

- **Routes with required path parameters** (`"orgs:members"`) require the `params` object; omitting `params` or misspelling `org_id` fails `tsc --noEmit` immediately.
- **Routes without path parameters** (`"customers:list"`) allow calling `route("customers:list")` with zero arguments or optional query parameters.
- **Global `window.route` (`TypeGenConfig.global_route`)**: Setting `TypeGenConfig(global_route=True)` generates `src/generated/global.d.ts` declaring `window.route` and global `route()` for projects migrating from Laravel Ziggy.
- **CSRF Constants**: `routes.ts` also exports `CSRF_COOKIE_NAME` and `CSRF_HEADER_NAME` sourced directly from `app.csrf_config`.
