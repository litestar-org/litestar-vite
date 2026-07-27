/**
 * Astro 5 integration for Litestar-Vite.
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
 *       apiProxy: 'http://127.0.0.1:8000',
 *       types: true,
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
import { type LitestarIntegrationConfig, resolveIntegrationConfig, type ResolvedIntegrationConfig } from "./shared/integration-config.js"
import { installManagedShutdown } from "./shared/managed-shutdown.js"
import { normalizeHost } from "./shared/network.js"
import { createLitestarTypeGenPlugin, type TypesConfigShape } from "./shared/typegen-plugin.js"
import { hmrServerConfig } from "./shared/vite-compat.js"

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
      hmr?: {
        protocol?: "ws" | "wss"
        host?: string
        clientPort?: number
        path?: string
      }
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
 * Configuration for TypeScript type generation.
 *
 * Alias of the shared {@link TypesConfigShape} so every integration accepts an identical
 * `types` option. Retained as a named export for backwards compatibility.
 */
export type AstroTypesConfig = TypesConfigShape

/**
 * Configuration options for the Litestar integration.
 *
 * Alias of the shared {@link LitestarIntegrationConfig}. Retained as a named export for
 * backwards compatibility.
 */
export type LitestarAstroConfig = LitestarIntegrationConfig

function resolveConfig(config: LitestarAstroConfig = {}): ResolvedIntegrationConfig {
  return resolveIntegrationConfig(config, "src/generated")
}

/**
 * Create a Vite plugin for API proxying and server configuration.
 */
function createProxyPlugin(config: ResolvedIntegrationConfig): Plugin {
  return {
    name: "litestar-astro-proxy",
    config() {
      const hmrPath = `${(config.assetUrl ?? "/static").replace(/\/$/, "")}/vite-hmr`
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
          // Route HMR through the Litestar port so DevTools never sees the framework port.
          ...(config.litestarPort !== undefined
            ? hmrServerConfig({
                protocol: "ws" as const,
                host: "127.0.0.1",
                clientPort: config.litestarPort,
                path: hmrPath,
              })
            : {}),
          proxy: {
            [config.apiPrefix]: {
              target: config.apiProxy,
              changeOrigin: true,
              secure: false,
              ws: true,
            },
          },
        },
      }
    },
    configureServer(server: ViteDevServer) {
      installManagedShutdown(server)
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
 *       apiProxy: 'http://127.0.0.1:8000',
 *       apiPrefix: '/api',
 *       types: {
 *         enabled: true,
 *         output: 'src/generated',
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
 * import { route } from '../generated/routes';
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
            createLitestarTypeGenPlugin(config.types, {
              pluginName: "litestar-astro-types",
              frameworkName: "litestar-astro",
              sdkClientPlugin: "@hey-api/client-fetch",
              executor: config.executor,
              hasPythonConfig: config.hasPythonConfig,
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

        if (config.verbose) {
          logger.info(`Litestar integration configured - proxying ${config.apiPrefix}/* to ${config.apiProxy}`)
        }
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
          const host = normalizeHost(address.address)
          const url = `http://${host}:${address.port}`
          fs.mkdirSync(path.dirname(config.hotFile), { recursive: true })
          fs.writeFileSync(config.hotFile, url)
          if (config.verbose) {
            logger.info(`Hotfile written: ${config.hotFile} -> ${url}`)
          }
        }
      },

      "astro:build:start": ({ logger }) => {
        if (config.verbose) {
          logger.info("Building with Litestar integration")
          logger.info(`  Make sure your Litestar backend is accessible at: ${config.apiProxy}`)
        }
      },
    },
  }
}
