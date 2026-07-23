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
 * Pinned fallback package specs for the type generator.
 *
 * Keep this in sync with CURRENT_NPM_VERSION_RANGES in the Python scaffold
 * registry. @hey-api/openapi-ts uses the TypeScript compiler API and is not
 * currently compatible with TypeScript 7.
 */
export const HEY_API_PINNED_SPEC = "@hey-api/openapi-ts@0.98.2"
export const TYPESCRIPT_PINNED_SPEC = "typescript@6.0.3"
export const TYPEGEN_FALLBACK_PACKAGE_SPECS = [HEY_API_PINNED_SPEC, TYPESCRIPT_PINNED_SPEC] as const
