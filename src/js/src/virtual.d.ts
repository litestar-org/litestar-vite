/**
 * Type declarations for litestar-vite virtual modules.
 *
 * To use these types in your project, add a triple-slash reference in your
 * vite-env.d.ts or a global declaration file:
 *
 * ```ts
 * /// <reference types="litestar-vite-plugin/virtual" />
 * ```
 *
 * Or include it in your tsconfig.json:
 *
 * ```json
 * {
 *   "compilerOptions": {
 *     "types": ["litestar-vite-plugin/virtual"]
 *   }
 * }
 * ```
 *
 * For type-safe static props, augment the StaticProps interface:
 *
 * ```ts
 * declare module 'virtual:litestar-static-props' {
 *   interface StaticProps {
 *     appName: string
 *     version: string
 *     features: {
 *       darkMode: boolean
 *       analytics: boolean
 *     }
 *   }
 *   export default StaticProps
 * }
 * ```
 *
 * @module virtual
 */

/**
 * Static props configured in Python ViteConfig.static_props.
 *
 * This interface can be augmented in user code to provide type-safe access
 * to static props.
 */
export interface StaticProps {
  [key: string]: unknown
}

declare module "virtual:litestar-static-props" {
  const props: StaticProps
  export default props
  export { props as staticProps }
}
