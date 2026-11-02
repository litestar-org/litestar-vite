# Typed Routes (`route()` & `wsRoute()`)

Hardcoding URL strings like `` `/api/users/${userId}/invoices?status=open` `` across frontend components leads to silent 404s whenever a backend route path or parameter name changes.

When `TypeGenConfig(generate_routes=True)` is active (the default whenever `types=True`), `litestar-vite` inspects every HTTP and WebSocket route on your `Litestar` router and generates `src/generated/routes.ts` with compile-time checked `route()` and `wsRoute()` helpers.

---

## 1. Naming Routes in Litestar

Give your Litestar route handlers semantic `name="..."` identifiers. If `name` is omitted, `extract_route_metadata()` derives a deterministic name from the handler function name:

```python
from typing import Annotated
from uuid import UUID
from litestar import get, websocket_listener
from litestar.params import Parameter


@get("/api/organizations/{org_id:uuid}/members", name="orgs:members", sync_to_thread=False)
def list_members(org_id: Annotated[UUID, Parameter()], role: str = "all") -> list[dict[str, str]]:
    """Return members for an organization."""
    return [{"org_id": str(org_id), "role": role}]


@websocket_listener("/ws/rooms/{room_id:str}", name="rooms:stream")
def room_socket(data: str, room_id: str) -> str:
    """Echo messages inside a named WebSocket room."""
    return f"[{room_id}] {data}"
```

---

## 2. Semantic Parameter Type Aliases

`routes.ts` emits semantic TypeScript type aliases corresponding to Litestar path and query parameter types:

| Python / OpenAPI Parameter Type | Generated TypeScript Alias | Description |
| --- | --- | --- |
| `uuid.UUID` (`format: "uuid"`) | `type UUID = string` | RFC 4122 UUID string (`"123e4567-e89b-..."`) |
| `datetime.datetime` (`format: "date-time"`) | `type DateTime = string` | ISO 8601 timestamp string |
| `datetime.date` (`format: "date"`) | `type DateOnly = string` | ISO 8601 date string (`"2026-11-02"`) |
| `int` / `float` | `number` | Numeric path or query parameter |
| `bool` | `boolean` | Boolean query flag |

---

## 3. Using `route()` and `wsRoute()` in TypeScript

Import `route`, `wsRoute`, `hasRoute`, `currentRoute`, and `RouteParams` from your generated `src/generated/routes.ts` module:

```typescript title="src/navigation.ts"
import { currentRoute, hasRoute, route, wsRoute, type RouteParams } from "./generated/routes";

type OrgMemberParams = RouteParams<"orgs:members">;

const params: OrgMemberParams = { org_id: "123e4567-e89b-12d3-a456-426614174000" };
const membersUrl = route("orgs:members", params, { role: "admin" });

const socketUrl = wsRoute("rooms:stream", { room_id: "general" });

if (hasRoute("orgs:members") && currentRoute() === "orgs:members") {
  console.log("Viewing organization members:", membersUrl, socketUrl);
}
```

### How `wsRoute()` Resolves WebSocket Origins

- When called in the browser with a relative path (`/ws/rooms/general`), `wsRoute()` automatically resolves the origin using `window.location` (`ws://` on `http:` and `wss://` on `https:`).
- When an explicit `serverUrl` is configured or passed, `wsRoute()` normalizes `http://` -> `ws://` and `https://` -> `wss://`.
- Internal `ChannelsPlugin` and Vite HMR/SSR proxy WebSocket endpoints are automatically filtered out of `routes.json` and `routes.ts` so `wsRoute()` only exposes application WebSocket routes.

---

## 4. Compile-Time Parameter Enforcement & Global `window.route`

- **Routes with required path parameters** (`"orgs:members"`) require the `params` object; omitting `params` or misspelling `org_id` fails `tsc --noEmit` immediately.
- **Routes without path parameters** (`"customers:list"`) allow calling `route("customers:list")` with zero arguments or optional query parameters.
- **Global `window.route` (`TypeGenConfig.global_route`)**: Setting `TypeGenConfig(global_route=True)` generates `src/generated/global.d.ts` declaring `window.route` and global `route()` for projects migrating from Laravel Ziggy.
- **CSRF Constants**: `routes.ts` also exports `CSRF_COOKIE_NAME` and `CSRF_HEADER_NAME` sourced directly from `app.csrf_config`.
