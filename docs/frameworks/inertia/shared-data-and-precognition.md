# Shared Data, Flash Messages & Precognition

Cross-cutting concerns like the currently authenticated user, organization permissions, toast notifications (`flash`), field-level validation errors (`error`), and real-time form validation (`@precognition`) are first-class primitives in `litestar-vite.inertia`.

---

## 1. Per-Request Shared Props, Flash Messages & Validation Errors

```python title="docs/examples/inertia/shared_and_flash.py"
--8<-- "docs/examples/inertia/shared_and_flash.py"
```

---

## 2. Typing Shared Props (`InertiaConfig.shared_page_prop_types`)

Props registered dynamically inside guards, middleware, or dependencies via `share(connection, key, value)` have no static return annotation on individual route handlers.

By declaring `InertiaConfig(shared_page_prop_types={"currentUser": AuthenticatedUser})`, `litestar-vite`'s OpenAPI/TypeScript generator registers `AuthenticatedUser` in the shared schema registry and emits the exact TypeScript type on `SharedPageProps` in `page-props.ts` — eliminating `unknown` or hand-maintained duplicate interfaces.

---

## 3. Flash Messages & Generated `inertia.d.ts`

Calling `flash(connection, category, message)` stages a toast message in the request scope (and persists it across `InertiaRedirect` / `303 See Other` redirects when session middleware is active).

When `TypeGenConfig` runs (with `InertiaTypeGenConfig(include_default_flash=True)`), `litestar-vite` generates `src/generated/inertia.d.ts` augmenting Inertia's `FlashDataType` with `FlashMessages` (`success?: string[]`, `error?: string[]`, `info?: string[]`, `warning?: string[]`), so `page.flash.success` is strongly typed in React, Vue, and Svelte.

---

## 4. Live Form Validation with Laravel Precognition (`@precognition`)

[Laravel Precognition](https://laravel.com/docs/precognition) lets your frontend validate form fields against your exact Litestar DTO/msgspec/Pydantic validation rules as the user types, without executing the handler body's side effects (database writes, emails, billing calls):

1. Enable `InertiaConfig(precognition=True)` (which registers `create_precognition_exception_handler` to normalize Litestar `ValidationException` errors into Precognition's `{ message, errors }` JSON format).
2. Decorate your mutation route handler with [`@precognition`](../../reference/inertia.md#litestar_vite.inertia.precognition.precognition).
3. When the client sends `Precognition: true` (and optional `Precognition-Validate-Only: name,slug`), Litestar runs parameter and body validation first:
   - If validation fails, Litestar returns `422 Unprocessable Entity` with field-keyed error messages filtered to `Precognition-Validate-Only`.
   - If validation succeeds on a `Precognition: true` request, `@precognition` short-circuits before executing your route handler body and returns `204 No Content` with `Precognition: true` and `Precognition-Success: true`.
