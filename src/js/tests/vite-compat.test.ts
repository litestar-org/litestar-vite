import { describe, expect, it } from "vitest"
import { buildBundlerOptions, buildInputOptions, isVite8Plus, resolveUserBuildInput } from "../src/shared/vite-compat"

// Vite 8+ uses Rolldown (`rolldownOptions`); Vite 7 uses Rollup (`rollupOptions`).
const bundlerKey = isVite8Plus ? "rolldownOptions" : "rollupOptions"
const otherBundlerKey = isVite8Plus ? "rollupOptions" : "rolldownOptions"

describe("vite-compat", () => {
  describe("buildInputOptions", () => {
    it("places input under the version-appropriate bundler key", () => {
      expect(buildInputOptions("app.ts")).toEqual({ [bundlerKey]: { input: "app.ts" } })
    })

    it("handles array inputs", () => {
      expect(buildInputOptions(["app.ts", "admin.ts"])).toEqual({ [bundlerKey]: { input: ["app.ts", "admin.ts"] } })
    })

    it("returns an empty fragment for undefined input", () => {
      expect(buildInputOptions(undefined)).toEqual({})
    })
  })

  describe("resolveUserBuildInput", () => {
    it("returns undefined for undefined build config", () => {
      expect(resolveUserBuildInput(undefined)).toBeUndefined()
    })

    it("reads from the version-appropriate key", () => {
      expect(resolveUserBuildInput({ [bundlerKey]: { input: "app.ts" } })).toBe("app.ts")
    })

    it("falls back to the other bundler key for configs carried across a Vite major", () => {
      expect(resolveUserBuildInput({ [otherBundlerKey]: { input: "legacy.ts" } })).toBe("legacy.ts")
    })
  })

  describe("buildBundlerOptions", () => {
    it("wraps options under the version-appropriate bundler key", () => {
      expect(buildBundlerOptions({ input: "app.ts", treeshake: true })).toEqual({ [bundlerKey]: { input: "app.ts", treeshake: true } })
    })
  })
})
