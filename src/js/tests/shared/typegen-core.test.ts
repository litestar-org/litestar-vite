import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"

// Mock node:child_process exec (promisified as execAsync)
vi.mock("node:child_process", async (importOriginal) => {
  const actual = await importOriginal<typeof import("node:child_process")>()
  return {
    ...actual,
    exec: vi.fn(),
  }
})

// Mock node:fs
vi.mock("node:fs", async (importOriginal) => {
  const actual = await importOriginal<typeof import("node:fs")>()
  return {
    ...actual,
    default: {
      ...actual.default,
      existsSync: vi.fn(() => true),
      readFileSync: vi.fn(() => "{}"),
      writeFileSync: vi.fn(),
      mkdirSync: vi.fn(),
    },
    existsSync: vi.fn(() => true),
    readFileSync: vi.fn(() => "{}"),
    writeFileSync: vi.fn(),
    mkdirSync: vi.fn(),
  }
})

// Mock node:module createRequire
vi.mock("node:module", async (importOriginal) => {
  const actual = await importOriginal<typeof import("node:module")>()
  return {
    ...actual,
    createRequire: vi.fn(() => {
      const mockRequire = vi.fn() as any
      mockRequire.resolve = vi.fn(() => "/fake/path/to/@hey-api/openapi-ts/package.json")
      return mockRequire
    }),
  }
})

// Mock install-hint module
vi.mock("../../src/install-hint.js", () => ({
  resolveInstallHint: vi.fn((pkg?: string) => `npm install -D ${pkg || "@hey-api/openapi-ts"}`),
  resolvePackageExecutor: vi.fn((cmd: string) => `npx ${cmd}`),
}))

// Mock emit functions
vi.mock("../../src/shared/emit-page-props-types.js", () => ({
  emitPagePropsTypes: vi.fn(() => Promise.resolve(false)),
}))

vi.mock("../../src/shared/emit-schemas-types.js", () => ({
  emitSchemasTypes: vi.fn(() => Promise.resolve(false)),
}))

import { exec } from "node:child_process"
import fs from "node:fs"

import type { TypeGenCoreConfig, TypeGenLogger } from "../../src/shared/typegen-core"
import { runTypeGeneration } from "../../src/shared/typegen-core"

describe("typegen-core", () => {
  let mockLogger: TypeGenLogger

  beforeEach(() => {
    vi.clearAllMocks()

    // Setup default mocks
    vi.mocked(fs.existsSync).mockReturnValue(true)

    // Create mock logger
    mockLogger = {
      info: vi.fn(),
      warn: vi.fn(),
      error: vi.fn(),
    }
  })

  afterEach(() => {
    vi.resetAllMocks()
  })

  /**
   * Tests for error differentiation between different error types.
   */
  describe("error differentiation", () => {
    const createTestConfig = (projectRoot: string): TypeGenCoreConfig => ({
      projectRoot,
      openapiPath: "openapi.json",
      output: "src/types",
      pagePropsPath: "inertia-pages.json",
      routesPath: "routes.json",
      generateSdk: true,
      generateZod: false,
      generatePageProps: false,
      generateSchemas: false,
      sdkClientPlugin: "@hey-api/client-fetch",
    })

    it("treats 'not installed' error separately from runtime ENOENT - shows install hint", async () => {
      // "not installed" comes from our own check in runHeyApiGeneration
      const notInstalledError = new Error("@hey-api/openapi-ts not installed")
      vi.mocked(exec).mockImplementation((_cmd, _opts, callback) => {
        if (callback) {
          callback(notInstalledError, { stdout: "", stderr: "" })
        }
        return {} as any
      })

      const config = createTestConfig("/home/user/myproject")

      const result = await runTypeGeneration(config, { logger: mockLogger })

      expect(result.warnings).toHaveLength(1)
      expect(result.warnings[0]).toContain("@hey-api/openapi-ts not installed")
      expect(result.warnings[0]).toContain("npm install")
    })

    it("shows install hint with zod when generateZod is enabled", async () => {
      const notInstalledError = new Error("@hey-api/openapi-ts not installed")
      vi.mocked(exec).mockImplementation((_cmd, _opts, callback) => {
        if (callback) {
          callback(notInstalledError, { stdout: "", stderr: "" })
        }
        return {} as any
      })

      const config: TypeGenCoreConfig = {
        ...createTestConfig("/home/user/project"),
        generateZod: true,
      }

      const result = await runTypeGeneration(config, { logger: mockLogger })

      expect(result.warnings).toHaveLength(1)
      expect(result.warnings[0]).toContain("@hey-api/openapi-ts zod")
    })
  })

  describe("standard missing package warnings", () => {
    /**
     * Tests for the standard "not installed" warning behavior (lines 224-228 of typegen-core.ts).
     * These tests verify that when ENOENT occurs and projectRoot does NOT contain /src/,
     * the standard "@hey-api/openapi-ts not installed" warning is shown.
     */

    const createStandardTestConfig = (overrides: Partial<TypeGenCoreConfig> = {}): TypeGenCoreConfig => ({
      projectRoot: "/home/user/myproject", // NO /src/ in path
      openapiPath: "openapi.json",
      output: "types",
      pagePropsPath: "inertia-pages.json",
      routesPath: "routes.json",
      generateSdk: true,
      generateZod: false,
      generatePageProps: false,
      generateSchemas: false,
      sdkClientPlugin: "@hey-api/client-fetch",
      ...overrides,
    })

    it("shows standard 'not installed' warning when package is not installed", async () => {
      // "not installed" error triggers the install hint path
      const notInstalledError = new Error("@hey-api/openapi-ts not installed")
      vi.mocked(exec).mockImplementation((_cmd, _opts, callback) => {
        if (callback) {
          callback(notInstalledError, { stdout: "", stderr: "" })
        }
        return {} as any
      })

      const config = createStandardTestConfig()

      const result = await runTypeGeneration(config, { logger: mockLogger })

      expect(result.warnings).toHaveLength(1)
      expect(result.warnings[0]).toContain("@hey-api/openapi-ts not installed")
      expect(result.warnings[0]).toContain("npm install -D @hey-api/openapi-ts")
    })

    it("includes correct install hint format: npm install -D @hey-api/openapi-ts", async () => {
      const notInstalledError = new Error("@hey-api/openapi-ts not installed")
      vi.mocked(exec).mockImplementation((_cmd, _opts, callback) => {
        if (callback) {
          callback(notInstalledError, { stdout: "", stderr: "" })
        }
        return {} as any
      })

      const config = createStandardTestConfig()

      const result = await runTypeGeneration(config, { logger: mockLogger })

      // Verify the exact format of the warning
      expect(result.warnings[0]).toMatch(/run: npm install -D @hey-api\/openapi-ts/)
    })

    it("includes zod in install hint when generateZod is true", async () => {
      const notInstalledError = new Error("@hey-api/openapi-ts not installed")
      vi.mocked(exec).mockImplementation((_cmd, _opts, callback) => {
        if (callback) {
          callback(notInstalledError, { stdout: "", stderr: "" })
        }
        return {} as any
      })

      const config = createStandardTestConfig({ generateZod: true })

      const result = await runTypeGeneration(config, { logger: mockLogger })

      // Should include zod in the package list
      expect(result.warnings[0]).toContain("@hey-api/openapi-ts zod")
      expect(result.warnings[0]).toMatch(/npm install -D @hey-api\/openapi-ts zod/)
    })

    it("does not include zod when generateZod is false", async () => {
      const notInstalledError = new Error("@hey-api/openapi-ts not installed")
      vi.mocked(exec).mockImplementation((_cmd, _opts, callback) => {
        if (callback) {
          callback(notInstalledError, { stdout: "", stderr: "" })
        }
        return {} as any
      })

      const config = createStandardTestConfig({ generateZod: false })

      const result = await runTypeGeneration(config, { logger: mockLogger })

      // Should NOT include zod
      expect(result.warnings[0]).not.toContain("zod")
      expect(result.warnings[0]).toContain("npm install -D @hey-api/openapi-ts")
    })

    it("calls logger.warn with the correct warning message", async () => {
      const notInstalledError = new Error("@hey-api/openapi-ts not installed")
      vi.mocked(exec).mockImplementation((_cmd, _opts, callback) => {
        if (callback) {
          callback(notInstalledError, { stdout: "", stderr: "" })
        }
        return {} as any
      })

      const config = createStandardTestConfig()

      await runTypeGeneration(config, { logger: mockLogger })

      // Verify logger.warn was called
      expect(mockLogger.warn).toHaveBeenCalledTimes(1)
      expect(mockLogger.warn).toHaveBeenCalledWith(expect.stringContaining("@hey-api/openapi-ts not installed"))
      expect(mockLogger.warn).toHaveBeenCalledWith(expect.stringContaining("npm install -D @hey-api/openapi-ts"))
    })

    it("calls logger.warn with zod hint when generateZod is true", async () => {
      const notInstalledError = new Error("@hey-api/openapi-ts not installed")
      vi.mocked(exec).mockImplementation((_cmd, _opts, callback) => {
        if (callback) {
          callback(notInstalledError, { stdout: "", stderr: "" })
        }
        return {} as any
      })

      const config = createStandardTestConfig({ generateZod: true })

      await runTypeGeneration(config, { logger: mockLogger })

      expect(mockLogger.warn).toHaveBeenCalledWith(expect.stringContaining("@hey-api/openapi-ts zod"))
    })

    it("returns result with warnings array populated, errors array empty", async () => {
      const notInstalledError = new Error("@hey-api/openapi-ts not installed")
      vi.mocked(exec).mockImplementation((_cmd, _opts, callback) => {
        if (callback) {
          callback(notInstalledError, { stdout: "", stderr: "" })
        }
        return {} as any
      })

      const config = createStandardTestConfig()

      const result = await runTypeGeneration(config, { logger: mockLogger })

      expect(result).toMatchObject({
        generated: false,
        generatedFiles: [],
        warnings: expect.arrayContaining([expect.stringContaining("not installed")]),
        errors: [],
      })
    })

    it("works without logger (silent mode) - warnings still captured in result", async () => {
      const notInstalledError = new Error("@hey-api/openapi-ts not installed")
      vi.mocked(exec).mockImplementation((_cmd, _opts, callback) => {
        if (callback) {
          callback(notInstalledError, { stdout: "", stderr: "" })
        }
        return {} as any
      })

      const config = createStandardTestConfig()

      // Should not throw when no logger provided
      const result = await runTypeGeneration(config)

      // Warnings should still be captured in result
      expect(result.warnings).toHaveLength(1)
      expect(result.warnings[0]).toContain("@hey-api/openapi-ts not installed")
    })

    it("warning message format matches expected pattern", async () => {
      const notInstalledError = new Error("@hey-api/openapi-ts not installed")
      vi.mocked(exec).mockImplementation((_cmd, _opts, callback) => {
        if (callback) {
          callback(notInstalledError, { stdout: "", stderr: "" })
        }
        return {} as any
      })

      const config = createStandardTestConfig()

      const result = await runTypeGeneration(config, { logger: mockLogger })

      // The warning should match this exact pattern
      const expectedPattern = /^@hey-api\/openapi-ts not installed - run: npm install -D @hey-api\/openapi-ts$/
      expect(result.warnings[0]).toMatch(expectedPattern)
    })

    it("warning with zod matches expected format", async () => {
      const notInstalledError = new Error("@hey-api/openapi-ts not installed")
      vi.mocked(exec).mockImplementation((_cmd, _opts, callback) => {
        if (callback) {
          callback(notInstalledError, { stdout: "", stderr: "" })
        }
        return {} as any
      })

      const config = createStandardTestConfig({ generateZod: true })

      const result = await runTypeGeneration(config, { logger: mockLogger })

      // The warning should include zod
      const expectedPattern = /^@hey-api\/openapi-ts not installed - run: npm install -D @hey-api\/openapi-ts zod$/
      expect(result.warnings[0]).toMatch(expectedPattern)
    })

    it("result warnings and logger.warn receive identical messages", async () => {
      const notInstalledError = new Error("@hey-api/openapi-ts not installed")
      vi.mocked(exec).mockImplementation((_cmd, _opts, callback) => {
        if (callback) {
          callback(notInstalledError, { stdout: "", stderr: "" })
        }
        return {} as any
      })

      const config = createStandardTestConfig()

      const result = await runTypeGeneration(config, { logger: mockLogger })

      // The message pushed to result.warnings should match what logger.warn received
      expect(result.warnings[0]).toBe((mockLogger.warn as any).mock.calls[0][0])
    })
  })

  describe("runTypeGeneration basic behavior", () => {
    it("returns result with timing information", async () => {
      // Mock successful execution
      vi.mocked(exec).mockImplementation((_cmd, _opts, callback) => {
        if (callback) {
          callback(null, { stdout: "success", stderr: "" })
        }
        return {} as any
      })

      const config: TypeGenCoreConfig = {
        projectRoot: "/home/user/project",
        openapiPath: "openapi.json",
        output: "src/types",
        pagePropsPath: "inertia-pages.json",
        routesPath: "routes.json",
        generateSdk: true,
        generateZod: false,
        generatePageProps: false,
        generateSchemas: false,
        sdkClientPlugin: "@hey-api/client-fetch",
      }

      const result = await runTypeGeneration(config)

      expect(result.durationMs).toBeGreaterThanOrEqual(0)
      expect(result).toHaveProperty("generated")
      expect(result).toHaveProperty("generatedFiles")
      expect(result).toHaveProperty("skippedFiles")
      expect(result).toHaveProperty("warnings")
      expect(result).toHaveProperty("errors")
    })

    it("skips SDK generation when openapi file does not exist", async () => {
      vi.mocked(fs.existsSync).mockReturnValue(false)

      const config: TypeGenCoreConfig = {
        projectRoot: "/home/user/project",
        openapiPath: "openapi.json",
        output: "src/types",
        pagePropsPath: "inertia-pages.json",
        routesPath: "routes.json",
        generateSdk: true,
        generateZod: false,
        generatePageProps: false,
        generateSchemas: false,
        sdkClientPlugin: "@hey-api/client-fetch",
      }

      const result = await runTypeGeneration(config, { logger: mockLogger })

      // exec should not be called since openapi.json doesn't exist
      expect(exec).not.toHaveBeenCalled()
      expect(result.generated).toBe(false)
    })
  })
})
