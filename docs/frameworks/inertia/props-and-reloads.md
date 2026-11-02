# Props, Deferred Loading & Infinite Scroll

Inertia.js v2 introduces fine-grained control over **when** each prop is evaluated on the server and **how** it is merged on the client. Choosing the right prop wrapper keeps initial page loads instantaneous while eliminating manual `fetch()` state management.

---

## Prop Evaluation Matrix

| Helper | Sent on Initial Load? | Sent on Standard Partial Reload? | Sent When Explicitly Requested (`only`)? | Client Behavior |
| --- | --- | --- | --- | --- |
| **Plain value** (`"user": user`) | Yes | Yes (unless filtered) | Yes | Replaces prop value |
| [`always(key, value)`](../../reference/inertia.md#litestar_vite.inertia.always) | **Always** | **Always** (bypasses `only`/`except_`) | **Always** | Replaces prop value on every visit |
| [`defer(key, fn, group="default")`](../../reference/inertia.md#litestar_vite.inertia.defer) | **No** (queued in `deferredProps`) | No | **Yes** (auto-fetched by `<Deferred>` after mount) | Loaded in grouped background requests after initial paint |
| [`once(key, val_or_fn)`](../../reference/inertia.md#litestar_vite.inertia.once) | **Yes** | Skipped once cached on client | Yes (forces refresh) | Cached across client page navigations (`onceProps`) |
| [`optional(key, fn)`](../../reference/inertia.md#litestar_vite.inertia.optional) | **Never** | **Never** | **Only when listed in `only`** | Designed for `<WhenVisible data="...">` viewport loading |
| [`lazy(key, val_or_fn)`](../../reference/inertia.md#litestar_vite.inertia.lazy) | **No** | No | **Only when listed in `only`** | Classic on-demand partial reload prop |
| [`merge(key, val, strategy=..., match_on=...)`](../../reference/inertia.md#litestar_vite.inertia.merge) | Yes (replaces on full visit) | Appends / prepends / deep-merges | Appends / prepends / deep-merges | Combines items in-place during partial reloads (`mergeProps`) |

---

## Complete Prop Wrappers Example

```python title="docs/examples/inertia/props_and_reloads.py"
--8<-- "docs/examples/inertia/props_and_reloads.py"
```

> [!IMPORTANT]
> **Avoid the False-Lazy Pitfall**: Always pass a callable reference (`defer("metrics", _load_slow_analytics)` or `lazy("report", lambda: build_report(org_id))`) rather than calling the function eagerly (`defer("metrics", _load_slow_analytics())`). Both synchronous and `async def` callables are supported; async callables are resolved concurrently on the event loop by `InertiaResponse`.

---

## Consuming `<Deferred>` and `<WhenVisible>` on the Frontend

=== "React (`@inertiajs/react`)"

    ```tsx title="resources/pages/Analytics/Dashboard.tsx"
    import { Deferred, WhenVisible } from "@inertiajs/react";

    export default function AnalyticsDashboard() {
      return (
        <div>
          <Deferred data="metrics" fallback={<div>Loading charts...</div>}>
            <MetricsChart />
          </Deferred>

          <WhenVisible data="auditLog" fallback={<div>Scrolling into view...</div>}>
            <AuditLogTable />
          </WhenVisible>
        </div>
      );
    }
    ```

=== "Vue 3 (`@inertiajs/vue3`)"

    ```vue title="resources/pages/Analytics/Dashboard.vue"
    <script setup lang="ts">
    import { Deferred, WhenVisible } from "@inertiajs/vue3";
    </script>

    <template>
      <Deferred data="metrics">
        <template #fallback>
          <div>Loading charts...</div>
        </template>
        <MetricsChart />
      </Deferred>

      <WhenVisible data="auditLog">
        <template #fallback>
          <div>Scrolling into view...</div>
        </template>
        <AuditLogTable />
      </WhenVisible>
    </template>
    ```

---

## Chaining `defer(...).once()` and `defer(...).merge()`

`DeferredProp` supports fluent chaining for advanced v2 workflows:

- **`defer("catalog", load_catalog).once()`**: Defers the expensive computation until after the first page render, and then caches the result on the client across subsequent page visits.
- **`defer("feed", load_next_page).merge(strategy="append", match_on="id")`**: Defers initial feed loading and merges subsequent partial reloads by `id`.
