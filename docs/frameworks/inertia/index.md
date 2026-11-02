# Inertia.js Overview & Protocol Lifecycle

[Inertia.js](https://inertiajs.com) lets you build modern React, Vue 3, and Svelte 5 single-page applications using classic server-side routing and controllers. Instead of building a separate REST or GraphQL API for every screen, your Litestar route handlers declare `component="Users/Index"` and return Python `dict`, `msgspec.Struct`, `dataclass`, or Pydantic models directly.

--8<-- "tools/docs/includes/diagram-inertia-lifecycle.html"

---

## How the Inertia Protocol Works in Litestar

1. **Initial Full-Page Visit**:
   - The browser sends a standard HTTP request without an `X-Inertia` header.
   - `InertiaResponse` serializes the `PageProps` JSON envelope into `<script type="application/json" id="app_page" data-page="app">` (or the legacy `data-page` attribute on `#app` when `use_script_element=False`).
   - When `InertiaConfig(ssr=True)` is enabled, Litestar Vite pre-renders the initial HTML via the SSR IPC transport before returning the page.
2. **Subsequent Client Navigation**:
   - Clicking an Inertia `<Link>` or calling `router.visit()` sends an XHR/Fetch request with `X-Inertia: true` and `X-Inertia-Version`.
   - Litestar detects the Inertia visit and returns `application/json` containing only the `PageProps` envelope, swapping the page component in place without a full browser reload.
3. **Deferred Props & Partial Reloads**:
   - Props wrapped in `defer()` are omitted from the initial response and listed in `deferredProps`.
   - Immediately after mounting the initial page, the Inertia client fires batched background partial reloads to resolve each deferred group.
4. **Mutations & Asset Version Rotation**:
   - Following POST, PUT, PATCH, or DELETE requests, `InertiaMiddleware` converts 302 redirects into 303 See Other so the browser follows up with a GET request.
   - If the frontend bundle hash changes between deployments (`X-Inertia-Version` mismatch), Litestar responds with 409 Conflict and `X-Inertia-Location`, prompting a clean full-page reload.

---

## Protocol Headers & Status Codes

| Header | Direction | Description |
| --- | --- | --- |
| `X-Inertia` | Request & Response | `"true"` marks an Inertia XHR/Fetch navigation and JSON `PageProps` response. |
| `X-Inertia-Version` | Request | Current asset manifest hash known by the client; triggers 409 Conflict on mismatch. |
| `X-Inertia-Location` | Response (409) | Target URL for forced full-page reload or external redirect (`InertiaExternalRedirect`). |
| `X-Inertia-Partial-Component` | Request | Component name targeted by a partial reload (`only` / `except`). |
| `X-Inertia-Partial-Data` | Request | Comma-separated list of prop keys to include during a partial reload. |
| `X-Inertia-Partial-Except` | Request | Comma-separated list of prop keys to exclude during a partial reload. |
| `X-Inertia-Reset` | Request | Comma-separated list of merged prop keys to reset before evaluating new values. |
| `X-Inertia-Except-Once-Props` | Request | Comma-separated list of `once()` prop keys already cached on the client. |
| `X-Inertia-Error-Bag` | Request | Optional error bag namespace for scoping form validation errors. |
| `Precognition` | Request & Response | `"true"` activates live Laravel Precognition validation without side effects. |
| `Precognition-Validate-Only` | Request | Comma-separated field names to filter validation errors during live typing. |
| `Precognition-Success` | Response (204) | `"true"` confirms live validation succeeded. |

| HTTP Status | Meaning in Inertia |
| --- | --- |
| 200 OK | Full HTML shell on initial visit, or JSON `PageProps` envelope when `X-Inertia: true`. |
| 204 No Content | Successful `@precognition` live validation check (`Precognition-Success: true`). |
| 303 See Other | Redirect following `POST`, `PUT`, `PATCH`, or `DELETE` so the browser follows with `GET`. |
| 409 Conflict | Asset version mismatch or `InertiaExternalRedirect` (`X-Inertia-Location` header). |
| 422 Unprocessable Entity | Precognition live validation error payload (`{ message, errors }`). |

---

## The PageProps Wire Envelope

Optional protocol keys (`flash`, `deferredProps`, `mergeProps`, `prependProps`, `deepMergeProps`, `matchPropsOn`, `scrollProps`, `onceProps`) are **omitted** when empty to keep wire payloads minimal:

```json
{
  "component": "Posts/Index",
  "props": {
    "errors": {},
    "csrf_token": "9f86d081884c7d659a2feaa0c55ad015",
    "auth": { "user": { "id": 1, "name": "Alice" } },
    "posts": [{ "id": 10, "title": "Hello Inertia" }]
  },
  "url": "/posts?page=1",
  "version": "e3b0c44298fc1c149afbf4c8996fb924",
  "encryptHistory": false,
  "clearHistory": false,
  "flash": { "success": ["Post published"] },
  "deferredProps": { "default": ["analytics"] },
  "mergeProps": ["posts"],
  "matchPropsOn": ["posts.id"]
}
```

---

## Inertia Guide Directory

| Guide Page | Topics Covered |
| --- | --- |
| [**Configuration & Templates**](configuration-and-templates.md) | `InertiaConfig`, Vite plugin boundary, script-element bootstrap, Jinja templates vs SPA mode, and custom mount selectors |
| [**Pages & Responses**](pages-and-responses.md) | Route `component` declarations, returning `msgspec.Struct` or Pydantic models, automatic pagination unwrapping, and server prop filters |
| [**Routing, Links & Redirects**](routing-and-links.md) | Client navigation with `<Link>`, typed `route()` URLs, `InertiaRedirect` / `InertiaBack`, and POST-Redirect-GET |
| [**Forms, Validation & Precognition**](forms-and-validation.md) | Form state with `useForm`, automatic validation errors, manual `error()`, error bags, and live `@precognition` validation |
| [**File Uploads**](file-uploads.md) | Automatic multipart conversion, `UploadFile` handling, upload progress bars, and client previews |
| [**Shared Data & Flash Messages**](shared-data-and-flash.md) | Per-request `share()`, static and session shared props, typed shared prop schemas, and top-level flash messages |
| [**Partial Reloads & Deferred Props**](partial-reloads-and-deferred.md) | Prop evaluation matrix, `lazy()`, `optional()` with `<WhenVisible>`, `once()`, `always()`, and grouped `defer()` |
| [**Merging Props & Infinite Scroll**](merging-and-infinite-scroll.md) | Append, prepend, and deep-merge strategies, key deduplication, `scroll_props()`, and `infinite_scroll=True` |
| [**Polling, Prefetching & Remembering State**](client-visits.md) | Periodic polling (`usePoll`), link prefetching, and local history state (`useRemember`) |
| [**Security, History Encryption & Versioning**](security-and-versioning.md) | HttpOnly CSRF protection, automatic CSRF headers, browser history encryption, and rolling asset versioning |
| [**SSR, TypeScript & Upgrade Guide**](ssr-and-typescript.md) | Server-side rendering (`InertiaSSRConfig`), `resolvePageComponent`, generated `PageProps` types, and Inertia v2 to v3 migration |
