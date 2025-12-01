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

import { resolveInstallHint, resolvePackageExecutor } from "./install-hint.js"
import { debounce } from "./shared/debounce.js"

const execAsync = promisify(exec)

/**
 * Normalize a host address for use in URLs.
 * - Converts bind-all addresses (::, 0.0.0.0) to localhost
 * - Converts IPv6 localhost (::1) to localhost
 * - Wraps other IPv6 addresses in brackets for URL compatibility
 */
function normalizeHost(host: string): string {
  if (host === "::" || host === "::1" || host === "0.0.0.0") {
    return "localhost"
  }
  // If it contains ":" and isn't already bracketed, it's IPv6
  if (host.includes(":") && !host.startsWith("[")) {
    return `[${host}]`
  }
  return host
}

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
interface ResolvedNuxtConfig {
  apiProxy: string
  apiPrefix: string
  types: Required<NuxtTypesConfig> | false
  verbose: boolean
  hotFile?: string
  proxyMode: "vite" | "direct" | "proxy" | null
  /** Preferred dev server port (provided by Python via VITE_PORT) */
  devPort?: number
  /** JavaScript runtime executor for package commands */
  executor?: "node" | "bun" | "deno" | "yarn" | "pnpm"
}

/**
 * Resolve configuration with defaults.
 */
function resolveConfig(config: LitestarNuxtConfig = {}): ResolvedNuxtConfig {
  const runtimeConfigPath = process.env.LITESTAR_VITE_CONFIG_PATH
  let hotFile: string | undefined
  let proxyMode: "vite" | "direct" | "proxy" | null = "vite"
  let devPort: number | undefined

  // Read port from VITE_PORT environment variable (set by Python)
  const envPort = process.env.VITE_PORT
  if (envPort) {
    devPort = Number.parseInt(envPort, 10)
    if (Number.isNaN(devPort)) {
      devPort = undefined
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
      }
      const bundleDir = json.bundleDir ?? "public"
      const hot = json.hotFile ?? "hot"
      hotFile = path.resolve(process.cwd(), bundleDir, hot)
      proxyMode = json.proxyMode ?? "vite"
      // Runtime config port is the preferred dev server port
      if (json.port !== undefined) {
        devPort = json.port
      }
      pythonExecutor = json.executor
    } catch {
      hotFile = undefined
    }
  }

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
    hotFile,
    proxyMode,
    devPort,
    executor: config.executor ?? pythonExecutor,
  }
}

/**
 * Find a free port.
 */
async function getPort(): Promise<number> {
  return new Promise((resolve, reject) => {
    import("node:net").then(({ createServer }) => {
      const server = createServer()
      server.unref()
      server.on("error", reject)
      server.listen(0, () => {
        const address = server.address()
        const port = typeof address === "object" && address ? address.port : 0
        server.close(() => resolve(port))
      })
    })
  })
}

/**
 * Create the Vite plugin for API proxying.
 *
 * Port handling:
 * - Python (Litestar) auto-selects a free port and sets VITE_PORT + PORT env vars
 * - Nuxt/Nitro reads PORT from environment (set by Python before npm run dev)
 * - This plugin just configures the API proxy, not the server port
 */
function createProxyPlugin(config: ResolvedNuxtConfig): Plugin {
  let hmrPort = 0

  return {
    name: "litestar-nuxt-proxy",
    async config() {
      hmrPort = await getPort()
      // Note: Server port is controlled by PORT env var (set by Python)
      // We only configure the API proxy here
      return {
        server: {
          // Avoid HMR port collisions by letting Vite pick a free port for WS
          hmr: {
            port: hmrPort,
            host: "127.0.0.1",
            clientPort: config.devPort,
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

      // Write HMR hotfile
      if (config.hotFile) {
        const hmrHotFile = `${config.hotFile}.hmr`
        const hmrUrl = `http://127.0.0.1:${hmrPort}`
        fs.writeFileSync(hmrHotFile, hmrUrl)
        if (config.verbose) {
          console.log(colors.cyan("[litestar-nuxt]"), colors.dim(`HMR Hotfile written: ${hmrHotFile} -> ${hmrUrl}`))
        }
      }

      // Note: Hotfile is written by Nuxt's 'listen' hook in litestarNuxtModule,
      // which fires when Nitro's main HTTP server starts (not Vite's internal HMR server).
      // This Vite hook only handles the integration status banner.
      server.httpServer?.once("listening", () => {
        setTimeout(() => {
          console.log("")
          console.log(`  ${colors.cyan("[litestar-nuxt]")} ${colors.green("Integration active")}`)
          console.log(`  ${colors.dim("├─")} API Proxy: ${colors.yellow(config.apiProxy)}`)
          console.log(`  ${colors.dim("├─")} API Prefix: ${colors.yellow(config.apiPrefix)}`)
          console.log(`  ${colors.dim("├─")} HMR Port: ${colors.yellow(hmrPort)}`)
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
 * Create the type generation Vite plugin for Nuxt.
 */
function createTypeGenerationPlugin(typesConfig: Required<NuxtTypesConfig>, executor?: string): Plugin {
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
        args.push("--plugins", "zod", "@hey-api/typescript")
      }

      await execAsync(resolvePackageExecutor(args.join(" "), executor), {
        cwd: process.cwd(),
      })

      // Also generate route types if routes.json exists
      const routesPath = path.resolve(process.cwd(), typesConfig.routesPath)
      if (fs.existsSync(routesPath)) {
        await emitRouteTypes(routesPath, typesConfig.output)
      }

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
    plugins.push(createTypeGenerationPlugin(config.types, config.executor))
  }

  return plugins
}

/**
 * Nuxt module definition for Litestar integration.
 *
 * This is a function-based module that works with Nuxt's module system.
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

// Nuxt module interface (simple function-based)
interface NuxtModuleFunction {
  (userOptions: LitestarNuxtConfig, nuxt: NuxtContext): void | Promise<void>
  meta?: {
    name: string
    configKey: string
    compatibility?: { nuxt: string }
  }
  getOptions?: () => LitestarNuxtConfig
}

interface ListenInfo {
  url: string
  host: string
  port: number
}

interface NuxtContext {
  options: {
    vite: { plugins?: Plugin[] }
    runtimeConfig?: {
      public?: Record<string, unknown>
    }
    nitro?: {
      devProxy?: Record<string, unknown>
    }
    // The litestar config key from nuxt.config.ts
    litestar?: LitestarNuxtConfig
  }
  hook?: (name: string, fn: (...args: unknown[]) => void | Promise<void>) => void
}

/**
 * Litestar Nuxt module setup function.
 * This function is called by Nuxt when the module is loaded.
 */
function litestarNuxtModule(userOptions: LitestarNuxtConfig, nuxt: NuxtContext): void {
  // Merge options from nuxt.options.litestar (configKey) with inline options
  // The configKey in meta allows users to configure via nuxt.config.ts
  const nuxtConfigOptions = (nuxt.options as Record<string, unknown>).litestar as LitestarNuxtConfig | undefined
  const mergedOptions = { ...nuxtConfigOptions, ...userOptions }
  const config = resolveConfig(mergedOptions)
  const plugins = litestarPlugins(config)

  // Add plugins to Nuxt's Vite config
  nuxt.options.vite = nuxt.options.vite || {}
  nuxt.options.vite.plugins = nuxt.options.vite.plugins || []
  nuxt.options.vite.plugins.push(...plugins)

  // Expose API proxy URL in runtime config for server routes to use
  // Server routes can access this via useRuntimeConfig().public.apiProxy
  nuxt.options.runtimeConfig = nuxt.options.runtimeConfig || {}
  nuxt.options.runtimeConfig.public = nuxt.options.runtimeConfig.public || {}
  nuxt.options.runtimeConfig.public.apiProxy = config.apiProxy
  nuxt.options.runtimeConfig.public.apiPrefix = config.apiPrefix

  // Configure Nitro devProxy for development HTTP requests
  // Note: devProxy only handles direct HTTP requests (client-side fetch in dev)
  // For SSR, users should create a server/api/[...].ts catch-all route with proxyRequest
  nuxt.options.nitro = nuxt.options.nitro || {}
  nuxt.options.nitro.devProxy = nuxt.options.nitro.devProxy || {}
  nuxt.options.nitro.devProxy[config.apiPrefix] = {
    target: config.apiProxy,
    changeOrigin: true,
    ws: true,
  }

  if (config.verbose) {
    console.log(colors.cyan("[litestar-nuxt]"), "Runtime config:")
    console.log(`  apiProxy: ${config.apiProxy}`)
    console.log(`  apiPrefix: ${config.apiPrefix}`)
    console.log(`  verbose: ${config.verbose}`)
    console.log(colors.cyan("[litestar-nuxt]"), "Nitro devProxy configured:")
    console.log(JSON.stringify(nuxt.options.nitro.devProxy, null, 2))
  }

  // Write hotfile for Litestar proxy to discover Nuxt server URL
  // Use the port from NUXT_PORT env (set by Python) since that's what Nuxt will use
  if (config.hotFile && config.devPort) {
    const rawHost = process.env.NUXT_HOST || process.env.HOST || "localhost"
    const host = normalizeHost(rawHost)
    const url = `http://${host}:${config.devPort}`
    fs.mkdirSync(path.dirname(config.hotFile), { recursive: true })
    fs.writeFileSync(config.hotFile, url)
    if (config.verbose) {
      console.log(colors.cyan("[litestar-nuxt]"), colors.dim(`Hotfile written: ${config.hotFile} -> ${url}`))
    }
  }

  // Also register Nuxt's 'listen' hook as a backup to update hotfile with actual server URL
  // This fires when Nitro's main HTTP server starts (not Vite's internal HMR server)
  if (nuxt.hook && config.hotFile) {
    nuxt.hook("listen", (_server: unknown, listener: unknown) => {
      const info = listener as ListenInfo
      if (info && typeof info.port === "number") {
        const host = normalizeHost(info.host || "localhost")
        const url = `http://${host}:${info.port}`
        fs.writeFileSync(config.hotFile as string, url)
        if (config.verbose) {
          console.log(colors.cyan("[litestar-nuxt]"), colors.dim(`Hotfile updated via listen hook: ${url}`))
        }
      }
    })
  }

  console.log(colors.cyan("[litestar-nuxt]"), "Module initialized")
}

// Add metadata to the function
litestarNuxtModule.meta = {
  name: "litestar-vite",
  configKey: "litestar",
  compatibility: {
    nuxt: ">=3.0.0",
  },
}

// Default options getter
litestarNuxtModule.getOptions = (): LitestarNuxtConfig => ({
  apiProxy: "http://localhost:8000",
  apiPrefix: "/api",
  types: false,
  verbose: false,
})

export const litestarModule: NuxtModuleFunction = litestarNuxtModule

// Default export for Nuxt module system
export default litestarModule
