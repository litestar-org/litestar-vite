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

import { exec } from "node:child_process"
import fs from "node:fs"
import path from "node:path"
import { promisify } from "node:util"
import colors from "picocolors"
import type { Plugin, ViteDevServer } from "vite"

import { resolveInstallHint } from "./install-hint.js"

const execAsync = promisify(exec)

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
}

/**
 * Resolve configuration with defaults.
 */
function resolveConfig(config: LitestarSvelteKitConfig = {}): ResolvedConfig {
  const runtimeConfigPath = process.env.LITESTAR_VITE_CONFIG_PATH
  let hotFile: string | undefined
  let proxyMode: "vite" | "direct" | "proxy" | null = "vite"
  let port: number | undefined

  // Read port from VITE_PORT environment variable (set by Python)
  const envPort = process.env.VITE_PORT
  if (envPort) {
    port = Number.parseInt(envPort, 10)
    if (Number.isNaN(port)) {
      port = undefined
    }
  }

  if (runtimeConfigPath && fs.existsSync(runtimeConfigPath)) {
    try {
      const json = JSON.parse(fs.readFileSync(runtimeConfigPath, "utf-8")) as {
        bundleDir?: string
        hotFile?: string
        proxyMode?: "vite" | "direct" | "proxy" | null
        port?: number
      }
      const bundleDir = json.bundleDir ?? "public"
      const hot = json.hotFile ?? "hot"
      hotFile = path.resolve(process.cwd(), bundleDir, hot)
      proxyMode = json.proxyMode ?? "vite"
      // Runtime config port takes precedence over VITE_PORT env
      if (json.port !== undefined) {
        port = json.port
      }
    } catch {
      hotFile = undefined
    }
  }

  let typesConfig: Required<SvelteKitTypesConfig> | false = false

  if (config.types === true) {
    typesConfig = {
      enabled: true,
      output: "src/lib/api",
      openapiPath: "openapi.json",
      routesPath: "routes.json",
      generateZod: false,
      debounce: 300,
    }
  } else if (typeof config.types === "object" && config.types !== null) {
    typesConfig = {
      enabled: config.types.enabled ?? true,
      output: config.types.output ?? "src/lib/api",
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
    hotFile,
    proxyMode,
    port,
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
            const host = address.address === "::" ? "localhost" : address.address
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
    plugins.push(createTypeGenerationPlugin(config.types))
  }

  return plugins
}

/**
 * Create the type generation plugin for SvelteKit.
 */
function createTypeGenerationPlugin(typesConfig: Required<SvelteKitTypesConfig>): Plugin {
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
        console.log(colors.cyan("[litestar-sveltekit]"), colors.yellow("OpenAPI schema not found:"), typesConfig.openapiPath)
        return false
      }

      console.log(colors.cyan("[litestar-sveltekit]"), colors.dim("Generating TypeScript types..."))

      const args = ["@hey-api/openapi-ts", "-i", typesConfig.openapiPath, "-o", typesConfig.output]

      if (typesConfig.generateZod) {
        args.push("--plugins", "@hey-api/schemas", "@hey-api/types")
      }

      await execAsync(`npx ${args.join(" ")}`, {
        cwd: process.cwd(),
      })

      const duration = Date.now() - startTime
      console.log(colors.cyan("[litestar-sveltekit]"), colors.green("Types generated"), colors.dim(`in ${duration}ms`))

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
        console.log(colors.cyan("[litestar-sveltekit]"), colors.yellow("@hey-api/openapi-ts not installed"), "- run:", resolveInstallHint())
      } else {
        console.error(colors.cyan("[litestar-sveltekit]"), colors.red("Type generation failed:"), message)
      }
      return false
    } finally {
      isGenerating = false
    }
  }

  const debouncedRunTypeGeneration = debounce(runTypeGeneration, typesConfig.debounce)

  return {
    name: "litestar-sveltekit-types",
    enforce: "pre",

    configureServer(devServer) {
      server = devServer
      console.log(colors.cyan("[litestar-sveltekit]"), colors.dim("Watching for schema changes:"), colors.yellow(typesConfig.openapiPath))
    },

    handleHotUpdate({ file }) {
      if (!typesConfig.enabled) {
        return
      }

      const relativePath = path.relative(process.cwd(), file)
      const openapiPath = typesConfig.openapiPath.replace(/^\.\//, "")
      const routesPath = typesConfig.routesPath.replace(/^\.\//, "")

      if (relativePath === openapiPath || relativePath === routesPath || file.endsWith(openapiPath) || file.endsWith(routesPath)) {
        console.log(colors.cyan("[litestar-sveltekit]"), colors.dim("Schema changed:"), colors.yellow(relativePath))
        debouncedRunTypeGeneration()
      }
    },
  }
}

// Default export for simpler imports
export default litestarSvelteKit
