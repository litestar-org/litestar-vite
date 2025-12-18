/**
 * Base types for Inertia.js module augmentation.
 *
 * This module provides empty interfaces that can be extended by generated
 * page-props.ts or user module augmentation.
 *
 * @example
 * // In your app's global.d.ts or types/index.d.ts:
 * declare module 'litestar-vite-plugin/inertia' {
 *   interface User {
 *     avatarUrl?: string | null
 *     roles: Role[]
 *   }
 *   interface SharedProps {
 *     locale?: string
 *     currentTeam?: Team
 *   }
 * }
 */

/** User interface - extend via module augmentation */
// biome-ignore lint/suspicious/noEmptyInterface: Empty interface for module augmentation
export interface User {}

/** Authentication data interface - extend via module augmentation */
// biome-ignore lint/suspicious/noEmptyInterface: Empty interface for module augmentation
export interface AuthData {}

/** Flash messages interface - extend via module augmentation */
// biome-ignore lint/suspicious/noEmptyInterface: Empty interface for module augmentation
export interface FlashMessages {}

/** User-defined shared props - extend via module augmentation */
// biome-ignore lint/suspicious/noEmptyInterface: Empty interface for module augmentation
export interface SharedProps {}

/** Generated shared props (populated by page-props.ts) */
// biome-ignore lint/suspicious/noEmptyInterface: Empty interface for module augmentation
export interface GeneratedSharedProps {}

/** Full shared props = generated + user-defined */
export type FullSharedProps = GeneratedSharedProps & SharedProps & { [key: string]: unknown }

/** Page props mapped by component name (populated by page-props.ts) */
// biome-ignore lint/suspicious/noEmptyInterface: Empty interface for module augmentation
export interface PageProps {}

/** Component name union type */
export type ComponentName = keyof PageProps

/** Type-safe props for a specific component */
export type InertiaPageProps<C extends ComponentName> = PageProps[C]

/** Get props type for a specific page component */
export type PagePropsFor<C extends ComponentName> = PageProps[C]
