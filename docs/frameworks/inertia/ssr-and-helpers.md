# SSR, Client Helpers & Type Generation

This page covers the TypeScript helpers exported by `litestar-vite-plugin/inertia-helpers`, script-element initial page bootstrapping, and automatic `PageProps` TypeScript generation.

---

## 1. Script-Element Initial Page Bootstrap (`use_script_element=True`)

By default, `InertiaConfig(use_script_element=True)` embeds initial page props inside a `<script type="application/json" data-page="app">` element instead of an HTML-escaped `data-page="..."` attribute on `<div id="app">`. This reduces initial HTML payload size by ~30% on data-heavy pages and avoids double-parsing HTML entities.

- **Inertia v3 clients** read `<script type="application/json" data-page="app">` automatically.
- **Inertia v2 clients** enable it with `defaults: { future: { useScriptElementForInitialPage: true } }` in both the client entrypoint (`main.tsx` / `main.ts`) and SSR entrypoint (`ssr.tsx` / `ssr.ts`):

```tsx title="resources/ssr.tsx"
import { createInertiaApp } from "@inertiajs/react";
import ReactDOMServer from "react-dom/server";
import { resolvePageComponent } from "litestar-vite-plugin/inertia-helpers";

export default function render(page: unknown) {
  return createInertiaApp({
    page: page as never,
    render: ReactDOMServer.renderToString,
    defaults: {
      future: {
        useScriptElementForInitialPage: true,
      },
    },
    resolve: (name) =>
      resolvePageComponent(
        `./pages/${name}.tsx`,
        import.meta.glob("./pages/**/*.tsx", { eager: true }),
      ),
    setup: ({ App, props }) => <App {...props} />,
  });
}
```

---

## 2. `resolvePageComponent` & `unwrapPageProps`

`litestar-vite-plugin/inertia-helpers` exports two zero-dependency utilities for Inertia applications:

| Function | Signature | Purpose |
| --- | --- | --- |
| [`resolvePageComponent`](../../reference/typescript/helpers.md) | `resolvePageComponent<T>(path: string \| string[], pages: Record<string, Promise<T> \| (() => Promise<T>) \| T>): Promise<T>` | Resolves a page module from `import.meta.glob(...)` (eager or lazy), supporting fallback path arrays and descriptive errors when a component is missing |
| [`unwrapPageProps`](../../reference/typescript/helpers.md) | `unwrapPageProps<T>(props: T): UnwrappedPageProps<T>` | Unwraps nested `{ content: ... }` envelopes when handlers wrap structured responses |

---

## 3. Automatic `page-props.ts` Type Generation

When `TypeGenConfig(generate_page_props=True)` is active, `litestar-vite` inspects every route handler with a `component="..."` option (`extract_inertia_pages`), resolves its return type annotation against the OpenAPI schema registry, and generates `src/generated/page-props.ts`:

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

Import `PagePropsFor<"Invoices/Index">` in your React, Vue, or Svelte page component to get end-to-end compile-time type safety from your Python controller to your UI template.
