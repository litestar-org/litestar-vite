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

import { resolveInstallHint, resolvePackageExecutor } from "./install-hint.js"
import { debounce } from "./shared/debounce.js"

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
    plugins.push(createTypeGenerationPlugin(config.types, config.executor))
  }

  return plugins
}

/**
 * Generate TypeScript route types from routes.json metadata.
 */
async function emitRouteTypes(routesPath: string, outputDir: string): Promise<void> {
  const contents = await fs.promises.readFile(routesPath, "utf-8")
  const json = JSON.parse(contents)

  const outDir = path.resolve(process.cwd(), outputDir)
  await fs.promises.mkdir(outDir, { recursive: true })
  const outFile = path.join(outDir, "routes.ts")

  const banner = `// AUTO-GENERATED by litestar-vite. Do not edit.
/* eslint-disable */

`

  // Extract just the routes object from the full metadata
  const routesData = json.routes || json

  // Build route name union type and route map
  const routeNames = Object.keys(routesData)
  const routeNameType = routeNames.length > 0 ? routeNames.map((n) => `"${n}"`).join(" | ") : "never"

  // Build parameter types for each route
  const routeParamTypes: string[] = []
  for (const [name, data] of Object.entries(routesData)) {
    const routeData = data as { uri: string; parameters?: string[]; parameterTypes?: Record<string, string> }
    if (routeData.parameters && routeData.parameters.length > 0) {
      const params = routeData.parameters.map((p) => `${p}: string | number`).join("; ")
      routeParamTypes.push(`  "${name}": { ${params} }`)
    } else {
      routeParamTypes.push(`  "${name}": Record<string, never>`)
    }
  }

  const body = `/**
 * AUTO-GENERATED by litestar-vite.
 *
 * Exports:
 * - routesMeta: full route metadata
 * - routes: name -> uri map
 * - serverRoutes: alias of routes for clarity in apps
 * - route(): type-safe URL generator
 * - hasRoute(): type guard
 * - csrf helpers re-exported from litestar-vite-plugin/helpers
 *
 * @see https://litestar-vite.litestar.dev/
 */
export const routesMeta = ${JSON.stringify(json, null, 2)} as const

/**
 * Route name to URI mapping.
 */
export const routes = ${JSON.stringify(Object.fromEntries(Object.entries(routesData).map(([name, data]) => [name, (data as { uri: string }).uri])), null, 2)} as const

/**
 * Alias for server-injected route map (more descriptive for consumers).
 */
export const serverRoutes = routes

/**
 * All available route names.
 */
export type RouteName = ${routeNameType}

/**
 * Parameter types for each route.
 */
export interface RouteParams {
${routeParamTypes.join("\n")}
}

/**
 * Generate a URL for a named route with type-safe parameters.
 *
 * @param name - The route name
 * @param params - Route parameters (required if route has path parameters)
 * @returns The generated URL
 *
 * @example
 * \`\`\`ts
 * import { route } from '@/generated/routes'
 *
 * // Route without parameters
 * route('home')  // "/"
 *
 * // Route with parameters
 * route('user:detail', { user_id: 123 })  // "/users/123"
 * \`\`\`
 */
export function route<T extends RouteName>(
  name: T,
  ...args: RouteParams[T] extends Record<string, never> ? [] : [params: RouteParams[T]]
): string {
  let uri = routes[name] as string
  const params = args[0] as Record<string, string | number> | undefined

  if (params) {
    for (const [key, value] of Object.entries(params)) {
      // Handle both {param} and {param:type} syntax
      uri = uri.replace(new RegExp(\`\\\\{$\{key}(?::[^}]+)?\\\\}\`, "g"), String(value))
    }
  }

  return uri
}

/**
 * Check if a route name exists.
 */
export function hasRoute(name: string): name is RouteName {
  return name in routes
}

declare global {
  interface Window {
    /**
     * Fully-typed route metadata injected by Litestar.
     */
    __LITESTAR_ROUTES__?: typeof routesMeta
    /**
     * Simple route map (name -> uri) for legacy consumers.
     */
    routes?: typeof routes
    serverRoutes?: typeof serverRoutes
  }
  // eslint-disable-next-line no-var
  var routes: typeof routes | undefined
  var serverRoutes: typeof serverRoutes | undefined
}

// Re-export helper functions from litestar-vite-plugin
// These work with the routes defined above
export { getCsrfToken, csrfHeaders, csrfFetch } from "litestar-vite-plugin/helpers"
`

  await fs.promises.writeFile(outFile, `${banner}${body}`, "utf-8")
}

/**
 * Create the type generation plugin for SvelteKit.
 */
function createTypeGenerationPlugin(typesConfig: Required<SvelteKitTypesConfig>, executor?: string): Plugin {
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

      // Check for user config file first
      const projectRoot = process.cwd()
      const candidates = [path.resolve(projectRoot, "openapi-ts.config.ts"), path.resolve(projectRoot, "hey-api.config.ts"), path.resolve(projectRoot, ".hey-api.config.ts")]
      const configPath = candidates.find((p) => fs.existsSync(p)) || null

      let args: string[]
      if (configPath) {
        // Use user config file
        console.log(colors.cyan("[litestar-sveltekit]"), colors.dim("Using config:"), configPath)
        args = ["@hey-api/openapi-ts", "--file", configPath]
      } else {
        // Build args with proper plugins
        args = ["@hey-api/openapi-ts", "-i", typesConfig.openapiPath, "-o", typesConfig.output]

        const plugins = ["@hey-api/typescript", "@hey-api/schemas"]
        if (typesConfig.generateSdk) {
          plugins.push("@hey-api/sdk", "@hey-api/client-fetch")
        }
        if (typesConfig.generateZod) {
          plugins.push("zod")
        }
        if (plugins.length) {
          args.push("--plugins", ...plugins)
        }
      }

      await execAsync(resolvePackageExecutor(args.join(" "), executor), {
        cwd: projectRoot,
      })

      // Also generate route types if routes.json exists
      const routesPath = path.resolve(process.cwd(), typesConfig.routesPath)
      if (fs.existsSync(routesPath)) {
        await emitRouteTypes(routesPath, typesConfig.output)
      }

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

    async buildStart() {
      // Run type generation at build start if enabled and openapi.json exists
      if (typesConfig.enabled) {
        const openapiPath = path.resolve(process.cwd(), typesConfig.openapiPath)
        if (fs.existsSync(openapiPath)) {
          await runTypeGeneration()
        }
      }
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
