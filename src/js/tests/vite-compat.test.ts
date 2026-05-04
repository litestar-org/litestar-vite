import { version } from "vite"
import { describe, expect, it } from "vitest"

import { buildBundlerOptions, buildInputOptions, isVite8Plus, resolveUserBuildInput, viteMajor } from "../src/shared/vite-compat"

describe("vite-compat", () => {
  const expectedMajor = Number(version.split(".")[0])

  it("detects the correct Vite major version", () => {
    expect(viteMajor).toBe(expectedMajor)
  })

  it("sets isVite8Plus based on major version", () => {
    expect(isVite8Plus).toBe(expectedMajor >= 8)
  })

  describe("buildInputOptions", () => {
    it("returns rolldownOptions for Vite 8+", () => {
      const result = buildInputOptions("app.ts")
      const key = isVite8Plus ? "rolldownOptions" : "rollupOptions"
      expect(result).toEqual({ [key]: { input: "app.ts" } })
    })

    it("handles array inputs", () => {
      const result = buildInputOptions(["app.ts", "admin.ts"])
      const key = isVite8Plus ? "rolldownOptions" : "rollupOptions"
      expect(result).toEqual({ [key]: { input: ["app.ts", "admin.ts"] } })
    })
  })

  describe("resolveUserBuildInput", () => {
    it("returns undefined for undefined build config", () => {
      expect(resolveUserBuildInput(undefined)).toBeUndefined()
    })

    it("reads from version-appropriate key", () => {
      const key = isVite8Plus ? "rolldownOptions" : "rollupOptions"
      const build = { [key]: { input: "app.ts" } }
      expect(resolveUserBuildInput(build)).toBe("app.ts")
    })

    it("falls back to alternate key", () => {
      // If user uses the "wrong" key for their Vite version, still works
      const fallbackKey = isVite8Plus ? "rollupOptions" : "rolldownOptions"
      const build = { [fallbackKey]: { input: "legacy.ts" } }
      expect(resolveUserBuildInput(build)).toBe("legacy.ts")
    })
  })

  describe("buildBundlerOptions", () => {
    it("wraps options under the correct key", () => {
      const result = buildBundlerOptions({ input: "app.ts", treeshake: true })
      const key = isVite8Plus ? "rolldownOptions" : "rollupOptions"
      expect(result).toEqual({ [key]: { input: "app.ts", treeshake: true } })
    })
  })
})
