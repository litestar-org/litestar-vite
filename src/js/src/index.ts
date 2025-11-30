/// <reference path="./globals.d.ts" />

import { exec } from "node:child_process"
import { createHash } from "node:crypto"
import fs from "node:fs"
import type { AddressInfo } from "node:net"
import path from "node:path"
import { fileURLToPath } from "node:url"
import { promisify } from "node:util"
import colors from "picocolors"
import { type ConfigEnv, type Plugin, type PluginOption, type ResolvedConfig, type SSROptions, type UserConfig, type ViteDevServer, loadEnv } from "vite"
import fullReload, { type Config as FullReloadConfig } from "vite-plugin-full-reload"

import { resolveInstallHint } from "./install-hint.js"
import { type BackendStatus, type LitestarMeta, checkBackendAvailability, loadLitestarMeta } from "./litestar-meta.js"

const execAsync = promisify(exec)

/**
 * Configuration for TypeScript type generation.
 *
 * Type generation works as follows:
 * 1. Python's Litestar exports openapi.json and routes.json on startup (and reload)
 * 2. The Vite plugin watches these files for changes
 * 3. When they change, it runs @hey-api/openapi-ts to generate TypeScript types
 * 4. HMR event is sent to notify the client
 */
export interface TypesConfig {
  /**
   * Enable type generation.
   *
   * @default false
   */
  enabled?: boolean
  /**
   * Path to output generated TypeScript types.
   *
   * @default 'src/types/api'
   */
  output?: string
  /**
   * Path where the OpenAPI schema is exported by Litestar.
   * The Vite plugin watches this file and runs @hey-api/openapi-ts when it changes.
   *
   * @default 'openapi.json'
   */
  openapiPath?: string
  /**
   * Path where route metadata is exported by Litestar.
   * The Vite plugin watches this file for route helper generation.
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
   * Generate a typed SDK client (fetch) in addition to types.
   *
   * @default false
   */
  generateSdk?: boolean
  /**
   * Debounce time in milliseconds for type regeneration.
   * Prevents regeneration from running too frequently when
   * multiple files are written in quick succession.
   *
   * @default 300
   */
  debounce?: number
}

export interface PluginConfig {
  /**
   * The path or paths of the entry points to compile.
   */
  input: string | string[]
  /**
   * The base path to use for all asset URLs.
   *
   * @default '/static/'
   */
  assetUrl?: string
  /**
   * The public directory where all compiled/bundled assets should be written.
   *
   * @default 'public/dist'
   */
  bundleDirectory?: string
  /**
   * Litestar's public assets directory.  These are the assets that Vite will serve when developing.
   *
   * @default 'resources'
   */
  resourceDirectory?: string

  /**
   * The path to the "hot" file.
   *
   * @default `${bundleDirectory}/hot`
   */
  hotFile?: string

  /**
   * The path of the SSR entry point.
   */
  ssr?: string | string[]

  /**
   * The directory where the SSR bundle should be written.
   *
   * @default '${bundleDirectory}/bootstrap/ssr'
   */
  ssrOutputDirectory?: string

  /**
   * Configuration for performing full page refresh on python (or other) file changes.
   *
   * {@link https://github.com/ElMassimo/vite-plugin-full-reload}
   * @default false
   */
  refresh?: boolean | string | string[] | RefreshConfig | RefreshConfig[]

  /**
   * Utilize TLS certificates.
   *
   * @default null
   */
  detectTls?: string | boolean | null
  /**
   * Automatically detect the index.html file.
   *
   * @default true
   */
  autoDetectIndex?: boolean
  /**
   * Transform the code while serving.
   */
  transformOnServe?: (code: string, url: DevServerUrl) => string
  /**
   * Enable and configure TypeScript type generation.
   *
   * When set to `true`, enables type generation with default settings.
   * When set to a TypesConfig object, enables type generation with custom settings.
   *
   * Type generation creates TypeScript types from your Litestar OpenAPI schema
   * and route metadata using @hey-api/openapi-ts.
   *
   * @example
   * ```ts
   * // Simple enable
   * litestar({ input: 'src/main.ts', types: true })
   *
   * // With custom config
   * litestar({
   *   input: 'src/main.ts',
   *   types: {
   *     enabled: true,
   *     output: 'src/api/types',
   *     generateZod: true
   *   }
   * })
   * ```
   *
   * @default false
   */
  types?: boolean | TypesConfig
}

interface RefreshConfig {
  paths: string[]
  config?: FullReloadConfig
}

/**
 * Resolved plugin configuration with all defaults applied.
 * Note: `types` is resolved to `Required<TypesConfig> | false` instead of `boolean | TypesConfig`
 */
interface ResolvedPluginConfig extends Omit<Required<PluginConfig>, "types"> {
  types: Required<TypesConfig> | false
}

interface PythonDefaults {
  assetUrl?: string
  baseUrl?: string
  bundleDir?: string
  resourceDir?: string
  publicDir?: string
  manifest?: string
  mode?: string
  // New dev server mode fields
  devServerMode?: "vite_proxy" | "vite_direct" | "external_proxy"
  externalTarget?: string | null
  externalHttp2?: boolean
  // SSR fields
  ssrEnabled?: boolean
  ssrOutDir?: string
  types?: {
    enabled: boolean
    output: string
    openapiPath: string
    routesPath: string
    generateZod: boolean
    generateSdk: boolean
  } | null
}

interface LitestarPlugin extends Plugin {
  config: (config: UserConfig, env: ConfigEnv) => UserConfig
}

type DevServerUrl = `${"http" | "https"}://${string}:${number}`

let exitHandlersBound = false

export const refreshPaths = ["src/**", "resources/**", "assets/**"].filter((path) => fs.existsSync(path.replace(/\*\*$/, "")))

/**
 * Litestar plugin for Vite.
 *
 * @param config - A config object or relative path(s) of the scripts to be compiled.
 */
export default function litestar(config: string | string[] | PluginConfig): [LitestarPlugin, ...Plugin[]] {
  const pluginConfig = resolvePluginConfig(config)

  const plugins: Plugin[] = [resolveLitestarPlugin(pluginConfig), ...(resolveFullReloadConfig(pluginConfig) as Plugin[])]

  // Add type generation plugin if enabled
  if (pluginConfig.types !== false && pluginConfig.types.enabled) {
    plugins.push(resolveTypeGenerationPlugin(pluginConfig.types))
  }

  return plugins as [LitestarPlugin, ...Plugin[]]
}

/**
 * Resolve the index.html path to use for the Vite server.
 */
async function findIndexHtmlPath(server: ViteDevServer, pluginConfig: ResolvedPluginConfig): Promise<string | null> {
  if (!pluginConfig.autoDetectIndex) {
    console.log("Auto-detection disabled.") // Debug log
    return null
  }

  // Use server.config.root which is the resolved root directory
  const root = server.config.root
  const possiblePaths = [
    path.join(root, "index.html"),
    path.join(root, pluginConfig.resourceDirectory.replace(/^\//, ""), "index.html"), // Ensure resourceDirectory path is relative to root
    path.join(root, "public", "index.html"), // Check public even if publicDir is false, might exist
  ]
  // console.log("Checking paths:", possiblePaths); // Debug log

  for (const indexPath of possiblePaths) {
    try {
      // Use async access check
      await fs.promises.access(indexPath)
      // console.log("Found index.html at:", indexPath); // Debug log
      return indexPath
    } catch {
      // File doesn't exist at this path, continue checking
    }
  }
  // console.log("index.html not found in checked paths."); // Debug log
  return null
}

/**
 * Resolve the Litestar Plugin configuration.
 */
function normalizeAppUrl(appUrl: string | undefined, fallbackPort?: string): { url: string | null; note?: string } {
  if (!appUrl || appUrl === "__litestar_app_url_missing__") {
    return { url: null, note: "APP_URL missing" }
  }
  try {
    const url = new URL(appUrl)

    const rebuilt = url.origin + (url.pathname === "/" ? "" : url.pathname) + (url.search ?? "") + (url.hash ?? "")

    return { url: rebuilt }
  } catch {
    return { url: null, note: "APP_URL invalid" }
  }
}

function resolveLitestarPlugin(pluginConfig: ResolvedPluginConfig): LitestarPlugin {
  let viteDevServerUrl: DevServerUrl
  let resolvedConfig: ResolvedConfig
  let userConfig: UserConfig
  let litestarMeta: LitestarMeta = {}
  const pythonDefaults = loadPythonDefaults()
  const devServerMode = pythonDefaults?.devServerMode ?? "vite_proxy"
  const defaultAliases: Record<string, string> = {
    "@": `/${pluginConfig.resourceDirectory.replace(/^\/+/, "").replace(/\/+$/, "")}/`,
  }

  return {
    name: "litestar",
    enforce: "post",
    config: (config, { command, mode }) => {
      userConfig = config
      const ssr = !!userConfig.build?.ssr
      const env = loadEnv(mode, userConfig.envDir || process.cwd(), "")
      const assetUrl = normalizeAssetUrl(env.ASSET_URL || pluginConfig.assetUrl)
      const serverConfig = command === "serve" ? (resolveDevelopmentEnvironmentServerConfig(pluginConfig.detectTls) ?? resolveEnvironmentServerConfig(env)) : undefined
      const devBase = pluginConfig.assetUrl.startsWith("/") ? pluginConfig.assetUrl : pluginConfig.assetUrl.replace(/\/+$/, "")

      ensureCommandShouldRunInEnvironment(command, env)

      return {
        base: userConfig.base ?? (command === "build" ? resolveBase(pluginConfig, assetUrl) : devBase),
        publicDir: userConfig.publicDir ?? false,
        clearScreen: false,
        build: {
          manifest: userConfig.build?.manifest ?? (ssr ? false : "manifest.json"),
          ssrManifest: userConfig.build?.ssrManifest ?? (ssr ? "ssr-manifest.json" : false),
          outDir: userConfig.build?.outDir ?? resolveOutDir(pluginConfig, ssr),
          rollupOptions: {
            input: userConfig.build?.rollupOptions?.input ?? resolveInput(pluginConfig, ssr),
          },
          assetsInlineLimit: userConfig.build?.assetsInlineLimit ?? 0,
        },
        server: {
          origin: userConfig.server?.origin ?? "__litestar_vite_placeholder__",
          // Auto-configure HMR to use a path that routes through Litestar proxy
          // Note: Vite automatically prepends `base` to `hmr.path`, so we just use "vite-hmr"
          // Result: base="/static/" + path="vite-hmr" = "/static/vite-hmr"
          hmr:
            userConfig.server?.hmr === false
              ? false
              : {
                  path: "vite-hmr",
                  ...(serverConfig?.hmr ?? {}),
                  ...(userConfig.server?.hmr === true ? {} : userConfig.server?.hmr),
                },
          // Auto-configure proxy to forward API requests to Litestar backend
          // This allows the app to work when accessing Vite directly (not through Litestar proxy)
          // Only proxies /api and /schema routes - everything else is handled by Vite
          proxy:
            userConfig.server?.proxy ??
            (env.APP_URL
              ? {
                  "/api": {
                    target: env.APP_URL,
                    changeOrigin: true,
                  },
                  "/schema": {
                    target: env.APP_URL,
                    changeOrigin: true,
                  },
                }
              : undefined),
          ...(process.env.VITE_ALLOW_REMOTE
            ? {
                host: userConfig.server?.host ?? "0.0.0.0",
                port: userConfig.server?.port ?? (env.VITE_PORT ? Number.parseInt(env.VITE_PORT) : 5173),
                strictPort: userConfig.server?.strictPort ?? true,
              }
            : undefined),
          ...(serverConfig
            ? {
                host: userConfig.server?.host ?? serverConfig.host,
                https: userConfig.server?.https ?? serverConfig.https,
              }
            : undefined),
        },
        resolve: {
          alias: Array.isArray(userConfig.resolve?.alias)
            ? [
                ...(userConfig.resolve?.alias ?? []),
                ...Object.keys(defaultAliases).map((alias) => ({
                  find: alias,
                  replacement: defaultAliases[alias],
                })),
              ]
            : {
                ...defaultAliases,
                ...userConfig.resolve?.alias,
              },
        },
        ssr: {
          noExternal: noExternalInertiaHelpers(userConfig),
        },
        // Explicitly set appType if you know you're serving an SPA index.html
        // appType: 'spa', // Try adding this - might simplify things if appropriate
      }
    },
    async configResolved(config) {
      resolvedConfig = config
      // Ensure base ends with / for dev server if not empty
      if (resolvedConfig.command === "serve" && resolvedConfig.base && !resolvedConfig.base.endsWith("/")) {
        resolvedConfig = {
          ...resolvedConfig,
          base: `${resolvedConfig.base}/`,
        }
      }
      // Debug log resolved config
      // console.log("Resolved Vite Config:", resolvedConfig);

      const hint = pluginConfig.types !== false ? pluginConfig.types.routesPath : undefined
      litestarMeta = await loadLitestarMeta(resolvedConfig, hint)
    },
    transform(code: string, id: string): string | undefined {
      // Added 'id' for context
      // Avoid transforming unrelated files during serve if placeholder isn't present
      if (resolvedConfig.command === "serve" && code.includes("__litestar_vite_placeholder__")) {
        // Debug log transformation
        // console.log(`Transforming ${id} with dev server URL: ${viteDevServerUrl}`);
        const transformedCode = code.replace(/__litestar_vite_placeholder__/g, viteDevServerUrl)
        // Apply user transform *only* if the placeholder was found and replaced
        return pluginConfig.transformOnServe(transformedCode, viteDevServerUrl)
      }
      return undefined
    },
    async configureServer(server) {
      const envDir = resolvedConfig.envDir || process.cwd()
      const envWithApp = loadEnv(resolvedConfig.mode, envDir, "APP_URL")
      const rawAppUrl = envWithApp.APP_URL ?? "__litestar_app_url_missing__"
      const normalizedAppUrl = normalizeAppUrl(rawAppUrl, envWithApp.LITESTAR_PORT)
      const appUrl = normalizedAppUrl.url ?? rawAppUrl

      // Resolve hotFile path relative to Vite root to handle --app-dir scenarios
      // The hotFile path in pluginConfig may be relative, so we need to resolve it
      // against the Vite root directory to ensure it's written/read from the correct location
      if (pluginConfig.hotFile && !path.isAbsolute(pluginConfig.hotFile)) {
        pluginConfig.hotFile = path.resolve(server.config.root, pluginConfig.hotFile)
      }

      // Find index.html path *once* when server starts for logging purposes
      const initialIndexPath = await findIndexHtmlPath(server, pluginConfig)

      server.httpServer?.once("listening", () => {
        const address = server.httpServer?.address()

        const isAddressInfo = (x: string | AddressInfo | null | undefined): x is AddressInfo => typeof x === "object"
        if (isAddressInfo(address)) {
          viteDevServerUrl = userConfig.server?.origin ? (userConfig.server.origin as DevServerUrl) : resolveDevServerUrl(address, server.config, userConfig)
          // Only write hotfile for Vite modes (not external_proxy)
          if (devServerMode !== "external_proxy") {
            fs.mkdirSync(path.dirname(pluginConfig.hotFile), { recursive: true })
            fs.writeFileSync(pluginConfig.hotFile, viteDevServerUrl)
          }

          // Check backend availability and log status
          setTimeout(async () => {
            const version = litestarMeta.litestarVersion ?? process.env.LITESTAR_VERSION ?? "unknown"
            const backendStatus = await checkBackendAvailability(appUrl)

            // Use resolvedConfig.logger for consistency
            resolvedConfig.logger.info(`\n  ${colors.red(`${colors.bold("LITESTAR")} ${version}`)}`)
            resolvedConfig.logger.info("")

            // Index mode
            if (initialIndexPath) {
              resolvedConfig.logger.info(
                `  ${colors.green("➜")}  ${colors.bold("Index Mode")}: SPA (Serving ${colors.cyan(path.relative(server.config.root, initialIndexPath))} from root)`,
              )
            } else {
              resolvedConfig.logger.info(`  ${colors.green("➜")}  ${colors.bold("Index Mode")}: Litestar (Plugin will serve placeholder for /index.html)`)
            }

            // Dev server URL
            resolvedConfig.logger.info(`  ${colors.green("➜")}  ${colors.bold("Dev Server")}: ${colors.cyan(viteDevServerUrl)}`)

            // App URL with backend status
            if (backendStatus.available) {
              resolvedConfig.logger.info(
                `  ${colors.green("➜")}  ${colors.bold("App URL")}:    ${colors.cyan(appUrl.replace(/:(\d+)/, (_, port) => `:${colors.bold(port)}`))} ${colors.green("✓")}`,
              )
            } else {
              resolvedConfig.logger.info(
                `  ${colors.yellow("➜")}  ${colors.bold("App URL")}:    ${colors.cyan(appUrl.replace(/:(\d+)/, (_, port) => `:${colors.bold(port)}`))} ${colors.yellow("⚠")}`,
              )
            }

            // Assets base path
            resolvedConfig.logger.info(`  ${colors.green("➜")}  ${colors.bold("Assets Base")}: ${colors.cyan(resolvedConfig.base)}`)

            // Type generation status
            if (pluginConfig.types !== false && pluginConfig.types.enabled) {
              const openapiExists = fs.existsSync(path.resolve(process.cwd(), pluginConfig.types.openapiPath))
              const routesExists = fs.existsSync(path.resolve(process.cwd(), pluginConfig.types.routesPath))

              if (openapiExists || routesExists) {
                resolvedConfig.logger.info(`  ${colors.green("➜")}  ${colors.bold("Type Gen")}:   ${colors.green("enabled")} ${colors.dim(`→ ${pluginConfig.types.output}`)}`)
              } else {
                resolvedConfig.logger.info(`  ${colors.yellow("➜")}  ${colors.bold("Type Gen")}:   ${colors.yellow("waiting")} ${colors.dim("(no schema files yet)")}`)
              }
            }

            // Backend status warnings/hints
            if (!backendStatus.available) {
              resolvedConfig.logger.info("")
              resolvedConfig.logger.info(`  ${colors.yellow("⚠")}  ${colors.bold("Backend Status")}`)

              if (backendStatus.error === "APP_URL not configured" || normalizedAppUrl.note) {
                resolvedConfig.logger.info(`     ${colors.dim("APP_URL environment variable is not set.")}`)
                resolvedConfig.logger.info(`     ${colors.dim("Set APP_URL in your .env file or environment.")}`)
                if (normalizedAppUrl.note === "APP_URL invalid") {
                  resolvedConfig.logger.info(`     ${colors.dim(`Current APP_URL is invalid: ${rawAppUrl}`)}`)
                }
              } else {
                resolvedConfig.logger.info(`     ${colors.dim(backendStatus.error ?? "Backend not available")}`)
                resolvedConfig.logger.info("")
                resolvedConfig.logger.info(`     ${colors.bold("To start your Litestar app:")}`)
                resolvedConfig.logger.info(`     ${colors.cyan("litestar run")} ${colors.dim("or")} ${colors.cyan("uvicorn app:app --reload")}`)
              }

              resolvedConfig.logger.info("")
              resolvedConfig.logger.info(`     ${colors.dim("The Vite dev server is running and will serve assets.")}`)
              resolvedConfig.logger.info(`     ${colors.dim("Start your Litestar backend to view the full application.")}`)
            }

            resolvedConfig.logger.info("")
          }, 100)
        }
      })

      // Clean up hot file (only for Vite modes)
      if (!exitHandlersBound && devServerMode !== "external_proxy") {
        const clean = () => {
          if (pluginConfig.hotFile && fs.existsSync(pluginConfig.hotFile)) {
            // Check hotFile exists
            fs.rmSync(pluginConfig.hotFile)
          }
        }
        process.on("exit", clean)
        process.on("SIGINT", () => process.exit())
        process.on("SIGTERM", () => process.exit())
        process.on("SIGHUP", () => process.exit())
        exitHandlersBound = true
      }

      // Add PRE-middleware to intercept requests BEFORE Vite's base redirect
      // This allows serving index.html at "/" while using a different base for assets
      server.middlewares.use(async (req, res, next) => {
        const indexPath = await findIndexHtmlPath(server, pluginConfig)

        // Serve index.html at root "/" even when base is "/static/"
        // This prevents Vite from redirecting "/" to "/static/"
        if (indexPath && (req.url === "/" || req.url === "/index.html")) {
          const currentUrl = req.url
          try {
            const htmlContent = await fs.promises.readFile(indexPath, "utf-8")
            // Transform the HTML using Vite's pipeline - this injects the correct base-prefixed paths
            const transformedHtml = await server.transformIndexHtml(req.originalUrl ?? currentUrl, htmlContent, req.originalUrl)
            res.statusCode = 200
            res.setHeader("Content-Type", "text/html")
            res.end(transformedHtml)
            return
          } catch (e) {
            resolvedConfig.logger.error(`Error serving index.html from ${indexPath}: ${e instanceof Error ? e.message : e}`)
            next(e)
            return
          }
        }

        // Serve placeholder for /index.html when no index.html exists
        if (!indexPath && req.url === "/index.html") {
          try {
            const placeholderPath = path.join(dirname(), "dev-server-index.html")
            const placeholderContent = await fs.promises.readFile(placeholderPath, "utf-8")
            res.statusCode = 200
            res.setHeader("Content-Type", "text/html")
            res.end(placeholderContent.replace(/{{ APP_URL }}/g, appUrl))
          } catch (e) {
            resolvedConfig.logger.error(`Error serving placeholder index.html: ${e instanceof Error ? e.message : e}`)
            res.statusCode = 404
            res.end("Not Found (Error loading placeholder)")
          }
          return
        }

        next()
      })
    },
  }
}

/**
 * Validate the command can run in the given environment.
 */
function ensureCommandShouldRunInEnvironment(command: "build" | "serve", env: Record<string, string>): void {
  const allowedDevModes = ["dev", "development", "local", "docker"]
  if (command === "build" || env.LITESTAR_BYPASS_ENV_CHECK === "1") {
    return
  }

  if (typeof env.LITESTAR_MODE !== "undefined" && !allowedDevModes.includes(env.LITESTAR_MODE)) {
    throw Error("Run the Vite dev server only in development. Set LITESTAR_MODE=dev/development/local/docker or set LITESTAR_BYPASS_ENV_CHECK=1 to skip this check.")
  }

  if (typeof env.CI !== "undefined") {
    throw Error(
      "You should not run the Vite HMR server in CI environments. You should build your assets for production instead. To disable this ENV check you may set LITESTAR_BYPASS_ENV_CHECK=1",
    )
  }
}

/**
 * The version of the Litestar Vite plugin being run.
 */
function pluginVersion(): string {
  try {
    return JSON.parse(fs.readFileSync(path.join(dirname(), "../package.json")).toString())?.version
  } catch {
    return ""
  }
}

function loadPythonDefaults(): PythonDefaults | null {
  const configPath = process.env.LITESTAR_VITE_CONFIG_PATH
  if (!configPath) {
    return null
  }
  if (!fs.existsSync(configPath)) {
    return null
  }
  try {
    const data = JSON.parse(fs.readFileSync(configPath, "utf8")) as PythonDefaults
    return data
  } catch {
    return null
  }
}

/**
 * Convert the users configuration into a standard structure with defaults.
 */
function resolvePluginConfig(config: string | string[] | PluginConfig): ResolvedPluginConfig {
  if (typeof config === "undefined") {
    throw new Error("litestar-vite-plugin: missing configuration.")
  }
  const pythonDefaults = loadPythonDefaults()
  const resolvedConfig = typeof config === "string" || Array.isArray(config) ? { input: config, ssr: config } : config

  if (typeof resolvedConfig.input === "undefined") {
    throw new Error('litestar-vite-plugin: missing configuration for "input".')
  }
  if (typeof resolvedConfig.resourceDirectory === "string") {
    resolvedConfig.resourceDirectory = resolvedConfig.resourceDirectory.trim().replace(/^\/+/, "").replace(/\/+$/, "")

    if (resolvedConfig.resourceDirectory === "") {
      throw new Error("litestar-vite-plugin: resourceDirectory must be a subdirectory. E.g. 'resources'.")
    }
  }

  if (typeof resolvedConfig.bundleDirectory === "string") {
    resolvedConfig.bundleDirectory = resolvedConfig.bundleDirectory.trim().replace(/^\/+/, "").replace(/\/+$/, "")

    if (resolvedConfig.bundleDirectory === "") {
      throw new Error("litestar-vite-plugin: bundleDirectory must be a subdirectory. E.g. 'public'.")
    }
  }

  if (typeof resolvedConfig.ssrOutputDirectory === "string") {
    resolvedConfig.ssrOutputDirectory = resolvedConfig.ssrOutputDirectory.trim().replace(/^\/+/, "").replace(/\/+$/, "")
  }

  if (resolvedConfig.refresh === true) {
    resolvedConfig.refresh = [{ paths: refreshPaths }]
  }

  // Resolve types configuration (default enabled)
  let typesConfig: Required<TypesConfig> | false = false
  if (typeof resolvedConfig.types === "undefined" && pythonDefaults?.types) {
    typesConfig = {
      enabled: pythonDefaults.types.enabled,
      output: pythonDefaults.types.output,
      openapiPath: pythonDefaults.types.openapiPath,
      routesPath: pythonDefaults.types.routesPath,
      generateZod: pythonDefaults.types.generateZod,
      generateSdk: pythonDefaults.types.generateSdk,
      debounce: 300,
    }
  } else if (resolvedConfig.types === true || typeof resolvedConfig.types === "undefined") {
    typesConfig = {
      enabled: true,
      output: "src/generated/types",
      openapiPath: "src/generated/openapi.json",
      routesPath: "src/generated/routes.json",
      generateZod: false,
      generateSdk: false,
      debounce: 300,
    }
  } else if (typeof resolvedConfig.types === "object" && resolvedConfig.types !== null) {
    const userProvidedOpenapi = Object.prototype.hasOwnProperty.call(resolvedConfig.types, "openapiPath")
    const userProvidedRoutes = Object.prototype.hasOwnProperty.call(resolvedConfig.types, "routesPath")

    typesConfig = {
      enabled: resolvedConfig.types.enabled ?? true,
      output: resolvedConfig.types.output ?? "src/generated/types",
      openapiPath: resolvedConfig.types.openapiPath ?? (resolvedConfig.types.output ? path.join(resolvedConfig.types.output, "openapi.json") : "src/generated/openapi.json"),
      routesPath: resolvedConfig.types.routesPath ?? (resolvedConfig.types.output ? path.join(resolvedConfig.types.output, "routes.json") : "src/generated/routes.json"),
      generateZod: resolvedConfig.types.generateZod ?? false,
      generateSdk: resolvedConfig.types.generateSdk ?? false,
      debounce: resolvedConfig.types.debounce ?? 300,
    }

    // If the user only set output (not openapi/routes), cascade them under output for consistency
    if (!userProvidedOpenapi && resolvedConfig.types.output) {
      typesConfig.openapiPath = path.join(typesConfig.output, "openapi.json")
    }
    if (!userProvidedRoutes && resolvedConfig.types.output) {
      typesConfig.routesPath = path.join(typesConfig.output, "routes.json")
    }
  }

  return {
    input: resolvedConfig.input,
    assetUrl: normalizeAssetUrl(resolvedConfig.assetUrl ?? pythonDefaults?.assetUrl ?? "/static/"),
    resourceDirectory: resolvedConfig.resourceDirectory ?? pythonDefaults?.resourceDir ?? "resources",
    bundleDirectory: resolvedConfig.bundleDirectory ?? pythonDefaults?.bundleDir ?? "public",
    ssr: resolvedConfig.ssr ?? resolvedConfig.input,
    ssrOutputDirectory:
      resolvedConfig.ssrOutputDirectory ?? pythonDefaults?.ssrOutDir ?? path.join(resolvedConfig.resourceDirectory ?? pythonDefaults?.resourceDir ?? "resources", "bootstrap/ssr"),
    refresh: resolvedConfig.refresh ?? false,
    hotFile: resolvedConfig.hotFile ?? path.join(resolvedConfig.bundleDirectory ?? "public", "hot"),
    detectTls: resolvedConfig.detectTls ?? false,
    autoDetectIndex: resolvedConfig.autoDetectIndex ?? true,
    transformOnServe: resolvedConfig.transformOnServe ?? ((code) => code),
    types: typesConfig,
  }
}

/**
 * Resolve the Vite base option from the configuration.
 */
function resolveBase(config: ResolvedPluginConfig, assetUrl: string): string {
  // In development mode, use the assetUrl directly
  if (process.env.NODE_ENV === "development") {
    return assetUrl
  }
  // In production, use the full assetUrl
  return assetUrl.endsWith("/") ? assetUrl : `${assetUrl}/`
}

/**
 * Resolve the Vite input path from the configuration.
 */
function resolveInput(config: ResolvedPluginConfig, ssr: boolean): string | string[] | undefined {
  if (ssr) {
    return config.ssr
  }

  return config.input
}

/**
 * Resolve the Vite outDir path from the configuration.
 * Should be relative to the project root for Vite config, Vite resolves it internally.
 */
function resolveOutDir(config: ResolvedPluginConfig, ssr: boolean): string {
  if (ssr) {
    // Return path relative to root
    return config.ssrOutputDirectory.replace(/^\/+/, "").replace(/\/+$/, "")
  }
  // Return path relative to root
  return config.bundleDirectory.replace(/^\/+/, "").replace(/\/+$/, "")
}

function resolveFullReloadConfig({ refresh: config }: ResolvedPluginConfig): PluginOption[] {
  if (typeof config === "boolean") {
    return []
  }

  if (typeof config === "string") {
    config = [{ paths: [config] }]
  }

  if (!Array.isArray(config)) {
    config = [config]
  }

  if (config.some((c) => typeof c === "string")) {
    config = [{ paths: config }] as RefreshConfig[]
  }

  return (config as RefreshConfig[]).flatMap((c) => {
    const plugin = fullReload(c.paths, c.config)

    /* eslint-disable-next-line @typescript-eslint/ban-ts-comment */
    /** @ts-ignore */
    plugin.__litestar_plugin_config = c

    return plugin
  })
}

/**
 * Create a debounced function that delays invoking func until after
 * wait milliseconds have elapsed since the last time the debounced
 * function was invoked.
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
 * Type generation plugin for Litestar.
 *
 * This plugin watches the OpenAPI schema and routes JSON files exported by Litestar.
 * When these files change (e.g., after Python server reload), it runs @hey-api/openapi-ts
 * to generate TypeScript types and notifies HMR clients.
 *
 * Flow:
 * 1. Litestar exports openapi.json and routes.json on startup (via server_lifespan hook)
 * 2. This plugin detects file changes via Vite's handleHotUpdate
 * 3. Runs npx @hey-api/openapi-ts to generate TypeScript types
 * 4. Sends HMR event to notify client
 */
function resolveTypeGenerationPlugin(typesConfig: Required<TypesConfig>): Plugin {
  let lastTypesHash: string | null = null
  let lastRoutesHash: string | null = null
  let server: ViteDevServer | null = null
  let isGenerating = false
  let resolvedConfig: ResolvedConfig | null = null

  /**
   * Run @hey-api/openapi-ts to generate TypeScript types from the OpenAPI schema.
   */
  async function runTypeGeneration(): Promise<boolean> {
    if (isGenerating) {
      return false
    }

    isGenerating = true
    const startTime = Date.now()

    try {
      // Check if openapi.json exists
      const openapiPath = path.resolve(process.cwd(), typesConfig.openapiPath)
      const routesPath = path.resolve(process.cwd(), typesConfig.routesPath)

      let generated = false

      if (fs.existsSync(openapiPath)) {
        if (resolvedConfig) {
          resolvedConfig.logger.info(`${colors.cyan("litestar-vite")} ${colors.dim("generating TypeScript types...")}`)
        }

        // Build @hey-api/openapi-ts command
        const args = ["@hey-api/openapi-ts", "-i", typesConfig.openapiPath, "-o", typesConfig.output]

        if (typesConfig.generateZod) {
          args.push("--plugins", "@hey-api/schemas", "@hey-api/types")
        }
        if (typesConfig.generateSdk) {
          args.push("--client", "fetch")
        }

        await execAsync(`npx ${args.join(" ")}`, {
          cwd: process.cwd(),
        })

        generated = true
      } else if (resolvedConfig) {
        resolvedConfig.logger.warn(`${colors.cyan("litestar-vite")} ${colors.yellow("OpenAPI schema not found:")} ${typesConfig.openapiPath}`)
      }

      // Always try to emit routes types when routes metadata is present
      if (fs.existsSync(routesPath)) {
        await emitRouteTypes(routesPath, typesConfig.output)
        generated = true
      }

      if (generated && resolvedConfig) {
        const duration = Date.now() - startTime
        resolvedConfig.logger.info(`${colors.cyan("litestar-vite")} ${colors.green("TypeScript artifacts updated")} ${colors.dim(`in ${duration}ms`)}`)
      }

      // Notify HMR clients that types have been updated
      if (generated && server) {
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
      if (resolvedConfig) {
        const message = error instanceof Error ? error.message : String(error)
        // Don't show error if @hey-api/openapi-ts is not installed - just warn once
        if (message.includes("not found") || message.includes("ENOENT")) {
          resolvedConfig.logger.warn(`${colors.cyan("litestar-vite")} ${colors.yellow("@hey-api/openapi-ts not installed")} - run: ${resolveInstallHint()}`)
        } else {
          resolvedConfig.logger.error(`${colors.cyan("litestar-vite")} ${colors.red("type generation failed:")} ${message}`)
        }
      }
      return false
    } finally {
      isGenerating = false
    }
  }

  // Create debounced version
  const debouncedRunTypeGeneration = debounce(runTypeGeneration, typesConfig.debounce)

  return {
    name: "litestar-vite-types",
    enforce: "pre",

    configResolved(config) {
      resolvedConfig = config
    },

    configureServer(devServer) {
      server = devServer

      // Log that we're watching for schema changes
      if (typesConfig.enabled) {
        resolvedConfig?.logger.info(`${colors.cyan("litestar-vite")} ${colors.dim("watching for schema changes:")} ${colors.yellow(typesConfig.openapiPath)}`)
      }
    },

    async handleHotUpdate({ file }) {
      if (!typesConfig.enabled) {
        return
      }

      const relativePath = path.relative(process.cwd(), file)
      const openapiPath = typesConfig.openapiPath.replace(/^\.\//, "")
      const routesPath = typesConfig.routesPath.replace(/^\.\//, "")

      // Check if the changed file is our OpenAPI schema or routes metadata
      if (relativePath === openapiPath || relativePath === routesPath || file.endsWith(openapiPath) || file.endsWith(routesPath)) {
        if (resolvedConfig) {
          resolvedConfig.logger.info(`${colors.cyan("litestar-vite")} ${colors.dim("schema changed:")} ${colors.yellow(relativePath)}`)
        }
        const newHash = await hashFile(file)
        if (relativePath === openapiPath) {
          if (lastTypesHash === newHash) return
          lastTypesHash = newHash
        } else {
          if (lastRoutesHash === newHash) return
          lastRoutesHash = newHash
        }
        debouncedRunTypeGeneration()
      }
    },
  }
}

async function hashFile(filePath: string): Promise<string> {
  const content = await fs.promises.readFile(filePath)
  return createHash("sha1").update(content).digest("hex")
}

/**
 * Resolve the dev server URL from the server address and configuration.
 */
function resolveDevServerUrl(address: AddressInfo, config: ResolvedConfig, userConfig: UserConfig): DevServerUrl {
  const configHmrProtocol = typeof config.server.hmr === "object" ? config.server.hmr.protocol : null
  const clientProtocol = configHmrProtocol ? (configHmrProtocol === "wss" ? "https" : "http") : null
  const serverProtocol = config.server.https ? "https" : "http"
  const protocol = clientProtocol ?? serverProtocol

  const configHmrHost = typeof config.server.hmr === "object" ? config.server.hmr.host : null
  const configHost = typeof config.server.host === "string" ? config.server.host : null
  const remoteHost = process.env.VITE_ALLOW_REMOTE && !userConfig.server?.host ? "localhost" : null
  const serverAddress = isIpv6(address) ? `[${address.address}]` : address.address
  let host = configHmrHost ?? remoteHost ?? configHost ?? serverAddress

  // Normalize 0.0.0.0 to 127.0.0.1 - 0.0.0.0 is a bind address meaning "all interfaces"
  // but is not connectable as a target address for the proxy
  if (host === "0.0.0.0") {
    host = "127.0.0.1"
  }

  const configHmrClientPort = typeof config.server.hmr === "object" ? config.server.hmr.clientPort : null
  const port = configHmrClientPort ?? address.port

  return `${protocol}://${host}:${port}`
}

function isIpv6(address: AddressInfo): boolean {
  return (
    address.family === "IPv6" ||
    // In node >=18.0 <18.4 this was an integer value. This was changed in a minor version.
    // See: https://github.com/laravel/vite-plugin/issues/103
    // eslint-disable-next-line @typescript-eslint/ban-ts-comment
    // @ts-ignore-next-line
    address.family === 6
  )
}

/**
 * Add the Inertia helpers to the list of SSR dependencies that aren't externalized.
 *
 * @see https://vitejs.dev/guide/ssr.html#ssr-externals
 */
function noExternalInertiaHelpers(config: UserConfig): true | Array<string | RegExp> {
  /* eslint-disable-next-line @typescript-eslint/ban-ts-comment */
  /* @ts-ignore */
  const userNoExternal = (config.ssr as SSROptions | undefined)?.noExternal
  const pluginNoExternal = ["litestar-vite-plugin"]

  if (userNoExternal === true) {
    return true
  }

  if (typeof userNoExternal === "undefined") {
    return pluginNoExternal
  }

  return [...(Array.isArray(userNoExternal) ? userNoExternal : [userNoExternal]), ...pluginNoExternal]
}

/**
 * Resolve the server config from the environment.
 */
function resolveEnvironmentServerConfig(env: Record<string, string>):
  | {
      hmr?: { host: string }
      host?: string
      https?: { cert: Buffer; key: Buffer }
    }
  | undefined {
  if (!env.VITE_SERVER_KEY && !env.VITE_SERVER_CERT) {
    return
  }

  if (!fs.existsSync(env.VITE_SERVER_KEY) || !fs.existsSync(env.VITE_SERVER_CERT)) {
    throw Error(
      `Unable to find the certificate files specified in your environment. Ensure you have correctly configured VITE_SERVER_KEY: [${env.VITE_SERVER_KEY}] and VITE_SERVER_CERT: [${env.VITE_SERVER_CERT}].`,
    )
  }

  const host = resolveHostFromEnv(env)

  if (!host) {
    throw Error(`Unable to determine the host from the environment's APP_URL: [${env.APP_URL}].`)
  }

  return {
    hmr: { host },
    host,
    https: {
      key: fs.readFileSync(env.VITE_DEV_SERVER_KEY),
      cert: fs.readFileSync(env.VITE_DEV_SERVER_CERT),
    },
  }
}

/**
 * Resolve the host name from the environment.
 */
function resolveHostFromEnv(env: Record<string, string>): string | undefined {
  try {
    return new URL(env.APP_URL).host
  } catch {
    return
  }
}

/**
 * Resolve the Herd or Valet server config for the given host.
 */
function resolveDevelopmentEnvironmentServerConfig(host: string | boolean | null):
  | {
      hmr?: { host: string }
      host?: string
      https?: { cert: string; key: string }
    }
  | undefined {
  if (host === false) {
    return
  }

  const configPath = determineDevelopmentEnvironmentConfigPath()

  if (typeof configPath === "undefined" && host === null) {
    return
  }

  if (typeof configPath === "undefined") {
    throw Error("Unable to find the Herd or Valet configuration directory. Please check they are correctly installed.")
  }

  const resolvedHost = host === true || host === null ? `${path.basename(process.cwd())}.${resolveDevelopmentEnvironmentTld(configPath)}` : host

  const keyPath = path.resolve(configPath, "certs", `${resolvedHost}.key`)
  const certPath = path.resolve(configPath, "certs", `${resolvedHost}.crt`)

  if ((!fs.existsSync(keyPath) || !fs.existsSync(certPath)) && host === null) {
    throw Error(`Unable to find certificate files for your host [${host}] in the [${configPath}/certs] directory.`)
  }

  return {
    hmr: { host: resolvedHost },
    host: resolvedHost,
    https: {
      key: keyPath,
      cert: certPath,
    },
  }
}

/**
 * Resolve the path configuration directory.
 */
function determineDevelopmentEnvironmentConfigPath(): string | undefined {
  const envConfigPath = path.resolve(process.cwd(), ".config")

  if (fs.existsSync(envConfigPath)) {
    return envConfigPath
  }

  return path.resolve(process.cwd(), ".config")
}

/**
 * Resolve the TLD via the config path.
 */
function resolveDevelopmentEnvironmentTld(configPath: string): string {
  const configFile = path.resolve(configPath, "config.json")

  if (!fs.existsSync(configFile)) {
    throw Error(`Unable to find the configuration file [${configFile}].`)
  }

  const config: { tld: string } = JSON.parse(fs.readFileSync(configFile, "utf-8"))

  return config.tld
}

/**
 * The directory of the current file.
 */
function dirname(): string {
  // Use path.resolve relative to process.cwd() as a more robust alternative
  // Assumes the script runs from the project root or similar predictable location.
  // Adjust the relative path if necessary based on actual execution context.
  try {
    // Attempt original method first
    return fileURLToPath(new URL(".", import.meta.url))
  } catch {
    // Fallback for environments where import.meta.url is problematic (like some test runners)
    return path.resolve(process.cwd(), "src/js/src")
  }
}

function normalizeAssetUrl(url: string): string {
  const trimmed = url.trim()

  if (trimmed === "") {
    return "static"
  }

  const isExternal = trimmed.startsWith("http://") || trimmed.startsWith("https://")
  if (isExternal) {
    return trimmed.replace(/\/+$/, "")
  }

  const withLeading = trimmed.startsWith("/") ? `/${trimmed.replace(/^\/+/, "")}` : trimmed
  const withTrailing = withLeading.endsWith("/") ? withLeading : `${withLeading}/`
  return withTrailing
}
