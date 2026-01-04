/**
 * Unified Litestar type generation Vite plugin.
 *
 * This is a thin wrapper around typegen-core.ts that adds:
 * - Vite plugin lifecycle hooks
 * - File watching with debounce
 * - Caching for HMR efficiency
 * - WebSocket notifications
 */
import fs from "node:fs"
import path from "node:path"
import colors from "picocolors"
import type { Plugin, ResolvedConfig, ViteDevServer } from "vite"

import { debounce } from "./debounce.js"
import { emitPagePropsTypes } from "./emit-page-props-types.js"
import { emitSchemasTypes } from "./emit-schemas-types.js"
import { formatPath } from "./format-path.js"
import { shouldRunOpenApiTs, updateOpenApiTsCache } from "./typegen-cache.js"
import { buildHeyApiPlugins, findOpenApiTsConfig, runHeyApiGeneration, type TypeGenCoreConfig, type TypeGenLogger } from "./typegen-core.js"

export interface RequiredTypeGenConfig {
  enabled: boolean
  output: string
  openapiPath: string
  routesPath: string
  pagePropsPath: string
  schemasTsPath?: string
  generateZod: boolean
  generateSdk: boolean
  generateRoutes: boolean
  generatePageProps: boolean
  generateSchemas: boolean
  globalRoute: boolean
  debounce: number
}

export interface TypeGenPluginOptions {
  /** Vite plugin name */
  pluginName: string
  /** Human-friendly prefix for logs */
  frameworkName: string
  /** @hey-api client plugin (e.g. "@hey-api/client-axios") */
  sdkClientPlugin: string
  /** JS runtime executor for package commands */
  executor?: string
  /** Whether .litestar.json was present (used for buildStart warnings) */
  hasPythonConfig?: boolean
}

async function getFileMtime(filePath: string): Promise<string> {
  const stat = await fs.promises.stat(filePath)
  return stat.mtimeMs.toString()
}

/**
 * Unified Litestar type generation Vite plugin.
 *
 * Watches OpenAPI, routes.json, and inertia page props metadata and generates:
 * - API types via @hey-api/openapi-ts (optional)
 * - routes.ts (optional)
 * - page-props.ts (optional)
 */
export function createLitestarTypeGenPlugin(typesConfig: RequiredTypeGenConfig, options: TypeGenPluginOptions): Plugin {
  const { pluginName, frameworkName, sdkClientPlugin, executor, hasPythonConfig } = options

  let lastTypesHash: string | null = null
  let lastPagePropsHash: string | null = null
  let server: ViteDevServer | null = null
  let isGenerating = false
  let resolvedConfig: ResolvedConfig | null = null

  /**
   * Create a logger that uses Vite's logger.
   */
  function createViteLogger(): TypeGenLogger {
    return {
      info: (message: string) => resolvedConfig?.logger.info(`${colors.cyan("•")} ${message}`),
      warn: (message: string) => resolvedConfig?.logger.warn(`${colors.yellow("!")} ${message}`),
      error: (message: string) => resolvedConfig?.logger.error(`${colors.red("✗")} ${message}`),
    }
  }

  /**
   * Run type generation with caching for HMR efficiency.
   */
  async function runTypeGenerationWithCache(): Promise<boolean> {
    if (isGenerating) {
      return false
    }

    isGenerating = true
    const startTime = Date.now()

    try {
      const projectRoot = resolvedConfig?.root ?? process.cwd()
      const absoluteOpenapiPath = path.resolve(projectRoot, typesConfig.openapiPath)
      const absolutePagePropsPath = path.resolve(projectRoot, typesConfig.pagePropsPath)

      let generated = false
      const logger = createViteLogger()

      // Find user config
      const configPath = findOpenApiTsConfig(projectRoot)
      const shouldGenerateSdk = configPath || typesConfig.generateSdk

      // Generate OpenAPI types (with caching)
      if (fs.existsSync(absoluteOpenapiPath) && shouldGenerateSdk) {
        const plugins = buildHeyApiPlugins({
          generateSdk: typesConfig.generateSdk,
          generateZod: typesConfig.generateZod,
          sdkClientPlugin,
        })

        const cacheOptions = {
          generateSdk: typesConfig.generateSdk,
          generateZod: typesConfig.generateZod,
          plugins,
        }

        // Check cache to skip generation if inputs unchanged
        const shouldRun = await shouldRunOpenApiTs(absoluteOpenapiPath, configPath, cacheOptions)

        if (shouldRun) {
          logger.info("Generating TypeScript types...")
          if (configPath && resolvedConfig) {
            const relConfigPath = formatPath(configPath, resolvedConfig.root)
            logger.info(`openapi-ts config: ${colors.yellow(relConfigPath)}`)
          }

          const coreConfig: TypeGenCoreConfig = {
            projectRoot,
            openapiPath: typesConfig.openapiPath,
            output: typesConfig.output,
            routesPath: typesConfig.routesPath,
            pagePropsPath: typesConfig.pagePropsPath,
            generateSdk: typesConfig.generateSdk,
            generateZod: typesConfig.generateZod,
            generatePageProps: false, // Handle separately below
            generateSchemas: typesConfig.generateSchemas,
            sdkClientPlugin,
            executor,
          }

          try {
            await runHeyApiGeneration(coreConfig, configPath, plugins, logger)
            await updateOpenApiTsCache(absoluteOpenapiPath, configPath, cacheOptions)
            generated = true
          } catch (error) {
            const message = error instanceof Error ? error.message : String(error)
            if (message.includes("not found") || message.includes("ENOENT")) {
              logger.warn("@hey-api/openapi-ts not installed")
            } else {
              logger.error(`Type generation failed: ${message}`)
            }
          }
        } else {
          resolvedConfig?.logger.info(`${colors.cyan("•")} TypeScript types ${colors.dim("(unchanged)")}`)
        }
      }

      // Generate page props types (uses its own caching via emitPagePropsTypes)
      if (typesConfig.generatePageProps && fs.existsSync(absolutePagePropsPath)) {
        try {
          const changed = await emitPagePropsTypes(absolutePagePropsPath, typesConfig.output)
          if (changed) {
            generated = true
          } else {
            resolvedConfig?.logger.info(`${colors.cyan("•")} Page props types ${colors.dim("(unchanged)")}`)
          }
        } catch (error) {
          const message = error instanceof Error ? error.message : String(error)
          logger.error(`Page props generation failed: ${message}`)
        }
      }

      // Generate schema helper types (uses its own caching via emitSchemasTypes)
      const absoluteRoutesPath = path.resolve(projectRoot, typesConfig.routesPath)
      if (typesConfig.generateSchemas && fs.existsSync(absoluteRoutesPath)) {
        try {
          const changed = await emitSchemasTypes(absoluteRoutesPath, typesConfig.output, typesConfig.schemasTsPath)
          if (changed) {
            generated = true
          } else {
            resolvedConfig?.logger.info(`${colors.cyan("•")} Schema types ${colors.dim("(unchanged)")}`)
          }
        } catch (error) {
          const message = error instanceof Error ? error.message : String(error)
          logger.error(`Schema types generation failed: ${message}`)
        }
      }

      if (generated && resolvedConfig) {
        const duration = Date.now() - startTime
        resolvedConfig.logger.info(`${colors.green("✓")} TypeScript artifacts updated ${colors.dim(`(${duration}ms)`)}`)
      }

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
      const message = error instanceof Error ? error.message : String(error)
      resolvedConfig?.logger.error(`${colors.cyan("litestar-vite")} ${colors.red("type generation failed:")} ${message}`)
      return false
    } finally {
      isGenerating = false
    }
  }

  const debouncedRunTypeGeneration = debounce(runTypeGenerationWithCache, typesConfig.debounce)

  return {
    name: pluginName,
    enforce: "pre",

    configResolved(config) {
      resolvedConfig = config
    },

    configureServer(devServer) {
      server = devServer
      if (typesConfig.enabled) {
        const openapiRel = path.basename(typesConfig.openapiPath)
        resolvedConfig?.logger.info(`${colors.cyan("•")} Watching: ${colors.yellow(openapiRel)}`)
      }
    },

    async buildStart() {
      if (typesConfig.enabled && hasPythonConfig === false) {
        const projectRoot = resolvedConfig?.root ?? process.cwd()
        const openapiPath = path.resolve(projectRoot, typesConfig.openapiPath)
        if (!fs.existsSync(openapiPath)) {
          this.warn(
            "Type generation is enabled but .litestar.json was not found.\n" +
              "The Litestar backend generates this file on startup.\n\n" +
              "Solutions:\n" +
              `  1. Start the backend first: ${colors.cyan("litestar run")}\n` +
              `  2. Use integrated dev: ${colors.cyan("litestar assets serve")}\n` +
              `  3. Disable types: ${colors.cyan("litestar({ input: [...], types: false })")}\n`,
          )
        }
      }

      if (typesConfig.enabled) {
        const projectRoot = resolvedConfig?.root ?? process.cwd()
        const openapiPath = path.resolve(projectRoot, typesConfig.openapiPath)
        const pagePropsPath = path.resolve(projectRoot, typesConfig.pagePropsPath)
        const hasOpenapi = fs.existsSync(openapiPath)
        const hasPageProps = typesConfig.generatePageProps && fs.existsSync(pagePropsPath)
        if (hasOpenapi || hasPageProps) {
          await runTypeGenerationWithCache()
        }
      }
    },

    async handleHotUpdate({ file }) {
      if (!typesConfig.enabled) {
        return
      }

      const root = resolvedConfig?.root ?? process.cwd()
      const relativePath = path.relative(root, file)
      const openapiPath = typesConfig.openapiPath.replace(/^\.\//, "")
      const pagePropsPath = typesConfig.pagePropsPath.replace(/^\.\//, "")

      const isOpenapi = relativePath === openapiPath || file.endsWith(openapiPath)
      const isPageProps = typesConfig.generatePageProps && (relativePath === pagePropsPath || file.endsWith(pagePropsPath))

      if (isOpenapi || isPageProps) {
        resolvedConfig?.logger.info(`${colors.cyan(frameworkName)} ${colors.dim("schema changed:")} ${colors.yellow(relativePath)}`)
        const newHash = await getFileMtime(file)
        if (isOpenapi) {
          if (lastTypesHash === newHash) return
          lastTypesHash = newHash
        } else if (isPageProps) {
          if (lastPagePropsHash === newHash) return
          lastPagePropsHash = newHash
        }
        debouncedRunTypeGeneration()
      }
    },
  }
}
