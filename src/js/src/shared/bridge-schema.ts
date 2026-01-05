/**
 * Canonical bridge schema for `.litestar.json`.
 *
 * This is the single source of truth on the TypeScript side for the config
 * contract emitted by the Python VitePlugin.
 *
 * The project is pre-1.0: no legacy keys, no fallbacks, fail-fast on mismatch.
 *
 * @module
 */

import fs from "node:fs"
import path from "node:path"

export type BridgeMode = "spa" | "template" | "htmx" | "hybrid" | "inertia" | "framework" | "ssr" | "ssg" | "external"
export type BridgeProxyMode = "vite" | "direct" | "proxy" | null
export type BridgeExecutor = "node" | "bun" | "deno" | "yarn" | "pnpm"

export interface BridgeTypesConfig {
  enabled: boolean
  output: string
  openapiPath: string
  routesPath: string
  pagePropsPath: string
  routesTsPath?: string
  schemasTsPath?: string
  generateZod: boolean
  generateSdk: boolean
  generateRoutes: boolean
  generatePageProps: boolean
  generateSchemas: boolean
  globalRoute: boolean
}

export interface BridgeSpaConfig {
  /** Use script element instead of data-page attribute for Inertia page data */
  useScriptElement: boolean
}

export interface BridgeSchema {
  assetUrl: string
  deployAssetUrl: string | null
  bundleDir: string
  resourceDir: string
  staticDir: string
  hotFile: string
  manifest: string

  mode: BridgeMode
  proxyMode: BridgeProxyMode
  host: string
  port: number

  ssrOutDir: string | null

  types: BridgeTypesConfig | null

  spa: BridgeSpaConfig | null

  executor: BridgeExecutor

  logging: {
    level: "quiet" | "normal" | "verbose"
    showPathsAbsolute: boolean
    suppressNpmOutput: boolean
    suppressViteBanner: boolean
    timestamps: boolean
  } | null

  litestarVersion: string
}

const allowedTopLevelKeys: ReadonlySet<string> = new Set([
  "assetUrl",
  "deployAssetUrl",
  "bundleDir",
  "resourceDir",
  "staticDir",
  "hotFile",
  "manifest",
  "mode",
  "proxyMode",
  "host",
  "port",
  "ssrOutDir",
  "types",
  "spa",
  "executor",
  "logging",
  "litestarVersion",
])

const allowedModes: ReadonlySet<string> = new Set(["spa", "template", "htmx", "hybrid", "inertia", "framework", "ssr", "ssg", "external"])
const allowedProxyModes: ReadonlySet<string> = new Set(["vite", "direct", "proxy"])
const allowedExecutors: ReadonlySet<string> = new Set(["node", "bun", "deno", "yarn", "pnpm"])
const allowedLogLevels: ReadonlySet<string> = new Set(["quiet", "normal", "verbose"])

function fail(message: string): never {
  throw new Error(`litestar-vite-plugin: invalid .litestar.json - ${message}`)
}

function assertObject(value: unknown, label: string): Record<string, unknown> {
  if (!value || typeof value !== "object" || Array.isArray(value)) {
    fail(`${label} must be an object`)
  }
  return value as Record<string, unknown>
}

function assertString(obj: Record<string, unknown>, key: string): string {
  const value = obj[key]
  if (typeof value !== "string" || value.length === 0) {
    fail(`"${key}" must be a non-empty string`)
  }
  return value
}

function assertBoolean(obj: Record<string, unknown>, key: string): boolean {
  const value = obj[key]
  if (typeof value !== "boolean") {
    fail(`"${key}" must be a boolean`)
  }
  return value
}

function assertNumber(obj: Record<string, unknown>, key: string): number {
  const value = obj[key]
  if (typeof value !== "number" || Number.isNaN(value)) {
    fail(`"${key}" must be a number`)
  }
  return value
}

function assertNullableString(obj: Record<string, unknown>, key: string): string | null {
  const value = obj[key]
  if (value === null) return null
  if (typeof value !== "string") {
    fail(`"${key}" must be a string or null`)
  }
  return value
}

function assertOptionalString(obj: Record<string, unknown>, key: string): string | undefined {
  const value = obj[key]
  if (value === undefined) return undefined
  if (typeof value !== "string" || value.length === 0) {
    fail(`"${key}" must be a non-empty string`)
  }
  return value
}

function assertEnum<T extends string>(value: unknown, key: string, allowed: ReadonlySet<string>): T {
  if (typeof value !== "string" || !allowed.has(value)) {
    fail(`"${key}" must be one of: ${Array.from(allowed).join(", ")}`)
  }
  return value as T
}

function assertProxyMode(value: unknown): BridgeProxyMode {
  if (value === null) return null
  return assertEnum<Exclude<BridgeProxyMode, null>>(value, "proxyMode", allowedProxyModes)
}

function assertOptionalBoolean(obj: Record<string, unknown>, key: string, defaultValue: boolean): boolean {
  const value = obj[key]
  if (value === undefined) return defaultValue
  if (typeof value !== "boolean") {
    fail(`"${key}" must be a boolean`)
  }
  return value
}

function parseTypesConfig(value: unknown): BridgeTypesConfig | null {
  if (value === null) return null
  const obj = assertObject(value, "types")

  const enabled = assertBoolean(obj, "enabled")
  const output = assertString(obj, "output")
  const openapiPath = assertString(obj, "openapiPath")
  const routesPath = assertString(obj, "routesPath")
  const pagePropsPath = assertString(obj, "pagePropsPath")
  const routesTsPath = assertOptionalString(obj, "routesTsPath")
  const schemasTsPath = assertOptionalString(obj, "schemasTsPath")
  const generateZod = assertBoolean(obj, "generateZod")
  const generateSdk = assertBoolean(obj, "generateSdk")
  const generateRoutes = assertBoolean(obj, "generateRoutes")
  const generatePageProps = assertBoolean(obj, "generatePageProps")
  const generateSchemas = assertOptionalBoolean(obj, "generateSchemas", true) // Default to true for backward compatibility
  const globalRoute = assertBoolean(obj, "globalRoute")

  return {
    enabled,
    output,
    openapiPath,
    routesPath,
    pagePropsPath,
    routesTsPath,
    schemasTsPath,
    generateZod,
    generateSdk,
    generateRoutes,
    generatePageProps,
    generateSchemas,
    globalRoute,
  }
}

function parseLogging(value: unknown): BridgeSchema["logging"] {
  if (value === null) return null
  const obj = assertObject(value, "logging")

  const level = assertEnum<"quiet" | "normal" | "verbose">(obj.level, "logging.level", allowedLogLevels)
  const showPathsAbsolute = assertBoolean(obj, "showPathsAbsolute")
  const suppressNpmOutput = assertBoolean(obj, "suppressNpmOutput")
  const suppressViteBanner = assertBoolean(obj, "suppressViteBanner")
  const timestamps = assertBoolean(obj, "timestamps")

  return { level, showPathsAbsolute, suppressNpmOutput, suppressViteBanner, timestamps }
}

function parseSpaConfig(value: unknown): BridgeSpaConfig | null {
  if (value === null || value === undefined) return null
  const obj = assertObject(value, "spa")

  const useScriptElement = assertBoolean(obj, "useScriptElement")

  return { useScriptElement }
}

export function parseBridgeSchema(value: unknown): BridgeSchema {
  const obj = assertObject(value, "root")

  for (const key of Object.keys(obj)) {
    if (!allowedTopLevelKeys.has(key)) {
      fail(`unknown top-level key "${key}"`)
    }
  }

  const assetUrl = assertString(obj, "assetUrl")
  const deployAssetUrl = assertNullableString(obj, "deployAssetUrl")
  const bundleDir = assertString(obj, "bundleDir")
  const resourceDir = assertString(obj, "resourceDir")
  const staticDir = assertString(obj, "staticDir")
  const hotFile = assertString(obj, "hotFile")
  const manifest = assertString(obj, "manifest")

  const mode = assertEnum<BridgeMode>(obj.mode, "mode", allowedModes)
  const proxyMode = assertProxyMode(obj.proxyMode)
  const host = assertString(obj, "host")
  const port = assertNumber(obj, "port")

  const ssrOutDir = assertNullableString(obj, "ssrOutDir")

  const types = parseTypesConfig(obj.types)
  const spa = parseSpaConfig(obj.spa)
  const executor = assertEnum<BridgeExecutor>(obj.executor, "executor", allowedExecutors)
  const logging = parseLogging(obj.logging)
  const litestarVersion = assertString(obj, "litestarVersion")

  return {
    assetUrl,
    deployAssetUrl,
    bundleDir,
    resourceDir,
    staticDir,
    hotFile,
    manifest,
    mode,
    proxyMode,
    host,
    port,
    ssrOutDir,
    types,
    spa,
    executor,
    logging,
    litestarVersion,
  }
}

export function readBridgeConfig(explicitPath?: string): BridgeSchema | null {
  const envPath = explicitPath ?? process.env.LITESTAR_VITE_CONFIG_PATH
  if (envPath) {
    if (!fs.existsSync(envPath)) {
      return null
    }
    return readBridgeConfigFile(envPath)
  }

  const defaultPath = path.join(process.cwd(), ".litestar.json")
  if (fs.existsSync(defaultPath)) {
    return readBridgeConfigFile(defaultPath)
  }

  return null
}

function readBridgeConfigFile(filePath: string): BridgeSchema {
  let raw: unknown
  try {
    raw = JSON.parse(fs.readFileSync(filePath, "utf-8")) as unknown
  } catch (e) {
    const msg = e instanceof Error ? e.message : String(e)
    fail(`failed to parse JSON (${msg})`)
  }

  return parseBridgeSchema(raw)
}
