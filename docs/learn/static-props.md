# Static Props (`virtual:litestar-static-props`)

Applications frequently need build-time or startup-time configuration constants in the frontend — such as public feature flags, application version metadata, OAuth client IDs, or regional limits — without making an extra HTTP request on page load or maintaining duplicate `.env` files.

`ViteConfig(static_props=...)` solves this by serializing a Python dictionary (including `msgspec.Struct`, `dataclass`, or Pydantic models) into `.litestar.json`, generating TypeScript definitions in `static-props.ts`, and exposing the values through the Vite virtual module `virtual:litestar-static-props`.

---

## When to Use `static_props` vs. Inertia Shared Props

| Mechanism | Evaluation Time | Works In | Best For |
| --- | --- | --- | --- |
| **`ViteConfig.static_props`** | Startup / Build time | **All 4 modes** (`spa`, `hybrid`, `template`, `framework`) | Public feature flags, app name/version, public DSNs, static tier limits |
| **`InertiaConfig.extra_static_page_props`** | Every Inertia HTTP response | `mode="hybrid"` only | Static page props consumed via Inertia `usePage().props` |
| **`inertia.share(connection, key, val)`** | Per-request | `mode="hybrid"` only | Current authenticated user, request permissions, flash messages |

> [!WARNING]
> Never place secrets (database URLs, private API keys, signing secrets) in `static_props`. Values in `static_props` are bundled directly into client-side JavaScript.

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
