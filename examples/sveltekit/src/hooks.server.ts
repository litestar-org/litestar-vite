/**
 * SvelteKit server hooks for API proxying.
 *
 * In production, the SvelteKit Node.js server runs separately from Litestar.
 * This hook proxies /api/* requests to the Litestar backend so client-side
 * fetches work correctly without requiring an external reverse proxy.
 *
 * Environment variables:
 *   LITESTAR_API - Base URL of the Litestar API server (default: http://localhost:8000)
 */
import type { Handle } from "@sveltejs/kit"

const LITESTAR_API = process.env.LITESTAR_API || "http://localhost:8000"
const BODYLESS_METHODS = new Set(["GET", "HEAD"])

type ProxyRequestInit = RequestInit & {
  duplex?: "half"
}

export const handle: Handle = async ({ event, resolve }) => {
  // Proxy /api/* requests to the Litestar backend
  if (event.url.pathname.startsWith("/api")) {
    const apiUrl = `${LITESTAR_API}${event.url.pathname}${event.url.search}`

    try {
      const headers = new Headers(event.request.headers)
      headers.delete("connection")
      headers.delete("content-length")
      headers.delete("host")

      // Forward the request to Litestar
      const requestInit: ProxyRequestInit = {
        method: event.request.method,
        headers,
      }

      if (!BODYLESS_METHODS.has(event.request.method)) {
        requestInit.body = event.request.body
        requestInit.duplex = "half"
      }

      const response = await fetch(apiUrl, requestInit)

      // Return the proxied response
      return new Response(response.body, {
        status: response.status,
        statusText: response.statusText,
        headers: new Headers(response.headers),
      })
    } catch (error) {
      console.error(`[hooks.server] Failed to proxy ${event.url.pathname} to ${apiUrl}:`, error)
      return new Response(JSON.stringify({ error: "API proxy failed", detail: String(error) }), {
        status: 502,
        headers: { "content-type": "application/json" },
      })
    }
  }

  return resolve(event)
}
