/**
 * CSRF token utilities for Litestar applications.
 *
 * The CSRF token is injected into the page by Litestar in one of these ways:
 * 1. window.__LITESTAR_CSRF__ (SPA mode)
 * 2. <meta name="csrf-token" content="..."> (template mode)
 * 3. Inertia shared props (Inertia mode)
 *
 * @module
 */

declare global {
  interface Window {
    __LITESTAR_CSRF__?: string
  }
}

/**
 * Get the CSRF token from the page.
 *
 * Checks multiple sources in order:
 * 1. window.__LITESTAR_CSRF__ (injected by SPA handler)
 * 2. <meta name="csrf-token"> element
 * 3. Inertia page props (if Inertia is present)
 *
 * @returns The CSRF token or empty string if not found
 *
 * @example
 * ```ts
 * import { getCsrfToken } from 'litestar-vite-plugin/helpers'
 *
 * fetch('/api/submit', {
 *   method: 'POST',
 *   headers: {
 *     'X-CSRF-Token': getCsrfToken(),
 *   },
 *   body: JSON.stringify(data),
 * })
 * ```
 */
export function getCsrfToken(): string {
  // Check window global (SPA mode)
  if (typeof window !== "undefined" && window.__LITESTAR_CSRF__) {
    return window.__LITESTAR_CSRF__
  }

  // Check meta tag (template mode)
  if (typeof document !== "undefined") {
    const meta = document.querySelector('meta[name="csrf-token"]')
    if (meta) {
      return meta.getAttribute("content") || ""
    }
  }

  // Check Inertia page props
  if (typeof window !== "undefined") {
    const win = window as unknown as Record<string, unknown>
    const inertiaPage = win.__INERTIA_PAGE__ as Record<string, unknown> | undefined
    if (inertiaPage?.props) {
      const props = inertiaPage.props as Record<string, unknown>
      if (typeof props.csrf_token === "string") {
        return props.csrf_token
      }
    }
  }

  return ""
}

/**
 * Create headers object with CSRF token included.
 *
 * @param additionalHeaders - Additional headers to include
 * @returns Headers object with X-CSRF-Token set
 *
 * @example
 * ```ts
 * import { csrfHeaders } from 'litestar-vite-plugin/helpers'
 *
 * fetch('/api/submit', {
 *   method: 'POST',
 *   headers: csrfHeaders({ 'Content-Type': 'application/json' }),
 *   body: JSON.stringify(data),
 * })
 * ```
 */
export function csrfHeaders(additionalHeaders: Record<string, string> = {}): Record<string, string> {
  const token = getCsrfToken()
  return {
    ...additionalHeaders,
    ...(token ? { "X-CSRF-Token": token } : {}),
  }
}

/**
 * Create a fetch wrapper that automatically includes CSRF token.
 *
 * @param input - Request URL or Request object
 * @param init - Request options
 * @returns Fetch response promise
 *
 * @example
 * ```ts
 * import { csrfFetch } from 'litestar-vite-plugin/helpers'
 *
 * // Automatically includes CSRF token
 * csrfFetch('/api/submit', {
 *   method: 'POST',
 *   body: JSON.stringify(data),
 * })
 * ```
 */
export function csrfFetch(input: RequestInfo | URL, init?: RequestInit): Promise<Response> {
  const token = getCsrfToken()

  if (!token) {
    return fetch(input, init)
  }

  const headers = new Headers(init?.headers)
  if (!headers.has("X-CSRF-Token")) {
    headers.set("X-CSRF-Token", token)
  }

  return fetch(input, {
    ...init,
    headers,
  })
}
