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

interface CsrfTokenCache {
  token: string
  windowToken?: string
  metaToken?: string
  inertiaToken?: string
}

let csrfTokenCache: CsrfTokenCache | null = null
export const DEFAULT_CSRF_HEADER_NAME = "X-CSRFToken"

function getWindowToken(): string | undefined {
  if (typeof window !== "undefined") {
    return window.__LITESTAR_CSRF__
  }

  return undefined
}

function getMetaToken(): string | undefined {
  if (typeof document !== "undefined") {
    const meta = document.querySelector('meta[name="csrf-token"]')
    if (meta) {
      const content = meta.getAttribute("content")
      if (content !== null && content.length > 0) {
        return content
      }
    }
  }

  return undefined
}

function getInertiaToken(): string | undefined {
  if (typeof window === "undefined") {
    return undefined
  }

  const win = window as unknown as Record<string, unknown>
  const inertiaPage = win.__INERTIA_PAGE__ as Record<string, unknown> | undefined
  if (inertiaPage?.props) {
    const props = inertiaPage.props as Record<string, unknown>
    if (typeof props.csrf_token === "string") {
      return props.csrf_token
    }
  }

  return undefined
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
 *     'X-CSRFToken': getCsrfToken(),
 *   },
 *   body: JSON.stringify(data),
 * })
 * ```
 */
export function getCsrfToken(): string {
  const windowToken = getWindowToken()
  if (windowToken) {
    if (csrfTokenCache?.windowToken === windowToken && csrfTokenCache.token === windowToken) {
      return csrfTokenCache.token
    }

    csrfTokenCache = {
      token: windowToken,
      windowToken,
    }
    return windowToken
  }

  const metaToken = getMetaToken()
  const inertiaToken = getInertiaToken()
  const token = metaToken ?? inertiaToken ?? ""

  if (
    csrfTokenCache &&
    csrfTokenCache.windowToken === undefined &&
    csrfTokenCache.metaToken === metaToken &&
    csrfTokenCache.inertiaToken === inertiaToken &&
    csrfTokenCache.token === token
  ) {
    return csrfTokenCache.token
  }

  csrfTokenCache = {
    token,
    windowToken: undefined,
    metaToken,
    inertiaToken,
  }

  return token
}

function hasCsrfHeader(headers: HeadersInit | undefined): boolean {
  if (headers == null) {
    return false
  }

  if (headers instanceof Headers) {
    return headers.has(DEFAULT_CSRF_HEADER_NAME)
  }

  if (Array.isArray(headers)) {
    return headers.some((entry) => Array.isArray(entry) && entry.length >= 2 && typeof entry[0] === "string" && entry[0].toLowerCase() === DEFAULT_CSRF_HEADER_NAME.toLowerCase())
  }

  return Object.keys(headers as Record<string, string>).some((key) => key.toLowerCase() === DEFAULT_CSRF_HEADER_NAME.toLowerCase())
}

/**
 * Create headers object with CSRF token included.
 *
 * @param additionalHeaders - Additional headers to include
 * @returns Headers object with Litestar's default CSRF header set
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
  if (!token) {
    return additionalHeaders
  }

  const existingTokenHeader = Object.keys(additionalHeaders).find((key) => key.toLowerCase() === DEFAULT_CSRF_HEADER_NAME.toLowerCase())
  if (existingTokenHeader !== undefined) {
    return additionalHeaders
  }

  return {
    ...additionalHeaders,
    [DEFAULT_CSRF_HEADER_NAME]: token,
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

  if (!hasCsrfHeader(init?.headers)) {
    if (!init || typeof init.headers === "undefined") {
      return fetch(input, {
        ...init,
        headers: { [DEFAULT_CSRF_HEADER_NAME]: token },
      })
    }

    if (typeof init.headers === "object" && init.headers !== null && !(init.headers instanceof Headers)) {
      if (Array.isArray(init.headers)) {
        return fetch(input, {
          ...init,
          headers: [...init.headers, [DEFAULT_CSRF_HEADER_NAME, token]],
        })
      }

      return fetch(input, {
        ...init,
        headers: {
          ...init.headers,
          [DEFAULT_CSRF_HEADER_NAME]: token,
        },
      })
    }

    if (init.headers instanceof Headers) {
      const headers = new Headers(init.headers)
      headers.set(DEFAULT_CSRF_HEADER_NAME, token)
      return fetch(input, {
        ...init,
        headers,
      })
    }
  }

  return fetch(input, init)
}
