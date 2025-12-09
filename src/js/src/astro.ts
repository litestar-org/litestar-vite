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
 *       types: {
 *         enabled: true,
 *         output: 'src/generated/api',
 *       },
 *     }),
 *   ],
 * });
 * ```
 *
 * @module
 */

import fs from "node:fs"
import type { IncomingMessage, ServerResponse } from "node:http"
import path from "node:path"
import type { Plugin, ViteDevServer } from "vite"

import { createTypeGenerationPlugin } from "./shared/create-type-gen-plugin.js"

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
    "astro:server:setup"?: (options: { server: ViteDevServer; logger: AstroIntegrationLogger }) => void | Promise<void>
    "astro:server:start"?: (options: { address: AddressInfo; logger: AstroIntegrationLogger }) => void | Promise<void>
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
 * Configuration for TypeScript type generation in Astro.
 */
export interface AstroTypesConfig {
  /**
   * Enable type generation.
   *
   * @default false
   */
  enabled?: boolean

  /**
   * Path to output generated TypeScript types.
   * Relative to the Astro project root.
   *
   * @default 'src/types/api'
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
   * Enable and configure TypeScript type generation.
   *
   * When set to `true`, enables type generation with default settings.
   * When set to an AstroTypesConfig object, enables type generation with custom settings.
   *
   * @default false
   */
  types?: boolean | AstroTypesConfig

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
  types: Required<AstroTypesConfig> | false
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

  // Resolve types config
  let typesConfig: Required<AstroTypesConfig> | false = false

  if (config.types === true) {
    typesConfig = {
      enabled: true,
      output: "src/types/api",
      openapiPath: "openapi.json",
      routesPath: "routes.json",
      generateZod: false,
      generateSdk: true,
      debounce: 300,
    }
  } else if (typeof config.types === "object" && config.types !== null) {
    typesConfig = {
      enabled: config.types.enabled ?? true,
      output: config.types.output ?? "src/types/api",
      openapiPath: config.types.openapiPath ?? "openapi.json",
      routesPath: config.types.routesPath ?? "routes.json",
      generateZod: config.types.generateZod ?? false,
      generateSdk: config.types.generateSdk ?? true,
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
 * Create a Vite plugin for API proxying and server configuration.
 */
function createProxyPlugin(config: ResolvedLitestarAstroConfig): Plugin {
  return {
    name: "litestar-astro-proxy",
    config() {
      return {
        server: {
          // Force IPv4 binding for consistency with Python proxy configuration
          // Without this, Astro might bind to IPv6 localhost which the proxy can't reach
          host: "127.0.0.1",
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
 *       types: {
 *         enabled: true,
 *         output: 'src/generated/api',
 *       },
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
          if (config.types !== false) {
            logger.info(`  Types Output: ${config.types.output}`)
          }
          if (config.port !== undefined) {
            logger.info(`  Port: ${config.port}`)
          }
        }

        // Build the plugins array
        const plugins: Plugin[] = [createProxyPlugin(config)]

        // Add type generation plugin if enabled
        if (config.types !== false && config.types.enabled) {
          plugins.push(
            createTypeGenerationPlugin(config.types, {
              frameworkName: "litestar-astro",
              pluginName: "litestar-astro-types",
              clientPlugin: "@hey-api/client-fetch",
            }),
          )
        }

        // Build the config update object
        const configUpdate: AstroConfigPartial = {
          vite: {
            plugins,
          },
        }

        // Set the Astro server port and host in dev mode
        // This must be done through Astro's server config, not just Vite's
        if (command === "dev") {
          configUpdate.server = {
            // Force IPv4 binding for consistency with Python proxy configuration
            host: "127.0.0.1",
            // Set port from Python config/env if provided
            ...(config.port !== undefined ? { port: config.port } : {}),
          }
          if (config.verbose) {
            logger.info("Setting Astro server host to 127.0.0.1")
            if (config.port !== undefined) {
              logger.info(`Setting Astro server port to ${config.port}`)
            }
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
          server.middlewares.use((req: IncomingMessage, _res: ServerResponse, next: () => void) => {
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
