import { exec } from "node:child_process"
import fs from "node:fs"
import os from "node:os"
import path from "node:path"
import { promisify } from "node:util"
import { afterEach, beforeAll, beforeEach, describe, expect, it } from "vitest"

const execAsync = promisify(exec)
const repoRoot = process.cwd()
let cliPath = ""

async function ensureCliBuilt(root: string): Promise<string> {
  const outputPath = path.join(root, "dist/js/typegen-cli.js")
  if (fs.existsSync(outputPath)) {
    return outputPath
  }

  const entryPath = path.join(root, "src/js/src/typegen-cli.ts")
  const { build } = await import("esbuild")
  fs.mkdirSync(path.dirname(outputPath), { recursive: true })

  await build({
    entryPoints: [entryPath],
    platform: "node",
    format: "esm",
    outfile: outputPath,
    bundle: true,
    packages: "external",
    banner: {
      js: "#!/usr/bin/env node",
    },
  })

  return outputPath
}

describe("typegen-cli", () => {
  let tmpDir: string
  let originalCwd: string

  beforeAll(async () => {
    cliPath = await ensureCliBuilt(repoRoot)
  })

  beforeEach(() => {
    // Create temp directory
    tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), "litestar-vite-cli-test-"))
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

  // Helper to create a minimal valid .litestar.json
  function createConfig(overrides: Record<string, any> = {}): Record<string, any> {
    const baseTypes = {
      enabled: false,
      output: path.join(tmpDir, "generated"),
      openapiPath: path.join(tmpDir, "generated/openapi.json"),
      routesPath: path.join(tmpDir, "generated/routes.json"),
      pagePropsPath: path.join(tmpDir, "generated/inertia-pages.json"),
      generateZod: false,
      generateSdk: false,
      generateRoutes: false,
      generatePageProps: false,
      globalRoute: false,
    }

    const mergedConfig = {
      assetUrl: "/static/",
      deployAssetUrl: null,
      bundleDir: "public",
      hotFile: "hot",
      resourceDir: "src",
      staticDir: "src/public",
      manifest: "manifest.json",
      mode: "spa",
      proxyMode: "vite",
      port: 5173,
      host: "127.0.0.1",
      ssrOutDir: null,
      logging: {
        level: "normal",
        showPathsAbsolute: false,
        suppressNpmOutput: false,
        suppressViteBanner: false,
        timestamps: false,
      },
      spa: null,
      executor: "node",
      litestarVersion: "2.19.0",
      ...overrides,
    }

    // Merge types separately to avoid duplicate key warning
    mergedConfig.types = { ...baseTypes, ...(overrides.types || {}) }
    return mergedConfig
  }

  describe("Configuration reading", () => {
    it("exits with error when .litestar.json is missing", async () => {
      // No .litestar.json file created
      try {
        await execAsync(`node ${cliPath}`)
        expect.fail("Should have thrown error")
      } catch (error: any) {
        expect(error.code).toBe(1)
        expect(error.stderr || error.stdout).toContain(".litestar.json not found")
      }
    })

    it("exits successfully when type generation is disabled", async () => {
      const config = createConfig({
        types: {
          enabled: false,
        },
      })

      fs.writeFileSync(path.join(tmpDir, ".litestar.json"), JSON.stringify(config, null, 2))

      const result = await execAsync(`node ${cliPath}`)

      expect(result.stdout).toContain("Type generation is disabled")
    })

    it("handles enabled types config with no OpenAPI file", async () => {
      const config = createConfig({
        types: {
          enabled: true,
          output: path.join(tmpDir, "generated"),
          openapiPath: path.join(tmpDir, "openapi.json"),
          pagePropsPath: path.join(tmpDir, "inertia-pages.json"),
          generateZod: false,
          generateSdk: true,
          generatePageProps: false,
        },
      })

      fs.writeFileSync(path.join(tmpDir, ".litestar.json"), JSON.stringify(config, null, 2))

      // Should complete without crashing (no files to process)
      const result = await execAsync(`node ${cliPath}`)
      expect(result.code).toBeUndefined() // Success
    })
  })

  describe("OpenAPI type generation", () => {
    it("generates types when openapi.json exists", async () => {
      const outputDir = path.join(tmpDir, "generated")
      fs.mkdirSync(outputDir, { recursive: true })

      const openapi = {
        openapi: "3.1.0",
        info: { title: "Test API", version: "1.0.0" },
        paths: {
          "/test": {
            get: {
              operationId: "test_get",
              responses: {
                "200": {
                  description: "Success",
                  content: {
                    "application/json": {
                      schema: {
                        type: "object",
                        properties: {
                          message: { type: "string" },
                        },
                      },
                    },
                  },
                },
              },
            },
          },
        },
      }

      fs.writeFileSync(path.join(tmpDir, "openapi.json"), JSON.stringify(openapi, null, 2))

      const config = createConfig({
        types: {
          enabled: true,
          output: outputDir,
          openapiPath: path.join(tmpDir, "openapi.json"),
          pagePropsPath: path.join(tmpDir, "inertia-pages.json"),
          generateZod: false,
          generateSdk: true,
          generatePageProps: false,
        },
      })

      fs.writeFileSync(path.join(tmpDir, ".litestar.json"), JSON.stringify(config, null, 2))

      try {
        const result = await execAsync(`node ${cliPath}`)
        // Either @hey-api/openapi-ts is installed and types were generated,
        // or it's not installed and we get a warning (but still succeed)
        const hasTypes = result.stdout.includes("TypeScript artifacts updated")
        const hasWarning = result.stdout.includes("@hey-api/openapi-ts not installed")
        expect(hasTypes || hasWarning).toBe(true)
      } catch (error: any) {
        // May fail if @hey-api/openapi-ts is not installed, that's okay
        const output = (error.stdout || "") + (error.stderr || "")
        if (error.message?.includes("not installed") || output.includes("not installed")) {
          expect(output).toContain("@hey-api/openapi-ts not installed")
        } else {
          throw error
        }
      }
    })
  })

  describe("Page props generation", () => {
    it("generates page-props.ts when inertia-pages.json exists", async () => {
      const outputDir = path.join(tmpDir, "generated")
      fs.mkdirSync(outputDir, { recursive: true })

      const pageProps = {
        pages: {
          "Dashboard/Index": {
            handler: "dashboard_index",
            propsType: "{ stats: StatsDto; user: UserDto }",
            route: "/dashboard",
          },
          "Auth/Login": {
            handler: "auth_login",
            propsType: "{ errors: ValidationErrorsDto }",
            route: "/login",
          },
        },
        sharedProps: {
          auth: { type: "AuthDto", optional: true },
          flash: { type: "FlashDto", optional: true },
        },
        typeGenConfig: {
          includeDefaultAuth: false,
          includeDefaultFlash: false,
        },
      }

      fs.writeFileSync(path.join(tmpDir, "inertia-pages.json"), JSON.stringify(pageProps, null, 2))

      const config = createConfig({
        types: {
          enabled: true,
          output: outputDir,
          openapiPath: path.join(tmpDir, "openapi.json"),
          pagePropsPath: path.join(tmpDir, "inertia-pages.json"),
          generateZod: false,
          generateSdk: false,
          generatePageProps: true,
        },
      })

      fs.writeFileSync(path.join(tmpDir, ".litestar.json"), JSON.stringify(config, null, 2))

      const result = await execAsync(`node ${cliPath}`)

      // Should generate page-props.ts
      const pagePropsPath = path.join(outputDir, "page-props.ts")
      expect(fs.existsSync(pagePropsPath)).toBe(true)

      const content = fs.readFileSync(pagePropsPath, "utf-8")
      expect(content).toContain("Dashboard/Index")
      expect(content).toContain("Auth/Login")
      expect(content).toContain("StatsDto")
      expect(content).toContain("UserDto")
      expect(result.stdout).toContain("TypeScript artifacts updated")
    })

    it("reports unchanged when page props haven't changed", async () => {
      const outputDir = path.join(tmpDir, "generated")
      fs.mkdirSync(outputDir, { recursive: true })

      const pageProps = {
        pages: {
          "Home/Index": {
            message: "string",
          },
        },
        sharedProps: {},
        typeGenConfig: {
          includeDefaultAuth: false,
          includeDefaultFlash: false,
        },
      }

      fs.writeFileSync(path.join(tmpDir, "inertia-pages.json"), JSON.stringify(pageProps, null, 2))

      const config = createConfig({
        types: {
          enabled: true,
          output: outputDir,
          openapiPath: path.join(tmpDir, "openapi.json"),
          pagePropsPath: path.join(tmpDir, "inertia-pages.json"),
          generateZod: false,
          generateSdk: false,
          generatePageProps: true,
        },
      })

      fs.writeFileSync(path.join(tmpDir, ".litestar.json"), JSON.stringify(config, null, 2))

      // First run - should generate
      const result1 = await execAsync(`node ${cliPath}`)
      expect(result1.stdout).toContain("TypeScript artifacts updated")

      // Second run - should be unchanged
      const result2 = await execAsync(`node ${cliPath}`)
      expect(result2.stdout).toContain("Page props types")
      expect(result2.stdout).toContain("unchanged")
    })
  })

  describe("Cache integration", () => {
    it("always runs hey-api on every invocation (no caching)", async () => {
      // CLI never uses caching - it always runs hey-api
      // This matches the old _run_openapi_ts behavior in Python
      // Caching is only used by the Vite plugin for HMR efficiency
      const outputDir = path.join(tmpDir, "generated")
      fs.mkdirSync(outputDir, { recursive: true })

      const openapi = {
        openapi: "3.1.0",
        info: { title: "Test API", version: "1.0.0" },
        paths: {},
      }

      fs.writeFileSync(path.join(tmpDir, "openapi.json"), JSON.stringify(openapi, null, 2))

      const config = createConfig({
        types: {
          enabled: true,
          output: outputDir,
          openapiPath: path.join(tmpDir, "openapi.json"),
          pagePropsPath: path.join(tmpDir, "inertia-pages.json"),
          generateZod: false,
          generateSdk: true,
          generatePageProps: false,
        },
      })

      fs.writeFileSync(path.join(tmpDir, ".litestar.json"), JSON.stringify(config, null, 2))

      try {
        // First run - should generate
        const result1 = await execAsync(`node ${cliPath}`)
        expect(result1.stdout).toContain("Generating TypeScript types")

        // Second run - should ALSO generate (no caching in CLI)
        const result2 = await execAsync(`node ${cliPath}`)
        expect(result2.stdout).toContain("Generating TypeScript types")
      } catch (error: any) {
        // Expected if @hey-api/openapi-ts is not installed
        const output = (error.stdout || "") + (error.stderr || "")
        if (error.message?.includes("not installed") || output.includes("not installed")) {
          expect(output).toContain("@hey-api/openapi-ts not installed")
        } else {
          throw error
        }
      }
    })
  })

  describe("CLI flags", () => {
    it("accepts --verbose flag", async () => {
      const config = createConfig({
        types: {
          enabled: false,
        },
      })

      fs.writeFileSync(path.join(tmpDir, ".litestar.json"), JSON.stringify(config, null, 2))

      const result = await execAsync(`node ${cliPath} --verbose`)

      expect(result.stdout).toContain("Type generation is disabled")
    })

    it("accepts --no-cache flag", async () => {
      const outputDir = path.join(tmpDir, "generated")
      fs.mkdirSync(outputDir, { recursive: true })

      const pageProps = {
        pages: {},
        sharedProps: {},
        typeGenConfig: {
          includeDefaultAuth: false,
          includeDefaultFlash: false,
        },
      }

      fs.writeFileSync(path.join(tmpDir, "inertia-pages.json"), JSON.stringify(pageProps, null, 2))

      const config = createConfig({
        types: {
          enabled: true,
          output: outputDir,
          openapiPath: path.join(tmpDir, "openapi.json"),
          pagePropsPath: path.join(tmpDir, "inertia-pages.json"),
          generateZod: false,
          generateSdk: false,
          generatePageProps: true,
        },
      })

      fs.writeFileSync(path.join(tmpDir, ".litestar.json"), JSON.stringify(config, null, 2))

      // Run with --no-cache should always regenerate
      const result = await execAsync(`node ${cliPath} --no-cache`)
      expect(result.stdout).toBeTruthy()
    })
  })

  describe("Error handling", () => {
    it("handles invalid JSON in .litestar.json", async () => {
      fs.writeFileSync(path.join(tmpDir, ".litestar.json"), "invalid json {{{")

      try {
        await execAsync(`node ${cliPath}`)
        expect.fail("Should have thrown error")
      } catch (error: any) {
        expect(error.code).toBe(1)
      }
    })

    it("exits with error on page props generation failure", async () => {
      const outputDir = path.join(tmpDir, "generated")
      fs.mkdirSync(outputDir, { recursive: true })

      // Create invalid inertia-pages.json
      fs.writeFileSync(path.join(tmpDir, "inertia-pages.json"), "invalid json")

      const config = createConfig({
        types: {
          enabled: true,
          output: outputDir,
          openapiPath: path.join(tmpDir, "openapi.json"),
          pagePropsPath: path.join(tmpDir, "inertia-pages.json"),
          generateZod: false,
          generateSdk: false,
          generatePageProps: true,
        },
      })

      fs.writeFileSync(path.join(tmpDir, ".litestar.json"), JSON.stringify(config, null, 2))

      try {
        await execAsync(`node ${cliPath}`)
        expect.fail("Should have thrown error")
      } catch (error: any) {
        expect(error.code).toBe(1)
        expect(error.stdout || error.stderr).toContain("Page props generation failed")
      }
    })
  })
})
