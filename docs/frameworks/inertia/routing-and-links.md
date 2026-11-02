# Routing, Links & Redirects

In Inertia applications, **all routing is defined on the server** using standard Litestar `@get`, `@post`, `@put`, `@patch`, and `@delete` decorators. You do not need `react-router` or `vue-router`.

---

## How Litestar Routing Compares to Laravel + Ziggy

| Concept | Laravel + Ziggy | Litestar + `litestar-vite` |
| --- | --- | --- |
| **Route Declaration** | `Route::get('/users/{id}', ...)->name('users.show')` | `@get("/users/{user_id:int}", name="users.show", component="Users/Show")` |
| **Frontend URL Helper** | Ziggy `route('users.show', { id: 1 })` | Native generated `route("users.show", { user_id: 1 })` in `routes.ts` |
| **Parameter Type Safety** | Runtime lookup | **Compile-time TypeScript check** (autocomplete on route names & required path/query params) |
| **Plain URL Strings** | `<Link href="/users/1">` | `<Link href="/users/1">` (first-class citizen) |

---

## 1. Client-Side Navigation with `<Link>` and `route()`

Use Inertia's `<Link>` component for internal navigation so clicks are intercepted as lightweight XHR/Fetch requests instead of full browser reloads. Pair `<Link>` with the generated `route()` function from `@/generated/routes` for compile-time URL safety:

=== "React (`@inertiajs/react`)"

    ```tsx title="resources/components/Nav.tsx"
    import { Link } from "@inertiajs/react";
    import { route } from "@/generated/routes";

    export function Nav({ userId }: { userId: number }) {
      return (
        <nav>
          <Link href={route("dashboard")}>Dashboard</Link>
          <Link href={route("users.show", { user_id: userId })}>My Profile</Link>
          <Link href={route("logout")} method="post" as="button">
            Sign Out
          </Link>
        </nav>
      );
    }
    ```

=== "Vue 3 (`@inertiajs/vue3`)"

    ```vue title="resources/components/Nav.vue"
    <script setup lang="ts">
    import { Link } from "@inertiajs/vue3";
    import { route } from "@/generated/routes";

    defineProps<{ userId: number }>();
    </script>

    <template>
      <nav>
        <Link :href="route('dashboard')">Dashboard</Link>
        <Link :href="route('users.show', { user_id: userId })">My Profile</Link>
        <Link :href="route('logout')" method="post" as="button">Sign Out</Link>
      </nav>
    </template>
    ```

=== "Svelte 5 (`@inertiajs/svelte`)"

    ```svelte title="resources/components/Nav.svelte"
    <script lang="ts">
      import { router } from "@inertiajs/svelte";
      import { route } from "@/generated/routes";

      let { userId }: { userId: number } = $props();
    </script>

    <nav>
      <a href={route("dashboard")} onclick={(e) => { e.preventDefault(); router.visit(route("dashboard")); }}>
        Dashboard
      </a>
      <button type="button" onclick={() => router.post(route("logout"))}>
        Sign Out
      </button>
    </nav>
    ```

### Global `window.route` (`TypeGenConfig.global_route`)

If you want `route()` available globally without importing it in every file (similar to Laravel Ziggy), set `TypeGenConfig(global_route=True)` in Python and register `window.route = route` in your application entrypoint.

---

## 2. Redirect Primitives

Inertia expects specific HTTP status codes when redirecting after form submissions or navigating to external domains:

| Class | Status / Header | Security & Behavior |
| --- | --- | --- |
| [`InertiaRedirect(request, redirect_to="/...")`](../../reference/inertia.md#litestar_vite.inertia.InertiaRedirect) | `303 See Other` (after `PUT`/`PATCH`/`DELETE`) or `302 Found` | Validates that `redirect_to` is same-origin (or relative) to prevent open-redirect vulnerabilities, and preserves staged `flash()` / `error()` session data. |
| [`InertiaBack(request)`](../../reference/inertia.md#litestar_vite.inertia.InertiaBack) | `303 See Other` to `Referer` | Redirects back to the referring page if the `Referer` header matches the request's origin; falls back to `base_url` otherwise. |
| [`InertiaExternalRedirect(request, redirect_to="https://...")`](../../reference/inertia.md#litestar_vite.inertia.InertiaExternalRedirect) | `409 Conflict` + `X-Inertia-Location` | Instructs the Inertia client to perform a full `window.location` redirect to an external URL (e.g., Stripe Checkout or an OAuth provider). |

---

## 3. The POST-Redirect-GET Pattern

Following any mutation (`POST`, `PUT`, `PATCH`, `DELETE`), return an `InertiaRedirect` or `InertiaBack` so the browser follows up with a `GET` visit and updates the page props cleanly:

```python
from typing import Any
from litestar import Request, post
from litestar_vite.inertia import InertiaBack, InertiaExternalRedirect, InertiaRedirect, flash


@post("/projects/{project_id:int}/archive", sync_to_thread=False)
def archive_project(request: Request[Any, Any, Any], project_id: int) -> InertiaRedirect:
    """Archive a project, flash a notification, and redirect to the index."""
    flash(request, f"Project #{project_id} archived.", category="success")
    return InertiaRedirect(request, redirect_to="/projects")


@post("/comments", sync_to_thread=False)
def post_comment(request: Request[Any, Any, Any]) -> InertiaBack:
    """Return to whichever page submitted the comment."""
    flash(request, "Comment added.", category="info")
    return InertiaBack(request)


@post("/billing/checkout", sync_to_thread=False)
def start_checkout(request: Request[Any, Any, Any]) -> InertiaExternalRedirect:
    """Redirect outside the SPA to an external payment gateway."""
    return InertiaExternalRedirect(request, redirect_to="https://checkout.stripe.com/pay/cs_test_123")
```
