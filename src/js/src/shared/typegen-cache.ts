import crypto from "node:crypto"
import fs from "node:fs"
import path from "node:path"

const CACHE_DIR = "node_modules/.cache/litestar-vite"
const CACHE_FILE = "typegen-cache.json"

interface CacheEntry {
  inputHash: string // SHA-256 of openapi.json
  configHash: string // SHA-256 of config file (if exists)
  optionsHash: string // Hash of generator options
  timestamp: number
}

interface CacheData {
  [key: string]: CacheEntry
}

/**
 * Load cache from disk.
 */
async function loadCache(): Promise<CacheData> {
  const cacheFilePath = path.join(CACHE_DIR, CACHE_FILE)
  try {
    const content = await fs.promises.readFile(cacheFilePath, "utf-8")
    return JSON.parse(content)
  } catch {
    return {}
  }
}

/**
 * Save cache to disk.
 */
async function saveCache(cache: CacheData): Promise<void> {
  const cacheFilePath = path.join(CACHE_DIR, CACHE_FILE)
  await fs.promises.mkdir(CACHE_DIR, { recursive: true })
  await fs.promises.writeFile(cacheFilePath, JSON.stringify(cache, null, 2), "utf-8")
}

/**
 * Compute SHA-256 hash of a file.
 */
async function hashFile(filePath: string): Promise<string> {
  try {
    const content = await fs.promises.readFile(filePath)
    return crypto.createHash("sha256").update(content).digest("hex")
  } catch {
    // If file doesn't exist, return empty hash
    return ""
  }
}

/**
 * Compute SHA-256 hash of an object.
 * Keys are sorted for deterministic hashing.
 */
function hashObject(obj: object): string {
  const sorted = JSON.stringify(obj, Object.keys(obj).sort())
  return crypto.createHash("sha256").update(sorted).digest("hex")
}

/**
 * Check if openapi-ts should run based on input cache.
 *
 * @param openapiPath - Path to openapi.json
 * @param configPath - Path to config file (or null)
 * @param options - Generator options
 * @returns true if generation should run, false if cached
 */
export async function shouldRunOpenApiTs(
  openapiPath: string,
  configPath: string | null,
  options: { generateSdk: boolean; generateZod: boolean; plugins: string[] },
): Promise<boolean> {
  const cache = await loadCache()
  const inputHash = await hashFile(openapiPath)
  const configHash = configPath ? await hashFile(configPath) : ""
  const optionsHash = hashObject(options)

  const cacheKey = "openapi-ts"
  const entry = cache[cacheKey]

  if (entry && entry.inputHash === inputHash && entry.configHash === configHash && entry.optionsHash === optionsHash) {
    return false // Skip - inputs unchanged
  }

  // Will run - inputs changed or no cache
  return true
}

/**
 * Update cache after successful openapi-ts run.
 *
 * @param openapiPath - Path to openapi.json
 * @param configPath - Path to config file (or null)
 * @param options - Generator options
 */
export async function updateOpenApiTsCache(
  openapiPath: string,
  configPath: string | null,
  options: { generateSdk: boolean; generateZod: boolean; plugins: string[] },
): Promise<void> {
  const cache = await loadCache()
  cache["openapi-ts"] = {
    inputHash: await hashFile(openapiPath),
    configHash: configPath ? await hashFile(configPath) : "",
    optionsHash: hashObject(options),
    timestamp: Date.now(),
  }
  await saveCache(cache)
}

/**
 * Compute input hash for page props generation.
 *
 * @param pagePropsPath - Path to inertia-pages.json
 * @returns Hash of the input file
 */
export async function computePagePropsHash(pagePropsPath: string): Promise<string> {
  return hashFile(pagePropsPath)
}

/**
 * Check if page props types should be regenerated.
 *
 * @param pagePropsPath - Path to inertia-pages.json
 * @returns true if generation should run, false if cached
 */
export async function shouldRegeneratePageProps(pagePropsPath: string): Promise<boolean> {
  const cache = await loadCache()
  const currentHash = await hashFile(pagePropsPath)

  const cacheKey = "page-props"
  const entry = cache[cacheKey]

  if (entry && entry.inputHash === currentHash) {
    return false // Skip - input unchanged
  }

  return true
}

/**
 * Update cache after successful page props generation.
 *
 * @param pagePropsPath - Path to inertia-pages.json
 */
export async function updatePagePropsCache(pagePropsPath: string): Promise<void> {
  const cache = await loadCache()
  cache["page-props"] = {
    inputHash: await hashFile(pagePropsPath),
    configHash: "",
    optionsHash: "",
    timestamp: Date.now(),
  }
  await saveCache(cache)
}
