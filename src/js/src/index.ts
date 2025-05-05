import fs from "node:fs"
import type { AddressInfo } from "node:net"
import path from "node:path"
import { fileURLToPath } from "node:url"
import colors from "picocolors"
import { type ConfigEnv, type Plugin, type PluginOption, type ResolvedConfig, type SSROptions, type UserConfig, type ViteDevServer, loadEnv } from "vite"
import fullReload, { type Config as FullReloadConfig } from "vite-plugin-full-reload"

interface PluginConfig {
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
}

interface RefreshConfig {
  paths: string[]
  config?: FullReloadConfig
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

  return [resolveLitestarPlugin(pluginConfig), ...(resolveFullReloadConfig(pluginConfig) as Plugin[])]
}

/**
 * Resolve the index.html path to use for the Vite server.
 */
async function findIndexHtmlPath(server: ViteDevServer, pluginConfig: Required<PluginConfig>): Promise<string | null> {
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
function resolveLitestarPlugin(pluginConfig: Required<PluginConfig>): LitestarPlugin {
  let viteDevServerUrl: DevServerUrl
  let resolvedConfig: ResolvedConfig
  let userConfig: UserConfig
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
      const assetUrl = env.ASSET_URL || pluginConfig.assetUrl
      const serverConfig = command === "serve" ? (resolveDevelopmentEnvironmentServerConfig(pluginConfig.detectTls) ?? resolveEnvironmentServerConfig(env)) : undefined

      ensureCommandShouldRunInEnvironment(command, env)

      return {
        base: userConfig.base ?? (command === "build" ? resolveBase(pluginConfig, assetUrl) : pluginConfig.assetUrl),
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
                hmr:
                  userConfig.server?.hmr === false
                    ? false
                    : {
                        ...serverConfig.hmr,
                        ...(userConfig.server?.hmr === true ? {} : userConfig.server?.hmr),
                      },
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
    configResolved(config) {
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
      const appUrl = loadEnv(resolvedConfig.mode, envDir, "APP_URL").APP_URL ?? "undefined"

      // Find index.html path *once* when server starts for logging purposes
      const initialIndexPath = await findIndexHtmlPath(server, pluginConfig)

      server.httpServer?.once("listening", () => {
        const address = server.httpServer?.address()

        const isAddressInfo = (x: string | AddressInfo | null | undefined): x is AddressInfo => typeof x === "object"
        if (isAddressInfo(address)) {
          viteDevServerUrl = userConfig.server?.origin ? (userConfig.server.origin as DevServerUrl) : resolveDevServerUrl(address, server.config, userConfig)
          fs.mkdirSync(path.dirname(pluginConfig.hotFile), { recursive: true })
          fs.writeFileSync(pluginConfig.hotFile, viteDevServerUrl)

          setTimeout(() => {
            // Use resolvedConfig.logger for consistency
            resolvedConfig.logger.info(`\n  ${colors.red(`${colors.bold("LITESTAR")} ${litestarVersion()}`)}  ${colors.dim("plugin")} ${colors.bold(`v${pluginVersion()}`)}`)
            resolvedConfig.logger.info("")
            if (initialIndexPath) {
              resolvedConfig.logger.info(
                `  ${colors.green("➜")}  ${colors.bold("Index Mode")}: SPA (Serving ${colors.cyan(path.relative(server.config.root, initialIndexPath))} from root)`,
              )
            } else {
              resolvedConfig.logger.info(`  ${colors.green("➜")}  ${colors.bold("Index Mode")}: Litestar (Plugin will serve placeholder for /index.html)`)
            }
            resolvedConfig.logger.info(`  ${colors.green("➜")}  ${colors.bold("Dev Server")}: ${colors.cyan(viteDevServerUrl)}`)
            resolvedConfig.logger.info(`  ${colors.green("➜")}  ${colors.bold("App URL")}:    ${colors.cyan(appUrl.replace(/:(\d+)/, (_, port) => `:${colors.bold(port)}`))}`)
            resolvedConfig.logger.info(`  ${colors.green("➜")}  ${colors.bold("Assets Base")}: ${colors.cyan(resolvedConfig.base)}`) // Log the base path being used
          }, 100)
        }
      })

      // Clean up hot file
      if (!exitHandlersBound) {
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

      // *** MODIFIED MIDDLEWARE ***
      return () => {
        // Run middleware early to intercept before Vite's base/HTML handlers
        server.middlewares.use(async (req, res, next) => {
          const indexPath = await findIndexHtmlPath(server, pluginConfig)
          if (indexPath && (req.url === "/" || req.url === "/index.html")) {
            const currentUrl = req.url
            try {
              const htmlContent = await fs.promises.readFile(indexPath, "utf-8")
              // Transform the HTML using Vite's pipeline
              const transformedHtml = await server.transformIndexHtml(req.originalUrl ?? currentUrl, htmlContent, req.originalUrl)
              res.statusCode = 200
              res.setHeader("Content-Type", "text/html")
              res.end(transformedHtml)
              // Request handled, stop further processing
              return
            } catch (e) {
              // Log the error and pass it to Vite's error handler
              resolvedConfig.logger.error(`Error serving index.html from ${indexPath}: ${e instanceof Error ? e.message : e}`)
              next(e)
              return
            }
          }

          // Original logic: If index.html should NOT be served automatically,
          // AND the request is specifically for /index.html, serve the placeholder.
          // Requests for '/' will likely be handled by Litestar in this case.
          if (!indexPath && req.url === "/index.html") {
            try {
              const placeholderPath = path.join(dirname(), "dev-server-index.html")
              const placeholderContent = await fs.promises.readFile(placeholderPath, "utf-8")
              res.statusCode = 200 // Serve placeholder with 200 OK, or 404 if preferred
              res.setHeader("Content-Type", "text/html")
              res.end(placeholderContent.replace(/{{ APP_URL }}/g, appUrl))
            } catch (e) {
              resolvedConfig.logger.error(`Error serving placeholder index.html: ${e instanceof Error ? e.message : e}`)
              res.statusCode = 404
              res.end("Not Found (Error loading placeholder)")
            }
            // Request handled (or error), stop further processing
            return
          }

          // If none of the above conditions matched, pass the request to the next middleware (Vite's default handlers)
          next()
        })
      }
    },
  }
}

/**
 * Validate the command can run in the given environment.
 */
function ensureCommandShouldRunInEnvironment(command: "build" | "serve", env: Record<string, string>): void {
  const validEnvironmentNames = ["dev", "development", "local", "docker"]
  if (command === "build" || env.LITESTAR_BYPASS_ENV_CHECK === "1") {
    return
  }

  if (typeof env.LITESTAR_MODE !== "undefined" && validEnvironmentNames.some((e) => e === env.LITESTAR_MODE)) {
    throw Error(
      "You should only run Vite dev server when Litestar is development mode. You should build your assets for production instead. To disable this ENV check you may set LITESTAR_BYPASS_ENV_CHECK=1",
    )
  }

  if (typeof env.CI !== "undefined") {
    throw Error(
      "You should not run the Vite HMR server in CI environments. You should build your assets for production instead. To disable this ENV check you may set LITESTAR_BYPASS_ENV_CHECK=1",
    )
  }
}

/**
 * The version of Litestar being run.
 */
function litestarVersion(): string {
  return ""
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

/**
 * Convert the users configuration into a standard structure with defaults.
 */
function resolvePluginConfig(config: string | string[] | PluginConfig): Required<PluginConfig> {
  if (typeof config === "undefined") {
    throw new Error("litestar-vite-plugin: missing configuration.")
  }
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

  return {
    input: resolvedConfig.input,
    assetUrl: resolvedConfig.assetUrl ?? "static",
    resourceDirectory: resolvedConfig.resourceDirectory ?? "resources",
    bundleDirectory: resolvedConfig.bundleDirectory ?? "public",
    ssr: resolvedConfig.ssr ?? resolvedConfig.input,
    ssrOutputDirectory: resolvedConfig.ssrOutputDirectory ?? path.join(resolvedConfig.resourceDirectory ?? "resources", "bootstrap/ssr"),
    refresh: resolvedConfig.refresh ?? false,
    hotFile: resolvedConfig.hotFile ?? path.join(resolvedConfig.bundleDirectory ?? "public", "hot"),
    detectTls: resolvedConfig.detectTls ?? false,
    autoDetectIndex: resolvedConfig.autoDetectIndex ?? true,
    transformOnServe: resolvedConfig.transformOnServe ?? ((code) => code),
  }
}

/**
 * Resolve the Vite base option from the configuration.
 */
function resolveBase(config: Required<PluginConfig>, assetUrl: string): string {
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
function resolveInput(config: Required<PluginConfig>, ssr: boolean): string | string[] | undefined {
  if (ssr) {
    return config.ssr
  }

  return config.input
}

/**
 * Resolve the Vite outDir path from the configuration.
 * Should be relative to the project root for Vite config, Vite resolves it internally.
 */
function resolveOutDir(config: Required<PluginConfig>, ssr: boolean): string {
  if (ssr) {
    // Return path relative to root
    return config.ssrOutputDirectory.replace(/^\/+/, "").replace(/\/+$/, "")
  }
  // Return path relative to root
  return config.bundleDirectory.replace(/^\/+/, "").replace(/\/+$/, "")
}

function resolveFullReloadConfig({ refresh: config }: Required<PluginConfig>): PluginOption[] {
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
  const host = configHmrHost ?? remoteHost ?? configHost ?? serverAddress

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
