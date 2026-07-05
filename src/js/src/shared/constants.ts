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
 * Pinned fallback package spec for @hey-api/openapi-ts.
 *
 * Keep this in sync with CURRENT_NPM_VERSION_RANGES in the Python scaffold
 * registry and the optional peer dependency range in package.json.
 */
export const HEY_API_PINNED_SPEC = "@hey-api/openapi-ts@0.98.2"
