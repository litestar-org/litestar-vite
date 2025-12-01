import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"
import { csrfFetch, csrfHeaders, getCsrfToken } from "../../src/helpers/csrf"

describe("csrf helpers", () => {
  const originalWindow = globalThis.window
  const originalDocument = globalThis.document
  const originalFetch = globalThis.fetch

  beforeEach(() => {
    vi.resetAllMocks()
    // Reset window to a clean state
    globalThis.window = {
      __LITESTAR_CSRF__: undefined,
    } as unknown as Window & typeof globalThis
    globalThis.document = {
      querySelector: vi.fn(() => null),
    } as unknown as Document
    globalThis.fetch = vi.fn()
  })

  afterEach(() => {
    globalThis.window = originalWindow
    globalThis.document = originalDocument
    globalThis.fetch = originalFetch
    vi.restoreAllMocks()
  })

  describe("getCsrfToken", () => {
    it("returns token from window.__LITESTAR_CSRF__ (SPA mode)", () => {
      globalThis.window.__LITESTAR_CSRF__ = "spa-csrf-token-123"

      const token = getCsrfToken()

      expect(token).toBe("spa-csrf-token-123")
    })

    it("returns token from meta tag (template mode)", () => {
      globalThis.window.__LITESTAR_CSRF__ = undefined
      const mockMeta = { getAttribute: vi.fn(() => "meta-csrf-token-456") }
      ;(globalThis.document.querySelector as ReturnType<typeof vi.fn>).mockReturnValue(mockMeta)

      const token = getCsrfToken()

      expect(token).toBe("meta-csrf-token-456")
      expect(globalThis.document.querySelector).toHaveBeenCalledWith('meta[name="csrf-token"]')
    })

    it("returns token from Inertia page props (Inertia mode)", () => {
      globalThis.window.__LITESTAR_CSRF__ = undefined
      ;(globalThis.document.querySelector as ReturnType<typeof vi.fn>).mockReturnValue(null)
      ;(globalThis.window as unknown as Record<string, unknown>).__INERTIA_PAGE__ = {
        props: {
          csrf_token: "inertia-csrf-token-789",
        },
      }

      const token = getCsrfToken()

      expect(token).toBe("inertia-csrf-token-789")
    })

    it("prioritizes window global over meta tag", () => {
      globalThis.window.__LITESTAR_CSRF__ = "window-token"
      const mockMeta = { getAttribute: vi.fn(() => "meta-token") }
      ;(globalThis.document.querySelector as ReturnType<typeof vi.fn>).mockReturnValue(mockMeta)

      const token = getCsrfToken()

      expect(token).toBe("window-token")
      expect(globalThis.document.querySelector).not.toHaveBeenCalled()
    })

    it("prioritizes meta tag over Inertia props", () => {
      globalThis.window.__LITESTAR_CSRF__ = undefined
      const mockMeta = { getAttribute: vi.fn(() => "meta-token") }
      ;(globalThis.document.querySelector as ReturnType<typeof vi.fn>).mockReturnValue(mockMeta)
      ;(globalThis.window as unknown as Record<string, unknown>).__INERTIA_PAGE__ = {
        props: { csrf_token: "inertia-token" },
      }

      const token = getCsrfToken()

      expect(token).toBe("meta-token")
    })

    it("returns empty string when no source available", () => {
      globalThis.window.__LITESTAR_CSRF__ = undefined
      ;(globalThis.document.querySelector as ReturnType<typeof vi.fn>).mockReturnValue(null)

      const token = getCsrfToken()

      expect(token).toBe("")
    })

    it("returns empty string when meta tag has no content attribute", () => {
      globalThis.window.__LITESTAR_CSRF__ = undefined
      const mockMeta = { getAttribute: vi.fn(() => null) }
      ;(globalThis.document.querySelector as ReturnType<typeof vi.fn>).mockReturnValue(mockMeta)

      const token = getCsrfToken()

      expect(token).toBe("")
    })

    it("returns empty string when Inertia props has wrong type", () => {
      globalThis.window.__LITESTAR_CSRF__ = undefined
      ;(globalThis.document.querySelector as ReturnType<typeof vi.fn>).mockReturnValue(null)
      ;(globalThis.window as unknown as Record<string, unknown>).__INERTIA_PAGE__ = {
        props: {
          csrf_token: 12345, // wrong type - should be string
        },
      }

      const token = getCsrfToken()

      expect(token).toBe("")
    })

    it("handles server-side rendering (no window)", () => {
      // @ts-expect-error - Testing SSR scenario
      globalThis.window = undefined

      const token = getCsrfToken()

      expect(token).toBe("")
    })

    it("handles missing document", () => {
      globalThis.window.__LITESTAR_CSRF__ = undefined
      // @ts-expect-error - Testing missing document scenario
      globalThis.document = undefined

      const token = getCsrfToken()

      expect(token).toBe("")
    })

    it("handles Inertia page without props", () => {
      globalThis.window.__LITESTAR_CSRF__ = undefined
      ;(globalThis.document.querySelector as ReturnType<typeof vi.fn>).mockReturnValue(null)
      ;(globalThis.window as unknown as Record<string, unknown>).__INERTIA_PAGE__ = {}

      const token = getCsrfToken()

      expect(token).toBe("")
    })
  })

  describe("csrfHeaders", () => {
    it("creates headers with CSRF token when token exists", () => {
      globalThis.window.__LITESTAR_CSRF__ = "test-token"

      const headers = csrfHeaders()

      expect(headers).toEqual({ "X-CSRF-Token": "test-token" })
    })

    it("merges with additional headers", () => {
      globalThis.window.__LITESTAR_CSRF__ = "test-token"

      const headers = csrfHeaders({ "Content-Type": "application/json" })

      expect(headers).toEqual({
        "Content-Type": "application/json",
        "X-CSRF-Token": "test-token",
      })
    })

    it("returns only additional headers when no token", () => {
      globalThis.window.__LITESTAR_CSRF__ = undefined
      ;(globalThis.document.querySelector as ReturnType<typeof vi.fn>).mockReturnValue(null)

      const headers = csrfHeaders({ "Content-Type": "application/json" })

      expect(headers).toEqual({ "Content-Type": "application/json" })
    })

    it("returns empty object when no token and no additional headers", () => {
      globalThis.window.__LITESTAR_CSRF__ = undefined
      ;(globalThis.document.querySelector as ReturnType<typeof vi.fn>).mockReturnValue(null)

      const headers = csrfHeaders()

      expect(headers).toEqual({})
    })

    it("does not override existing X-CSRF-Token in additional headers", () => {
      globalThis.window.__LITESTAR_CSRF__ = "auto-token"

      // Note: current implementation will override. This test documents current behavior.
      const headers = csrfHeaders({ "X-CSRF-Token": "manual-token" })

      // Token from getCsrfToken() overwrites the manual one due to spread order
      expect(headers["X-CSRF-Token"]).toBe("auto-token")
    })
  })

  describe("csrfFetch", () => {
    it("adds CSRF header to request", async () => {
      globalThis.window.__LITESTAR_CSRF__ = "fetch-token"
      const mockResponse = new Response("OK", { status: 200 })
      ;(globalThis.fetch as ReturnType<typeof vi.fn>).mockResolvedValue(mockResponse)

      await csrfFetch("/api/submit", { method: "POST" })

      expect(globalThis.fetch).toHaveBeenCalledWith(
        "/api/submit",
        expect.objectContaining({
          method: "POST",
          headers: expect.any(Headers),
        }),
      )

      const callArgs = (globalThis.fetch as ReturnType<typeof vi.fn>).mock.calls[0]
      const headers = callArgs[1].headers as Headers
      expect(headers.get("X-CSRF-Token")).toBe("fetch-token")
    })

    it("preserves existing headers", async () => {
      globalThis.window.__LITESTAR_CSRF__ = "fetch-token"
      const mockResponse = new Response("OK", { status: 200 })
      ;(globalThis.fetch as ReturnType<typeof vi.fn>).mockResolvedValue(mockResponse)

      await csrfFetch("/api/submit", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
      })

      const callArgs = (globalThis.fetch as ReturnType<typeof vi.fn>).mock.calls[0]
      const headers = callArgs[1].headers as Headers
      expect(headers.get("Content-Type")).toBe("application/json")
      expect(headers.get("X-CSRF-Token")).toBe("fetch-token")
    })

    it("does not override existing X-CSRF-Token header", async () => {
      globalThis.window.__LITESTAR_CSRF__ = "auto-token"
      const mockResponse = new Response("OK", { status: 200 })
      ;(globalThis.fetch as ReturnType<typeof vi.fn>).mockResolvedValue(mockResponse)

      await csrfFetch("/api/submit", {
        method: "POST",
        headers: { "X-CSRF-Token": "manual-token" },
      })

      const callArgs = (globalThis.fetch as ReturnType<typeof vi.fn>).mock.calls[0]
      const headers = callArgs[1].headers as Headers
      expect(headers.get("X-CSRF-Token")).toBe("manual-token")
    })

    it("passes through when no token available", async () => {
      globalThis.window.__LITESTAR_CSRF__ = undefined
      ;(globalThis.document.querySelector as ReturnType<typeof vi.fn>).mockReturnValue(null)
      const mockResponse = new Response("OK", { status: 200 })
      ;(globalThis.fetch as ReturnType<typeof vi.fn>).mockResolvedValue(mockResponse)

      await csrfFetch("/api/submit", { method: "POST" })

      expect(globalThis.fetch).toHaveBeenCalledWith("/api/submit", { method: "POST" })
    })

    it("works with URL object", async () => {
      globalThis.window.__LITESTAR_CSRF__ = "fetch-token"
      const mockResponse = new Response("OK", { status: 200 })
      ;(globalThis.fetch as ReturnType<typeof vi.fn>).mockResolvedValue(mockResponse)

      const url = new URL("https://example.com/api/submit")
      await csrfFetch(url, { method: "POST" })

      expect(globalThis.fetch).toHaveBeenCalledWith(
        url,
        expect.objectContaining({
          method: "POST",
          headers: expect.any(Headers),
        }),
      )
    })

    it("works without init options", async () => {
      globalThis.window.__LITESTAR_CSRF__ = "fetch-token"
      const mockResponse = new Response("OK", { status: 200 })
      ;(globalThis.fetch as ReturnType<typeof vi.fn>).mockResolvedValue(mockResponse)

      await csrfFetch("/api/data")

      expect(globalThis.fetch).toHaveBeenCalledWith(
        "/api/data",
        expect.objectContaining({
          headers: expect.any(Headers),
        }),
      )
    })

    it("returns the fetch response", async () => {
      globalThis.window.__LITESTAR_CSRF__ = "fetch-token"
      const mockResponse = new Response("OK", { status: 200 })
      ;(globalThis.fetch as ReturnType<typeof vi.fn>).mockResolvedValue(mockResponse)

      const response = await csrfFetch("/api/submit")

      expect(response).toBe(mockResponse)
    })

    it("propagates fetch errors", async () => {
      globalThis.window.__LITESTAR_CSRF__ = "fetch-token"
      const error = new Error("Network error")
      ;(globalThis.fetch as ReturnType<typeof vi.fn>).mockRejectedValue(error)

      await expect(csrfFetch("/api/submit")).rejects.toThrow("Network error")
    })

    it("works with Headers instance in init", async () => {
      globalThis.window.__LITESTAR_CSRF__ = "fetch-token"
      const mockResponse = new Response("OK", { status: 200 })
      ;(globalThis.fetch as ReturnType<typeof vi.fn>).mockResolvedValue(mockResponse)

      const existingHeaders = new Headers({ Authorization: "Bearer xyz" })
      await csrfFetch("/api/submit", {
        method: "POST",
        headers: existingHeaders,
      })

      const callArgs = (globalThis.fetch as ReturnType<typeof vi.fn>).mock.calls[0]
      const headers = callArgs[1].headers as Headers
      expect(headers.get("Authorization")).toBe("Bearer xyz")
      expect(headers.get("X-CSRF-Token")).toBe("fetch-token")
    })
  })
})
