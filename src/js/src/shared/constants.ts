/**
 * Shared constants for litestar-vite plugin.
 *
 * Centralizes magic values that are reused across multiple modules.
 */

/**
 * Default debounce time in milliseconds for type regeneration.
 *
 * Used across all framework integrations (Vite, Nuxt, Astro, SvelteKit)
 * to avoid excessive regeneration during rapid file changes.
 */
export const DEBOUNCE_MS = 300

/**
 * Timeout in milliseconds for backend health checks.
 *
 * Used when checking if the Litestar backend is available
 * before attempting to fetch OpenAPI schema.
 */
export const BACKEND_CHECK_TIMEOUT_MS = 2000

/**
 * Default asset URL path.
 *
 * Used as fallback when no explicit assetUrl is configured.
 * Should match the default in Python ViteConfig.
 */
export const DEFAULT_ASSET_URL = "/static/"

/**
 * Default output directory for generated TypeScript types.
 *
 * Used by framework integrations as fallback when no output
 * is specified in Python bridge config or plugin options.
 */
export const DEFAULT_TYPES_OUTPUT = "src/generated"

/**
 * Pinned fallback package spec for @hey-api/openapi-ts.
 *
 * Keep this in sync with CURRENT_NPM_VERSION_RANGES in the Python scaffold
 * registry and the optional peer dependency range in package.json.
 */
export const HEY_API_PINNED_SPEC = "@hey-api/openapi-ts@0.98.2"
