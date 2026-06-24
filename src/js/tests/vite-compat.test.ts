import { describe, expect, it } from "vitest"
import { buildBundlerOptions, buildInputOptions, resolveUserBuildInput } from "../src/shared/vite-compat"

describe("vite-compat", () => {
  describe("buildInputOptions", () => {
    it("returns rolldownOptions", () => {
      expect(buildInputOptions("app.ts")).toEqual({ rolldownOptions: { input: "app.ts" } })
    })

    it("handles array inputs", () => {
      expect(buildInputOptions(["app.ts", "admin.ts"])).toEqual({ rolldownOptions: { input: ["app.ts", "admin.ts"] } })
    })

    it("returns an empty fragment for undefined input", () => {
      expect(buildInputOptions(undefined)).toEqual({})
    })
  })

  describe("resolveUserBuildInput", () => {
    it("returns undefined for undefined build config", () => {
      expect(resolveUserBuildInput(undefined)).toBeUndefined()
    })

    it("reads from rolldownOptions", () => {
      expect(resolveUserBuildInput({ rolldownOptions: { input: "app.ts" } })).toBe("app.ts")
    })

    it("falls back to legacy rollupOptions for configs carried over from Vite 7", () => {
      expect(resolveUserBuildInput({ rollupOptions: { input: "legacy.ts" } })).toBe("legacy.ts")
    })
  })

  describe("buildBundlerOptions", () => {
    it("wraps options under rolldownOptions", () => {
      expect(buildBundlerOptions({ input: "app.ts", treeshake: true })).toEqual({ rolldownOptions: { input: "app.ts", treeshake: true } })
    })
  })
})
