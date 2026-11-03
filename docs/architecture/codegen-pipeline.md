---
title: End-to-End TypeGen Pipeline
description: Architecture of the Python-to-TypeScript schema and route generation pipeline across OpenAPI, Routes, Inertia PageProps, and AsyncAPI Channels.
---

# End-to-End TypeGen Pipeline

When `ViteConfig(types=True)` (or `TypeGenConfig(...)`) is enabled, Litestar Vite turns Python route handlers, DTOs, `msgspec.Struct` / Pydantic models, Inertia page components, and WebSocket / Channels streams into compile-time checked TypeScript artifacts without manual synchronization.

--8<-- "tools/docs/includes/diagram-typegen-pipeline.html"

---

## Four-Stage Generation Lifecycle

### Python Introspection

On application startup (or when running `litestar assets generate-types`), Litestar Vite inspects the initialized `Litestar` instance:

- **OpenAPI Schema (`codegen/_openapi.py`)**: Confines all Litestar OpenAPI access (`OpenAPISupport`, `SchemaCreator`, `build_schema_name_map`) to a single private seam, serializing a deterministic OpenAPI 3.1 document with sorted keys.
- **Route Metadata (`codegen/_routes.py`)**: Extracts HTTP and WebSocket routes (`extract_route_metadata`), typed path and query parameters, `operationId` links, and Inertia `component` annotations while excluding internal proxy/HMR endpoints.
- **Inertia Page Metadata (`codegen/_inertia.py`)**: Maps every route with `component="..."` to its return-type schema reference or inline TypeScript type, plus registered `InertiaConfig` shared props.
- **AsyncAPI 3.0 Channels (`generate_asyncapi_schema`)**: When `litestar-asyncapi` (`AsyncAPIPlugin`) or `ChannelsPlugin` is registered, exports WebSocket and pub/sub channel payloads to `asyncapi.json` (and unlinks stale `asyncapi.json` / `channels.ts` files if the plugin is removed).

### Deterministic Disk Writes

Every exported JSON and TypeScript file is written through a content-hash check (`write_if_changed` in both Python and TypeScript). If the serialized byte content is identical to the file already on disk, the file's `mtime` is preserved so Vite's watcher never triggers redundant HMR rebuild loops.

### Vite TypeGen Plugin

On the JavaScript side, `createLitestarTypeGenPlugin` (shared across `litestar-vite-plugin`, `/astro`, `/sveltekit`, and `/nuxt`) watches the exported JSON files with a 300ms debounce window and runs four emitters:

| Input Artifact | Emitter | Generated Output | Primary Symbols |
| :--- | :--- | :--- | :--- |
| `openapi.json` | `@hey-api/openapi-ts` | `api/types.gen.ts`, `api/sdk.gen.ts` | Typed REST client, request/response models, optional Zod schemas |
| `routes.json` | `generate_routes_ts` / `routes.ts` | `routes.ts` | `route()`, `toRoute()`, `wsRoute()`, `routeDefinitions`, `RouteName` |
| `routes.json` + `openapi.json` | `emit-schemas-types.ts` | `schemas.ts` | `FormInput<R>`, `FormResponse<R, Status>`, `SuccessResponse<R>` |
| `inertia-pages.json` | `emit-page-props-types.ts` | `page-props.ts` | `PageProps`, `PagePropsFor<C>`, `InertiaPageProps<C>` |
| `asyncapi.json` | `emit-channels-types.ts` | `channels.ts` | `ChannelMap`, `ChannelName`, `ChannelPayload`, `bindTypedChannels()` |
| `.litestar.json` (`staticProps`) | `emit-static-props-types.ts` | `static-props.d.ts` | `declare module "virtual:litestar-static-props"` |

### HMR Notification

Whenever any generated TypeScript file changes on disk, `createLitestarTypeGenPlugin` dispatches a custom Vite WebSocket event (`litestar:types-updated`) and logs the regeneration duration in milliseconds.
