/**
 * SvelteKit integration for Litestar-Vite.
 *
 * This module provides a Vite plugin specifically designed to work alongside
 * SvelteKit's own Vite plugin. It enables:
 * - API proxy configuration for dev server
 * - Type generation integration (shares @hey-api/openapi-ts output)
 * - Seamless integration with SvelteKit's load functions
 *
 * @example
 * ```typescript
 * // vite.config.ts
 * import { sveltekit } from '@sveltejs/kit/vite';
 * import { litestarSvelteKit } from 'litestar-vite-plugin/sveltekit';
 * import { defineConfig } from 'vite';
 *
 * export default defineConfig({
 *   plugins: [
 *     litestarSvelteKit({
 *       apiProxy: 'http://localhost:8000',
 *       types: true,
 *     }),
 *     sveltekit(),  // SvelteKit plugin comes after
 *   ],
 * });
 * ```
 *
 * @module
 */

import fs from "node:fs"
import path from "node:path"
import colors from "picocolors"
import type { Plugin } from "vite"
import { type BridgeTypesConfig, readBridgeConfig } from "./shared/bridge-schema.js"
import { DEBOUNCE_MS } from "./shared/constants.js"
import { normalizeHost, resolveHotFilePath } from "./shared/network.js"
import { createLitestarTypeGenPlugin } from "./shared/typegen-plugin.js"

/**
 * Configuration for TypeScript type generation in SvelteKit.
 */
export interface SvelteKitTypesConfig {
  /**
   * Enable type generation.
   *
   * @default false
   */
  enabled?: boolean

  /**
   * Path to output generated TypeScript types.
   * Relative to the SvelteKit project root.
   *
   * @default 'src/lib/generated'
   */
  output?: string

  /**
   * Path where the OpenAPI schema is exported by Litestar.
   *
   * @default `${output}/openapi.json`
   */
  openapiPath?: string

  /**
   * Path where route metadata is exported by Litestar.
   *
   * @default `${output}/routes.json`
   */
  routesPath?: string

  /**
   * Optional path for the generated schemas.ts helper file.
   *
   * @default `${output}/schemas.ts`
   */
  schemasTsPath?: string

  /**
   * Path where Inertia page props metadata is exported by Litestar.
   *
   * @default `${output}/inertia-pages.json`
   */
  pagePropsPath?: string

  /**
   * Generate Zod schemas in addition to TypeScript types.
   *
   * @default false
   */
  generateZod?: boolean

  /**
   * Generate SDK client functions for API calls.
   *
   * @default true
   */
  generateSdk?: boolean

  /**
   * Generate typed routes.ts from routes.json metadata.
   *
   * @default true
   */
  generateRoutes?: boolean

  /**
   * Generate Inertia page props types from inertia-pages.json metadata.
   *
   * @default true
   */
  generatePageProps?: boolean

  /**
   * Generate schemas.ts with ergonomic form/response type helpers.
   *
   * @default true
   */
  generateSchemas?: boolean

  /**
   * Register route() globally on window object.
   *
   * @default false
   */
  globalRoute?: boolean

  /**
   * Debounce time in milliseconds for type regeneration.
   *
   * @default 300
   */
  debounce?: number
}

/**
 * Configuration options for the Litestar SvelteKit integration.
 */
export interface LitestarSvelteKitConfig {
  /**
   * URL of the Litestar API backend for proxying requests during development.
   *
   * @example 'http://localhost:8000'
   * @default 'http://localhost:8000'
   */
  apiProxy?: string

  /**
   * API route prefix to proxy to the Litestar backend.
   * Requests matching this prefix will be forwarded to the apiProxy URL.
   *
   * @example '/api'
   * @default '/api'
   */
  apiPrefix?: string

  /**
   * Enable and configure TypeScript type generation.
   *
   * When set to `true`, enables type generation with default settings.
   * When set to a SvelteKitTypesConfig object, enables type generation with custom settings.
   *
   * @default false
   */
  types?: boolean | SvelteKitTypesConfig

  /**
   * Enable verbose logging for debugging.
   *
   * @default false
   */
  verbose?: boolean

  /**
   * JavaScript runtime executor for package commands.
   * Used when running tools like @hey-api/openapi-ts.
   *
   * @default undefined (uses LITESTAR_VITE_RUNTIME env or 'node')
   */
  executor?: "node" | "bun" | "deno" | "yarn" | "pnpm"
}

/**
 * Resolved configuration with all defaults applied.
 */
interface ResolvedConfig {
  apiProxy: string
  apiPrefix: string
  types: Required<SvelteKitTypesConfig> | false
  verbose: boolean
  hotFile?: string
  proxyMode: "vite" | "direct" | "proxy" | null
  /** Port for Vite dev server (from VITE_PORT env or runtime config) */
  port?: number
  /** JavaScript runtime executor for package commands */
  executor?: "node" | "bun" | "deno" | "yarn" | "pnpm"
  /** Whether .litestar.json was found */
  hasPythonConfig: boolean
}

/**
 * Resolve configuration with defaults.
 */
/**
 * Types configuration from Python runtime config.
 */
function resolveConfig(config: LitestarSvelteKitConfig = {}): ResolvedConfig {
  let hotFile: string | undefined
  let proxyMode: "vite" | "direct" | "proxy" | null = "vite"
  let port: number | undefined
  let pythonTypesConfig: BridgeTypesConfig | undefined
  let hasPythonConfig = false

  // Read port from VITE_PORT environment variable (set by Python)
  const envPort = process.env.VITE_PORT
  if (envPort) {
    port = Number.parseInt(envPort, 10)
    if (Number.isNaN(port)) {
      port = undefined
    }
  }

  let pythonExecutor: "node" | "bun" | "deno" | "yarn" | "pnpm" | undefined

  const runtime = readBridgeConfig()
  if (runtime) {
    hasPythonConfig = true
    const hot = runtime.hotFile
    hotFile = resolveHotFilePath(runtime.bundleDir, hot)
    proxyMode = runtime.proxyMode
    port = runtime.port
    pythonExecutor = runtime.executor
    if (runtime.types) {
      pythonTypesConfig = runtime.types
    }
  }

  let typesConfig: Required<SvelteKitTypesConfig> | false = false

  const defaultTypesOutput = "src/lib/generated"
  const buildTypeDefaults = (output: string) => ({
    openapiPath: path.join(output, "openapi.json"),
    routesPath: path.join(output, "routes.json"),
    pagePropsPath: path.join(output, "inertia-pages.json"),
    schemasTsPath: path.join(output, "schemas.ts"),
  })

  // Priority: explicit Vite config > Python runtime config > disabled
  if (config.types === true) {
    // Explicit `types: true` in Vite config - use Python config if available, else defaults
    const output = pythonTypesConfig?.output ?? defaultTypesOutput
    const defaults = buildTypeDefaults(output)
    typesConfig = {
      enabled: true,
      output,
      openapiPath: pythonTypesConfig?.openapiPath ?? defaults.openapiPath,
      routesPath: pythonTypesConfig?.routesPath ?? defaults.routesPath,
      pagePropsPath: pythonTypesConfig?.pagePropsPath ?? defaults.pagePropsPath,
      schemasTsPath: pythonTypesConfig?.schemasTsPath ?? defaults.schemasTsPath,
      generateZod: pythonTypesConfig?.generateZod ?? false,
      generateSdk: pythonTypesConfig?.generateSdk ?? true,
      generateRoutes: pythonTypesConfig?.generateRoutes ?? true,
      generatePageProps: pythonTypesConfig?.generatePageProps ?? true,
      generateSchemas: pythonTypesConfig?.generateSchemas ?? true,
      globalRoute: pythonTypesConfig?.globalRoute ?? false,
      debounce: DEBOUNCE_MS,
    }
  } else if (typeof config.types === "object" && config.types !== null) {
    // Explicit types object in Vite config - merge with Python config
    const userProvidedOutput = Object.hasOwn(config.types, "output")
    const output = config.types.output ?? pythonTypesConfig?.output ?? defaultTypesOutput
    const defaults = buildTypeDefaults(output)
    const openapiFallback = userProvidedOutput ? defaults.openapiPath : (pythonTypesConfig?.openapiPath ?? defaults.openapiPath)
    const routesFallback = userProvidedOutput ? defaults.routesPath : (pythonTypesConfig?.routesPath ?? defaults.routesPath)
    const pagePropsFallback = userProvidedOutput ? defaults.pagePropsPath : (pythonTypesConfig?.pagePropsPath ?? defaults.pagePropsPath)
    const schemasFallback = userProvidedOutput ? defaults.schemasTsPath : (pythonTypesConfig?.schemasTsPath ?? defaults.schemasTsPath)

    typesConfig = {
      enabled: config.types.enabled ?? true,
      output,
      openapiPath: config.types.openapiPath ?? openapiFallback,
      routesPath: config.types.routesPath ?? routesFallback,
      pagePropsPath: config.types.pagePropsPath ?? pagePropsFallback,
      schemasTsPath: config.types.schemasTsPath ?? schemasFallback,
      generateZod: config.types.generateZod ?? pythonTypesConfig?.generateZod ?? false,
      generateSdk: config.types.generateSdk ?? pythonTypesConfig?.generateSdk ?? true,
      generateRoutes: config.types.generateRoutes ?? pythonTypesConfig?.generateRoutes ?? true,
      generatePageProps: config.types.generatePageProps ?? pythonTypesConfig?.generatePageProps ?? true,
      generateSchemas: config.types.generateSchemas ?? pythonTypesConfig?.generateSchemas ?? true,
      globalRoute: config.types.globalRoute ?? pythonTypesConfig?.globalRoute ?? false,
      debounce: config.types.debounce ?? DEBOUNCE_MS,
    }
  } else if (config.types !== false && pythonTypesConfig?.enabled) {
    // No explicit Vite config but Python has types enabled - use Python config
    const output = pythonTypesConfig.output ?? defaultTypesOutput
    const defaults = buildTypeDefaults(output)
    typesConfig = {
      enabled: true,
      output,
      openapiPath: pythonTypesConfig.openapiPath ?? defaults.openapiPath,
      routesPath: pythonTypesConfig.routesPath ?? defaults.routesPath,
      pagePropsPath: pythonTypesConfig.pagePropsPath ?? defaults.pagePropsPath,
      schemasTsPath: pythonTypesConfig.schemasTsPath ?? defaults.schemasTsPath,
      generateZod: pythonTypesConfig.generateZod ?? false,
      generateSdk: pythonTypesConfig.generateSdk ?? true,
      generateRoutes: pythonTypesConfig.generateRoutes ?? true,
      generatePageProps: pythonTypesConfig.generatePageProps ?? true,
      generateSchemas: pythonTypesConfig.generateSchemas ?? true,
      globalRoute: pythonTypesConfig.globalRoute ?? false,
      debounce: DEBOUNCE_MS,
    }
  }

  return {
    apiProxy: config.apiProxy ?? "http://localhost:8000",
    apiPrefix: config.apiPrefix ?? "/api",
    types: typesConfig,
    verbose: config.verbose ?? false,
    hotFile,
    proxyMode,
    port,
    executor: config.executor ?? pythonExecutor,
    hasPythonConfig,
  }
}

/**
 * Litestar integration plugin for SvelteKit.
 *
 * This plugin should be added BEFORE the sveltekit() plugin in your vite.config.ts.
 * It provides API proxying during development and integrates type generation.
 *
 * @param userConfig - Configuration options for the integration
 * @returns A Vite plugin array
 *
 * @example
 * ```typescript
 * // vite.config.ts
 * import { sveltekit } from '@sveltejs/kit/vite';
 * import { litestarSvelteKit } from 'litestar-vite-plugin/sveltekit';
 * import { defineConfig } from 'vite';
 *
 * export default defineConfig({
 *   plugins: [
 *     litestarSvelteKit({
 *       apiProxy: 'http://localhost:8000',
 *       apiPrefix: '/api',
 *       types: {
 *         enabled: true,
 *         output: 'src/lib/generated',
 *         generateZod: true,
 *       },
 *     }),
 *     sveltekit(),
 *   ],
 * });
 * ```
 *
 * @example Using with SvelteKit load functions
 * ```typescript
 * // src/routes/users/[id]/+page.ts
 * import type { PageLoad } from './$types';
 * import type { User } from '$lib/generated/api/types.gen';
 * import { route } from '$lib/generated/routes';
 *
 * export const load: PageLoad = async ({ params, fetch }) => {
 *   const response = await fetch(route('users.show', { id: params.id }));
 *   const user: User = await response.json();
 *   return { user };
 * };
 * ```
 */
export function litestarSvelteKit(userConfig: LitestarSvelteKitConfig = {}): Plugin[] {
  const config = resolveConfig(userConfig)
  const plugins: Plugin[] = []

  // Main plugin for proxy and logging
  plugins.push({
    name: "litestar-sveltekit",
    enforce: "pre",

    config() {
      return {
        server: {
          // Force IPv4 binding for consistency with Python proxy configuration
          // Without this, SvelteKit might bind to IPv6 localhost which the proxy can't reach
          host: "127.0.0.1",
          // Set the port from Python config/env to ensure SvelteKit uses the expected port
          // strictPort: true prevents SvelteKit from auto-incrementing to a different port
          ...(config.port !== undefined
            ? {
                port: config.port,
                strictPort: true,
              }
            : {}),
          proxy: {
            [config.apiPrefix]: {
              target: config.apiProxy,
              changeOrigin: true,
              secure: false,
            },
          },
        },
      }
    },

    configureServer(server) {
      if (config.verbose) {
        server.middlewares.use((req, _res, next) => {
          if (req.url?.startsWith(config.apiPrefix)) {
            console.log(colors.cyan("[litestar-sveltekit]"), `Proxying: ${req.method} ${req.url}`)
          }
          next()
        })
      }

      // Always write hotfile - proxy mode needs it for dynamic target discovery
      if (config.hotFile) {
        const hotFile = config.hotFile

        server.httpServer?.once("listening", () => {
          const address = server.httpServer?.address()
          if (address && typeof address === "object" && "port" in address) {
            const host = normalizeHost(address.address)
            const url = `http://${host}:${address.port}`
            fs.mkdirSync(path.dirname(hotFile), { recursive: true })
            fs.writeFileSync(hotFile, url)
            if (config.verbose) {
              console.log(colors.cyan("[litestar-sveltekit]"), colors.dim(`Hotfile written: ${hotFile} -> ${url}`))
            }
          }
        })
      }

      // Log startup info
      server.httpServer?.once("listening", () => {
        setTimeout(() => {
          console.log("")
          console.log(`  ${colors.cyan("[litestar-sveltekit]")} ${colors.green("Integration active")}`)
          console.log(`  ${colors.dim("├─")} API Proxy: ${colors.yellow(config.apiProxy)}`)
          console.log(`  ${colors.dim("├─")} API Prefix: ${colors.yellow(config.apiPrefix)}`)
          if (config.types !== false && config.types.enabled) {
            console.log(`  ${colors.dim("└─")} Types Output: ${colors.yellow(config.types.output)}`)
          } else {
            console.log(`  ${colors.dim("└─")} Types: ${colors.dim("disabled")}`)
          }
          console.log("")
        }, 100)
      })
    },
  })

  // Type generation plugin (if enabled)
  if (config.types !== false && config.types.enabled) {
    plugins.push(
      createLitestarTypeGenPlugin(config.types, {
        pluginName: "litestar-sveltekit-types",
        frameworkName: "litestar-sveltekit",
        sdkClientPlugin: "@hey-api/client-fetch",
        executor: config.executor,
        hasPythonConfig: config.hasPythonConfig,
      }),
    )
  }

  return plugins
}

// Default export for simpler imports
export default litestarSvelteKit
