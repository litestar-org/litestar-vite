# Typed Routes (`route()` & `wsRoute()`)

Hardcoding URL strings like `` `/api/users/${userId}/invoices?status=open` `` across frontend components leads to silent 404s whenever a backend route path or parameter name changes.

When `TypeGenConfig(generate_routes=True)` is active (the default whenever `types=True`), `litestar-vite` inspects every HTTP and WebSocket route on your `Litestar` router and generates `src/generated/routes.ts` with compile-time checked `route()` and `wsRoute()` helpers.

---

## 1. Naming Routes in Litestar

Give your Litestar route handlers semantic `name="..."` identifiers. If `name` is omitted, `extract_route_metadata()` derives a deterministic name from the handler function name:

```python
from typing import Annotated
from litestar import get, websocket_listener
from litestar.params import Parameter


@get("/api/organizations/{org_id:int}/members", name="orgs:members", sync_to_thread=False)
def list_members(org_id: Annotated[int, Parameter(gt=0)], role: str = "all") -> list[dict[str, str]]:
    """Return members for an organization."""
    return [{"org_id": str(org_id), "role": role}]


@websocket_listener("/ws/rooms/{room_id:str}", name="rooms:stream")
def room_socket(data: str, room_id: str) -> str:
    """Echo messages inside a named WebSocket room."""
    return f"[{room_id}] {data}"
```

---

## 2. Using `route()` and `wsRoute()` in TypeScript

Import `route`, `wsRoute`, `hasRoute`, and `currentRoute` from your generated `src/generated/routes.ts` module:

```typescript title="src/navigation.ts"
import { currentRoute, hasRoute, route, wsRoute } from "./generated/routes";

const membersUrl = route("orgs:members", { org_id: 42 }, { role: "admin" });

const socketUrl = wsRoute("rooms:stream", { room_id: "general" });

if (hasRoute("orgs:members") && currentRoute() === "orgs:members") {
  console.log("Viewing organization members:", membersUrl, socketUrl);
}
```

### Compile-Time Parameter Enforcement

- **Routes with required path parameters** (`"orgs:members"`) require the `params` object (`{ org_id: number | string }`); omitting `params` or misspelling `org_id` fails `tsc --noEmit` immediately.
- **Routes without path parameters** (`"customers:list"`) allow calling `route("customers:list")` with zero arguments or optional query parameters.
- **CSRF Constants**: `routes.ts` also exports `CSRF_COOKIE_NAME` and `CSRF_HEADER_NAME` sourced directly from `app.csrf_config` so `csrfFetch()` and `csrfHeaders()` stay aligned with custom CSRF cookie names.
