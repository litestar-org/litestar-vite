# OpenAPI TypeScript SDK & Schema Helpers

When `TypeGenConfig(generate_sdk=True)` is active, Litestar Vite exports Litestar's OpenAPI 3.1 schema to `src/generated/openapi.json` and runs [`@hey-api/openapi-ts`](https://heyapi.dev) inside `litestar-vite-plugin` to generate a complete, tree-shakeable TypeScript client SDK under `src/generated/api/`.

---

## Python Configuration

```python title="docs/examples/typegen/openapi_and_routes.py"
--8<-- "docs/examples/typegen/openapi_and_routes.py"
```

---

## Ergonomic Schema Type Helpers

Raw `@hey-api/openapi-ts` types require indexing into generated operation request/response unions. To make forms and API responses effortless, `TypeGenConfig(generate_schemas=True)` generates `src/generated/schemas.ts` with high-level utility types keyed by operation or route name:

| Helper Type | Resolves To | Example |
| --- | --- | --- |
| **`FormInput<K>`** | Request body payload type for operation `K` | `type CreateCustomerForm = FormInput<"customers:create">;` |
| **`FormResponse<K, Status>`** | Response body type for operation `K` and HTTP status code | `type ValidationErr = FormResponse<"customers:create", 422>;` |
| **`SuccessResponse<K>`** | 200 / `201` success response payload for operation `K` | `type CustomerList = SuccessResponse<"customers:list">;` |
| **`ErrorResponse<K>`** | Union of error response payloads (400, 422, 500) for operation `K` | `type CreateCustomerError = ErrorResponse<"customers:create">;` |
| **`PathParams<K>`** | Path parameter object for operation `K` | `type CustomerPath = PathParams<"customers:detail">;` |
| **`QueryParams<K>`** | Query string parameter object for operation `K` | `type CustomerQuery = QueryParams<"customers:list">;` |

```typescript title="src/components/CustomerList.tsx"
import { listCustomers } from "../generated/api";
import type { FormInput, SuccessResponse } from "../generated/schemas";

type Customers = SuccessResponse<"customers:list">;
type NewCustomerInput = FormInput<"customers:create">;

export async function fetchEnterpriseCustomers(_draft?: NewCustomerInput): Promise<Customers> {
  const { data } = await listCustomers({ throwOnError: true });
  return data.filter((customer: { tier: string }) => customer.tier === "enterprise");
}
```

---

## Runtime Zod Schema Generation

Set `TypeGenConfig(generate_zod=True)` when you want `@hey-api/openapi-ts` to emit runtime [Zod](https://zod.dev) validation schemas alongside static TypeScript interfaces — ideal for client-side form validation with React Hook Form, TanStack Form, or VeeValidate:

```python
from litestar_vite import TypeGenConfig, ViteConfig

config = ViteConfig(
    types=TypeGenConfig(
        generate_sdk=True,
        generate_zod=True,
    ),
)
```

---

## Customizing the OpenAPI Generator

If your project includes an `openapi-ts.config.ts` file in the root directory, `litestar-vite-plugin` respects your custom plugins, client selection (`@hey-api/client-fetch`), and formatting rules while keeping `input` and `output` synchronized with `.litestar.json`:

<!-- docs-example: skip -->
```typescript title="openapi-ts.config.ts"
import { defineConfig } from "@hey-api/openapi-ts";

export default defineConfig({
  input: "./src/generated/openapi.json",
  output: "./src/generated/api",
  plugins: [
    "@hey-api/client-fetch",
    "@hey-api/schemas",
    "@hey-api/sdk",
    {
      name: "@hey-api/typescript",
      enums: "javascript",
    },
  ],
});
```

---

## Generating Types from the CLI

In CI pipelines or before running `tsc --noEmit`, run `litestar assets generate-types` to export all JSON schemas and execute `@hey-api/openapi-ts` without starting the HTTP server:

```bash
litestar assets generate-types
```
