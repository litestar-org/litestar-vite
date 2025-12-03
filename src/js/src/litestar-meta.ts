import fs from "node:fs"
import path from "node:path"
import type { ResolvedConfig } from "vite"

export interface LitestarMeta {
  litestarVersion?: string
}

export interface BackendStatus {
  available: boolean
  url?: string
  error?: string
}

/**
 * Check if the Litestar backend is reachable at the given URL.
 *
 * Uses a GET request to the OpenAPI schema endpoint as a lightweight
 * health check, since it's typically enabled and responds quickly.
 * The schema path is read from LITESTAR_OPENAPI_PATH env var (default: "/schema").
 */
export async function checkBackendAvailability(appUrl: string | null): Promise<BackendStatus> {
  if (!appUrl || appUrl === "undefined") {
    return {
      available: false,
      error: "APP_URL not configured",
    }
  }

  try {
    const controller = new AbortController()
    const timeout = setTimeout(() => controller.abort(), 2000)

    // Use OpenAPI schema endpoint as a lightweight health check
    // The path is configurable via LITESTAR_OPENAPI_PATH (set by Python plugin)
    const schemaPath = process.env.LITESTAR_OPENAPI_PATH || "/schema"
    const urlObj = new URL(schemaPath, appUrl)
    if (urlObj.hostname === "0.0.0.0") {
      urlObj.hostname = "127.0.0.1"
    }
    const checkUrl = urlObj.href
    const response = await fetch(checkUrl, {
      method: "GET",
      signal: controller.signal,
    })
    clearTimeout(timeout)

    return {
      available: response.ok || response.status < 500,
      url: appUrl,
    }
  } catch (err) {
    const message = err instanceof Error ? err.message : String(err)
    // Connection refused typically means the server isn't running
    if (message.includes("ECONNREFUSED") || message.includes("fetch failed")) {
      return {
        available: false,
        url: appUrl,
        error: "Backend not reachable (is Litestar running?)",
      }
    }
    // Aborted means timeout
    if (message.includes("aborted")) {
      return {
        available: false,
        url: appUrl,
        error: "Backend connection timeout",
      }
    }
    return {
      available: false,
      url: appUrl,
      error: message,
    }
  }
}

function readJson(file: string): Record<string, unknown> | null {
  try {
    const raw = fs.readFileSync(file, "utf8")
    return JSON.parse(raw) as Record<string, unknown>
  } catch {
    return null
  }
}

function firstExisting(paths: string[]): string | null {
  for (const p of paths) {
    if (fs.existsSync(p)) return p
  }
  return null
}

function loadVersionFromRuntimeConfig(): string | null {
  const cfgPath = process.env.LITESTAR_VITE_CONFIG_PATH
  if (!cfgPath || !fs.existsSync(cfgPath)) return null
  try {
    const raw = fs.readFileSync(cfgPath, "utf8")
    const data = JSON.parse(raw) as Record<string, unknown>
    const v = data?.litestarVersion
    return typeof v === "string" && v.trim() ? v.trim() : null
  } catch {
    return null
  }
}

export async function loadLitestarMeta(resolvedConfig: ResolvedConfig, routesPathHint?: string): Promise<LitestarMeta> {
  const fromEnv = process.env.LITESTAR_VERSION?.trim()
  if (fromEnv) return { litestarVersion: fromEnv }

  const fromRuntime = loadVersionFromRuntimeConfig()
  if (fromRuntime) return { litestarVersion: fromRuntime }

  const root = resolvedConfig.root ?? process.cwd()
  const candidates = [routesPathHint ? path.resolve(root, routesPathHint) : null, path.resolve(root, "src/generated/routes.json"), path.resolve(root, "routes.json")].filter(
    Boolean,
  ) as string[]

  const match = firstExisting(candidates)
  if (!match) return {}

  const data = readJson(match)
  if (!data) return {}

  const fromData = (key: string): string | null => {
    const value = (data as Record<string, unknown>)[key]
    return typeof value === "string" ? value : null
  }

  const litestarVersion: string | null = fromData("litestar_version") ?? fromData("litestarVersion") ?? fromData("version")

  return litestarVersion ? { litestarVersion } : {}
}
