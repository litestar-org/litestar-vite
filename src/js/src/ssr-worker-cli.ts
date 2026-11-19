import fs from "node:fs"
import path from "node:path"
import { fileURLToPath } from "node:url"
import { readBridgeConfig } from "./shared/bridge-schema.js"
import { type SsrWorkerOptions, startSsrWorker } from "./ssr-worker.js"

function normalizeNonEmpty(value: string | null | undefined): string | undefined {
  if (typeof value !== "string") {
    return undefined
  }
  const trimmed = value.trim()
  return trimmed.length > 0 ? trimmed : undefined
}

function normalizeToken(value: string | null | undefined): string | undefined {
  return typeof value === "string" && value.length > 0 ? value : undefined
}

/** Resolve SSR worker options from CLI flags, environment variables, and bridge configuration. */
export function resolveSsrWorkerCliOptions(argv: readonly string[] = process.argv.slice(2), env: NodeJS.ProcessEnv = process.env): SsrWorkerOptions {
  let cliSsrDir: string | undefined
  let cliAuthToken: string | undefined

  for (let i = 0; i < argv.length; i += 1) {
    const arg = argv[i]
    if (arg === "--") {
      break
    }
    if (arg === "--ssr-dir") {
      const value = argv[i + 1]
      if (value !== undefined) {
        cliSsrDir = value
        i += 1
      }
    } else if (arg.startsWith("--ssr-dir=")) {
      cliSsrDir = arg.slice("--ssr-dir=".length)
    } else if (arg === "--auth-token") {
      const value = argv[i + 1]
      if (value !== undefined) {
        cliAuthToken = value
        i += 1
      }
    } else if (arg.startsWith("--auth-token=")) {
      cliAuthToken = arg.slice("--auth-token=".length)
    }
  }

  const bridgeConfigPath = normalizeNonEmpty(env.LITESTAR_VITE_CONFIG_PATH) ?? (env === process.env ? undefined : path.join(process.cwd(), ".litestar.json"))
  const ssrDir = normalizeNonEmpty(cliSsrDir) ?? normalizeNonEmpty(env.LITESTAR_SSR_DIR) ?? normalizeNonEmpty(readBridgeConfig(bridgeConfigPath)?.ssrOutDir)
  const authToken = normalizeToken(cliAuthToken) ?? normalizeToken(env.LITESTAR_SSR_AUTH_TOKEN)

  const options: SsrWorkerOptions = {}
  if (ssrDir !== undefined) {
    options.ssrDir = ssrDir
  }
  if (authToken !== undefined) {
    options.authToken = authToken
  }
  return options
}

/** Determine whether this module is the active CLI entrypoint, resolving symlinked bin paths. */
export function isDirectCliInvocation(argv1: string | undefined = process.argv[1], moduleUrl = import.meta.url): boolean {
  if (!argv1) {
    return false
  }
  const entryPath = path.resolve(argv1)
  const modulePath = path.resolve(fileURLToPath(moduleUrl))
  try {
    return fs.realpathSync(entryPath) === fs.realpathSync(modulePath)
  } catch {
    return entryPath === modulePath
  }
}

if (isDirectCliInvocation()) {
  startSsrWorker(resolveSsrWorkerCliOptions())
}
