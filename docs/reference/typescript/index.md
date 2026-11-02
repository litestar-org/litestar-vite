---
title: Vite Plugin & Core Types
description: TypeScript API reference for litestar-vite-plugin, litestar-vite-plugin/inertia, and litestar-vite-plugin/virtual.
---

# Vite Plugin & Core Types

The `litestar-vite-plugin` npm package ships 18 typed ESM entrypoints covering the Vite 7+ plugin, runtime helpers, framework bindings, meta-framework integrations, and server/island fragment adapters. This page documents the root Vite plugin (`litestar-vite-plugin`), base Inertia ambient types (`litestar-vite-plugin/inertia`), and the `virtual:litestar-static-props` ambient module (`litestar-vite-plugin/virtual`).

| Subpath | Import Specifier | Source Entrypoint | Exports |
| :--- | :--- | :--- | :--- |
| `.` | `litestar-vite-plugin` | `src/js/src/index.ts` | `PluginConfig`, `RefreshConfig`, `ResolvedPluginConfig`, `TypesConfig`, `DevServerUrl`, `litestar`, +4 more |
| `./inertia` | `litestar-vite-plugin/inertia` | `src/js/src/inertia-types.ts` | `User`, `AuthData`, `FlashMessages`, `SharedProps`, `GeneratedSharedProps`, `PageProps`, +4 more |
| `./virtual` | `litestar-vite-plugin/virtual` | `src/js/src/virtual.d.ts` | `StaticProps`, `virtual:litestar-static-props` |

## `litestar-vite-plugin`

**Package Subpath**: `.` · **Types**: `./dist/js/index.d.ts` · **Source**: `src/js/src/index.ts`

| Export | Kind | Description |
| :--- | :--- | :--- |
| `PluginConfig` | `interface` | Exported `interface` from `src/js/src/index.ts`. |
| `RefreshConfig` | `interface` | Exported `interface` from `src/js/src/index.ts`. |
| `ResolvedPluginConfig` | `interface` | Resolved plugin configuration with all defaults applied. Note: `types` is resolved to `RequiredTypeGenConfig \| false` instead of `boolean \| TypesConfig` Note: `executor` remains optional - undefined means auto-detect from env Note: `inertiaMode` is resolved to boolean (auto-detected from .litestar.json Inertia metadata) |
| `TypesConfig` | `type` | Configuration for TypeScript type generation. |
| `DevServerUrl` | `type` | Exported `type` from `src/js/src/index.ts`. |
| `litestar` | `default function` | Litestar plugin for Vite. |
| `litestarViteSsrPlugin` | `function` | Exported `function` from `src/js/src/dev-ssr.ts`. |
| `DevSsrOptions` | `interface` | Exported `interface` from `src/js/src/shared/ssr-types.ts`. |
| `SsrRenderRequest` | `interface` | Exported `interface` from `src/js/src/shared/ssr-types.ts`. |
| `SsrRenderResponse` | `interface` | Exported `interface` from `src/js/src/shared/ssr-types.ts`. |

#### `PluginConfig`

```ts
export interface PluginConfig
```

| Property | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `input` | `string \| string[]` | — | — |
| `assetUrl?` | `string` | — | — |
| `deployAssetUrl?` | `string` | — | — |
| `bundleDir?` | `string` | — | — |
| `staticDir?` | `string` | — | — |
| `resourceDir?` | `string` | — | — |
| `hotFile?` | `string` | — | — |
| `ssr?` | `string \| string[]` | — | — |
| `devSsr?` | `DevSsrOptions` | — | — |
| `ssrOutDir?` | `string` | — | — |
| `refresh?` | `boolean \| string \| string[] \| RefreshConfig \| RefreshConfig[]` | — | — |
| `detectTls?` | `string \| boolean \| null` | — | — |
| `autoDetectIndex?` | `boolean` | — | — |
| `inertiaMode?` | `boolean` | — | — |
| `transformOnServe?` | `(code: string, url: DevServerUrl) => string` | — | — |
| `types?` | `boolean \| "auto" \| TypesConfig` | — | — |
| `executor?` | `"node" \| "bun" \| "deno" \| "yarn" \| "pnpm"` | — | — |

#### `RefreshConfig`

```ts
export interface RefreshConfig
```

| Property | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `paths` | `string[]` | — | — |
| `config?` | `FullReloadConfig` | — | — |

#### `ResolvedPluginConfig`

```ts
export interface ResolvedPluginConfig extends Omit<Required<PluginConfig>, "types" | "executor" | "inertiaMode" | "deployAssetUrl">
```

Resolved plugin configuration with all defaults applied. Note: `types` is resolved to `RequiredTypeGenConfig | false` instead of `boolean | TypesConfig` Note: `executor` remains optional - undefined means auto-detect from env Note: `inertiaMode` is resolved to boolean (auto-detected from .litestar.json Inertia metadata)

| Property | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `types` | `RequiredTypeGenConfig \| false` | — | — |
| `executor?` | `"node" \| "bun" \| "deno" \| "yarn" \| "pnpm"` | — | — |
| `deployAssetUrl?` | `string` | — | — |
| `inertiaMode` | `boolean` | — | — |
| `hasPythonConfig` | `boolean` | — | — |

#### `TypesConfig`

```ts
export type TypesConfig = TypesConfigShape
```

Configuration for TypeScript type generation.

| Property | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `enabled?` | `boolean` | — | — |
| `output?` | `string` | — | — |
| `openapiPath?` | `string` | — | — |
| `routesPath?` | `string` | — | — |
| `pagePropsPath?` | `string` | — | — |
| `schemasTsPath?` | `string` | — | — |
| `asyncapiPath?` | `string` | — | — |
| `channelsTsPath?` | `string` | — | — |
| `generateZod?` | `boolean` | — | — |
| `generateSdk?` | `boolean` | — | — |
| `generateRoutes?` | `boolean` | — | — |
| `generatePageProps?` | `boolean` | — | — |
| `generateSchemas?` | `boolean` | — | — |
| `generateChannels?` | `boolean` | — | — |
| `globalRoute?` | `boolean` | — | — |
| `failOnError?` | `boolean` | — | — |
| `debounce?` | `number` | — | — |

#### `DevServerUrl`

```ts
export type DevServerUrl = `${"http" | "https"}://${string}:${number}`
```

#### `litestar`

```ts
export default function litestar(config: string | string[] | PluginConfig): any[]
```

Litestar plugin for Vite.

#### `litestarViteSsrPlugin`

```ts
export function litestarViteSsrPlugin(options: DevSsrOptions =
```

#### `DevSsrOptions`

```ts
export interface DevSsrOptions
```

| Property | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `entrypoint?` | `string` | — | — |
| `componentRoots?` | `string[]` | — | — |
| `clientEntry?` | `string` | — | — |
| `endpoint?` | `string` | — | — |
| `hmr?` | `boolean` | — | — |

#### `SsrRenderRequest`

```ts
export interface SsrRenderRequest
```

| Property | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `id?` | `number \| string` | — | — |
| `method?` | `string` | — | — |
| `type?` | `"inertia" \| "fragment"` | — | — |
| `mode?` | `"static" \| "island"` | — | — |
| `params?` | `Record<string, unknown>` | — | — |
| `page?` | `object` | — | — |
| `component?` | `string` | — | — |
| `props?` | `Record<string, unknown>` | — | — |

#### `SsrRenderResponse`

```ts
export interface SsrRenderResponse
```

| Property | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `id?` | `number \| string` | — | — |
| `result?` | `object` | — | — |
| `error?` | `object` | — | — |

## `litestar-vite-plugin/inertia`

**Package Subpath**: `./inertia` · **Types**: `./dist/js/inertia-types.d.ts` · **Source**: `src/js/src/inertia-types.ts`

Base types for Inertia.js type generation.

| Export | Kind | Description |
| :--- | :--- | :--- |
| `User` | `interface` | User interface - customize in page-props.user.ts |
| `AuthData` | `interface` | Authentication data interface |
| `FlashMessages` | `interface` | Flash messages interface |
| `SharedProps` | `interface` | User-defined shared props - customize in page-props.user.ts |
| `GeneratedSharedProps` | `interface` | Generated shared props (populated by page-props.ts) |
| `PageProps` | `interface` | Page props mapped by component name (populated by page-props.ts) |
| `FullSharedProps` | `type` | Full shared props = generated + user-defined |
| `ComponentName` | `type` | Component name union type |
| `InertiaPageProps` | `type` | Type-safe props for a specific component |
| `PagePropsFor` | `type` | Get props type for a specific page component |

#### `User`

```ts
export interface User
```

User interface - customize in page-props.user.ts

#### `AuthData`

```ts
export interface AuthData
```

Authentication data interface

#### `FlashMessages`

```ts
export interface FlashMessages
```

Flash messages interface

#### `SharedProps`

```ts
export interface SharedProps
```

User-defined shared props - customize in page-props.user.ts

#### `GeneratedSharedProps`

```ts
export interface GeneratedSharedProps
```

Generated shared props (populated by page-props.ts)

#### `PageProps`

```ts
export interface PageProps
```

Page props mapped by component name (populated by page-props.ts)

#### `FullSharedProps`

```ts
export type FullSharedProps = GeneratedSharedProps & SharedProps & { [key: string]: unknown }
```

Full shared props = generated + user-defined

#### `ComponentName`

```ts
export type ComponentName = keyof PageProps
```

Component name union type

#### `InertiaPageProps`

```ts
export type InertiaPageProps<C extends ComponentName> = PageProps[C]
```

Type-safe props for a specific component

#### `PagePropsFor`

```ts
export type PagePropsFor<C extends ComponentName> = PageProps[C]
```

Get props type for a specific page component

## `litestar-vite-plugin/virtual`

**Package Subpath**: `./virtual` · **Types**: `./dist/js/virtual.d.ts` · **Source**: `src/js/src/virtual.d.ts`

Type declarations for litestar-vite virtual modules.

| Export | Kind | Description |
| :--- | :--- | :--- |
| `StaticProps` | `interface` | Static props configured in Python ViteConfig.static_props. |
| `virtual:litestar-static-props` | `module` | Vite virtual module exposing static props configured in Python `ViteConfig.static_props`. |

#### `StaticProps`

```ts
export interface StaticProps
```

Static props configured in Python ViteConfig.static_props.

#### `virtual:litestar-static-props`

```ts
declare module "virtual:litestar-static-props"
```

Vite virtual module exposing static props configured in Python `ViteConfig.static_props`.
