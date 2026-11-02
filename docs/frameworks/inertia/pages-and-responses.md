# Pages & Responses

In `mode="hybrid"`, any Litestar route handler can render an Inertia page component by setting `component="..."` (or `page="..."`) in the route decorator and returning a dictionary or typed model.

---

## 1. Declaring Page Handlers & Explicit `InertiaResponse`

You can return a plain `dict[str, Any]` or `msgspec.Struct` when `component="..."` is declared on the route decorator, or return an explicit [`InertiaResponse`](../../reference/inertia.md#litestar_vite.inertia.InertiaResponse) when you need per-response flags such as `encrypt_history=True`, `clear_history=True`, `template_name`, or `prop_filter`:

```python title="docs/examples/inertia/pages_and_responses.py"
--8<-- "docs/examples/inertia/pages_and_responses.py"
```

### Nested Page Components

Organize page components into subdirectories (`resources/pages/Users/Index.tsx`, `resources/pages/Settings/Profile.tsx`) and reference them with forward-slash paths (`component="Users/Index"`). `resolvePageComponent` maps the component string directly to `./pages/${name}.tsx` (or `.vue` / `.svelte`).

---

## 2. Direct Model Returns (`msgspec.Struct`, `dataclass`, Pydantic)

When a route handler returns a `msgspec.Struct`, `dataclass`, or Pydantic `BaseModel` directly instead of a `dict`, `InertiaResponse` serializes its top-level fields as the page's props — respecting `msgspec.Struct(rename="camel")` and `msgspec.field(name=...)` aliases automatically:

```python
from litestar import get
from msgspec import Struct


class UserProfileProps(Struct, rename="camel"):
    user_id: int
    display_name: str
    is_verified: bool


@get("/profile", component="Profile/Show", sync_to_thread=False)
def show_profile() -> UserProfileProps:
    """Serializes as { userId: 42, displayName: 'Ada', isVerified: true }."""
    return UserProfileProps(user_id=42, display_name="Ada", is_verified=True)
```

---

## 3. Consuming Page Props on the Frontend

=== "React (`@inertiajs/react`)"

    ```tsx title="resources/pages/Profile/Show.tsx"
    import { Head } from "@inertiajs/react";

    interface ProfileShowProps {
      userId: number;
      displayName: string;
      isVerified: boolean;
    }

    export default function ProfileShow({ displayName, isVerified }: ProfileShowProps) {
      return (
        <>
          <Head title={`${displayName} — Profile`} />
          <h1>{displayName}</h1>
          {isVerified && <span>Verified</span>}
        </>
      );
    }
    ```

=== "Vue 3 (`@inertiajs/vue3`)"

    ```vue title="resources/pages/Profile/Show.vue"
    <script setup lang="ts">
    import { Head } from "@inertiajs/vue3";

    defineProps<{
      userId: number;
      displayName: string;
      isVerified: boolean;
    }>();
    </script>

    <template>
      <Head :title="`${displayName} — Profile`" />
      <h1>{{ displayName }}</h1>
      <span v-if="isVerified">Verified</span>
    </template>
    ```

=== "Svelte 5 (`@inertiajs/svelte`)"

    ```svelte title="resources/pages/Profile/Show.svelte"
    <script lang="ts">
      interface Props {
        userId: number;
        displayName: string;
        isVerified: boolean;
      }

      let { displayName, isVerified }: Props = $props();
    </script>

    <svelte:head>
      <title>{displayName} — Profile</title>
    </svelte:head>

    <h1>{displayName}</h1>
    {#if isVerified}
      <span>Verified</span>
    {/if}
    ```

---

## 4. Automatic Pagination Container Unwrapping (`key="..."`)

When a route handler returns a Litestar `OffsetPagination[T]`, `ClassicPagination[T]`, or `advanced_alchemy` pagination container, `InertiaResponse` automatically extracts the items into the prop key specified by `key="..."` (default `"items"`) alongside pagination metadata (`total`, `limit`, `offset`, or `current_page`, `total_pages`):

```python
from litestar import get
from litestar.pagination import OffsetPagination
from msgspec import Struct


class PostSummary(Struct):
    id: int
    title: str


@get("/posts", component="Posts/Index", key="posts", sync_to_thread=False)
def list_posts(limit: int = 10, offset: int = 0) -> OffsetPagination[PostSummary]:
    """Unwraps items into props['posts'] with pagination metadata."""
    items = [PostSummary(id=1, title="Hello Litestar")]
    return OffsetPagination(items=items, limit=limit, offset=offset, total=1)
```

---

## 5. Server-Side Prop Filtering (`only()` and `except_()`)

Use [`only(*keys)`](../../reference/inertia.md#litestar_vite.inertia.only) or [`except_(*keys)`](../../reference/inertia.md#litestar_vite.inertia.except_) with `InertiaResponse(..., prop_filter=...)` to restrict which keys from a shared service dictionary or model are serialized into `props`:

```python
from typing import Any
from litestar import Request, get
from litestar_vite.inertia import InertiaResponse, except_


@get("/users/{user_id:int}", component="Users/Show", sync_to_thread=False)
def show_user(request: Request[Any, Any, Any], user_id: int) -> InertiaResponse[dict[str, Any]]:
    """Exclude internal audit fields on the server before serialization."""
    record = {"id": user_id, "name": "Alice", "password_hash": "...", "internal_notes": "..."}
    return InertiaResponse(
        record,
        prop_filter=except_("password_hash", "internal_notes"),
    )
```
