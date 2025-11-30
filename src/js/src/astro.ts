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
/**
 * Astro config for updateConfig - partial types we support.
 */
interface AstroConfigPartial {
  server?: {
    port?: number
    host?: string | boolean
  }
  vite?: {
    plugins?: Plugin[]
    server?: {
      port?: number
      strictPort?: boolean
      proxy?: Record<string, unknown>
    }
  }
}

/**
 * AddressInfo from Node.js net module.
 */
interface AddressInfo {
  address: string
  family: string
  port: number
}

interface AstroIntegration {
  name: string
  hooks: {
    "astro:config:setup"?: (options: {
      config: unknown
      command: "dev" | "build" | "preview" | "sync"
      isRestart: boolean
      updateConfig: (newConfig: AstroConfigPartial) => unknown
      logger: AstroIntegrationLogger
    }) => void | Promise<void>
    "astro:server:setup"?: (options: {
      server: ViteDevServer
      logger: AstroIntegrationLogger
    }) => void | Promise<void>
    "astro:server:start"?: (options: {
      address: AddressInfo
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
  proxyMode: "vite" | "direct" | "proxy" | null
  /** Port for Vite dev server (from VITE_PORT env or runtime config) */
  port?: number
}

/**
 * Resolve configuration with defaults.
 */
function resolveConfig(config: LitestarAstroConfig = {}): ResolvedLitestarAstroConfig {
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

  return {
    apiProxy: config.apiProxy ?? "http://localhost:8000",
    apiPrefix: config.apiPrefix ?? "/api",
    typesPath: config.typesPath ?? "./src/types/api",
    openapiPath: config.openapiPath ?? "openapi.json",
    routesPath: config.routesPath ?? "routes.json",
    verbose: config.verbose ?? false,
    hotFile,
    proxyMode,
    port,
  }
}

/**
 * Create a Vite plugin for API proxying and server configuration.
 */
function createProxyPlugin(config: ResolvedLitestarAstroConfig): Plugin {
  return {
    name: "litestar-astro-proxy",
    config() {
      return {
        server: {
          // Set the port from Python config/env to ensure Astro uses the expected port
          // strictPort: true prevents Astro from auto-incrementing to a different port
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
      "astro:config:setup": ({ updateConfig, logger, command }) => {
        if (config.verbose) {
          logger.info("Configuring Litestar integration")
          logger.info(`  API Proxy: ${config.apiProxy}`)
          logger.info(`  API Prefix: ${config.apiPrefix}`)
          logger.info(`  Types Path: ${config.typesPath}`)
          if (config.port !== undefined) {
            logger.info(`  Port: ${config.port}`)
          }
        }

        // Build the config update object
        const configUpdate: AstroConfigPartial = {
          vite: {
            plugins: [createProxyPlugin(config)],
          },
        }

        // Set the Astro server port in dev mode
        // This must be done through Astro's server config, not Vite's
        if (command === "dev" && config.port !== undefined) {
          configUpdate.server = {
            port: config.port,
          }
          if (config.verbose) {
            logger.info(`Setting Astro server port to ${config.port}`)
          }
        }

        updateConfig(configUpdate)

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
      },

      // Write hotfile AFTER server starts listening (astro:server:start fires after listen())
      // Always write hotfile - proxy mode needs it for dynamic target discovery
      "astro:server:start": ({ address, logger }) => {
        if (config.hotFile) {
          // Normalize IPv4/IPv6 wildcards and localhost addresses to "localhost"
          const rawAddr = address.address
          const host = rawAddr === "::" || rawAddr === "::1" || rawAddr === "0.0.0.0" || rawAddr === "127.0.0.1" ? "localhost" : rawAddr
          const url = `http://${host}:${address.port}`
          fs.mkdirSync(path.dirname(config.hotFile), { recursive: true })
          fs.writeFileSync(config.hotFile, url)
          if (config.verbose) {
            logger.info(`Hotfile written: ${config.hotFile} -> ${url}`)
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
