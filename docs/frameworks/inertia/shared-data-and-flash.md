# Shared Data & Flash Messages

Cross-cutting concerns like the currently authenticated user, organization permissions, and toast notifications (`flash`) are shared across pages without repeating props in every route handler.

---

## Per-Request Shared Props (`share`)

Call [`share(connection, key, value)`](../../reference/inertia.md#litestar_vite.inertia.share) inside route handlers, guards, dependencies, or middleware to attach props to the current request's Inertia envelope:

```python title="docs/examples/inertia/shared_and_flash.py"
--8<-- "docs/examples/inertia/shared_and_flash.py"
```

### Lazy Shared Props

You can pass prop wrappers (`lazy()`, `once()`, `defer()`, `always()`) to `share()` so expensive shared data is only evaluated when needed or cached across visits:

```python
from typing import Any
from litestar import Request
from litestar_vite.inertia import lazy, once, share


def attach_shared_context(request: Request[Any, Any, Any]) -> None:
    """Attach cached permissions and on-demand notification counts."""
    share(request, "permissions", once("permissions", lambda: ["orders:read", "orders:write"]))
    share(request, "unreadCount", lazy("unreadCount", lambda: 5))
```

---

## Static & Session-Backed Shared Props

In addition to calling `share()` per request, `InertiaConfig` supports declarative static and session-backed props:

| Option | Type | Behavior |
| --- | --- | --- |
| `extra_static_page_props` | `dict[str, Any]` | Merged into every Inertia response (e.g., `{"appEnv": "production"}`). |
| `extra_session_page_props` | `set[str]` | Keys automatically read from `request.session` and included in `props` when present. |
| **Built-in Shared Props** | `errors`, `csrf_token` | Automatically injected on every Inertia response (`errors` defaults to `{}`). |

!!! note
    During partial reloads (`only` / `except`), shared props are filtered by the client's requested keys just like handler props — unless wrapped in `always()`.

---

## Typing Shared Props

Props registered dynamically via `share(connection, key, value)` inside guards or middleware have no static return annotation on individual route handlers.

By declaring `InertiaConfig(shared_page_prop_types={"currentUser": AuthenticatedUser})`, Litestar Vite's OpenAPI/TypeScript generator registers `AuthenticatedUser` in the shared schema registry and emits the exact TypeScript type on `SharedPageProps` in `page-props.ts` — eliminating `unknown` or hand-maintained duplicate interfaces.

---

## Top-Level Flash Messages

Inertia v2.3+ places flash messages at the **top level** of the page object (`page.flash`) rather than inside `page.props.flash` so flash messages are never accidentally cached in `window.history.state` or re-triggered on Back/Forward navigation.

Call [`flash(connection, message, category="info")`](../../reference/inertia.md#litestar_vite.inertia.flash) on the server:

```python
from typing import Any
from litestar import Request, post
from litestar_vite.inertia import InertiaRedirect, flash


@post("/settings", sync_to_thread=False)
def save_settings(request: Request[Any, Any, Any]) -> InertiaRedirect:
    """Persist settings and stage a top-level flash message across the redirect."""
    flash(request, "Settings saved.", category="success")
    return InertiaRedirect(request, redirect_to="/settings")
```

### Reading Flash Messages on the Client

When `TypeGenConfig` runs (with `InertiaTypeGenConfig(include_default_flash=True)`), Litestar Vite generates `src/generated/inertia.d.ts` augmenting Inertia's `FlashDataType` with `FlashMessages` (`success?: string[]`, `error?: string[]`, `info?: string[]`, `warning?: string[]`):

=== "React"

    ```tsx title="resources/components/ToastBanner.tsx"
    import { usePage } from "@inertiajs/react";

    export function ToastBanner() {
      const page = usePage() as { flash?: Record<string, string[]> };
      const messages = page.flash?.success ?? [];

      if (!messages.length) return null;
      return (
        <div role="status" className="toast-success">
          {messages.map((msg, idx) => (
            <p key={idx}>{msg}</p>
          ))}
        </div>
      );
    }
    ```

=== "Vue 3"

    ```vue title="resources/components/ToastBanner.vue"
    <script setup lang="ts">
    import { computed } from "vue";
    import { usePage } from "@inertiajs/vue3";

    const page = usePage() as unknown as { flash?: Record<string, string[]> };
    const messages = computed(() => page.flash?.success ?? []);
    </script>

    <template>
      <div v-if="messages.length" role="status" class="toast-success">
        <p v-for="(msg, idx) in messages" :key="idx">{{ msg }}</p>
      </div>
    </template>
    ```
