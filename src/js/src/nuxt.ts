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
 *     types: true,
 *   },
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
   * @default 'generated'
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
  /** Whether .litestar.json was found */
  hasPythonConfig: boolean
}

/**
 * Resolve configuration with defaults.
 */
function resolveConfig(config: LitestarNuxtConfig = {}): ResolvedNuxtConfig {
  let hotFile: string | undefined
  let proxyMode: "vite" | "direct" | "proxy" | null = "vite"
  let devPort: number | undefined
  let pythonTypesConfig: BridgeTypesConfig | undefined
  let hasPythonConfig = false

  // Read port from VITE_PORT environment variable (set by Python)
  const envPort = process.env.VITE_PORT
  if (envPort) {
    devPort = Number.parseInt(envPort, 10)
    if (Number.isNaN(devPort)) {
      devPort = undefined
    }
  }

  let pythonExecutor: "node" | "bun" | "deno" | "yarn" | "pnpm" | undefined

  const runtime = readBridgeConfig()
  if (runtime) {
    hasPythonConfig = true
    const hot = runtime.hotFile
    hotFile = resolveHotFilePath(runtime.bundleDir, hot)
    proxyMode = runtime.proxyMode
    devPort = runtime.port
    pythonExecutor = runtime.executor
    if (runtime.types) {
      pythonTypesConfig = runtime.types
    }
  }

  let typesConfig: Required<NuxtTypesConfig> | false = false

  const defaultTypesOutput = "generated"
  const buildTypeDefaults = (output: string) => ({
    openapiPath: path.join(output, "openapi.json"),
    routesPath: path.join(output, "routes.json"),
    pagePropsPath: path.join(output, "inertia-pages.json"),
    schemasTsPath: path.join(output, "schemas.ts"),
  })

  if (config.types === true) {
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
    devPort,
    executor: config.executor ?? pythonExecutor,
    hasPythonConfig,
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
      // We configure the host binding and HMR here
      return {
        server: {
          // Force IPv4 binding for consistency with Python proxy configuration
          // Without this, Nuxt/Nitro might bind to IPv6 localhost which the proxy can't reach
          host: "127.0.0.1",
          // Set the port from Python config/env to ensure Nuxt uses the expected port
          // strictPort: true prevents auto-incrementing to a different port
          ...(config.devPort !== undefined
            ? {
                port: config.devPort,
                strictPort: true,
              }
            : {}),
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

/** Internal helper to build Nuxt-side Vite plugins. */
function litestarPluginsFromResolved(config: ResolvedNuxtConfig): Plugin[] {
  const plugins: Plugin[] = [createProxyPlugin(config)]

  if (config.types !== false && config.types.enabled) {
    plugins.push(
      createLitestarTypeGenPlugin(config.types, {
        pluginName: "litestar-nuxt-types",
        frameworkName: "litestar-nuxt",
        sdkClientPlugin: "@hey-api/client-nuxt",
        executor: config.executor,
        hasPythonConfig: config.hasPythonConfig,
      }),
    )
  }

  return plugins
}

/** Internal helper to build Nuxt-side Vite plugins. */
function _litestarPlugins(userConfig: LitestarNuxtConfig = {}): Plugin[] {
  return litestarPluginsFromResolved(resolveConfig(userConfig))
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
 *       output: 'generated',
 *     },
 *   },
 * });
 * ```
 *
 * @example Using generated types in a composable
 * ```typescript
 * // composables/useApi.ts
 * import type { User } from '~/generated/api/types.gen';
 * import { route } from '~/generated/routes';
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
  const plugins = litestarPluginsFromResolved(config)

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
