# End-to-End Type Generation Overview

Maintaining duplicate data models, API URL strings, and WebSocket payload types across Python and TypeScript is one of the largest sources of bugs in full-stack applications.

When `ViteConfig(types=True)` (or an explicit [`TypeGenConfig`](../reference/plugin-and-config.md#litestar_vite.config.TypeGenConfig)) is enabled, `litestar-vite` exports canonical JSON schemas from Litestar on startup and drives `litestar-vite-plugin` to generate strongly typed TypeScript modules in `src/generated/`.

--8<-- "tools/docs/includes/diagram-typegen-pipeline.html"

---

## Generated Artifacts Summary

| Python Source | Intermediate JSON (`write_if_changed`) | Generated TypeScript Output | What You Import in Frontend Code |
| --- | --- | --- | --- |
| Litestar OpenAPI (`_openapi.py`) | `src/generated/openapi.json` | `src/generated/api/` (`@hey-api/openapi-ts`) + `src/generated/schemas.ts` | Typed SDK functions, `FormInput<op>`, `FormResponse<op>`, `SuccessResponse<op>` |
| Litestar Router (`_routes.py`) | `src/generated/routes.json` | `src/generated/routes.ts` | `route("users:detail", { user_id: 42 })`, `wsRoute(...)`, `RouteName` |
| Inertia Handlers (`_inertia.py`) | `src/generated/inertia-pages.json` | `src/generated/page-props.ts` + `inertia.d.ts` | `PagePropsFor<"Users/Show">`, `SharedPageProps`, `FlashMessages` |
| `ViteConfig.static_props` | `.litestar.json` (`staticProps`) | `src/generated/static-props.ts` | `import props from "virtual:litestar-static-props"` |
| `AsyncAPIPlugin` (`_asyncapi.py`) | `src/generated/asyncapi.json` | `src/generated/channels.ts` | `createTypedChannels(ws)`, `useEventStream()`, `useWsChannel()` |

---

## SHA-256 `write_if_changed` Determinism

Every intermediate JSON and generated TypeScript file passes through [`write_if_changed()`](../reference/tooling-and-codegen.md#litestar_vite.codegen.write_if_changed) and [`encode_deterministic_json()`](../reference/tooling-and-codegen.md#litestar_vite.codegen.encode_deterministic_json):

1. JSON keys are sorted deterministically and volatile timestamps are stripped before comparison.
2. If the SHA-256 digest of the newly rendered content matches the existing file on disk, **no disk write occurs**.
3. This prevents unnecessary file-watcher events and avoids infinite Vite HMR reload loops during `litestar run --reload`.

---

## Explore TypeGen Guides

- [**OpenAPI TypeScript SDK & Schema Helpers (`schemas.ts`)**](openapi-sdk.md)
- [**Typed Routes (`route()` & `wsRoute()`)**](routes.md)
- [**AsyncAPI & Realtime Channels (`channels.ts`)**](realtime-channels.md)
