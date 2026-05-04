/**
 * Network utilities for URL and host normalization.
 */

import path from "node:path"

/**
 * Normalizes a host address for URL construction.
 *
 * Handles various host formats to produce browser-compatible URLs:
 * - Converts bind-all addresses (::, 0.0.0.0) to localhost
 * - Converts IPv4/IPv6 localhost addresses (::1, 127.0.0.1) to localhost
 * - Wraps other IPv6 addresses in brackets for URL compatibility
 *
 * @example
 * ```typescript
 * normalizeHost("::") // => "localhost"
 * normalizeHost("0.0.0.0") // => "localhost"
 * normalizeHost("::1") // => "localhost"
 * normalizeHost("127.0.0.1") // => "localhost"
 * normalizeHost("fe80::1") // => "[fe80::1]"
 * normalizeHost("[fe80::1]") // => "[fe80::1]" (already bracketed)
 * normalizeHost("192.168.1.1") // => "192.168.1.1"
 * ```
 */
export function normalizeHost(host: string): string {
  // Handle wildcard and localhost addresses
  if (host === "::" || host === "::1" || host === "0.0.0.0" || host === "127.0.0.1") {
    return "localhost"
  }
  // If it contains ":" and isn't already bracketed, it's an IPv6 address
  if (host.includes(":") && !host.startsWith("[")) {
    return `[${host}]`
  }
  return host
}

/**
 * Resolve the Litestar dev server port for HMR routing.
 *
 * Framework integrations (Astro/Nuxt/SvelteKit) need this port to set
 * `vite.server.hmr.clientPort` so the browser opens the HMR WebSocket against
 * Litestar — NOT the framework dev server's port — preserving the
 * single-port-via-ASGI contract.
 *
 * Resolution order:
 *   1. `bridge.litestarPort` (preferred; written by Python ≥0.23.0).
 *   2. Parse `bridge.appUrl` (works with older bridges that lack `litestarPort`).
 *   3. `LITESTAR_PORT` / `PORT` env var.
 *   4. `null` if no signal.
 */
export function resolveLitestarPort(bridgeLitestarPort: number | null | undefined, bridgeAppUrl: string | null | undefined, env: NodeJS.ProcessEnv = process.env): number | null {
  if (typeof bridgeLitestarPort === "number" && Number.isInteger(bridgeLitestarPort) && bridgeLitestarPort > 0) {
    return bridgeLitestarPort
  }
  if (typeof bridgeAppUrl === "string" && bridgeAppUrl.length > 0) {
    try {
      const parsed = new URL(bridgeAppUrl)
      if (parsed.port) {
        const p = Number.parseInt(parsed.port, 10)
        if (!Number.isNaN(p) && p > 0) return p
      }
      if (parsed.protocol === "https:") return 443
      if (parsed.protocol === "http:") return 80
    } catch {
      // fall through
    }
  }
  const raw = env.LITESTAR_PORT ?? env.PORT
  if (raw) {
    const p = Number.parseInt(raw, 10)
    if (!Number.isNaN(p) && p > 0) return p
  }
  return null
}

/**
 * Resolve the absolute hot file path from bundleDir + hotFile.
 *
 * Python config stores hot_file as a filename (relative to bundle_dir) by default.
 * If hotFile already includes bundleDir, avoid double-prefixing.
 */
export function resolveHotFilePath(bundleDir: string, hotFile: string, rootDir: string = process.cwd()): string {
  if (path.isAbsolute(hotFile)) {
    return hotFile
  }

  const normalizedHot = hotFile.replace(/^\/+/, "")
  const normalizedBundle = bundleDir.replace(/^\/+/, "").replace(/\/+$/, "")

  if (normalizedBundle && normalizedHot.startsWith(`${normalizedBundle}/`)) {
    return path.resolve(rootDir, normalizedHot)
  }

  return path.resolve(rootDir, normalizedBundle, normalizedHot)
}
