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
 *       types: {
 *         enabled: true,
 *         output: 'src/lib/api',
 *       },
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

import { createTypeGenerationPlugin } from "./shared/create-type-gen-plugin.js"

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
   * Recommended to use SvelteKit's $lib alias path.
   *
   * @default 'src/lib/api'
   */
  output?: string

  /**
   * Path where the OpenAPI schema is exported by Litestar.
   *
   * @default 'openapi.json'
   */
  openapiPath?: string

  /**
   * Path where route metadata is exported by Litestar.
   *
   * @default 'routes.json'
   */
  routesPath?: string

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
}

/**
 * Resolve configuration with defaults.
 */
/**
 * Types configuration from Python runtime config.
 */
interface PythonTypesConfig {
  enabled?: boolean
  output?: string
  openapiPath?: string
  routesPath?: string
  generateZod?: boolean
  generateSdk?: boolean
}

function resolveConfig(config: LitestarSvelteKitConfig = {}): ResolvedConfig {
  const runtimeConfigPath = process.env.LITESTAR_VITE_CONFIG_PATH
  let hotFile: string | undefined
  let proxyMode: "vite" | "direct" | "proxy" | null = "vite"
  let port: number | undefined
  let pythonTypesConfig: PythonTypesConfig | undefined

  // Read port from VITE_PORT environment variable (set by Python)
  const envPort = process.env.VITE_PORT
  if (envPort) {
    port = Number.parseInt(envPort, 10)
    if (Number.isNaN(port)) {
      port = undefined
    }
  }

  let pythonExecutor: "node" | "bun" | "deno" | "yarn" | "pnpm" | undefined

  if (runtimeConfigPath && fs.existsSync(runtimeConfigPath)) {
    try {
      const json = JSON.parse(fs.readFileSync(runtimeConfigPath, "utf-8")) as {
        bundleDir?: string
        hotFile?: string
        proxyMode?: "vite" | "direct" | "proxy" | null
        port?: number
        executor?: "node" | "bun" | "deno" | "yarn" | "pnpm"
        types?: PythonTypesConfig | null
      }
      const bundleDir = json.bundleDir ?? "public"
      const hot = json.hotFile ?? "hot"
      hotFile = path.resolve(process.cwd(), bundleDir, hot)
      proxyMode = json.proxyMode ?? "vite"
      // Runtime config port takes precedence over VITE_PORT env
      if (json.port !== undefined) {
        port = json.port
      }
      pythonExecutor = json.executor
      // Read types config from Python
      if (json.types) {
        pythonTypesConfig = json.types
      }
    } catch {
      hotFile = undefined
    }
  }

  let typesConfig: Required<SvelteKitTypesConfig> | false = false

  // Priority: explicit Vite config > Python runtime config > disabled
  if (config.types === true) {
    // Explicit `types: true` in Vite config - use Python config if available, else defaults
    typesConfig = {
      enabled: true,
      output: pythonTypesConfig?.output ?? "src/lib/api",
      openapiPath: pythonTypesConfig?.openapiPath ?? "openapi.json",
      routesPath: pythonTypesConfig?.routesPath ?? "routes.json",
      generateZod: pythonTypesConfig?.generateZod ?? false,
      generateSdk: pythonTypesConfig?.generateSdk ?? true,
      debounce: 300,
    }
  } else if (typeof config.types === "object" && config.types !== null) {
    // Explicit types object in Vite config - merge with Python config
    typesConfig = {
      enabled: config.types.enabled ?? true,
      output: config.types.output ?? pythonTypesConfig?.output ?? "src/lib/api",
      openapiPath: config.types.openapiPath ?? pythonTypesConfig?.openapiPath ?? "openapi.json",
      routesPath: config.types.routesPath ?? pythonTypesConfig?.routesPath ?? "routes.json",
      generateZod: config.types.generateZod ?? pythonTypesConfig?.generateZod ?? false,
      generateSdk: config.types.generateSdk ?? pythonTypesConfig?.generateSdk ?? true,
      debounce: config.types.debounce ?? 300,
    }
  } else if (config.types !== false && pythonTypesConfig?.enabled) {
    // No explicit Vite config but Python has types enabled - use Python config
    typesConfig = {
      enabled: true,
      output: pythonTypesConfig.output ?? "src/lib/api",
      openapiPath: pythonTypesConfig.openapiPath ?? "openapi.json",
      routesPath: pythonTypesConfig.routesPath ?? "routes.json",
      generateZod: pythonTypesConfig.generateZod ?? false,
      generateSdk: pythonTypesConfig.generateSdk ?? true,
      debounce: 300,
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
 *         output: 'src/lib/api',
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
 * import type { User } from '$lib/api/types.gen';
 * import { route } from '$lib/api/routes';
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
            // Normalize IPv6 addresses to localhost, and wrap any remaining IPv6 in brackets
            let host = address.address
            if (host === "::" || host === "::1") {
              host = "localhost"
            } else if (host.includes(":")) {
              // IPv6 address - wrap in brackets for URL
              host = `[${host}]`
            }
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
      createTypeGenerationPlugin(config.types, {
        frameworkName: "litestar-sveltekit",
        pluginName: "litestar-sveltekit-types",
        clientPlugin: "@hey-api/client-fetch",
        executor: config.executor,
      }),
    )
  }

  return plugins
}

// Default export for simpler imports
export default litestarSvelteKit
