# Inertia.js Overview & Protocol Lifecycle

[Inertia.js](https://inertiajs.com) lets you build modern React, Vue 3, and Svelte 5 single-page applications using classic server-side routing and controllers. Instead of building a separate REST or GraphQL API for every screen, your Litestar route handlers declare `component="Users/Index"` and return Python `dict`, `msgspec.Struct`, `dataclass`, or Pydantic models directly.

--8<-- "tools/docs/includes/diagram-inertia-lifecycle.html"

---

## How the Inertia Protocol Works in Litestar

1. **Initial Full-Page Visit (`GET /dashboard`)**:
   - The browser sends a standard HTTP request without an `X-Inertia` header.
   - `InertiaResponse` serializes the `PageProps` envelope (`component`, `props`, `url`, `version`, `encryptHistory`, `clearHistory`, `deferredProps`, `mergeProps`, `onceProps`, `flash`) into `<script type="application/json" id="app_page" data-page="app">` (when `use_script_element=True`, the default) or a `data-page` attribute on `#app`.
   - When `InertiaConfig(ssr=True)` is enabled, `litestar-vite` pre-renders the initial HTML via the SSR IPC transport and splices `<!--inertia-head-->` and `<!--inertia-->` before returning `200 OK text/html`.
2. **Subsequent Client Navigation (`X-Inertia: true`)**:
   - Clicking an Inertia `<Link>` or calling `router.visit()` sends an XHR/Fetch request with `X-Inertia: true` and `X-Inertia-Version: <hash>`.
   - Litestar detects `request.is_inertia == True` and returns `200 OK application/json` containing only the `PageProps` JSON envelope, swapping the page component in place without a full browser reload.
3. **Deferred Props & Partial Reloads (`X-Inertia-Partial-Data`)**:
   - Props wrapped in `defer(key, fn, group=...)` are omitted from the initial response and listed in `deferredProps: { default: [...] }`.
   - Immediately after mounting the initial page, the Inertia client fires batched background partial reloads (`X-Inertia-Partial-Component` + `X-Inertia-Partial-Data`) to resolve each deferred group.
4. **Mutations (`303 See Other`) & Asset Version Rotation (`409 Conflict`)**:
   - Following `POST`, `PUT`, `PATCH`, or `DELETE` requests, `InertiaMiddleware` converts `302 Found` redirects into `303 See Other` so the browser follows up with a `GET` request.
   - If the frontend bundle hash changes between deployments (`X-Inertia-Version` mismatch), Litestar responds with `409 Conflict` and `X-Inertia-Location: <url>`, prompting the client to perform a clean full-page reload.

---

## Protocol Headers & Status Codes

| Header | Direction | Description |
| --- | --- | --- |
| `X-Inertia` | Request & Response | `"true"` marks an Inertia XHR/Fetch navigation and JSON `PageProps` response. |
| `X-Inertia-Version` | Request | Current asset manifest hash known by the client; triggers `409 Conflict` on mismatch. |
| `X-Inertia-Location` | Response (`409`) | Target URL for forced full-page reload or external redirect (`InertiaExternalRedirect`). |
| `X-Inertia-Partial-Component` | Request | Component name targeted by a partial reload (`only` / `except`). |
| `X-Inertia-Partial-Data` | Request | Comma-separated list of prop keys to include during a partial reload. |
| `X-Inertia-Partial-Except` | Request | Comma-separated list of prop keys to exclude during a partial reload. |
| `X-Inertia-Reset` | Request | Comma-separated list of merged prop keys to reset before evaluating new values. |
| `X-Inertia-Except-Once-Props` | Request | Comma-separated list of `once()` prop keys already cached on the client. |
| `X-Inertia-Error-Bag` | Request | Optional error bag namespace for scoping form validation errors. |
| `Precognition` | Request & Response | `"true"` activates live Laravel Precognition validation without side effects. |
| `Precognition-Validate-Only` | Request | Comma-separated field names to filter validation errors during live typing. |
| `Precognition-Success` | Response (`204`) | `"true"` confirms live validation succeeded. |

| HTTP Status | Meaning in Inertia |
| --- | --- |
| `200 OK` | Full HTML shell on initial visit, or JSON `PageProps` envelope when `X-Inertia: true`. |
| `204 No Content` | Successful `@precognition` live validation check (`Precognition-Success: true`). |
| `303 See Other` | Redirect following `POST`, `PUT`, `PATCH`, or `DELETE` so the browser follows with `GET`. |
| `409 Conflict` | Asset version mismatch or `InertiaExternalRedirect` (`X-Inertia-Location` header). |
| `422 Unprocessable Entity` | Precognition live validation error payload (`{ message, errors }`). |

---

## The `PageProps` Wire Envelope

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
| [**Configuration & Templates**](configuration-and-templates.md) | `InertiaConfig`, `InertiaTypeGenConfig`, Vite plugin boundary, `useScriptElementForInitialPage`, Jinja templates vs SPA mode, `app_selector`, and multiple templates |
| [**Pages & Responses**](pages-and-responses.md) | `@get(..., component="...")`, nested pages, `msgspec.Struct` / Pydantic direct returns, `InertiaResponse`, automatic pagination unwrapping, and server `only()` / `except_()` |
| [**Routing, Links & Redirects**](routing-and-links.md) | `<Link>`, `route()` helper, Laravel/Ziggy comparison, `InertiaRedirect`, `InertiaBack`, `InertiaExternalRedirect`, and POST-Redirect-GET |
| [**Forms, Validation & Precognition**](forms-and-validation.md) | `useForm` (React/Vue/Svelte), automatic Litestar validation errors, manual `error()`, Error Bags, custom error pages, and `@precognition` live validation |
| [**File Uploads**](file-uploads.md) | Multipart `FormData` conversion, `UploadFile` / `list[UploadFile]`, upload progress bars, and client image previews |
| [**Shared Data & Flash Messages**](shared-data-and-flash.md) | Per-request `share()`, lazy shared props, `extra_static_page_props`, `extra_session_page_props`, `shared_page_prop_types`, and top-level `page.flash` |
| [**Partial Reloads & Deferred Props**](partial-reloads-and-deferred.md) | Prop evaluation matrix, `lazy()`, `optional()` + `<WhenVisible>`, `once()`, `always()`, `defer()` + `<Deferred>`, and `X-Inertia-Reset` |
| [**Merging Props & Infinite Scroll**](merging-and-infinite-scroll.md) | `merge()` (`append`, `prepend`, `deep`, `match_on`), `scroll_props()`, `@get(..., infinite_scroll=True)`, and `<WhenVisible always>` |
| [**Polling, Prefetching & Remembering State**](client-visits.md) | `usePoll`, `<Link prefetch>` & `router.prefetch()`, `useRemember`, and remembered `useForm` keys |
| [**Security, History Encryption & Versioning**](security-and-versioning.md) | `CSRFConfig(cookie_httponly=True)`, `csrfHeaders()`, `encrypt_history=True`, `clear_history()`, and `X-Inertia-Version` rolling deploys |
| [**SSR, TypeScript & Upgrade Guide**](ssr-and-typescript.md) | `InertiaSSRConfig`, `resolvePageComponent`, `unwrapPageProps`, `page-props.ts`, `PagePropsFor<C>`, module augmentation, and Inertia v2 -> v3 upgrade guide |
