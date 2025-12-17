import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"
import { detectExecutor, resolveInstallHint, resolvePackageExecutor } from "../src/install-hint"

// Mock fs module
vi.mock("node:fs", () => ({
  default: {
    existsSync: vi.fn(() => false),
    readFileSync: vi.fn(() => "{}"),
  },
  existsSync: vi.fn(() => false),
  readFileSync: vi.fn(() => "{}"),
}))

import fs from "node:fs"

describe("install-hint", () => {
  const originalEnv = { ...process.env }

  beforeEach(() => {
    vi.resetModules()
    vi.mocked(fs.existsSync).mockReturnValue(false)
    vi.mocked(fs.readFileSync).mockReturnValue("{}")
    process.env = { ...originalEnv }
    process.env.LITESTAR_VITE_RUNTIME = undefined
    process.env.LITESTAR_VITE_INSTALL_CMD = undefined
    process.env.LITESTAR_VITE_CONFIG_PATH = undefined
  })

  afterEach(() => {
    process.env = originalEnv
    vi.clearAllMocks()
  })

  describe("detectExecutor", () => {
    it("returns node by default when no lockfiles exist", () => {
      expect(detectExecutor()).toBe("node")
    })

    it("returns bun when bun.lockb exists", () => {
      vi.mocked(fs.existsSync).mockImplementation((p) => String(p).includes("bun.lockb"))

      expect(detectExecutor()).toBe("bun")
    })

    it("returns bun when bun.lock exists", () => {
      vi.mocked(fs.existsSync).mockImplementation((p) => String(p).includes("bun.lock") && !String(p).includes("bun.lockb"))

      expect(detectExecutor()).toBe("bun")
    })

    it("returns pnpm when pnpm-lock.yaml exists", () => {
      vi.mocked(fs.existsSync).mockImplementation((p) => String(p).includes("pnpm-lock.yaml"))

      expect(detectExecutor()).toBe("pnpm")
    })

    it("returns yarn when yarn.lock exists", () => {
      vi.mocked(fs.existsSync).mockImplementation((p) => String(p).includes("yarn.lock"))

      expect(detectExecutor()).toBe("yarn")
    })

    it("returns deno when deno.lock exists", () => {
      vi.mocked(fs.existsSync).mockImplementation((p) => String(p).includes("deno.lock"))

      expect(detectExecutor()).toBe("deno")
    })

    it("reads executor from .litestar.json", () => {
      vi.mocked(fs.existsSync).mockImplementation((p) => String(p).includes(".litestar.json"))
      vi.mocked(fs.readFileSync).mockReturnValue(JSON.stringify({ executor: "bun" }))

      expect(detectExecutor()).toBe("bun")
    })

    it("prioritizes env var over .litestar.json", () => {
      process.env.LITESTAR_VITE_RUNTIME = "pnpm"
      vi.mocked(fs.existsSync).mockReturnValue(true)
      vi.mocked(fs.readFileSync).mockReturnValue(JSON.stringify({ executor: "bun" }))

      expect(detectExecutor()).toBe("pnpm")
    })

    it("prioritizes .litestar.json over lockfiles", () => {
      vi.mocked(fs.existsSync).mockReturnValue(true)
      vi.mocked(fs.readFileSync).mockReturnValue(JSON.stringify({ executor: "yarn" }))

      expect(detectExecutor()).toBe("yarn")
    })
  })

  describe("resolveInstallHint", () => {
    it("returns npm install by default", () => {
      const hint = resolveInstallHint()

      expect(hint).toBe("npm install -D @hey-api/openapi-ts")
    })

    it("returns npm install for custom package", () => {
      const hint = resolveInstallHint("some-package")

      expect(hint).toBe("npm install -D some-package")
    })

    it("returns bun add for bun runtime", () => {
      process.env.LITESTAR_VITE_RUNTIME = "bun"

      const hint = resolveInstallHint()

      expect(hint).toBe("bun add -d @hey-api/openapi-ts")
    })

    it("returns bun add for BUN runtime (case insensitive)", () => {
      process.env.LITESTAR_VITE_RUNTIME = "BUN"

      const hint = resolveInstallHint()

      expect(hint).toBe("bun add -d @hey-api/openapi-ts")
    })

    it("returns deno add for deno runtime", () => {
      process.env.LITESTAR_VITE_RUNTIME = "deno"

      const hint = resolveInstallHint()

      expect(hint).toBe("deno add -d npm:@hey-api/openapi-ts")
    })

    it("returns pnpm add for pnpm runtime", () => {
      process.env.LITESTAR_VITE_RUNTIME = "pnpm"

      const hint = resolveInstallHint()

      expect(hint).toBe("pnpm add -D @hey-api/openapi-ts")
    })

    it("returns yarn add for yarn runtime", () => {
      process.env.LITESTAR_VITE_RUNTIME = "yarn"

      const hint = resolveInstallHint()

      expect(hint).toBe("yarn add -D @hey-api/openapi-ts")
    })

    it("uses LITESTAR_VITE_INSTALL_CMD when set", () => {
      process.env.LITESTAR_VITE_INSTALL_CMD = "custom-install"

      const hint = resolveInstallHint()

      expect(hint).toBe("custom-install -D @hey-api/openapi-ts")
    })

    it("uses LITESTAR_VITE_INSTALL_CMD with custom package", () => {
      process.env.LITESTAR_VITE_INSTALL_CMD = "custom-install"

      const hint = resolveInstallHint("my-package")

      expect(hint).toBe("custom-install -D my-package")
    })

    it("trims whitespace from LITESTAR_VITE_INSTALL_CMD", () => {
      process.env.LITESTAR_VITE_INSTALL_CMD = "  custom-install  "

      const hint = resolveInstallHint()

      expect(hint).toBe("custom-install -D @hey-api/openapi-ts")
    })

    it("ignores empty LITESTAR_VITE_INSTALL_CMD", () => {
      process.env.LITESTAR_VITE_INSTALL_CMD = "   "

      const hint = resolveInstallHint()

      expect(hint).toBe("npm install -D @hey-api/openapi-ts")
    })

    it("prioritizes LITESTAR_VITE_RUNTIME over LITESTAR_VITE_INSTALL_CMD", () => {
      process.env.LITESTAR_VITE_RUNTIME = "bun"
      process.env.LITESTAR_VITE_INSTALL_CMD = "custom-install"

      const hint = resolveInstallHint()

      // Runtime takes precedence
      expect(hint).toBe("bun add -d @hey-api/openapi-ts")
    })

    it("handles unknown runtime as npm", () => {
      process.env.LITESTAR_VITE_RUNTIME = "unknown-runtime"

      const hint = resolveInstallHint()

      expect(hint).toBe("npm install -D @hey-api/openapi-ts")
    })

    it("detects bun from lockfile when no env var set", () => {
      vi.mocked(fs.existsSync).mockImplementation((p) => String(p).includes("bun.lockb"))

      const hint = resolveInstallHint()

      expect(hint).toBe("bun add -d @hey-api/openapi-ts")
    })

    it("reads from .litestar.json when available", () => {
      vi.mocked(fs.existsSync).mockImplementation((p) => String(p).includes(".litestar.json"))
      vi.mocked(fs.readFileSync).mockReturnValue(JSON.stringify({ executor: "pnpm" }))

      const hint = resolveInstallHint()

      expect(hint).toBe("pnpm add -D @hey-api/openapi-ts")
    })
  })

  describe("resolvePackageExecutor", () => {
    it("returns npx by default", () => {
      const executor = resolvePackageExecutor("@hey-api/openapi-ts -i schema.json")

      expect(executor).toBe("npx @hey-api/openapi-ts -i schema.json")
    })

    it("returns bunx for bun runtime", () => {
      process.env.LITESTAR_VITE_RUNTIME = "bun"

      const executor = resolvePackageExecutor("@hey-api/openapi-ts")

      expect(executor).toBe("bunx @hey-api/openapi-ts")
    })

    it("returns bunx for BUN runtime (case insensitive)", () => {
      process.env.LITESTAR_VITE_RUNTIME = "BUN"

      const executor = resolvePackageExecutor("@hey-api/openapi-ts")

      expect(executor).toBe("bunx @hey-api/openapi-ts")
    })

    it("returns deno run for deno runtime", () => {
      process.env.LITESTAR_VITE_RUNTIME = "deno"

      const executor = resolvePackageExecutor("@hey-api/openapi-ts")

      expect(executor).toBe("deno run -A npm:@hey-api/openapi-ts")
    })

    it("returns pnpm dlx for pnpm runtime", () => {
      process.env.LITESTAR_VITE_RUNTIME = "pnpm"

      const executor = resolvePackageExecutor("@hey-api/openapi-ts")

      expect(executor).toBe("pnpm dlx @hey-api/openapi-ts")
    })

    it("returns yarn dlx for yarn runtime", () => {
      process.env.LITESTAR_VITE_RUNTIME = "yarn"

      const executor = resolvePackageExecutor("@hey-api/openapi-ts")

      expect(executor).toBe("yarn dlx @hey-api/openapi-ts")
    })

    it("prefers explicit executor over env var", () => {
      process.env.LITESTAR_VITE_RUNTIME = "yarn"

      const executor = resolvePackageExecutor("@hey-api/openapi-ts", "bun")

      expect(executor).toBe("bunx @hey-api/openapi-ts")
    })

    it("uses env var when executor is undefined", () => {
      process.env.LITESTAR_VITE_RUNTIME = "pnpm"

      const executor = resolvePackageExecutor("@hey-api/openapi-ts", undefined)

      expect(executor).toBe("pnpm dlx @hey-api/openapi-ts")
    })

    it("uses detected executor when executor is empty string", () => {
      vi.mocked(fs.existsSync).mockImplementation((p) => String(p).includes("pnpm-lock.yaml"))

      const executor = resolvePackageExecutor("@hey-api/openapi-ts", "")

      // Empty string triggers lockfile detection
      expect(executor).toBe("pnpm dlx @hey-api/openapi-ts")
    })

    it("handles unknown runtime as npx", () => {
      process.env.LITESTAR_VITE_RUNTIME = "unknown-runtime"

      const executor = resolvePackageExecutor("@hey-api/openapi-ts")

      expect(executor).toBe("npx @hey-api/openapi-ts")
    })

    it("handles unknown explicit executor as npx", () => {
      const executor = resolvePackageExecutor("@hey-api/openapi-ts", "unknown")

      expect(executor).toBe("npx @hey-api/openapi-ts")
    })

    it("works with package command containing arguments", () => {
      process.env.LITESTAR_VITE_RUNTIME = "bun"

      const executor = resolvePackageExecutor("@hey-api/openapi-ts -i /path/to/schema.json -o src/types -c @hey-api/client-fetch")

      expect(executor).toBe("bunx @hey-api/openapi-ts -i /path/to/schema.json -o src/types -c @hey-api/client-fetch")
    })

    it("handles 'node' as explicit executor (default)", () => {
      const executor = resolvePackageExecutor("@hey-api/openapi-ts", "node")

      expect(executor).toBe("npx @hey-api/openapi-ts")
    })

    it("detects bun from lockfile when no env var set", () => {
      vi.mocked(fs.existsSync).mockImplementation((p) => String(p).includes("bun.lockb"))

      const executor = resolvePackageExecutor("@hey-api/openapi-ts")

      expect(executor).toBe("bunx @hey-api/openapi-ts")
    })

    it("reads from .litestar.json when available", () => {
      vi.mocked(fs.existsSync).mockImplementation((p) => String(p).includes(".litestar.json"))
      vi.mocked(fs.readFileSync).mockReturnValue(JSON.stringify({ executor: "yarn" }))

      const executor = resolvePackageExecutor("@hey-api/openapi-ts")

      expect(executor).toBe("yarn dlx @hey-api/openapi-ts")
    })
  })
})
