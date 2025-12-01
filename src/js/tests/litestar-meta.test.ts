import fs from "node:fs"
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"
import { checkBackendAvailability, loadLitestarMeta } from "../src/litestar-meta"
import { createMockViteConfig } from "./__fixtures__/mock-vite-config"

// Mock node:fs
vi.mock("node:fs", () => ({
  default: {
    existsSync: vi.fn(),
    readFileSync: vi.fn(),
  },
  existsSync: vi.fn(),
  readFileSync: vi.fn(),
}))

describe("litestar-meta", () => {
  const originalEnv = { ...process.env }
  const originalFetch = globalThis.fetch

  beforeEach(() => {
    vi.resetAllMocks()
    process.env = { ...originalEnv }
    process.env.LITESTAR_VERSION = undefined
    process.env.LITESTAR_OPENAPI_PATH = undefined
    globalThis.fetch = vi.fn()
  })

  afterEach(() => {
    process.env = originalEnv
    globalThis.fetch = originalFetch
    vi.restoreAllMocks()
  })

  describe("checkBackendAvailability", () => {
    it("returns unavailable when appUrl is null", async () => {
      const result = await checkBackendAvailability(null)

      expect(result).toEqual({
        available: false,
        error: "APP_URL not configured",
      })
    })

    it("returns unavailable when appUrl is 'undefined' string", async () => {
      const result = await checkBackendAvailability("undefined")

      expect(result).toEqual({
        available: false,
        error: "APP_URL not configured",
      })
    })

    it("returns available for successful response (2xx)", async () => {
      const mockResponse = new Response("OK", { status: 200 })
      ;(globalThis.fetch as ReturnType<typeof vi.fn>).mockResolvedValue(mockResponse)

      const result = await checkBackendAvailability("http://localhost:8000")

      expect(result).toEqual({
        available: true,
        url: "http://localhost:8000",
      })
      expect(globalThis.fetch).toHaveBeenCalledWith(
        "http://localhost:8000/schema",
        expect.objectContaining({
          method: "GET",
          signal: expect.any(AbortSignal),
        }),
      )
    })

    it("returns available for 4xx responses (client error, but server running)", async () => {
      const mockResponse = new Response("Not Found", { status: 404 })
      ;(globalThis.fetch as ReturnType<typeof vi.fn>).mockResolvedValue(mockResponse)

      const result = await checkBackendAvailability("http://localhost:8000")

      expect(result).toEqual({
        available: true,
        url: "http://localhost:8000",
      })
    })

    it("returns unavailable for 5xx responses", async () => {
      const mockResponse = new Response("Internal Server Error", { status: 500 })
      Object.defineProperty(mockResponse, "ok", { value: false })
      ;(globalThis.fetch as ReturnType<typeof vi.fn>).mockResolvedValue(mockResponse)

      const result = await checkBackendAvailability("http://localhost:8000")

      expect(result).toEqual({
        available: false,
        url: "http://localhost:8000",
      })
    })

    it("uses custom schema path from LITESTAR_OPENAPI_PATH", async () => {
      process.env.LITESTAR_OPENAPI_PATH = "/api/openapi"
      const mockResponse = new Response("OK", { status: 200 })
      ;(globalThis.fetch as ReturnType<typeof vi.fn>).mockResolvedValue(mockResponse)

      await checkBackendAvailability("http://localhost:8000")

      expect(globalThis.fetch).toHaveBeenCalledWith("http://localhost:8000/api/openapi", expect.anything())
    })

    it("returns unavailable with ECONNREFUSED error", async () => {
      const error = new Error("fetch failed: ECONNREFUSED")
      ;(globalThis.fetch as ReturnType<typeof vi.fn>).mockRejectedValue(error)

      const result = await checkBackendAvailability("http://localhost:8000")

      expect(result).toEqual({
        available: false,
        url: "http://localhost:8000",
        error: "Backend not reachable (is Litestar running?)",
      })
    })

    it("returns unavailable with fetch failed error", async () => {
      const error = new Error("fetch failed")
      ;(globalThis.fetch as ReturnType<typeof vi.fn>).mockRejectedValue(error)

      const result = await checkBackendAvailability("http://localhost:8000")

      expect(result).toEqual({
        available: false,
        url: "http://localhost:8000",
        error: "Backend not reachable (is Litestar running?)",
      })
    })

    it("returns unavailable with timeout (aborted) error", async () => {
      const error = new Error("The operation was aborted")
      ;(globalThis.fetch as ReturnType<typeof vi.fn>).mockRejectedValue(error)

      const result = await checkBackendAvailability("http://localhost:8000")

      expect(result).toEqual({
        available: false,
        url: "http://localhost:8000",
        error: "Backend connection timeout",
      })
    })

    it("returns unavailable with generic error message", async () => {
      const error = new Error("Network is unreachable")
      ;(globalThis.fetch as ReturnType<typeof vi.fn>).mockRejectedValue(error)

      const result = await checkBackendAvailability("http://localhost:8000")

      expect(result).toEqual({
        available: false,
        url: "http://localhost:8000",
        error: "Network is unreachable",
      })
    })

    it("handles non-Error objects in catch block", async () => {
      ;(globalThis.fetch as ReturnType<typeof vi.fn>).mockRejectedValue("string error")

      const result = await checkBackendAvailability("http://localhost:8000")

      expect(result).toEqual({
        available: false,
        url: "http://localhost:8000",
        error: "string error",
      })
    })
  })

  describe("loadLitestarMeta", () => {
    it("returns version from LITESTAR_VERSION env var", async () => {
      process.env.LITESTAR_VERSION = "2.15.0"
      const config = createMockViteConfig()

      const meta = await loadLitestarMeta(config)

      expect(meta).toEqual({ litestarVersion: "2.15.0" })
    })

    it("trims whitespace from LITESTAR_VERSION env var", async () => {
      process.env.LITESTAR_VERSION = "  2.15.0  "
      const config = createMockViteConfig()

      const meta = await loadLitestarMeta(config)

      expect(meta).toEqual({ litestarVersion: "2.15.0" })
    })

    it("returns version from routes.json with litestar_version key", async () => {
      const config = createMockViteConfig({ root: "/app" })
      ;(fs.existsSync as ReturnType<typeof vi.fn>).mockImplementation((path: string) => {
        return path === "/app/src/generated/routes.json"
      })
      ;(fs.readFileSync as ReturnType<typeof vi.fn>).mockReturnValue(JSON.stringify({ routes: {}, litestar_version: "2.14.0" }))

      const meta = await loadLitestarMeta(config)

      expect(meta).toEqual({ litestarVersion: "2.14.0" })
    })

    it("returns version from routes.json with litestarVersion key", async () => {
      const config = createMockViteConfig({ root: "/app" })
      ;(fs.existsSync as ReturnType<typeof vi.fn>).mockImplementation((path: string) => {
        return path === "/app/src/generated/routes.json"
      })
      ;(fs.readFileSync as ReturnType<typeof vi.fn>).mockReturnValue(JSON.stringify({ routes: {}, litestarVersion: "2.13.0" }))

      const meta = await loadLitestarMeta(config)

      expect(meta).toEqual({ litestarVersion: "2.13.0" })
    })

    it("returns version from routes.json with version key", async () => {
      const config = createMockViteConfig({ root: "/app" })
      ;(fs.existsSync as ReturnType<typeof vi.fn>).mockImplementation((path: string) => {
        return path === "/app/src/generated/routes.json"
      })
      ;(fs.readFileSync as ReturnType<typeof vi.fn>).mockReturnValue(JSON.stringify({ routes: {}, version: "2.12.0" }))

      const meta = await loadLitestarMeta(config)

      expect(meta).toEqual({ litestarVersion: "2.12.0" })
    })

    it("prioritizes litestar_version over other keys", async () => {
      const config = createMockViteConfig({ root: "/app" })
      ;(fs.existsSync as ReturnType<typeof vi.fn>).mockImplementation((path: string) => {
        return path === "/app/src/generated/routes.json"
      })
      ;(fs.readFileSync as ReturnType<typeof vi.fn>).mockReturnValue(
        JSON.stringify({
          routes: {},
          litestar_version: "2.14.0",
          litestarVersion: "2.13.0",
          version: "2.12.0",
        }),
      )

      const meta = await loadLitestarMeta(config)

      expect(meta).toEqual({ litestarVersion: "2.14.0" })
    })

    it("uses custom routes path hint when provided", async () => {
      const config = createMockViteConfig({ root: "/app" })
      ;(fs.existsSync as ReturnType<typeof vi.fn>).mockImplementation((path: string) => {
        return path === "/app/custom/routes.json"
      })
      ;(fs.readFileSync as ReturnType<typeof vi.fn>).mockReturnValue(JSON.stringify({ routes: {}, litestar_version: "2.11.0" }))

      const meta = await loadLitestarMeta(config, "custom/routes.json")

      expect(meta).toEqual({ litestarVersion: "2.11.0" })
    })

    it("tries routes.json in root as fallback", async () => {
      const config = createMockViteConfig({ root: "/app" })
      ;(fs.existsSync as ReturnType<typeof vi.fn>).mockImplementation((path: string) => {
        return path === "/app/routes.json"
      })
      ;(fs.readFileSync as ReturnType<typeof vi.fn>).mockReturnValue(JSON.stringify({ routes: {}, litestar_version: "2.10.0" }))

      const meta = await loadLitestarMeta(config)

      expect(meta).toEqual({ litestarVersion: "2.10.0" })
    })

    it("returns empty object when no routes file found", async () => {
      const config = createMockViteConfig({ root: "/app" })
      ;(fs.existsSync as ReturnType<typeof vi.fn>).mockReturnValue(false)

      const meta = await loadLitestarMeta(config)

      expect(meta).toEqual({})
    })

    it("returns empty object when routes file cannot be parsed", async () => {
      const config = createMockViteConfig({ root: "/app" })
      ;(fs.existsSync as ReturnType<typeof vi.fn>).mockImplementation((path: string) => {
        return path === "/app/routes.json"
      })
      ;(fs.readFileSync as ReturnType<typeof vi.fn>).mockReturnValue("invalid json {")

      const meta = await loadLitestarMeta(config)

      expect(meta).toEqual({})
    })

    it("returns empty object when routes file read throws error", async () => {
      const config = createMockViteConfig({ root: "/app" })
      ;(fs.existsSync as ReturnType<typeof vi.fn>).mockImplementation((path: string) => {
        return path === "/app/routes.json"
      })
      ;(fs.readFileSync as ReturnType<typeof vi.fn>).mockImplementation(() => {
        throw new Error("Permission denied")
      })

      const meta = await loadLitestarMeta(config)

      expect(meta).toEqual({})
    })

    it("returns empty object when version value is not a string", async () => {
      const config = createMockViteConfig({ root: "/app" })
      ;(fs.existsSync as ReturnType<typeof vi.fn>).mockImplementation((path: string) => {
        return path === "/app/routes.json"
      })
      ;(fs.readFileSync as ReturnType<typeof vi.fn>).mockReturnValue(JSON.stringify({ routes: {}, litestar_version: 123 }))

      const meta = await loadLitestarMeta(config)

      expect(meta).toEqual({})
    })

    it("uses process.cwd() when config.root is undefined", async () => {
      const config = createMockViteConfig()
      // @ts-expect-error - Testing undefined root
      config.root = undefined
      ;(fs.existsSync as ReturnType<typeof vi.fn>).mockReturnValue(false)

      const meta = await loadLitestarMeta(config)

      expect(meta).toEqual({})
      expect(fs.existsSync).toHaveBeenCalled()
    })
  })
})
