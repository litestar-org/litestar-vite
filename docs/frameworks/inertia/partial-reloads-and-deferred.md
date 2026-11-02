# Partial Reloads & Deferred Props

Inertia gives you fine-grained control over **when** each prop is evaluated on the server. Choosing the right prop wrapper keeps initial page loads instantaneous while avoiding manual `fetch()` state management.

---

## Prop Evaluation Matrix

| Helper | Initial Load | Partial Reload | Client Behavior |
| --- | --- | --- | --- |
| **Plain value** | Included | Included unless filtered | Replaces prop value |
| [`always`](../../reference/inertia.md#litestar_vite.inertia.always) | Always included | Always included (bypasses `only` / `except_`) | Replaces prop value on every visit (auth, errors) |
| [`defer`](../../reference/inertia.md#litestar_vite.inertia.defer) | Queued in `deferredProps` | Auto-fetched by `<Deferred>` after mount | Loaded in grouped background requests after initial paint |
| [`once`](../../reference/inertia.md#litestar_vite.inertia.once) | Included | Skipped once cached (`only` forces refresh) | Cached across client page navigations (`onceProps`) |
| [`optional`](../../reference/inertia.md#litestar_vite.inertia.optional) | Excluded | Only when listed in `only` | Designed for `<WhenVisible>` viewport loading |
| [`lazy`](../../reference/inertia.md#litestar_vite.inertia.lazy) | Excluded | Only when listed in `only` | Classic on-demand partial reload prop |
| [`merge`](../../reference/inertia.md#litestar_vite.inertia.merge) | Included | Appends, prepends, or deep-merges | Combines items in place during partial reloads (`mergeProps`) |

---

## Complete Server Example

```python title="docs/examples/inertia/props_and_reloads.py"
--8<-- "docs/examples/inertia/props_and_reloads.py"
```

!!! important
    **Avoid the False-Lazy Pitfall**: Always pass a callable reference (`defer("metrics", _load_slow_analytics)` or `lazy("report", lambda: build_report(org_id))`) rather than calling the function eagerly (`defer("metrics", _load_slow_analytics())`). Both synchronous and `async def` callables are supported; async callables are resolved concurrently on the event loop by `InertiaResponse`.

---

## Client-Initiated Partial Reloads

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

## Deferred Props & Grouped Resolution

Props wrapped in `defer(key, fn, group="default")` are omitted from the initial response and grouped in `deferredProps: { default: ["metrics"], charts: ["revenue", "retention"] }`. Props in the same `group` are fetched together in a single background request after the page mounts:

=== "React"

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

=== "Vue 3"

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

## Viewport-Triggered Loading (`optional` + `<WhenVisible>`)

Wrap below-the-fold data in `optional("audit_log", load_audit_log)` on the server and `<WhenVisible data="audit_log" buffer={200}>` on the client. An `IntersectionObserver` triggers a partial reload (`only: ["audit_log"]`) when the element approaches within 200px of the viewport. Pass `always` (`<WhenVisible data="audit_log" always>`) to re-fetch every time the element enters the viewport.

---

## Client-Cached Props (`once`) & Fluent Chaining

- **`once("countries", load_countries)`**: Evaluated on the first visit and advertised in `onceProps: {"countries": {"prop": "countries"}}`. On subsequent Inertia navigations, the client sends `X-Inertia-Except-Once-Props: countries` so the server skips re-evaluating `load_countries`. Explicitly requesting `only: ["countries"]` forces a refresh.
- **`defer("catalog", load_catalog).once()`**: Defers the expensive query until after initial paint, then caches the resolved value in `onceProps` across subsequent page navigations.
