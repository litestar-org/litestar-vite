/**
 * Inertia.js helpers for Litestar applications.
 *
 * This module provides Inertia-specific runtime utilities.
 * For CSRF utilities, import from `litestar-vite-plugin/helpers`.
 *
 * For type-safe routing, import from your generated routes file:
 * ```ts
 * import { route, routeDefinitions, type RouteName } from '@/generated/routes'
 * ```
 *
 * @module
 */

/**
 * Unwrap page props that may have content nested under "content" key.
 *
 * Litestar wraps route return values under `content`. This utility
 * spreads the content at the top level for ergonomic prop access.
 *
 * @param props - The raw page props from Inertia
 * @returns Props with content unwrapped if applicable
 */
export function unwrapPageProps<T extends Record<string, unknown>>(props: T): T {
  if (props.content !== undefined && props.content !== null && typeof props.content === "object" && !Array.isArray(props.content)) {
    const { content, ...rest } = props
    return { ...rest, ...(content as Record<string, unknown>) } as T
  }
  return props
}

/**
 * Wrap a component to automatically unwrap Litestar's content prop.
 *
 * @param component - The original component (function or object with default)
 * @returns Wrapped component that transforms props
 */
function wrapComponent<T>(module: T): T {
  // Handle ES module with default export
  const mod = module as Record<string, unknown>
  if (mod.default && typeof mod.default === "function") {
    const Original = mod.default as (props: Record<string, unknown>) => unknown
    const Wrapped = (props: Record<string, unknown>) => Original(unwrapPageProps(props))
    // Copy static properties (displayName, layout, etc.)
    Object.assign(Wrapped, Original)
    return { ...mod, default: Wrapped } as T
  }
  // Handle direct function export
  if (typeof module === "function") {
    const Original = module as unknown as (props: Record<string, unknown>) => unknown
    const Wrapped = (props: Record<string, unknown>) => Original(unwrapPageProps(props))
    Object.assign(Wrapped, Original)
    return Wrapped as T
  }
  return module
}

/**
 * Resolve a page component from a glob import.
 *
 * Used with Inertia.js to dynamically import page components.
 * Automatically unwraps Litestar's `content` prop for ergonomic access.
 *
 * @param path - Component path or array of paths to try
 * @param pages - Glob import result (e.g., import.meta.glob('./pages/**\/*.vue'))
 * @returns Promise resolving to the component
 * @throws Error if no matching component is found
 *
 * @example
 * ```ts
 * import { resolvePageComponent } from 'litestar-vite-plugin/inertia-helpers'
 *
 * createInertiaApp({
 *   resolve: (name) => resolvePageComponent(
 *     `./pages/${name}.vue`,
 *     import.meta.glob('./pages/**\/*.vue')
 *   ),
 *   // ...
 * })
 * ```
 */
export async function resolvePageComponent<T>(path: string | string[], pages: Record<string, Promise<T> | (() => Promise<T>)>): Promise<T> {
  for (const p of Array.isArray(path) ? path : [path]) {
    const page = pages[p]

    if (typeof page === "undefined") {
      continue
    }

    const resolved = typeof page === "function" ? await page() : await page
    return wrapComponent(resolved)
  }

  throw new Error(`Page not found: ${path}`)
}

// ============================================================================
// Pagination Types
// ============================================================================

/**
 * Offset-based pagination props.
 *
 * Returned when a route returns Litestar's `OffsetPagination` type.
 * Contains items plus metadata for offset/limit pagination.
 *
 * @example
 * ```ts
 * interface User { id: string; name: string }
 * const { items, total, limit, offset } = props.users as OffsetPaginationProps<User>
 * ```
 */
export interface OffsetPaginationProps<T> {
  /** The paginated items for the current page */
  items: T[]
  /** Total number of items across all pages */
  total: number
  /** Maximum items per page (page size) */
  limit: number
  /** Number of items skipped (offset from start) */
  offset: number
}

/**
 * Classic page-based pagination props.
 *
 * Returned when a route returns Litestar's `ClassicPagination` type.
 * Contains items plus metadata for page number pagination.
 *
 * @example
 * ```ts
 * interface Post { id: string; title: string }
 * const { items, currentPage, totalPages, pageSize } = props.posts as ClassicPaginationProps<Post>
 * ```
 */
export interface ClassicPaginationProps<T> {
  /** The paginated items for the current page */
  items: T[]
  /** Current page number (1-indexed) */
  currentPage: number
  /** Total number of pages */
  totalPages: number
  /** Number of items per page */
  pageSize: number
}

/**
 * Cursor-based pagination props.
 *
 * Used for cursor/keyset pagination, commonly with infinite scroll.
 * Contains items plus cursor tokens for navigation.
 *
 * @example
 * ```ts
 * interface Message { id: string; content: string }
 * const { items, hasMore, nextCursor } = props.messages as CursorPaginationProps<Message>
 * if (hasMore && nextCursor) {
 *   // Fetch more with cursor
 * }
 * ```
 */
export interface CursorPaginationProps<T> {
  /** The paginated items for the current page */
  items: T[]
  /** Total number of items (if known) */
  total?: number
  /** Whether more items exist after the current page */
  hasMore?: boolean
  /** Whether a next page exists */
  hasNext?: boolean
  /** Whether a previous page exists */
  hasPrevious?: boolean
  /** Cursor token for fetching the next page */
  nextCursor?: string | null
  /** Cursor token for fetching the previous page */
  previousCursor?: string | null
}

/**
 * Union type for any pagination props.
 *
 * Use when you need to handle multiple pagination styles.
 *
 * @example
 * ```ts
 * function renderPagination<T>(data: PaginationProps<T>) {
 *   if ('offset' in data) {
 *     // Handle offset pagination
 *   } else if ('currentPage' in data) {
 *     // Handle classic pagination
 *   } else {
 *     // Handle cursor pagination
 *   }
 * }
 * ```
 */
export type PaginationProps<T> = OffsetPaginationProps<T> | ClassicPaginationProps<T> | CursorPaginationProps<T>

// ============================================================================
// Infinite Scroll Types (Inertia v2)
// ============================================================================

/**
 * Scroll props configuration for Inertia v2 infinite scroll.
 *
 * Returned in the `scrollProps` field of an Inertia response when
 * `infinite_scroll=True` is set on the route.
 *
 * @example
 * ```ts
 * // In your Inertia page component
 * import { usePage } from '@inertiajs/vue3'
 *
 * const page = usePage()
 * const scrollProps = page.props.scrollProps as ScrollProps
 *
 * function loadMore() {
 *   if (scrollProps.nextPage) {
 *     router.get(url, { [scrollProps.pageName]: scrollProps.nextPage })
 *   }
 * }
 * ```
 */
export interface ScrollProps {
  /** Query parameter name for page number (default: "page") */
  pageName: string
  /** Current page number */
  currentPage: number
  /** Previous page number, or null if on first page */
  previousPage: number | null
  /** Next page number, or null if on last page */
  nextPage: number | null
}

// ============================================================================
// Precognition Types (Laravel Precognition Protocol)
// ============================================================================

/**
 * HTTP headers used by the Precognition protocol.
 *
 * These headers enable real-time form validation without executing
 * handler side effects. Compatible with Laravel's laravel-precognition
 * frontend libraries.
 *
 * @example
 * ```ts
 * // Sending a Precognition request
 * fetch('/users', {
 *   method: 'POST',
 *   headers: {
 *     [PrecognitionHeaders.PRECOGNITION]: 'true',
 *     [PrecognitionHeaders.VALIDATE_ONLY]: 'email,password',
 *   },
 *   body: JSON.stringify({ email: 'test@example.com', password: '123' })
 * })
 * ```
 */
export const PrecognitionHeaders = {
  /** Indicates this is a Precognition validation request */
  PRECOGNITION: "Precognition",
  /** Returned on successful validation (204 response) */
  PRECOGNITION_SUCCESS: "Precognition-Success",
  /** Comma-separated list of fields to validate (partial validation) */
  VALIDATE_ONLY: "Precognition-Validate-Only",
} as const

/**
 * Validation error format returned by Precognition responses.
 *
 * Follows Laravel's validation error format for compatibility
 * with laravel-precognition-vue and laravel-precognition-react.
 *
 * @example
 * ```ts
 * // Error response from server (422)
 * const response: PrecognitionValidationErrors = {
 *   message: "The given data was invalid.",
 *   errors: {
 *     email: ["The email field is required."],
 *     password: ["The password must be at least 8 characters."]
 *   }
 * }
 * ```
 */
export interface PrecognitionValidationErrors {
  /** Human-readable error message */
  message: string
  /** Map of field names to array of error messages */
  errors: Record<string, string[]>
}

/**
 * Configuration options for Precognition forms.
 *
 * Use with laravel-precognition-vue or laravel-precognition-react.
 *
 * @example
 * ```ts
 * // Vue 3
 * import { useForm } from 'laravel-precognition-vue'
 *
 * const form = useForm('post', '/users', {
 *   email: '',
 *   password: '',
 * }, {
 *   validationTimeout: 500,
 *   onSuccess: () => { ... }
 * })
 * ```
 */
export interface PrecognitionFormConfig {
  /**
   * Debounce timeout in milliseconds before sending validation request.
   * Helps prevent excessive requests during rapid typing.
   *
   * Default varies by library, typically 300-500ms.
   */
  validationTimeout?: number

  /**
   * Callback when form submission succeeds.
   */
  onSuccess?: () => void

  /**
   * Callback when form submission fails with validation errors.
   */
  onValidationError?: (errors: PrecognitionValidationErrors) => void

  /**
   * Callback before each Precognition request.
   * Return false to cancel the request.
   */
  onBefore?: () => boolean | undefined

  /**
   * Callback after each Precognition request completes.
   */
  onFinish?: () => void
}

/**
 * Check if a response is a successful Precognition validation.
 *
 * @param response - Fetch Response object
 * @returns True if this is a successful Precognition response (204 with header)
 */
export function isPrecognitionSuccess(response: Response): boolean {
  return response.status === 204 && response.headers.get(PrecognitionHeaders.PRECOGNITION_SUCCESS) === "true"
}

/**
 * Check if a response is a Precognition validation error.
 *
 * @param response - Fetch Response object
 * @returns True if this is a Precognition validation error (422 with header)
 */
export function isPrecognitionError(response: Response): boolean {
  return response.status === 422 && response.headers.get(PrecognitionHeaders.PRECOGNITION) === "true"
}

/**
 * Extract validation errors from a Precognition error response.
 *
 * @param response - Fetch Response object (must be a Precognition error)
 * @returns Promise resolving to validation errors
 * @throws If response is not valid JSON
 */
export async function extractPrecognitionErrors(response: Response): Promise<PrecognitionValidationErrors> {
  return response.json() as Promise<PrecognitionValidationErrors>
}
