# Forms, Validation & Live Precognition

Inertia includes a reactive `useForm` helper that tracks form state, submission progress, processing status, and field-level validation errors returned by Litestar.

---

## Submitting Forms with useForm

=== "React"

    ```tsx title="resources/pages/Users/Create.tsx"
    import type { FormEvent } from "react";
    import { useForm } from "@inertiajs/react";
    import { route } from "@/generated/routes";

    export default function CreateUser() {
      const form = useForm({
        name: "",
        email: "",
      });

      function handleSubmit(e: FormEvent) {
        e.preventDefault();
        form.post(route("users.store"));
      }

      return (
        <form onSubmit={handleSubmit}>
          <input
            value={form.data.name}
            onChange={(e) => form.setData("name", e.target.value)}
          />
          {form.errors.name && <p className="error">{form.errors.name}</p>}

          <input
            type="email"
            value={form.data.email}
            onChange={(e) => form.setData("email", e.target.value)}
          />
          {form.errors.email && <p className="error">{form.errors.email}</p>}

          <button type="submit" disabled={form.processing}>
            Create User
          </button>
        </form>
      );
    }
    ```

=== "Vue 3"

    ```vue title="resources/pages/Users/Create.vue"
    <script setup lang="ts">
    import { useForm } from "@inertiajs/vue3";
    import { route } from "@/generated/routes";

    const form = useForm({
      name: "",
      email: "",
    });

    function submit() {
      form.post(route("users.store"));
    }
    </script>

    <template>
      <form @submit.prevent="submit">
        <input v-model="form.name" />
        <p v-if="form.errors.name">{{ form.errors.name }}</p>

        <input v-model="form.email" type="email" />
        <p v-if="form.errors.email">{{ form.errors.email }}</p>

        <button type="submit" :disabled="form.processing">Create User</button>
      </form>
    </template>
    ```

=== "Svelte 5"

    <!-- docs-example: skip -->
    ```svelte title="resources/pages/Users/Create.svelte"
    <script lang="ts">
      import { useForm } from "@inertiajs/svelte";
      import { route } from "@/generated/routes";

      const form = useForm({
        name: "",
        email: "",
      });

      function submit(e: SubmitEvent) {
        e.preventDefault();
        $form.post(route("users.store"));
      }
    </script>

    <form onsubmit={submit}>
      <input bind:value={$form.name} />
      {#if $form.errors.name}<p>{$form.errors.name}</p>{/if}

      <input type="email" bind:value={$form.email} />
      {#if $form.errors.email}<p>{$form.errors.email}</p>{/if}

      <button type="submit" disabled={$form.processing}>Create User</button>
    </form>
    ```

---

## Server-Side Validation & `error`

Litestar Vite supports both **automatic schema validation** (from `msgspec.Struct`, Pydantic, or Litestar DTO constraints) and **manual domain errors** via [`error(connection, key, message)`](../../reference/inertia.md#litestar_vite.inertia.error):

```python
from typing import Annotated, Any
from litestar import Request, post
from msgspec import Meta, Struct
from litestar_vite.inertia import InertiaBack, InertiaRedirect, error, flash


class CreateUserPayload(Struct):
    name: Annotated[str, Meta(min_length=2)]
    email: Annotated[str, Meta(pattern=r"^[^@]+@[^@]+\.[^@]+$")]


@post("/users", name="users.store", sync_to_thread=False)
def create_user(
    request: Request[Any, Any, Any],
    data: CreateUserPayload,
) -> InertiaRedirect | InertiaBack:
    """Validate payload and check domain uniqueness."""
    if data.email == "taken@example.com":
        error(request, "email", "That email address is already registered.")
        return InertiaBack(request)

    flash(request, f"Created {data.name}", category="success")
    return InertiaRedirect(request, redirect_to="/users")
```

### Error Bags

When a page contains multiple forms sharing field names (such as `email`), pass `{ errorBag: "inviteUser" }` in `form.post(url, { errorBag: "inviteUser" })`. The Inertia client sends the `X-Inertia-Error-Bag: inviteUser` request header, and `InertiaMiddleware` automatically scopes any `error(request, "email", ...)` or validation errors under `props.errors.inviteUser`.

### Custom Error Pages

Configure `InertiaConfig(redirect_404="/404", redirect_unauthorized_to="/login")` for automatic redirects, or register a custom Litestar `exception_handlers` mapping returning `InertiaResponse(..., status_code=exc.status_code)` with `component="Error"` to render a branded Inertia error page while preserving the HTTP status code.

---

## Live Validation with Laravel Precognition

[Laravel Precognition](https://laravel.com/docs/precognition) lets your frontend validate form fields against your exact Litestar validation rules as the user types, **without executing the route handler body**:

1. Enable `InertiaConfig(precognition=True)` in `ViteConfig`.
2. Decorate your mutation route handler with [`@precognition`](../../reference/inertia.md#litestar_vite.inertia.precognition.precognition):

```python
from typing import Annotated
from litestar import post
from msgspec import Meta, Struct
from litestar_vite.inertia import precognition


class CreateWorkspaceInput(Struct):
    name: Annotated[str, Meta(min_length=3, max_length=60)]
    slug: Annotated[str, Meta(pattern=r"^[a-z0-9-]+$")]


@post("/workspaces", name="workspaces.store", sync_to_thread=False)
@precognition
def create_workspace(data: CreateWorkspaceInput) -> dict[str, str]:
    """Only runs on real form submission; Precognition requests short-circuit with 204."""
    return {"slug": data.slug}
```

### How Precognition Works

- When the client sends `Precognition: true` (and optional `Precognition-Validate-Only: slug`), Litestar validates `data: CreateWorkspaceInput` first (you can also inspect `request.is_precognition` and `request.precognition_validate_only` inside custom guards or dependencies).
- If validation fails, Litestar returns 422 Unprocessable Entity with `{ "message": "...", "errors": { "slug": ["..."] } }` filtered to `Precognition-Validate-Only`.
- If validation passes on a `Precognition: true` request, `@precognition` short-circuits before executing `create_workspace` and returns 204 No Content with `Precognition: true` and `Precognition-Success: true`.
- `litestar-vite-plugin/inertia-helpers` also exports `isPrecognitionSuccess`, `isPrecognitionError`, `extractPrecognitionErrors`, and `PrecognitionHeaders` for custom client integrations.
