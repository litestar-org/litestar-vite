/**
 * Nuxt module for Litestar-Vite.
 *
 * This module provides seamless integration between Nuxt 3+ and Litestar backend.
 * It enables:
 * - API proxy configuration for dev server
 * - Type generation integration (shares @hey-api/openapi-ts output)
 * - Server-side and client-side API access patterns
 *
 * @example
 * ```typescript
 * // nuxt.config.ts
 * export default defineNuxtConfig({
 *   modules: ['litestar-vite-plugin/nuxt'],
 *   litestar: {
 *     apiProxy: 'http://localhost:8000',
 *     apiPrefix: '/api',
 *     types: {
 *       enabled: true,
 *       output: 'types/api',
 *     },
 *   },
 * });
 * ```
 *
 * @module
 */

import { exec } from "node:child_process"
import fs from "node:fs"
import path from "node:path"
import { promisify } from "node:util"
import colors from "picocolors"
import type { Plugin, ViteDevServer } from "vite"

import { resolveInstallHint } from "./install-hint"

const execAsync = promisify(exec)

/**
 * Configuration for TypeScript type generation in Nuxt.
 */
export interface NuxtTypesConfig {
  /**
   * Enable type generation.
   *
   * @default false
   */
  enabled?: boolean

  /**
   * Path to output generated TypeScript types.
   * Relative to the Nuxt project root.
   *
   * @default 'types/api'
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
   * Debounce time in milliseconds for type regeneration.
   *
   * @default 300
   */
  debounce?: number
}

/**
 * Configuration options for the Litestar Nuxt module.
 */
export interface LitestarNuxtConfig {
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
   * When set to a NuxtTypesConfig object, enables type generation with custom settings.
   *
   * @default false
   */
  types?: boolean | NuxtTypesConfig

  /**
   * Enable verbose logging for debugging.
   *
   * @default false
   */
  verbose?: boolean
}

/**
 * Resolved configuration with all defaults applied.
 */
interface ResolvedNuxtConfig {
  apiProxy: string
  apiPrefix: string
  types: Required<NuxtTypesConfig> | false
  verbose: boolean
}

/**
 * Resolve configuration with defaults.
 */
function resolveConfig(config: LitestarNuxtConfig = {}): ResolvedNuxtConfig {
  let typesConfig: Required<NuxtTypesConfig> | false = false

  if (config.types === true) {
    typesConfig = {
      enabled: true,
      output: "types/api",
      openapiPath: "openapi.json",
      routesPath: "routes.json",
      generateZod: false,
      debounce: 300,
    }
  } else if (typeof config.types === "object" && config.types !== null) {
    typesConfig = {
      enabled: config.types.enabled ?? true,
      output: config.types.output ?? "types/api",
      openapiPath: config.types.openapiPath ?? "openapi.json",
      routesPath: config.types.routesPath ?? "routes.json",
      generateZod: config.types.generateZod ?? false,
      debounce: config.types.debounce ?? 300,
    }
  }

  return {
    apiProxy: config.apiProxy ?? "http://localhost:8000",
    apiPrefix: config.apiPrefix ?? "/api",
    types: typesConfig,
    verbose: config.verbose ?? false,
  }
}

/**
 * Create a debounced function.
 */
function debounce<T extends (...args: unknown[]) => void>(func: T, wait: number): T {
  let timeout: ReturnType<typeof setTimeout> | null = null
  return ((...args: unknown[]) => {
    if (timeout) {
      clearTimeout(timeout)
    }
    timeout = setTimeout(() => func(...args), wait)
  }) as T
}

/**
 * Create the Vite plugin for API proxying.
 */
function createProxyPlugin(config: ResolvedNuxtConfig): Plugin {
  return {
    name: "litestar-nuxt-proxy",
    config() {
      return {
        server: {
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
            console.log(colors.cyan("[litestar-nuxt]"), `Proxying: ${req.method} ${req.url}`)
          }
          next()
        })
      }

      server.httpServer?.once("listening", () => {
        setTimeout(() => {
          console.log("")
          console.log(`  ${colors.cyan("[litestar-nuxt]")} ${colors.green("Integration active")}`)
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
  }
}

/**
 * Create the type generation Vite plugin for Nuxt.
 */
function createTypeGenerationPlugin(typesConfig: Required<NuxtTypesConfig>): Plugin {
  let server: ViteDevServer | null = null
  let isGenerating = false

  async function runTypeGeneration(): Promise<boolean> {
    if (isGenerating) {
      return false
    }

    isGenerating = true
    const startTime = Date.now()

    try {
      const openapiPath = path.resolve(process.cwd(), typesConfig.openapiPath)
      if (!fs.existsSync(openapiPath)) {
        console.log(colors.cyan("[litestar-nuxt]"), colors.yellow("OpenAPI schema not found:"), typesConfig.openapiPath)
        return false
      }

      console.log(colors.cyan("[litestar-nuxt]"), colors.dim("Generating TypeScript types..."))

      const args = ["@hey-api/openapi-ts", "-i", typesConfig.openapiPath, "-o", typesConfig.output]

      if (typesConfig.generateZod) {
        args.push("--plugins", "@hey-api/schemas", "@hey-api/types")
      }

      await execAsync(`npx ${args.join(" ")}`, {
        cwd: process.cwd(),
      })

      const duration = Date.now() - startTime
      console.log(colors.cyan("[litestar-nuxt]"), colors.green("Types generated"), colors.dim(`in ${duration}ms`))

      // Notify HMR clients
      if (server) {
        server.ws.send({
          type: "custom",
          event: "litestar:types-updated",
          data: {
            output: typesConfig.output,
            timestamp: Date.now(),
          },
        })
      }

      return true
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error)
      if (message.includes("not found") || message.includes("ENOENT")) {
        console.log(colors.cyan("[litestar-nuxt]"), colors.yellow("@hey-api/openapi-ts not installed"), "- run:", resolveInstallHint())
      } else {
        console.error(colors.cyan("[litestar-nuxt]"), colors.red("Type generation failed:"), message)
      }
      return false
    } finally {
      isGenerating = false
    }
  }

  const debouncedRunTypeGeneration = debounce(runTypeGeneration, typesConfig.debounce)

  return {
    name: "litestar-nuxt-types",
    enforce: "pre",

    configureServer(devServer) {
      server = devServer
      console.log(colors.cyan("[litestar-nuxt]"), colors.dim("Watching for schema changes:"), colors.yellow(typesConfig.openapiPath))
    },

    handleHotUpdate({ file }) {
      if (!typesConfig.enabled) {
        return
      }

      const relativePath = path.relative(process.cwd(), file)
      const openapiPath = typesConfig.openapiPath.replace(/^\.\//, "")
      const routesPath = typesConfig.routesPath.replace(/^\.\//, "")

      if (relativePath === openapiPath || relativePath === routesPath || file.endsWith(openapiPath) || file.endsWith(routesPath)) {
        console.log(colors.cyan("[litestar-nuxt]"), colors.dim("Schema changed:"), colors.yellow(relativePath))
        debouncedRunTypeGeneration()
      }
    },
  }
}

/**
 * Litestar Vite plugins for Nuxt.
 *
 * This function returns an array of Vite plugins that can be added to Nuxt's
 * vite configuration. For the full Nuxt module experience, use the module
 * directly in your nuxt.config.ts.
 *
 * @param userConfig - Configuration options
 * @returns Array of Vite plugins
 *
 * @example Using as Vite plugins in nuxt.config.ts
 * ```typescript
 * import { litestarPlugins } from 'litestar-vite-plugin/nuxt';
 *
 * export default defineNuxtConfig({
 *   vite: {
 *     plugins: [
 *       ...litestarPlugins({
 *         apiProxy: 'http://localhost:8000',
 *         types: true,
 *       }),
 *     ],
 *   },
 * });
 * ```
 */
export function litestarPlugins(userConfig: LitestarNuxtConfig = {}): Plugin[] {
  const config = resolveConfig(userConfig)
  const plugins: Plugin[] = [createProxyPlugin(config)]

  if (config.types !== false && config.types.enabled) {
    plugins.push(createTypeGenerationPlugin(config.types))
  }

  return plugins
}

/**
 * Nuxt module definition for Litestar integration.
 *
 * This is a minimal module interface that can be used with Nuxt's module system.
 * For full type safety, install @nuxt/kit as a dev dependency.
 *
 * @example
 * ```typescript
 * // nuxt.config.ts
 * export default defineNuxtConfig({
 *   modules: ['litestar-vite-plugin/nuxt'],
 *   litestar: {
 *     apiProxy: 'http://localhost:8000',
 *     apiPrefix: '/api',
 *     types: {
 *       enabled: true,
 *       output: 'types/api',
 *     },
 *   },
 * });
 * ```
 *
 * @example Using generated types in a composable
 * ```typescript
 * // composables/useApi.ts
 * import type { User } from '~/types/api/types.gen';
 * import { route } from '~/types/api/routes';
 *
 * export async function useUser(id: string) {
 *   const { data } = await useFetch<User>(route('users.show', { id }));
 *   return data;
 * }
 * ```
 */
export const litestarModule = {
  meta: {
    name: "litestar-vite",
    configKey: "litestar",
    compatibility: {
      nuxt: ">=3.0.0",
    },
  },

  defaults: {
    apiProxy: "http://localhost:8000",
    apiPrefix: "/api",
    types: false,
    verbose: false,
  } satisfies LitestarNuxtConfig,

  /**
   * Setup function for the Nuxt module.
   * This is called by Nuxt when the module is loaded.
   */
  setup(userOptions: LitestarNuxtConfig, nuxt: { options: { vite: { plugins?: Plugin[] } } }) {
    const config = resolveConfig(userOptions)
    const plugins = litestarPlugins(config)

    // Add plugins to Nuxt's Vite config
    nuxt.options.vite = nuxt.options.vite || {}
    nuxt.options.vite.plugins = nuxt.options.vite.plugins || []
    nuxt.options.vite.plugins.push(...plugins)

    console.log(colors.cyan("[litestar-nuxt]"), "Module initialized")
  },
}

// Default export for Nuxt module system
export default litestarModule
