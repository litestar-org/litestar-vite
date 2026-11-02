# Static Props (`virtual:litestar-static-props`)

Applications frequently need build-time or startup-time configuration constants in the frontend — such as public feature flags, application version metadata, OAuth client IDs, or regional limits — without making an extra HTTP request on page load or maintaining duplicate `.env` files.

`ViteConfig(static_props=...)` solves this by serializing a Python dictionary (including `msgspec.Struct`, `dataclass`, or Pydantic models) into `.litestar.json`, generating TypeScript definitions in `static-props.ts`, and exposing the values through the Vite virtual module `virtual:litestar-static-props`.

---

## When to Use `static_props` vs. Inertia Shared Props

| Mechanism | Evaluation Time | Works In | Best For |
| --- | --- | --- | --- |
| **`ViteConfig.static_props`** | Startup / Build time | **All modes** (`spa`, `hybrid`, `template`, `framework`) | Public feature flags, app name/version, public DSNs, static tier limits |
| **`InertiaConfig.extra_static_page_props`** | Every Inertia HTTP response | `mode="hybrid"` only | Static page props consumed via Inertia `usePage().props` |
| **`inertia.share(connection, key, val)`** | Per-request | `mode="hybrid"` only | Current authenticated user, request permissions, flash messages |

> [!WARNING]
> **Build-Time & Startup-Only Boundary**:
> 1. Never place secrets (database URLs, private API keys, signing secrets) in `static_props` — values are bundled into client-side JavaScript.
> 2. `static_props` are written to `.litestar.json` at Python startup (`set_environment`) and `litestar assets generate-types`, and read by `litestar-vite-plugin` when Vite starts or runs `vite build`. For values that change per-request or at runtime without rebuilding assets, use an API endpoint or Inertia's `share()`.

---

## 1. Define `static_props` in Python

Pass any JSON-serializable dictionary or `msgspec.Struct` values to `ViteConfig(static_props=...)`:

```python title="docs/examples/learn/static_props_app.py"
--8<-- "docs/examples/learn/static_props_app.py"
```

---

## 2. Consume `virtual:litestar-static-props` in TypeScript

When `TypeGenConfig` runs, `litestar-vite` generates `src/generated/static-props.ts` with strongly typed interfaces for your `static_props` keys and declares the `virtual:litestar-static-props` module:

```typescript title="src/config.ts"
import staticProps, { appName, features } from "virtual:litestar-static-props";

console.log(appName);
if (features.enable_billing_v2) {
  console.log(`Max upload: ${features.max_upload_mb} MB`);
}

export { staticProps };
```

Both default import (`import staticProps from "virtual:litestar-static-props"`) and named top-level property imports (`import { appName, features } from "virtual:litestar-static-props"`) are supported out of the box by `litestar-vite-plugin`.

---

## 3. TypeScript Ambient Declaration (`env.d.ts`)

If your `tsconfig.json` does not automatically include `src/generated/static-props.ts`, reference the built-in virtual module types in `src/env.d.ts` (or `src/vite-env.d.ts`):

```typescript title="src/env.d.ts"
/// <reference types="vite/client" />
/// <reference types="litestar-vite-plugin/virtual" />
```
