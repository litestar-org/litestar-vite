# OpenAPI TypeScript SDK & Schema Helpers

When `TypeGenConfig(generate_sdk=True)` is active, `litestar-vite` exports Litestar's OpenAPI 3.1 schema to `src/generated/openapi.json` and runs [`@hey-api/openapi-ts`](https://heyapi.dev) inside `litestar-vite-plugin` to generate a complete, tree-shakeable TypeScript client SDK under `src/generated/api/`.

---

## 1. Python Configuration (`TypeGenConfig`)

```python title="docs/examples/typegen/openapi_and_routes.py"
--8<-- "docs/examples/typegen/openapi_and_routes.py"
```

---

## 2. Ergonomic Schema Type Helpers (`schemas.ts`)

Raw `@hey-api/openapi-ts` types require indexing into generated operation request/response unions. To make forms and API responses effortless, `TypeGenConfig(generate_schemas=True)` generates `src/generated/schemas.ts` with three high-level utility types keyed by operation or route name:

| Helper Type | Resolves To | Example |
| --- | --- | --- |
| **`FormInput<K>`** | Request body payload type for operation `K` | `type CreateCustomerForm = FormInput<"customers:create">;` |
| **`FormResponse<K, Status>`** | Response body type for operation `K` and HTTP status code | `type ValidationErr = FormResponse<"customers:create", 422>;` |
| **`SuccessResponse<K>`** | `200` / `201` success response payload for operation `K` | `type CustomerList = SuccessResponse<"customers:list">;` |

```typescript title="src/components/CustomerList.tsx"
import { listCustomers } from "../generated/api";
import type { SuccessResponse } from "../generated/schemas";

type Customers = SuccessResponse<"customers:list">;

export async function fetchEnterpriseCustomers(): Promise<Customers> {
  const { data } = await listCustomers({ throwOnError: true });
  return data.filter((customer: { tier: string }) => customer.tier === "enterprise");
}
```

---

## 3. Generating Types from the CLI (`litestar assets generate-types`)

In CI pipelines or before running `tsc --noEmit`, run `litestar assets generate-types` to export all JSON schemas and execute `@hey-api/openapi-ts` without starting the HTTP server:

```bash
litestar assets generate-types
```
