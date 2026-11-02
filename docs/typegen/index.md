# End-to-End Type Generation Overview

Maintaining duplicate data models, API URL strings, and WebSocket payload types across Python and TypeScript is one of the largest sources of bugs in full-stack applications.

When `ViteConfig(types=True)` (or an explicit [`TypeGenConfig`](../reference/plugin-and-config.md#litestar_vite.config.TypeGenConfig)) is enabled, Litestar Vite exports canonical JSON schemas from Litestar on startup and drives `litestar-vite-plugin` to generate strongly typed TypeScript modules in `src/generated/`.

--8<-- "tools/docs/includes/diagram-typegen-pipeline.html"

---

## Generated Artifacts Summary

All intermediate schemas and generated TypeScript files are written under `TypeGenConfig.output` (`src/generated/` by default):

| Litestar Source | Generated Output | Frontend Exports |
| --- | --- | --- |
| OpenAPI Schema | `openapi.json` → `api/` & `schemas.ts` | Typed SDK functions, `FormInput`, `FormResponse`, `SuccessResponse` |
| Router Metadata | `routes.json` → `routes.ts` | `route()`, `toRoute()`, `wsRoute()`, `isCurrentRoute()`, `RouteName` |
| Inertia Handlers | `inertia-pages.json` → `page-props.ts` & `inertia.d.ts` | `PagePropsFor`, `SharedPageProps`, `FlashMessages` |
| Static Props | `.litestar.json` → `static-props.ts` | `virtual:litestar-static-props` |
| AsyncAPI Plugin | `asyncapi.json` → `channels.ts` | `createTypedChannels()`, `useEventStream()`, `useQueueEventStream()` |

---

## Configuration Options

| Option | Default | Description |
| --- | --- | --- |
| `output` | `Path("src/generated")` | Output directory for exported JSON schemas and generated TypeScript files. |
| `generate_sdk` | `True` | Export `openapi.json` and run `@hey-api/openapi-ts` to generate `api/`. |
| `generate_routes` | `True` | Export `routes.json` and generate `routes.ts` route helpers. |
| `generate_page_props` | `True` | Export `inertia-pages.json` and generate `page-props.ts` when Inertia is active. |
| `generate_schemas` | `True` | Generate ergonomic `schemas.ts` form and response type helpers. |
| `generate_channels` | `False` | Export `asyncapi.json` and generate `channels.ts` (requires `litestar-asyncapi`). |
| `generate_zod` | `False` | Generate Zod validation schemas alongside the OpenAPI client SDK. |
| `global_route` | `False` | Emit a `global.d.ts` ambient declaration exposing `window.route` globally. |
| `fallback_type` | `"unknown"` | Fallback TypeScript type (`"unknown"` or `"any"`) for untyped handler props. |
| `type_import_paths` | `{}` | Map custom Python class names to TypeScript import paths in `page-props.ts`. |

---

## CLI Workflow

In CI pipelines or before running `tsc --noEmit`, run `litestar assets generate-types` to export all JSON schemas and execute TypeScript code generation without starting the HTTP server:

<!-- termynal -->

```console
$ litestar assets generate-types
✓ Exported openapi.json (unchanged, skipped write)
✓ Exported routes.json (14 routes, 2 websocket endpoints)
✓ Generated src/generated/routes.ts, schemas.ts, and api/
$ litestar assets export-routes --only api,users
✓ Exported filtered routes.json
```

---

## Deterministic Artifact Writes

Every intermediate JSON and generated TypeScript file passes through [`write_if_changed()`](../reference/tooling-and-codegen.md#litestar_vite.codegen.write_if_changed) and [`encode_deterministic_json()`](../reference/tooling-and-codegen.md#litestar_vite.codegen.encode_deterministic_json):

1. JSON keys are sorted deterministically and volatile timestamps are stripped before comparison.
2. If the SHA-256 digest of the newly rendered content matches the existing file on disk, **no disk write occurs**.
3. This prevents unnecessary file-watcher events and avoids infinite Vite HMR reload loops during `litestar run --reload`.

---

## Explore TypeGen & Realtime Guides

- [**OpenAPI TypeScript SDK & Schema Helpers**](openapi-sdk.md)
- [**Typed Routes**](routes.md)
- [**AsyncAPI Channels, WebSockets & SSE**](realtime-channels.md)
- [**Browser & Framework Event Streams**](event-streams.md)
