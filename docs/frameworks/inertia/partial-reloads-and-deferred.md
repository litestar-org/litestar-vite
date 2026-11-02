# Partial Reloads & Deferred Props

Inertia gives you fine-grained control over **when** each prop is evaluated on the server. Choosing the right prop wrapper keeps initial page loads instantaneous while avoiding manual `fetch()` state management.

---

## Prop Evaluation Matrix

| Helper | Sent on Initial Load? | Sent on Standard Partial Reload? | Sent When Explicitly Requested (`only`)? | Client Behavior |
| --- | --- | --- | --- | --- |
| **Plain value** (`"user": user`) | Yes | Yes (unless filtered) | Yes | Replaces prop value |
| [`always(key, value)`](../../reference/inertia.md#litestar_vite.inertia.always) | **Always** | **Always** (bypasses `only`/`except_`) | **Always** | Replaces prop value on every visit (`errors`, auth state) |
| [`defer(key, fn, group="default")`](../../reference/inertia.md#litestar_vite.inertia.defer) | **No** (queued in `deferredProps`) | No | **Yes** (auto-fetched by `<Deferred>` after mount) | Loaded in grouped background requests after initial paint |
| [`once(key, val_or_fn)`](../../reference/inertia.md#litestar_vite.inertia.once) | **Yes** | Skipped once cached (`X-Inertia-Except-Once-Props`) | Yes (forces refresh) | Cached across client page navigations (`onceProps`) |
| [`optional(key, fn)`](../../reference/inertia.md#litestar_vite.inertia.optional) | **Never** | **Never** | **Only when listed in `only`** | Designed for `<WhenVisible data="...">` viewport loading |
| [`lazy(key, val_or_fn)`](../../reference/inertia.md#litestar_vite.inertia.lazy) | **No** | No | **Only when listed in `only`** | Classic on-demand partial reload prop |
| [`merge(key, val, strategy=..., match_on=...)`](../../reference/inertia.md#litestar_vite.inertia.merge) | Yes (replaces on full visit) | Appends / prepends / deep-merges | Appends / prepends / deep-merges | Combines items in-place during partial reloads (`mergeProps`) |

---

## Complete Server Example

```python title="docs/examples/inertia/props_and_reloads.py"
--8<-- "docs/examples/inertia/props_and_reloads.py"
```

> [!IMPORTANT]
> **Avoid the False-Lazy Pitfall**: Always pass a callable reference (`defer("metrics", _load_slow_analytics)` or `lazy("report", lambda: build_report(org_id))`) rather than calling the function eagerly (`defer("metrics", _load_slow_analytics())`). Both synchronous and `async def` callables are supported; async callables are resolved concurrently on the event loop by `InertiaResponse`.

---

## 1. Client-Initiated Partial Reloads (`router.reload`)

Use `router.reload({ only: [...] })` or `router.reload({ except: [...] })` to refresh a subset of props on the current page without re-evaluating unrelated database queries:

```typescript
import { router } from "@inertiajs/react";

// Refresh only the "metrics" and "notifications" props
router.reload({ only: ["metrics", "notifications"] });

// Refresh everything except the heavy "catalog" prop
router.reload({ except: ["catalog"] });

// Reset merged arrays before reloading
router.reload({ only: ["feed"], reset: ["feed"] });
```

---

## 2. Deferred Props (`<Deferred>`) & Grouped Resolution

Props wrapped in `defer(key, fn, group="default")` are omitted from the initial response and grouped in `deferredProps: { default: ["metrics"], charts: ["revenue", "retention"] }`. Props in the same `group` are fetched together in a single background request after the page mounts:

=== "React (`@inertiajs/react`)"

    ```tsx title="resources/pages/Analytics/Dashboard.tsx"
    import { Deferred, WhenVisible } from "@inertiajs/react";

    export default function AnalyticsDashboard() {
      return (
        <div>
          <Deferred data="metrics" fallback={<div>Loading metrics...</div>}>
            <MetricsChart />
          </Deferred>

          <WhenVisible data="audit_log" buffer={200} fallback={<div>Scrolling into view...</div>}>
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
          <div>Loading metrics...</div>
        </template>
        <MetricsChart />
      </Deferred>

      <WhenVisible data="audit_log" :buffer="200">
        <template #fallback>
          <div>Scrolling into view...</div>
        </template>
        <AuditLogTable />
      </WhenVisible>
    </template>
    ```

---

## 3. Viewport-Triggered Loading (`optional()` + `<WhenVisible>`)

Wrap below-the-fold data in `optional("audit_log", load_audit_log)` on the server and `<WhenVisible data="audit_log" buffer={200}>` on the client. An `IntersectionObserver` triggers a partial reload (`only: ["audit_log"]`) when the element approaches within `200px` of the viewport. Pass `always` (`<WhenVisible data="audit_log" always>`) to re-fetch every time the element enters the viewport.

---

## 4. Client-Cached Props (`once()`) & Fluent Chaining

- **`once("countries", load_countries)`**: Evaluated on the first visit and listed in `onceProps: ["countries"]`. On subsequent Inertia navigations, the client sends `X-Inertia-Except-Once-Props: countries` so the server skips re-evaluating `load_countries`. Explicitly requesting `only: ["countries"]` forces a refresh.
- **`defer("catalog", load_catalog).once()`**: Defers the expensive query until after initial paint, then caches the resolved value in `onceProps` across subsequent page navigations.
