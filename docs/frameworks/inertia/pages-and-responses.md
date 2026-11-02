# Pages, Responses & Redirects

In `mode="hybrid"`, any Litestar route handler can render an Inertia page component by setting `component="..."` (or `page="..."`) in the route decorator and returning your page props dictionary or typed model.

---

## 1. Declaring Page Handlers & Explicit `InertiaResponse`

You can return a plain `dict[str, Any]` or `msgspec.Struct` when `component="..."` is declared on the route decorator, or return an explicit [`InertiaResponse`](../../reference/inertia.md#litestar_vite.inertia.InertiaResponse) when you need per-response flags such as `encrypt_history=True`, `clear_history=True`, or `prop_filter`:

```python title="docs/examples/inertia/pages_and_responses.py"
--8<-- "docs/examples/inertia/pages_and_responses.py"
```

### Direct Model Returns (`msgspec.Struct`, `dataclass`, Pydantic)

When a route handler returns a `msgspec.Struct`, `dataclass`, or Pydantic model directly (rather than a `dict`), `InertiaResponse` serializes its top-level fields as the page's props — respecting `msgspec.Struct(rename="camel")` and `msgspec.field(name=...)` aliases automatically.

---

## 2. Redirect Primitives

Inertia navigation expects specific HTTP status codes when redirecting after form submissions or navigating to external domains:

| Class | Status / Header | When to Use |
| --- | --- | --- |
| [`InertiaRedirect(request, redirect_to="/...")`](../../reference/inertia.md#litestar_vite.inertia.InertiaRedirect) | `303 See Other` (after `PUT`/`PATCH`/`DELETE`) or `302 Found` | Internal application redirects preserving staged `flash()` and `error()` session state |
| [`InertiaBack(request)`](../../reference/inertia.md#litestar_vite.inertia.InertiaBack) | `303 See Other` to `Referer` | Returning to the previous page after a form action or validation failure |
| [`InertiaExternalRedirect(request, redirect_to="https://...")`](../../reference/inertia.md#litestar_vite.inertia.InertiaExternalRedirect) | `409 Conflict` + `X-Inertia-Location` | Redirecting the browser outside the Inertia app (such as Stripe Checkout or an OAuth provider) |

---

## 3. History Encryption & Clearing (`v2`)

Sensitive pages (such as financial statements or healthcare records) should not leave plaintext `PageProps` cached in `window.history.state` after a user logs out:

- **Global Encryption**: Set `InertiaConfig(encrypt_history=True)` to encrypt browser history state across all Inertia responses using the browser's Web Crypto API.
- **Per-Response Encryption**: Return `InertiaResponse(..., encrypt_history=True)` on specific sensitive routes.
- **Clearing History on Logout**: Call `clear_history(request)` inside your logout handler (or pass `clear_history=True` to `InertiaResponse`) to instruct the Inertia v2 client to rotate its history encryption key.
