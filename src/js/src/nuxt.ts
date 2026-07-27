/**
 * Nuxt 4 module for Litestar-Vite.
 *
 * This module provides seamless integration between Nuxt 4 and a Litestar backend.
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
 *     apiProxy: 'http://127.0.0.1:8000',
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
import { type LitestarIntegrationConfig, resolveIntegrationConfig, type ResolvedIntegrationConfig } from "./shared/integration-config.js"
import { installManagedShutdown } from "./shared/managed-shutdown.js"
import { normalizeHost } from "./shared/network.js"
import { createLitestarTypeGenPlugin, type TypesConfigShape } from "./shared/typegen-plugin.js"
import { hmrServerConfig } from "./shared/vite-compat.js"

/**
 * Configuration for TypeScript type generation.
 *
 * Alias of the shared {@link TypesConfigShape} so every integration accepts an identical
 * `types` option. Retained as a named export for backwards compatibility.
 */
export type NuxtTypesConfig = TypesConfigShape

/**
 * Configuration options for the Litestar integration.
 *
 * Alias of the shared {@link LitestarIntegrationConfig}. Retained as a named export for
 * backwards compatibility.
 */
export type LitestarNuxtConfig = LitestarIntegrationConfig

function resolveConfig(config: LitestarNuxtConfig = {}): ResolvedIntegrationConfig {
  return resolveIntegrationConfig(config, "generated")
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
function createProxyPlugin(config: ResolvedIntegrationConfig): Plugin {
  let hmrPort = 0

  return {
    name: "litestar-nuxt-proxy",
    async config() {
      hmrPort = await getPort()
      // Note: Server port is controlled by PORT env var (set by Python)
      // We configure the host binding and HMR here
      const hmrPath = `${(config.assetUrl ?? "/static").replace(/\/$/, "")}/vite-hmr`
      // The browser must connect to the Litestar port (single-port-via-ASGI contract).
      // Falls back to the Nuxt dev port when no Litestar URL is known.
      const browserHmrPort = config.litestarPort ?? config.port
      return {
        server: {
          // Force IPv4 binding for consistency with Python proxy configuration
          // Without this, Nuxt/Nitro might bind to IPv6 localhost which the proxy can't reach
          host: "127.0.0.1",
          // Set the port from Python config/env to ensure Nuxt uses the expected port
          // strictPort: true prevents auto-incrementing to a different port
          ...(config.port !== undefined
            ? {
                port: config.port,
                strictPort: true,
              }
            : {}),
          // Vite serves HMR on a separate internal port; browsers reach it through
          // Litestar's /static/vite-hmr WebSocket handler. Vite 8.1 moved these network
          // options from server.hmr.* to server.ws.*; hmrServerConfig picks the right key.
          ...hmrServerConfig({
            port: hmrPort,
            host: "127.0.0.1",
            ...(browserHmrPort !== undefined ? { clientPort: browserHmrPort } : {}),
            ...(config.litestarPort !== undefined ? { path: hmrPath, protocol: "ws" as const } : {}),
          }),
        },
      }
    },
    configureServer(server) {
      installManagedShutdown(server)
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
      if (config.verbose) {
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
      }
    },
  }
}

/** Internal helper to build Nuxt-side Vite plugins. */
function litestarPluginsFromResolved(config: ResolvedIntegrationConfig): Plugin[] {
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
 *     apiProxy: 'http://127.0.0.1:8000',
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
 * // app/composables/useApi.ts
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
  url?: string
  address?: {
    address?: string
    port?: number
  }
  host?: string
  port?: number
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

  // Nuxt's listen hook is the authoritative primary hotfile writer. It fires
  // after Nitro's main HTTP server starts, so hotfile presence means ready.
  if (nuxt.hook && config.hotFile) {
    const hotFile = config.hotFile
    nuxt.hook("listen", (_server: unknown, listener: unknown) => {
      const info = listener as ListenInfo
      const port = info?.address?.port ?? info?.port
      if (typeof port === "number") {
        const host = normalizeHost(info.address?.address || info.host || "127.0.0.1")
        const url = `http://${host}:${port}`
        fs.mkdirSync(path.dirname(hotFile), { recursive: true })
        fs.writeFileSync(hotFile, url)
        if (config.verbose) {
          console.log(colors.cyan("[litestar-nuxt]"), colors.dim(`Hotfile written after listen: ${hotFile} -> ${url}`))
        }
      }
    })
  }

  if (config.verbose) {
    console.log(colors.cyan("[litestar-nuxt]"), "Module initialized")
  }
}

// Add metadata to the function
litestarNuxtModule.meta = {
  name: "litestar-vite",
  configKey: "litestar",
  compatibility: {
    nuxt: ">=4.0.0",
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
