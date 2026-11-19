/**
 * CSRF token utilities for Litestar applications.
 *
 * The CSRF token is injected into the page by Litestar in one of these ways:
 * 1. window.__LITESTAR_CSRF__ (SPA mode)
 * 2. <meta name="csrf-token" content="..."> (template mode)
 * 3. Inertia shared props (Inertia mode)
 * 4. csrftoken / XSRF-TOKEN cookie (SPA fallback)
 *
 * @module
 */

declare global {
  interface Window {
    __LITESTAR_CSRF__?: string
    __LITESTAR_CSRF_HEADER_NAME__?: string
    __LITESTAR_CSRF_COOKIE_NAME__?: string
  }
}

export interface CsrfOptions {
  /**
   * Fallback header name to use if window.__LITESTAR_CSRF_HEADER_NAME__ is undefined.
   * @default "X-CSRFToken"
   */
  headerName?: string
  /**
   * Fallback cookie name to check if window.__LITESTAR_CSRF_COOKIE_NAME__ is undefined.
   */
  cookieName?: string
}

export interface CsrfFetchOptions extends CsrfOptions {
  /**
   * Additional cross-origin origins allowed to receive automatic CSRF headers.
   * Each entry is normalized to its URL origin (for example `"https://api.example.com"`).
   */
  trustedOrigins?: readonly string[]
}

interface CsrfTokenCache {
  token: string
  windowToken?: string
  metaToken?: string
  inertiaToken?: string
  cookieToken?: string
}

let csrfTokenCache: CsrfTokenCache | null = null
const DEFAULT_CSRF_HEADER_NAME = "X-CSRFToken"
const URL_SCHEME_RE = /^[a-zA-Z][a-zA-Z0-9+.-]*:/

/**
 * Get the configured CSRF header name.
 *
 * Checks `window.__LITESTAR_CSRF_HEADER_NAME__` first, then falls back to `fallback`
 * (defaults to "X-CSRFToken").
 *
 * @param fallback - Optional fallback header name
 * @returns The CSRF header name
 */
export function getCsrfHeaderName(fallback: string = DEFAULT_CSRF_HEADER_NAME): string {
  if (typeof window !== "undefined" && typeof window.__LITESTAR_CSRF_HEADER_NAME__ === "string" && window.__LITESTAR_CSRF_HEADER_NAME__.length > 0) {
    return window.__LITESTAR_CSRF_HEADER_NAME__
  }
  return fallback
}

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

  if (typeof document !== "undefined") {
    const scriptEl = typeof document.getElementById === "function" ? document.getElementById("app_page") : null
    if (scriptEl && scriptEl.textContent) {
      try {
        const page = JSON.parse(scriptEl.textContent)
        if (page?.props?.csrf_token && typeof page.props.csrf_token === "string") {
          return page.props.csrf_token
        }
      } catch {
        // ignore JSON parse error
      }
    }

    if (typeof document.querySelector === "function") {
      const dataEl = document.querySelector("[data-page]")
      if (dataEl) {
        const raw = dataEl.getAttribute("data-page")
        if (raw && raw !== "app") {
          try {
            const page = JSON.parse(raw)
            if (page?.props?.csrf_token && typeof page.props.csrf_token === "string") {
              return page.props.csrf_token
            }
          } catch {
            // ignore JSON parse error
          }
        }
      }
    }
  }

  return undefined
}

function getCookie(name: string): string | undefined {
  if (typeof document === "undefined" || typeof document.cookie !== "string") {
    return undefined
  }

  const value = `; ${document.cookie}`
  const parts = value.split(`; ${name}=`)
  if (parts.length === 2) {
    const raw = parts.pop()?.split(";").shift()
    if (raw !== undefined && raw.length > 0) {
      try {
        return decodeURIComponent(raw)
      } catch {
        return raw
      }
    }
  }

  return undefined
}

function getCookieToken(cookieNameFallback?: string): string | undefined {
  if (typeof window !== "undefined" && typeof window.__LITESTAR_CSRF_COOKIE_NAME__ === "string" && window.__LITESTAR_CSRF_COOKIE_NAME__.length > 0) {
    const configured = getCookie(window.__LITESTAR_CSRF_COOKIE_NAME__)
    if (configured !== undefined) {
      return configured
    }
  }
  if (typeof cookieNameFallback === "string" && cookieNameFallback.length > 0) {
    const fallbackCookie = getCookie(cookieNameFallback)
    if (fallbackCookie !== undefined) {
      return fallbackCookie
    }
  }
  return getCookie("csrftoken") ?? getCookie("XSRF-TOKEN")
}

/**
 * Get the CSRF token from the page.
 *
 * Checks multiple sources in order:
 * 1. window.__LITESTAR_CSRF__ (injected by SPA handler)
 * 2. <meta name="csrf-token"> element
 * 3. Inertia page props (if Inertia is present)
 * 4. csrftoken / XSRF-TOKEN cookie (or custom cookieName fallback)
 *
 * @param cookieNameFallbackOrOptions - Optional fallback cookie name or options object
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
export function getCsrfToken(cookieNameFallbackOrOptions?: string | CsrfOptions): string {
  const cookieNameFallback =
    typeof cookieNameFallbackOrOptions === "object" && cookieNameFallbackOrOptions !== null ? cookieNameFallbackOrOptions.cookieName : cookieNameFallbackOrOptions

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
  const cookieToken = getCookieToken(cookieNameFallback)
  const token = metaToken ?? inertiaToken ?? cookieToken ?? ""

  if (
    csrfTokenCache &&
    csrfTokenCache.windowToken === undefined &&
    csrfTokenCache.metaToken === metaToken &&
    csrfTokenCache.inertiaToken === inertiaToken &&
    csrfTokenCache.cookieToken === cookieToken &&
    csrfTokenCache.token === token
  ) {
    return csrfTokenCache.token
  }

  csrfTokenCache = {
    token,
    windowToken: undefined,
    metaToken,
    inertiaToken,
    cookieToken,
  }

  return token
}

function hasCsrfHeader(headers: HeadersInit | undefined, headerName: string): boolean {
  if (headers == null) {
    return false
  }

  if (headers instanceof Headers) {
    return headers.has(headerName)
  }

  if (Array.isArray(headers)) {
    return headers.some((entry) => Array.isArray(entry) && entry.length >= 2 && typeof entry[0] === "string" && entry[0].toLowerCase() === headerName.toLowerCase())
  }

  return Object.keys(headers as Record<string, string>).some((key) => key.toLowerCase() === headerName.toLowerCase())
}

/**
 * Create headers object with CSRF token included.
 *
 * @param additionalHeaders - Additional headers to include
 * @param optionsOrHeaderFallback - Optional header name fallback or CsrfOptions object
 * @param cookieNameFallback - Optional cookie name fallback when optionsOrHeaderFallback is a header name string
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
export function csrfHeaders(additionalHeaders: Record<string, string> = {}, optionsOrHeaderFallback?: string | CsrfOptions, cookieNameFallback?: string): Record<string, string> {
  const options: CsrfOptions =
    typeof optionsOrHeaderFallback === "object" && optionsOrHeaderFallback !== null
      ? optionsOrHeaderFallback
      : {
          headerName: typeof optionsOrHeaderFallback === "string" ? optionsOrHeaderFallback : undefined,
          cookieName: cookieNameFallback,
        }

  const token = getCsrfToken(options.cookieName)
  if (!token) {
    return additionalHeaders
  }

  const headerName = getCsrfHeaderName(options.headerName ?? DEFAULT_CSRF_HEADER_NAME)
  const existingTokenHeader = Object.keys(additionalHeaders).find((key) => key.toLowerCase() === headerName.toLowerCase())
  if (existingTokenHeader !== undefined) {
    return additionalHeaders
  }

  return {
    ...additionalHeaders,
    [headerName]: token,
  }
}

function extractTargetUrl(target: RequestInfo | URL | undefined): string {
  if (typeof target === "string") {
    return target
  }
  if (target instanceof URL) {
    return target.href
  }
  if (target && typeof target === "object") {
    if ("url" in target && typeof target.url === "string") {
      return target.url
    }
    if ("href" in target && typeof target.href === "string") {
      return target.href
    }
  }
  return ""
}

function normalizeTrustedOrigins(trustedOrigins?: readonly string[]): Set<string> {
  const trusted = new Set<string>()
  if (!trustedOrigins) {
    return trusted
  }
  for (const entry of trustedOrigins) {
    if (typeof entry !== "string") {
      continue
    }
    try {
      const origin = new URL(entry).origin
      if (origin && origin !== "null") {
        trusted.add(origin)
      }
    } catch {
      // ignore malformed trusted origin entries
    }
  }
  return trusted
}

function normalizeUrlTarget(raw: string): string {
  const trimmed = raw.trim()
  let start = 0
  let end = trimmed.length
  while (start < end && trimmed.charCodeAt(start) <= 0x20) {
    start += 1
  }
  while (end > start && trimmed.charCodeAt(end - 1) <= 0x20) {
    end -= 1
  }
  const sliced = trimmed.slice(start, end)
  let normalized = ""
  for (let i = 0; i < sliced.length; i += 1) {
    const code = sliced.charCodeAt(i)
    if (code !== 0x09 && code !== 0x0a && code !== 0x0d) {
      normalized += sliced[i]
    }
  }
  return normalized
}

function isProtocolRelativePrefix(value: string): boolean {
  return value.startsWith("//") || value.startsWith("\\\\") || value.startsWith("/\\") || value.startsWith("\\/")
}

function isRequestObject(input: RequestInfo | URL): input is Request {
  return typeof Request !== "undefined" && input instanceof Request
}

/**
 * Determine whether a request target is allowed to receive an automatic CSRF header.
 *
 * Permits same-origin URLs and origins explicitly listed in `trustedOrigins`.
 * Rejects protocol-relative URLs, opaque origins, and malformed URLs.
 *
 * @param target - Request URL string, URL instance, Request object, or undefined
 * @param trustedOrigins - Optional cross-origin origins explicitly trusted for CSRF headers
 * @returns True when the target origin matches the current origin or a trusted origin
 */
export function isCsrfTrustedTarget(target: RequestInfo | URL | undefined, trustedOrigins?: readonly string[]): boolean {
  const rawTarget = extractTargetUrl(target)
  const trustedSet = normalizeTrustedOrigins(trustedOrigins)
  const currentOrigin = typeof window !== "undefined" ? window.location?.origin : undefined
  const trimmed = normalizeUrlTarget(rawTarget)

  if (isProtocolRelativePrefix(trimmed)) {
    return false
  }

  if (currentOrigin && currentOrigin !== "null") {
    try {
      const baseUrl = (typeof document !== "undefined" && document.baseURI) || window.location?.href || currentOrigin
      const resolved = new URL(trimmed, baseUrl)
      return resolved.origin !== "null" && (resolved.origin === currentOrigin || trustedSet.has(resolved.origin))
    } catch {
      return false
    }
  }

  if (!URL_SCHEME_RE.test(trimmed)) {
    return typeof window !== "undefined"
  }

  try {
    const resolved = new URL(trimmed)
    return resolved.origin !== "null" && trustedSet.has(resolved.origin)
  } catch {
    return false
  }
}

/**
 * Create a fetch wrapper that automatically includes CSRF token for same-origin
 * or explicitly trusted targets.
 *
 * @param input - Request URL or Request object
 * @param init - Request options
 * @param options - Optional CSRF configuration options (headerName, cookieName, and/or trustedOrigins)
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
export function csrfFetch(input: RequestInfo | URL, init?: RequestInit, options?: CsrfFetchOptions): Promise<Response> {
  const token = getCsrfToken(options?.cookieName)

  if (!token || !isCsrfTrustedTarget(input, options?.trustedOrigins)) {
    return fetch(input, init)
  }

  const headerName = getCsrfHeaderName(options?.headerName ?? DEFAULT_CSRF_HEADER_NAME)
  const hasExplicitCsrfHeader = hasCsrfHeader(init?.headers, headerName) || (isRequestObject(input) && hasCsrfHeader(input.headers, headerName))
  if (!hasExplicitCsrfHeader) {
    if (!init || typeof init.headers === "undefined") {
      if (isRequestObject(input)) {
        const headers = new Headers(input.headers)
        headers.set(headerName, token)
        return fetch(input, {
          ...init,
          headers,
        })
      }

      return fetch(input, {
        ...init,
        headers: { [headerName]: token },
      })
    }

    if (typeof init.headers === "object" && init.headers !== null && !(init.headers instanceof Headers)) {
      if (Array.isArray(init.headers)) {
        return fetch(input, {
          ...init,
          headers: [...init.headers, [headerName, token]],
        })
      }

      return fetch(input, {
        ...init,
        headers: {
          ...init.headers,
          [headerName]: token,
        },
      })
    }

    if (init.headers instanceof Headers) {
      const headers = new Headers(init.headers)
      headers.set(headerName, token)
      return fetch(input, {
        ...init,
        headers,
      })
    }
  }

  return fetch(input, init)
}
