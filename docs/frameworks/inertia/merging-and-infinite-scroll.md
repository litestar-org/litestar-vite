# Merging Props & Infinite Scroll

By default, partial reloads replace existing prop values. Using [`merge()`](../../reference/inertia.md#litestar_vite.inertia.merge), [`scroll_props()`](../../reference/inertia.md#litestar_vite.inertia.scroll_props), or `@get(..., infinite_scroll=True)` instructs the Inertia client to **append, prepend, or deep-merge** incoming items into existing client arrays.

---

## 1. Prop Merge Strategies (`merge()`)

```python
from litestar import get
from litestar_vite.inertia import merge


@get("/notifications", component="Notifications/Index", sync_to_thread=False)
def list_notifications(page: int = 1) -> dict[str, object]:
    """Demonstrate append, prepend, and deduplicated merge strategies."""
    items = [{"id": page * 10 + 1, "text": f"Notification #{page}"}]
    return {
        # Append new items and deduplicate by 'id'
        "notifications": merge("notifications", items, strategy="append", match_on="id"),
        # Prepend newest activity items at the top of the list
        "live_activity": merge("live_activity", items, strategy="prepend", match_on="id"),
        # Deep-merge nested filter counters
        "facets": merge("facets", {"unread": 3}, strategy="deep"),
    }
```

| Parameter | Options | Wire Protocol Field | Description |
| --- | --- | --- | --- |
| `strategy="append"` | Default | `mergeProps: ["notifications"]` | Appends new array items to the end of the existing client array. |
| `strategy="prepend"` | `"prepend"` | `prependProps: ["live_activity"]` | Prepends new array items to the start of the existing client array. |
| `strategy="deep"` | `"deep"` | `deepMergeProps: ["facets"]` | Recursively merges nested objects and arrays. |
| `match_on` | `str \| list[str]` | `matchPropsOn: ["notifications.id"]` | Deduplicates merged items by matching one or more keys (updating existing items in place). |

> [!TIP]
> To discard merged items and start fresh (for example, when the user changes a search filter), pass `reset: ["notifications"]` in `router.visit(url, { only: ["notifications"], reset: ["notifications"] })`.

---

## 2. Automatic Infinite Scroll (`infinite_scroll=True`)

When your route handler returns a Litestar `OffsetPagination[T]`, `ClassicPagination[T]`, or `advanced_alchemy` pagination container, setting `infinite_scroll=True` in the route decorator automatically configures `mergeProps` and `scrollProps` (`pageName`, `currentPage`, `previousPage`, `nextPage`):

```python
from litestar import get
from litestar.pagination import ClassicPagination
from msgspec import Struct


class FeedPost(Struct):
    id: int
    title: str


@get("/feed", component="Feed/Index", key="posts", infinite_scroll=True, sync_to_thread=False)
def feed_index(page: int = 1, page_size: int = 20) -> ClassicPagination[FeedPost]:
    """Automatically configures mergeProps=['posts'] and scrollProps metadata."""
    posts = [FeedPost(id=page * 100 + i, title=f"Post {i}") for i in range(1, 4)]
    return ClassicPagination(
        items=posts,
        page_size=page_size,
        current_page=page,
        total_pages=5,
    )
```

### Manual `scroll_props()` Configuration

If you build custom cursor or keyset pagination without `ClassicPagination` / `OffsetPagination`, attach [`scroll_props()`](../../reference/inertia.md#litestar_vite.inertia.scroll_props) explicitly:

```python
from litestar import get
from litestar_vite.inertia import InertiaResponse, merge, scroll_props


@get("/timeline", component="Timeline/Index", sync_to_thread=False)
def timeline(page: int = 1) -> InertiaResponse[dict[str, object]]:
    """Configure custom pagination metadata with scroll_props()."""
    items = [{"id": page, "body": f"Entry {page}"}]
    return InertiaResponse(
        {"entries": merge("entries", items, match_on="id")},
        scroll_props=scroll_props(
            page_name="page",
            current_page=page,
            previous_page=page - 1 if page > 1 else None,
            next_page=page + 1 if page < 10 else None,
        ),
    )
```

---

## 3. Frontend Infinite Scroll with `<WhenVisible>`

Pair `merge()` and `scrollProps` with `<WhenVisible always>` at the bottom of your list:

=== "React (`@inertiajs/react`)"

    ```tsx title="resources/pages/Feed/Index.tsx"
    import { WhenVisible } from "@inertiajs/react";

    interface FeedProps {
      posts: Array<{ id: number; title: string }>;
      nextPage?: number | null;
    }

    export default function FeedIndex({ posts, nextPage }: FeedProps) {
      return (
        <div>
          <ul>
            {posts.map((post) => (
              <li key={post.id}>{post.title}</li>
            ))}
          </ul>

          {nextPage && (
            <WhenVisible
              always
              params={{
                data: { page: nextPage },
                only: ["posts", "nextPage"],
                preserveUrl: true,
              }}
              fallback={<div>Loading more posts...</div>}
            >
              <div />
            </WhenVisible>
          )}
        </div>
      );
    }
    ```

=== "Vue 3 (`@inertiajs/vue3`)"

    ```vue title="resources/pages/Feed/Index.vue"
    <script setup lang="ts">
    import { WhenVisible } from "@inertiajs/vue3";

    defineProps<{
      posts: Array<{ id: number; title: string }>;
      nextPage?: number | null;
    }>();
    </script>

    <template>
      <ul>
        <li v-for="post in posts" :key="post.id">{{ post.title }}</li>
      </ul>

      <WhenVisible
        v-if="nextPage"
        always
        :params="{
          data: { page: nextPage },
          only: ['posts', 'nextPage'],
          preserveUrl: true,
        }"
      >
        <template #fallback>
          <div>Loading more posts...</div>
        </template>
        <div />
      </WhenVisible>
    </template>
    ```
