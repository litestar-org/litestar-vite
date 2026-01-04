/**
 * Network utilities for URL and host normalization.
 */

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
