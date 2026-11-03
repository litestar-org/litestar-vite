# Polling, Prefetching & Remembering State

Inertia provides built-in client hooks for periodic background polling (`usePoll`), link prefetching (`<Link prefetch>`), and preserving local component/form state across browser history navigation (`useRemember`).

---

## Periodic Polling

Use `usePoll(intervalMs, requestOptions, pollOptions)` to refresh specific props on an interval. By default, Inertia throttles polling automatically when the browser tab is in the background (`keepAlive: false`) and cleans up the timer when the component unmounts:

=== "React"

    <!-- docs-example: skip -->
    ```tsx title="resources/pages/System/Status.tsx"
    import { usePoll } from "@inertiajs/react";

    export default function SystemStatus({ metrics }: { metrics: { cpu: number; jobs: number } }) {
      const { start, stop } = usePoll(
        5000,
        { only: ["metrics"] },
        { keepAlive: false, autoStart: true },
      );

      return (
        <section>
          <p>CPU: {metrics.cpu}% | Active Jobs: {metrics.jobs}</p>
          <button type="button" onClick={stop}>Pause Polling</button>
          <button type="button" onClick={start}>Resume Polling</button>
        </section>
      );
    }
    ```

=== "Vue 3"

    <!-- docs-example: skip -->
    ```vue title="resources/pages/System/Status.vue"
    <script setup lang="ts">
    import { usePoll } from "@inertiajs/vue3";

    defineProps<{ metrics: { cpu: number; jobs: number } }>();

    const { start, stop } = usePoll(
      5000,
      { only: ["metrics"] },
      { keepAlive: false, autoStart: true },
    );
    </script>

    <template>
      <section>
        <p>CPU: {{ metrics.cpu }}% | Active Jobs: {{ metrics.jobs }}</p>
        <button type="button" @click="stop">Pause Polling</button>
        <button type="button" @click="start">Resume Polling</button>
      </section>
    </template>
    ```

!!! tip
    On the server, wrap props targeted by `usePoll(..., { only: ["metrics"] })` in `lazy("metrics", load_metrics)` or keep unrelated heavy props in `once()` so each 5-second poll executes only the lightweight metrics query.

---

## Link Prefetching

Add `prefetch` to `<Link>` components to warm the client cache before the user clicks:

| Strategy | Usage | Behavior |
| --- | --- | --- |
| **Hover (Default)** | `<Link href="/users" prefetch>` or `prefetch="hover"` | Prefetches after the user hovers over the link for >75ms. |
| **Mount** | `<Link href="/dashboard" prefetch="mount">` | Prefetches immediately when the link mounts into the DOM. |
| **Click (Mouse Down)** | `<Link href="/reports" prefetch="click">` | Starts fetching on `mousedown` before `mouseup` completes. |
| **Custom Cache TTL** | `<Link href="/users" prefetch cacheFor="1m">` | Controls how long the prefetched `PageProps` remain fresh (default 30s). |

You can also prefetch programmatically via `router.prefetch(route("users.index"), { method: "get" }, { cacheFor: "30s" })` or invalidate cached pages after a mutation with `router.flushAll()`.

---

## Remembering Local State

When a user types into a search filter or switches tabs and then clicks a link and presses the browser **Back** button, standard component state resets. `useRemember` automatically serializes local state into `window.history.state` and restores it on history navigation:

=== "React"

    <!-- docs-example: skip -->
    ```tsx title="resources/pages/Orders/FilterBar.tsx"
    import { useRemember } from "@inertiajs/react";

    export function FilterBar() {
      const [filters, setFilters] = useRemember(
        { search: "", status: "all", showArchived: false },
        "Orders/FilterBar",
      );

      return (
        <input
          value={filters.search}
          onChange={(e) => setFilters({ ...filters, search: e.target.value })}
          placeholder="Search orders..."
        />
      );
    }
    ```

=== "Vue 3"

    <!-- docs-example: skip -->
    ```vue title="resources/pages/Orders/FilterBar.vue"
    <script setup lang="ts">
    import { useRemember } from "@inertiajs/vue3";

    const filters = useRemember(
      { search: "", status: "all", showArchived: false },
      "Orders/FilterBar",
    );
    </script>

    <template>
      <input v-model="filters.search" placeholder="Search orders..." />
    </template>
    ```

### Remembering Form State

Pass a unique storage key as the first argument to `useForm("CreateUserForm", { name: "", email: "" })` to automatically remember unsaved form inputs and validation errors across Back/Forward history navigation.
