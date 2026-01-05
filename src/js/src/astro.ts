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
import { readBridgeConfig } from "./shared/bridge-schema.js"
import { DEBOUNCE_MS } from "./shared/constants.js"
import { normalizeHost, resolveHotFilePath } from "./shared/network.js"
import { createLitestarTypeGenPlugin } from "./shared/typegen-plugin.js"

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
   * @default 'src/generated'
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
  /** JavaScript runtime executor for package commands */
  executor?: "node" | "bun" | "deno" | "yarn" | "pnpm"
  /** Whether .litestar.json was found */
  hasPythonConfig: boolean
}

/**
 * Resolve configuration with defaults.
 */
function resolveConfig(config: LitestarAstroConfig = {}): ResolvedLitestarAstroConfig {
  let hotFile: string | undefined
  let proxyMode: "vite" | "direct" | "proxy" | null = "vite"
  let port: number | undefined
  let pythonTypesConfig: NonNullable<ReturnType<typeof readBridgeConfig>>["types"] | undefined
  let pythonExecutor: "node" | "bun" | "deno" | "yarn" | "pnpm" | undefined
  let hasPythonConfig = false

  // Read port from VITE_PORT environment variable (set by Python)
  const envPort = process.env.VITE_PORT
  if (envPort) {
    port = Number.parseInt(envPort, 10)
    if (Number.isNaN(port)) {
      port = undefined
    }
  }

  const runtime = readBridgeConfig()
  if (runtime) {
    hasPythonConfig = true
    const hot = runtime.hotFile
    hotFile = resolveHotFilePath(runtime.bundleDir, hot)
    proxyMode = runtime.proxyMode
    port = runtime.port
    pythonExecutor = runtime.executor
    if (runtime.types) {
      pythonTypesConfig = runtime.types
    }
  }

  // Resolve types config
  let typesConfig: Required<AstroTypesConfig> | false = false

  const defaultTypesOutput = "src/generated"
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
    port,
    executor: pythonExecutor,
    hasPythonConfig,
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
        logger.info("Building with Litestar integration")
        logger.info(`  Make sure your Litestar backend is accessible at: ${config.apiProxy}`)
      },
    },
  }
}
