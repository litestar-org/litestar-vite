# Inertia.js v2 Overview & Request Lifecycle

[Inertia.js v2](https://inertiajs.com) lets you build modern React, Vue 3, and Svelte 5 single-page applications using classic server-side routing and controllers. Instead of building a separate REST or GraphQL API for every screen, your Litestar route handlers declare `component="Users/Index"` and return Python `dict`, `msgspec.Struct`, `dataclass`, or Pydantic models directly.

--8<-- "tools/docs/includes/diagram-inertia-lifecycle.html"

---

## How the Inertia v2 Protocol Works in Litestar

1. **Initial Full-Page Visit (`GET /dashboard`)**:
   - The browser sends a standard HTTP request without an `X-Inertia` header.
   - `InertiaResponse` serializes the `PageProps` envelope (`component`, `props`, `url`, `version`, `encryptHistory`, `clearHistory`, `deferredProps`, `mergeProps`, `onceProps`) into `<script type="application/json" data-page="app">` inside your `root_template` (`index.html`).
   - When `InertiaConfig(ssr=True)` is enabled, `litestar-vite` also pre-renders the initial HTML via the SSR IPC transport and splices `<!--inertia-head-->` and `<!--inertia-body-->` before returning `200 OK text/html`.
2. **Subsequent Client Navigation (`X-Inertia: true`)**:
   - Clicking an Inertia `<Link>` intercepts the browser navigation and sends an XHR/Fetch request with `X-Inertia: true` and `X-Inertia-Version: <hash>`.
   - Litestar detects `request.is_inertia == True` and returns `200 OK application/json` containing only the `PageProps` JSON envelope, swapping the page component in place without a full browser reload.
3. **Deferred Props & Partial Reloads (`X-Inertia-Partial-Data`)**:
   - Props wrapped in `defer(key, fn, group=...)` are omitted from the initial response and listed in `deferredProps: { default: [...] }`.
   - Immediately after mounting the initial page, the Inertia v2 client fires batched background partial reloads (`X-Inertia-Partial-Component` + `X-Inertia-Partial-Data`) to resolve each deferred group.
4. **Mutations (`303 See Other`) & Asset Version Rotation (`409 Conflict`)**:
   - Following `POST`, `PUT`, `PATCH`, or `DELETE` requests, `InertiaMiddleware` converts `302 Found` redirects into `303 See Other` so the browser follows up with a `GET` request.
   - If the frontend bundle hash changes between deployments (`X-Inertia-Version` mismatch), Litestar responds with `409 Conflict` and `X-Inertia-Location: <url>`, prompting the client to perform a clean full-page reload.

---

## Inertia.js v2 Guide Navigation

| Guide Page | Topics Covered |
| --- | --- |
| [**Pages, Responses & Redirects**](pages-and-responses.md) | `@get(..., component="...")`, `InertiaResponse`, `msgspec.Struct` serialization, history encryption (`encrypt_history`, `clear_history`), `InertiaRedirect`, `InertiaBack`, and `InertiaExternalRedirect` |
| [**Props, Deferred Loading & Infinite Scroll**](props-and-reloads.md) | Complete prop evaluation lifecycle for `defer()`, `once()`, `optional()`, `lazy()`, `always()`, `only()`, `except_()`, `merge()`, and `scroll_props()` |
| [**Shared Data, Flash Messages & Precognition**](shared-data-and-precognition.md) | Per-request `share()`, `shared_page_prop_types`, session `flash()`, validation `error()`, and live Laravel Precognition (`@precognition`) |
| [**SSR, Client Helpers & Type Generation**](ssr-and-helpers.md) | Script-element bootstrap (`useScriptElementForInitialPage`), `resolvePageComponent()`, `unwrapPageProps()`, `page-props.ts`, and `inertia.d.ts` |
