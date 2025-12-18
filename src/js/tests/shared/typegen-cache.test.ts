import fs from "node:fs"
import os from "node:os"
import path from "node:path"
import { afterEach, beforeEach, describe, expect, it } from "vitest"

import { computePagePropsHash, shouldRegeneratePageProps, shouldRunOpenApiTs, updateOpenApiTsCache, updatePagePropsCache } from "../../src/shared/typegen-cache"

describe("typegen-cache", () => {
  let tmpDir: string
  let cacheDir: string
  let originalCwd: string

  beforeEach(() => {
    // Create temp directory
    tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), "litestar-vite-test-"))

    // Create cache directory inside temp
    cacheDir = path.join(tmpDir, "node_modules", ".cache", "litestar-vite")
    fs.mkdirSync(cacheDir, { recursive: true })

    // Change to temp directory
    originalCwd = process.cwd()
    process.chdir(tmpDir)
  })

  afterEach(() => {
    // Restore original directory
    process.chdir(originalCwd)

    // Cleanup temp directory
    if (fs.existsSync(tmpDir)) {
      fs.rmSync(tmpDir, { recursive: true, force: true })
    }
  })

  describe("shouldRunOpenApiTs", () => {
    it("returns true when no cache exists", async () => {
      const openapiPath = path.join(tmpDir, "openapi.json")
      fs.writeFileSync(openapiPath, JSON.stringify({ openapi: "3.1.0" }))

      const options = {
        generateSdk: true,
        generateZod: false,
        plugins: ["@hey-api/typescript", "@hey-api/schemas"],
      }

      const shouldRun = await shouldRunOpenApiTs(openapiPath, null, options)

      expect(shouldRun).toBe(true)
    })

    it("returns false when inputs are unchanged", async () => {
      const openapiPath = path.join(tmpDir, "openapi.json")
      const content = JSON.stringify({ openapi: "3.1.0" })
      fs.writeFileSync(openapiPath, content)

      const options = {
        generateSdk: true,
        generateZod: false,
        plugins: ["@hey-api/typescript", "@hey-api/schemas"],
      }

      // First run - should run
      const shouldRun1 = await shouldRunOpenApiTs(openapiPath, null, options)
      expect(shouldRun1).toBe(true)

      // Update cache
      await updateOpenApiTsCache(openapiPath, null, options)

      // Second run - should skip (inputs unchanged)
      const shouldRun2 = await shouldRunOpenApiTs(openapiPath, null, options)
      expect(shouldRun2).toBe(false)
    })

    it("returns true when openapi.json content changes", async () => {
      const openapiPath = path.join(tmpDir, "openapi.json")
      fs.writeFileSync(openapiPath, JSON.stringify({ openapi: "3.1.0" }))

      const options = {
        generateSdk: true,
        generateZod: false,
        plugins: ["@hey-api/typescript", "@hey-api/schemas"],
      }

      await updateOpenApiTsCache(openapiPath, null, options)

      // Change openapi.json
      fs.writeFileSync(openapiPath, JSON.stringify({ openapi: "3.1.0", info: { title: "Test" } }))

      const shouldRun = await shouldRunOpenApiTs(openapiPath, null, options)
      expect(shouldRun).toBe(true)
    })

    it("returns true when config file changes", async () => {
      const openapiPath = path.join(tmpDir, "openapi.json")
      const configPath = path.join(tmpDir, "openapi-ts.config.ts")
      fs.writeFileSync(openapiPath, JSON.stringify({ openapi: "3.1.0" }))
      fs.writeFileSync(configPath, "export default { client: 'fetch' }")

      const options = {
        generateSdk: true,
        generateZod: false,
        plugins: ["@hey-api/typescript", "@hey-api/schemas"],
      }

      await updateOpenApiTsCache(openapiPath, configPath, options)

      // Change config
      fs.writeFileSync(configPath, "export default { client: 'axios' }")

      const shouldRun = await shouldRunOpenApiTs(openapiPath, configPath, options)
      expect(shouldRun).toBe(true)
    })

    it("returns true when options change", async () => {
      const openapiPath = path.join(tmpDir, "openapi.json")
      fs.writeFileSync(openapiPath, JSON.stringify({ openapi: "3.1.0" }))

      const options1 = {
        generateSdk: true,
        generateZod: false,
        plugins: ["@hey-api/typescript", "@hey-api/schemas"],
      }

      await updateOpenApiTsCache(openapiPath, null, options1)

      // Change options
      const options2 = {
        generateSdk: true,
        generateZod: true, // Changed
        plugins: ["@hey-api/typescript", "@hey-api/schemas", "zod"],
      }

      const shouldRun = await shouldRunOpenApiTs(openapiPath, null, options2)
      expect(shouldRun).toBe(true)
    })

    it("handles missing openapi.json file", async () => {
      const openapiPath = path.join(tmpDir, "missing.json")

      const options = {
        generateSdk: true,
        generateZod: false,
        plugins: ["@hey-api/typescript", "@hey-api/schemas"],
      }

      // Should not throw, returns true (no cache match possible)
      const shouldRun = await shouldRunOpenApiTs(openapiPath, null, options)
      expect(shouldRun).toBe(true)
    })
  })

  describe("computePagePropsHash", () => {
    it("computes consistent hash for same content", async () => {
      const filePath = path.join(tmpDir, "inertia-pages.json")
      const content = JSON.stringify({ pages: {}, sharedProps: {} })
      fs.writeFileSync(filePath, content)

      const hash1 = await computePagePropsHash(filePath)
      const hash2 = await computePagePropsHash(filePath)

      expect(hash1).toBe(hash2)
      expect(hash1).toMatch(/^[a-f0-9]{64}$/) // SHA-256 hex
    })

    it("computes different hash for different content", async () => {
      const filePath = path.join(tmpDir, "inertia-pages.json")

      fs.writeFileSync(filePath, JSON.stringify({ pages: { Home: {} } }))
      const hash1 = await computePagePropsHash(filePath)

      fs.writeFileSync(filePath, JSON.stringify({ pages: { About: {} } }))
      const hash2 = await computePagePropsHash(filePath)

      expect(hash1).not.toBe(hash2)
    })

    it("returns empty string for missing file", async () => {
      const filePath = path.join(tmpDir, "missing.json")

      const hash = await computePagePropsHash(filePath)
      expect(hash).toBe("")
    })
  })

  describe("shouldRegeneratePageProps", () => {
    it("returns true when no cache exists", async () => {
      const filePath = path.join(tmpDir, "inertia-pages.json")
      fs.writeFileSync(filePath, JSON.stringify({ pages: {} }))

      const shouldRegen = await shouldRegeneratePageProps(filePath)
      expect(shouldRegen).toBe(true)
    })

    it("returns false when input is unchanged", async () => {
      const filePath = path.join(tmpDir, "inertia-pages.json")
      fs.writeFileSync(filePath, JSON.stringify({ pages: {} }))

      // First check - should regenerate
      const shouldRegen1 = await shouldRegeneratePageProps(filePath)
      expect(shouldRegen1).toBe(true)

      // Update cache
      await updatePagePropsCache(filePath)

      // Second check - should skip
      const shouldRegen2 = await shouldRegeneratePageProps(filePath)
      expect(shouldRegen2).toBe(false)
    })

    it("returns true when input changes", async () => {
      const filePath = path.join(tmpDir, "inertia-pages.json")
      fs.writeFileSync(filePath, JSON.stringify({ pages: {} }))

      await updatePagePropsCache(filePath)

      // Change content
      fs.writeFileSync(filePath, JSON.stringify({ pages: { Home: {} } }))

      const shouldRegen = await shouldRegeneratePageProps(filePath)
      expect(shouldRegen).toBe(true)
    })
  })

  describe("cache persistence", () => {
    it("persists cache across function calls", async () => {
      const openapiPath = path.join(tmpDir, "openapi.json")
      fs.writeFileSync(openapiPath, JSON.stringify({ openapi: "3.1.0" }))

      const options = {
        generateSdk: true,
        generateZod: false,
        plugins: ["@hey-api/typescript", "@hey-api/schemas"],
      }

      await updateOpenApiTsCache(openapiPath, null, options)

      // Cache file should exist
      const cacheFile = path.join(cacheDir, "typegen-cache.json")
      expect(fs.existsSync(cacheFile)).toBe(true)

      // Read and verify cache structure
      const cache = JSON.parse(fs.readFileSync(cacheFile, "utf-8"))
      expect(cache).toHaveProperty("openapi-ts")
      expect(cache["openapi-ts"]).toHaveProperty("inputHash")
      expect(cache["openapi-ts"]).toHaveProperty("configHash")
      expect(cache["openapi-ts"]).toHaveProperty("optionsHash")
      expect(cache["openapi-ts"]).toHaveProperty("timestamp")
    })

    it("handles corrupted cache gracefully", async () => {
      const cacheFile = path.join(cacheDir, "typegen-cache.json")
      fs.writeFileSync(cacheFile, "invalid json{{{")

      const openapiPath = path.join(tmpDir, "openapi.json")
      fs.writeFileSync(openapiPath, JSON.stringify({ openapi: "3.1.0" }))

      const options = {
        generateSdk: true,
        generateZod: false,
        plugins: ["@hey-api/typescript", "@hey-api/schemas"],
      }

      // Should not throw, returns true (cache read fails)
      const shouldRun = await shouldRunOpenApiTs(openapiPath, null, options)
      expect(shouldRun).toBe(true)
    })

    it("stores multiple cache entries independently", async () => {
      const openapiPath = path.join(tmpDir, "openapi.json")
      const pagePropsPath = path.join(tmpDir, "inertia-pages.json")

      fs.writeFileSync(openapiPath, JSON.stringify({ openapi: "3.1.0" }))
      fs.writeFileSync(pagePropsPath, JSON.stringify({ pages: {} }))

      const options = {
        generateSdk: true,
        generateZod: false,
        plugins: ["@hey-api/typescript", "@hey-api/schemas"],
      }

      await updateOpenApiTsCache(openapiPath, null, options)
      await updatePagePropsCache(pagePropsPath)

      const cacheFile = path.join(cacheDir, "typegen-cache.json")
      const cache = JSON.parse(fs.readFileSync(cacheFile, "utf-8"))

      expect(cache).toHaveProperty("openapi-ts")
      expect(cache).toHaveProperty("page-props")
    })
  })

  describe("hash determinism", () => {
    it("produces deterministic hash for same object with different key order", async () => {
      const openapiPath = path.join(tmpDir, "openapi.json")
      fs.writeFileSync(openapiPath, JSON.stringify({ openapi: "3.1.0" }))

      const options1 = {
        generateSdk: true,
        generateZod: false,
        plugins: ["@hey-api/typescript", "@hey-api/schemas"],
      }

      const options2 = {
        generateZod: false,
        generateSdk: true,
        plugins: ["@hey-api/typescript", "@hey-api/schemas"],
      }

      await updateOpenApiTsCache(openapiPath, null, options1)

      // Should skip - options are equivalent
      const shouldRun = await shouldRunOpenApiTs(openapiPath, null, options2)
      expect(shouldRun).toBe(false)
    })
  })
})
