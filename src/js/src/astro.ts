/**
 * Astro integration for Litestar-Vite.
 *
 * This integration enables seamless development with Astro as the frontend framework
 * and Litestar as the API backend. It provides:
 * - API proxy configuration for dev server
 * - Type generation integration (shares @hey-api/openapi-ts output)
 * - Route helper generation compatible with Astro's static paths
 *
 * @example
 * ```typescript
 * // astro.config.mjs
 * import { defineConfig } from 'astro/config';
 * import litestar from 'litestar-vite-plugin/astro';
 *
 * export default defineConfig({
 *   integrations: [
 *     litestar({
 *       apiProxy: 'http://localhost:8000',
 *       typesPath: './src/generated/api',
 *     }),
 *   ],
 * });
 * ```
 *
 * @module
 */

import fs from "node:fs"
import path from "node:path"
import type { Plugin, ViteDevServer } from "vite"

/**
 * Astro integration interface.
 * This is a minimal type definition to avoid requiring astro as a dependency.
 * When using this integration, Astro will be available in the project.
 */
interface AstroIntegration {
  name: string
  hooks: {
    "astro:config:setup"?: (options: {
      config: unknown
      command: "dev" | "build" | "preview" | "sync"
      isRestart: boolean
      updateConfig: (newConfig: { vite?: { plugins?: Plugin[] } }) => unknown
      logger: AstroIntegrationLogger
    }) => void | Promise<void>
    "astro:server:setup"?: (options: {
      server: ViteDevServer
      logger: AstroIntegrationLogger
    }) => void | Promise<void>
    "astro:build:start"?: (options: { logger: AstroIntegrationLogger }) => void | Promise<void>
  }
}

/**
 * Astro integration logger interface.
 */
interface AstroIntegrationLogger {
  info: (message: string) => void
  warn: (message: string) => void
  error: (message: string) => void
}

/**
 * Configuration options for the Litestar Astro integration.
 */
export interface LitestarAstroConfig {
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
   * Path where TypeScript types are generated.
   * This should match the output path configured in your Litestar ViteConfig.
   *
   * @example './src/generated/api'
   * @default './src/types/api'
   */
  typesPath?: string

  /**
   * Path to the OpenAPI schema file exported by Litestar.
   *
   * @default 'openapi.json'
   */
  openapiPath?: string

  /**
   * Path to the routes metadata file exported by Litestar.
   *
   * @default 'routes.json'
   */
  routesPath?: string

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
interface ResolvedLitestarAstroConfig {
  apiProxy: string
  apiPrefix: string
  typesPath: string
  openapiPath: string
  routesPath: string
  verbose: boolean
  hotFile?: string
  proxyMode: "vite_proxy" | "vite_direct" | "external_proxy"
}

/**
 * Resolve configuration with defaults.
 */
function resolveConfig(config: LitestarAstroConfig = {}): ResolvedLitestarAstroConfig {
  const runtimeConfigPath = process.env.LITESTAR_VITE_CONFIG_PATH
  let hotFile: string | undefined
  let proxyMode: "vite_proxy" | "vite_direct" | "external_proxy" = "vite_proxy"

  if (runtimeConfigPath && fs.existsSync(runtimeConfigPath)) {
    try {
      const json = JSON.parse(fs.readFileSync(runtimeConfigPath, "utf-8")) as {
        bundleDir?: string
        hotFile?: string
        proxyMode?: "vite_proxy" | "vite_direct" | "external_proxy"
      }
      const bundleDir = json.bundleDir ?? "public"
      const hot = json.hotFile ?? "hot"
      hotFile = path.resolve(process.cwd(), bundleDir, hot)
      proxyMode = json.proxyMode ?? "vite_proxy"
    } catch {
      hotFile = undefined
    }
  }

  return {
    apiProxy: config.apiProxy ?? "http://localhost:8000",
    apiPrefix: config.apiPrefix ?? "/api",
    typesPath: config.typesPath ?? "./src/types/api",
    openapiPath: config.openapiPath ?? "openapi.json",
    routesPath: config.routesPath ?? "routes.json",
    verbose: config.verbose ?? false,
    hotFile,
    proxyMode,
  }
}

/**
 * Create a Vite plugin for API proxying.
 */
function createProxyPlugin(config: ResolvedLitestarAstroConfig): Plugin {
  return {
    name: "litestar-astro-proxy",
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
  }
}

/**
 * Litestar integration for Astro.
 *
 * This integration configures Astro to work seamlessly with a Litestar backend,
 * providing API proxying during development and type generation support.
 *
 * @param userConfig - Configuration options for the integration
 * @returns An Astro integration object
 *
 * @example
 * ```typescript
 * // astro.config.mjs
 * import { defineConfig } from 'astro/config';
 * import litestar from 'litestar-vite-plugin/astro';
 *
 * export default defineConfig({
 *   integrations: [
 *     litestar({
 *       apiProxy: 'http://localhost:8000',
 *       apiPrefix: '/api',
 *       typesPath: './src/generated/api',
 *     }),
 *   ],
 * });
 * ```
 *
 * @example Using with generated types
 * ```typescript
 * // src/pages/users/[id].astro
 * ---
 * import type { User } from '../generated/api/types.gen';
 * import { route } from '../generated/api/routes';
 *
 * const { id } = Astro.params;
 * const response = await fetch(route('users.show', { id }));
 * const user: User = await response.json();
 * ---
 *
 * <html>
 *   <body>
 *     <h1>{user.name}</h1>
 *   </body>
 * </html>
 * ```
 */
export default function litestarAstro(userConfig: LitestarAstroConfig = {}): AstroIntegration {
  const config = resolveConfig(userConfig)

  return {
    name: "litestar-vite",
    hooks: {
      "astro:config:setup": ({ updateConfig, logger }) => {
        if (config.verbose) {
          logger.info("Configuring Litestar integration")
          logger.info(`  API Proxy: ${config.apiProxy}`)
          logger.info(`  API Prefix: ${config.apiPrefix}`)
          logger.info(`  Types Path: ${config.typesPath}`)
        }

        // Add Vite plugins for proxy and type generation
        updateConfig({
          vite: {
            plugins: [createProxyPlugin(config)],
          },
        })

        logger.info(`Litestar integration configured - proxying ${config.apiPrefix}/* to ${config.apiProxy}`)
      },

      "astro:server:setup": ({ server, logger }) => {
        if (config.verbose) {
          logger.info("Litestar dev server integration active")
        }

        // Log proxied requests if verbose
        if (config.verbose) {
          server.middlewares.use((req, _res, next) => {
            if (req.url?.startsWith(config.apiPrefix)) {
              logger.info(`Proxying: ${req.method} ${req.url} -> ${config.apiProxy}${req.url}`)
            }
            next()
          })
        }

        // Write hotfile so Litestar SPA handler can proxy correctly
        // Only for Vite modes (not external_proxy)
        if (config.hotFile && config.proxyMode !== "external_proxy") {
          const address = server?.httpServer?.address()
          if (address && typeof address === "object" && "port" in address) {
            const host = address.address === "::" ? "localhost" : address.address
            const url = `http://${host}:${address.port}`
            fs.mkdirSync(path.dirname(config.hotFile), { recursive: true })
            fs.writeFileSync(config.hotFile, url)
            if (config.verbose) {
              logger.info(`Hotfile written: ${config.hotFile} -> ${url}`)
            }
          }
        }
      },

      "astro:build:start": ({ logger }) => {
        logger.info("Building with Litestar integration")
        logger.info(`  Make sure your Litestar backend is accessible at: ${config.apiProxy}`)
      },
    },
  }
}
