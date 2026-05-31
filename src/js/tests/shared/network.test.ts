import { describe, expect, it } from "vitest"
import { normalizeHost, resolveLitestarPort } from "../../src/shared/network"

describe("normalizeHost", () => {
  it("collapses bind-all and localhost addresses", () => {
    expect(normalizeHost("::")).toBe("localhost")
    expect(normalizeHost("0.0.0.0")).toBe("localhost")
    expect(normalizeHost("::1")).toBe("localhost")
    expect(normalizeHost("127.0.0.1")).toBe("localhost")
  })

  it("brackets non-localhost IPv6", () => {
    expect(normalizeHost("fe80::1")).toBe("[fe80::1]")
    expect(normalizeHost("[fe80::1]")).toBe("[fe80::1]")
  })

  it("leaves IPv4 untouched", () => {
    expect(normalizeHost("192.168.1.1")).toBe("192.168.1.1")
  })
})

describe("resolveLitestarPort", () => {
  it("prefers bridgeLitestarPort when present", () => {
    expect(resolveLitestarPort(8000, "http://localhost:9999", { LITESTAR_PORT: "1111" })).toBe(8000)
  })

  it("falls back to parsing appUrl when bridgeLitestarPort is null", () => {
    expect(resolveLitestarPort(null, "http://localhost:9999")).toBe(9999)
  })

  it("returns 80 for http:// without explicit port", () => {
    expect(resolveLitestarPort(null, "http://api.example.com")).toBe(80)
  })

  it("returns 443 for https:// without explicit port", () => {
    expect(resolveLitestarPort(null, "https://api.example.com")).toBe(443)
  })

  it("falls back to LITESTAR_PORT env when bridge is empty", () => {
    expect(resolveLitestarPort(null, null, { LITESTAR_PORT: "8765" })).toBe(8765)
  })

  it("falls back to PORT env when LITESTAR_PORT missing", () => {
    expect(resolveLitestarPort(null, null, { PORT: "5500" })).toBe(5500)
  })

  it("returns null when no signal is available", () => {
    expect(resolveLitestarPort(null, null, {})).toBeNull()
    expect(resolveLitestarPort(undefined, undefined, {})).toBeNull()
  })

  it("ignores malformed appUrl and continues to env fallback", () => {
    expect(resolveLitestarPort(null, "::not-a-url::", { LITESTAR_PORT: "8000" })).toBe(8000)
  })

  it("rejects non-positive or non-integer bridgeLitestarPort and falls through", () => {
    expect(resolveLitestarPort(0, "http://localhost:9999")).toBe(9999)
    expect(resolveLitestarPort(-1, null, { PORT: "8000" })).toBe(8000)
  })
})
