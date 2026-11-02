# SSR, TypeScript & Upgrade Guide

This guide covers Server-Side Rendering (`InertiaSSRConfig`), client helpers (`resolvePageComponent`, `unwrapPageProps`), end-to-end `PageProps` TypeScript generation, and upgrading from Inertia v2 to v3.

---

## 1. Server-Side Rendering (`InertiaSSRConfig`)

Enabling `InertiaConfig(ssr=True)` (or `ssr=InertiaSSRConfig(...)`) pre-renders initial full-page Inertia visits on the server before returning HTML to the browser:

- **Development (`dev_mode=True`)**: Litestar sends the `PageProps` payload over `TCPStreamIPCTransport` to Vite's `/__litestar_ssr__` endpoint, which executes your `resources/ssr.tsx` (or `resources/ssr.ts`) entrypoint through Vite's `ModuleRunner` with full HMR invalidation.
- **Production (`dev_mode=False`)**: Litestar streams NDJSON requests over `StdioIPCTransport` (or `WasmIPCTransport`) to your compiled `ssr.js` worker (`startSsrWorker({ render })`).

```tsx title="resources/ssr.tsx"
import { createInertiaApp } from "@inertiajs/react";
import ReactDOMServer from "react-dom/server";
import { resolvePageComponent } from "litestar-vite-plugin/inertia-helpers";
import { startSsrWorker } from "litestar-vite-plugin/ssr-worker";

export default function render(page: unknown) {
  return createInertiaApp({
    page: page as never,
    render: ReactDOMServer.renderToString,
    defaults: {
      future: {
        useScriptElementForInitialPage: true,
      },
    },
    resolve: (name: string) =>
      resolvePageComponent(
        `./pages/${name}.tsx`,
        import.meta.glob("./pages/**/*.tsx", { eager: true }),
      ),
    setup: ({ App, props }: { App: any; props: any }) => <App {...props} />,
  });
}

startSsrWorker({ render });
```

### Bootstrap Interaction (`use_script_element`, `data-page`, `app_selector`)

When SSR returns `{ head, body }`, `inject_inertia_ssr_tags` splices `head` into `<!--inertia-head-->` (or `<head>`) and replaces `<div id="app">` (your configured `app_selector`) with the pre-rendered `body` while preserving `<script type="application/json" id="app_page" data-page="app">` when `use_script_element=True` (or the `data-page` attribute when `use_script_element=False`).

---

## 2. `resolvePageComponent` & `unwrapPageProps`

`litestar-vite-plugin/inertia-helpers` exports two zero-dependency utilities:

| Function | Signature | Purpose |
| --- | --- | --- |
| [`resolvePageComponent`](../../reference/typescript/helpers.md) | `resolvePageComponent<T>(path: string \| string[], pages: Record<string, Promise<T> \| (() => Promise<T>) \| T>): Promise<T>` | Resolves a page module from `import.meta.glob(...)` (eager or lazy), supporting fallback path arrays and descriptive errors when a component is missing. |
| [`unwrapPageProps`](../../reference/typescript/helpers.md) | `unwrapPageProps<T>(props: T): UnwrappedPageProps<T>` | Unwraps nested `{ content: ... }` envelopes when handlers wrap structured responses. |

---

## 3. Automatic `page-props.ts` & `inertia.d.ts` Type Generation

When `TypeGenConfig(generate_page_props=True)` is active, `litestar-vite` inspects every route handler with a `component="..."` option (`extract_inertia_pages`), writes `.litestar/inertia-pages.json`, and generates `src/generated/page-props.ts`:

```typescript title="src/generated/page-props.ts (Generated)"
import type { InvoiceSummary } from "./api/types.gen";

export interface InvoicesIndexProps {
  invoices: InvoiceSummary[];
}

export interface ComponentPropsMap {
  "Invoices/Index": InvoicesIndexProps;
  "Invoices/Show": InvoiceSummary;
}

export type PagePropsFor<C extends keyof ComponentPropsMap> =
  SharedPageProps & ComponentPropsMap[C];
```

### Customizing `User` and `SharedProps` via Module Augmentation

Customize default `AuthData` or `SharedProps` in `src/types/inertia.d.ts` (or disable default auth generation with `InertiaTypeGenConfig(include_default_auth=False)`):

<!-- docs-example: skip -->
```typescript title="src/types/inertia.d.ts"
import "litestar-vite-plugin/inertia";

declare module "litestar-vite-plugin/inertia" {
  interface User {
    id: string;
    email: string;
    roles: ("admin" | "member")[];
  }

  interface SharedProps {
    tenantId: string;
  }
}
```

---

## 4. Inertia v2 to v3 Upgrade Guide

| Feature | Inertia v2 | Inertia v3 (`@inertiajs/*` v3) |
| --- | --- | --- |
| **Script-Element Bootstrap** | Opt-in on client via `defaults: { future: { useScriptElementForInitialPage: true } }` | **Default behavior** when `InertiaConfig(use_script_element=True)` is active (`defaults: {}`). |
| **Document `<title>` Tag** | `<title inertia>` or `<title data-inertia>` | Plain `<title>App</title>` (v3 replaces the single `<title>` element automatically without marker attributes). |
| **HTTP Client** | Axios | Native `fetch` / XHR (no `axios` dependency required). |
| **Top-Level Flash** | Supported in v2.3+ (`page.flash`) | Standard (`page.flash`). |
