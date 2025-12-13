import { exec } from "node:child_process"
import fs from "node:fs"
import { createRequire } from "node:module"
import path from "node:path"
import { promisify } from "node:util"
import colors from "picocolors"
import type { Plugin, ResolvedConfig, ViteDevServer } from "vite"

import { resolveInstallHint, resolvePackageExecutor } from "../install-hint.js"
import { debounce } from "./debounce.js"
import { emitPagePropsTypes } from "./emit-page-props-types.js"
import { formatPath } from "./format-path.js"

const execAsync = promisify(exec)
const nodeRequire = createRequire(import.meta.url)

export interface RequiredTypeGenConfig {
  enabled: boolean
  output: string
  openapiPath: string
  routesPath: string
  pagePropsPath: string
  generateZod: boolean
  generateSdk: boolean
  generateRoutes: boolean
  generatePageProps: boolean
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
  let _chosenConfigPath: string | null = null

  async function runTypeGeneration(): Promise<boolean> {
    if (isGenerating) {
      return false
    }

    isGenerating = true
    const startTime = Date.now()

    try {
      const projectRoot = resolvedConfig?.root ?? process.cwd()
      const openapiPath = path.resolve(projectRoot, typesConfig.openapiPath)
      const pagePropsPath = path.resolve(projectRoot, typesConfig.pagePropsPath)

      let generated = false

      // Prefer user config if present (deterministic order)
      const candidates = [path.resolve(projectRoot, "openapi-ts.config.ts"), path.resolve(projectRoot, "hey-api.config.ts"), path.resolve(projectRoot, ".hey-api.config.ts")]
      const configPath = candidates.find((p) => fs.existsSync(p)) || null
      _chosenConfigPath = configPath

      // Skip openapi-ts if SDK generation is disabled and no custom config exists
      const shouldRunOpenApiTs = configPath || typesConfig.generateSdk

      if (fs.existsSync(openapiPath) && shouldRunOpenApiTs) {
        resolvedConfig?.logger.info(`${colors.cyan("•")} Generating TypeScript types...`)
        if (resolvedConfig && configPath) {
          const relConfigPath = formatPath(configPath, resolvedConfig.root)
          resolvedConfig.logger.info(`${colors.cyan("•")} openapi-ts config: ${colors.yellow(relConfigPath)}`)
        }

        // openapi-ts clears its output directory, so we isolate it from our own artifacts.
        const sdkOutput = path.join(typesConfig.output, "api")

        let args: string[]
        if (configPath) {
          args = ["@hey-api/openapi-ts", "--file", configPath]
        } else {
          args = ["@hey-api/openapi-ts", "-i", typesConfig.openapiPath, "-o", sdkOutput]

          const plugins = ["@hey-api/typescript", "@hey-api/schemas"]
          if (typesConfig.generateSdk) {
            plugins.push("@hey-api/sdk", sdkClientPlugin)
          }
          if (typesConfig.generateZod) {
            plugins.push("zod")
          }
          if (plugins.length) {
            args.push("--plugins", ...plugins)
          }
        }

        if (typesConfig.generateZod) {
          try {
            nodeRequire.resolve("zod", { paths: [projectRoot] })
          } catch {
            resolvedConfig?.logger.warn(`${colors.yellow("!")} zod not installed - run: ${resolveInstallHint()} zod`)
          }
        }

        await execAsync(resolvePackageExecutor(args.join(" "), executor), { cwd: projectRoot })
        generated = true
      }

      if (typesConfig.generatePageProps && fs.existsSync(pagePropsPath)) {
        await emitPagePropsTypes(pagePropsPath, typesConfig.output)
        generated = true
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
      if (resolvedConfig) {
        if (message.includes("not found") || message.includes("ENOENT")) {
          const zodHint = typesConfig.generateZod ? " zod" : ""
          resolvedConfig.logger.warn(
            `${colors.cyan("litestar-vite")} ${colors.yellow("@hey-api/openapi-ts not installed")} - run: ${resolveInstallHint()} -D @hey-api/openapi-ts${zodHint}`,
          )
        } else {
          resolvedConfig.logger.error(`${colors.cyan("litestar-vite")} ${colors.red("type generation failed:")} ${message}`)
        }
      }
      return false
    } finally {
      isGenerating = false
    }
  }

  const debouncedRunTypeGeneration = debounce(runTypeGeneration, typesConfig.debounce)

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
          await runTypeGeneration()
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
