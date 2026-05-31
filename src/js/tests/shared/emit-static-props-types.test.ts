import fs from "node:fs"
import path from "node:path"
import { afterEach, beforeEach, describe, expect, it } from "vitest"

import { emitStaticPropsTypes } from "../../src/shared/emit-static-props-types"

const tmpDirs: string[] = []
const originalEnv = { ...process.env }

const createTmpDir = (): string => {
  const dir = fs.mkdtempSync(path.join(process.cwd(), "vitest-static-props-emit-"))
  tmpDirs.push(dir)
  return dir
}

const createBridgeConfig = (staticProps: Record<string, unknown> | null, tmpDir: string): string => {
  const cfgPath = path.join(tmpDir, ".litestar.json")
  const config = {
    assetUrl: "/static",
    deployAssetUrl: null,
    bundleDir: "public",
    resourceDir: "resources",
    staticDir: "public",
    hotFile: "hot",
    manifest: "manifest.json",
    mode: "spa",
    proxyMode: "vite",
    host: "localhost",
    port: 5173,
    ssrOutDir: null,
    types: null,
    spa: null,
    executor: "node",
    logging: null,
    litestarVersion: "2.18.0",
    staticProps,
  }
  fs.writeFileSync(cfgPath, JSON.stringify(config), "utf-8")
  process.env.LITESTAR_VITE_CONFIG_PATH = cfgPath
  return cfgPath
}

beforeEach(() => {
  process.env = { ...originalEnv }
  // Point to a non-existent config file by default
  process.env.LITESTAR_VITE_CONFIG_PATH = path.join(process.cwd(), ".vitest-missing-config.json")
})

afterEach(() => {
  process.env = { ...originalEnv }
  for (const dir of tmpDirs) {
    try {
      fs.rmSync(dir, { recursive: true, force: true })
    } catch {
      // ignore
    }
  }
  tmpDirs.length = 0
})

describe("emitStaticPropsTypes", () => {
  it("generates empty interface when no static props", async () => {
    const tmpDir = createTmpDir()
    createBridgeConfig(null, tmpDir)

    const outputDir = path.join(tmpDir, "generated")
    const changed = await emitStaticPropsTypes(outputDir)

    expect(changed).toBe(true)

    const outFile = path.join(outputDir, "static-props.ts")
    expect(fs.existsSync(outFile)).toBe(true)

    const content = fs.readFileSync(outFile, "utf-8")
    expect(content).toContain("export interface StaticProps {}")
    expect(content).toContain("export const staticProps: StaticProps = {}")
    expect(content).toContain("Currently empty")
  })

  it("generates typed interface for simple props", async () => {
    const tmpDir = createTmpDir()
    createBridgeConfig(
      {
        appName: "My App",
        version: "1.0.0",
        debug: true,
        maxUsers: 100,
      },
      tmpDir,
    )

    const outputDir = path.join(tmpDir, "generated")
    const changed = await emitStaticPropsTypes(outputDir)

    expect(changed).toBe(true)

    const outFile = path.join(outputDir, "static-props.ts")
    const content = fs.readFileSync(outFile, "utf-8")

    expect(content).toContain("appName: string")
    expect(content).toContain("version: string")
    expect(content).toContain("debug: boolean")
    expect(content).toContain("maxUsers: number")
    expect(content).toContain("export const appName = staticProps.appName")
    expect(content).toContain("export const version = staticProps.version")
  })

  it("generates named interfaces for nested objects", async () => {
    const tmpDir = createTmpDir()
    createBridgeConfig(
      {
        database: {
          host: "localhost",
          port: 5432,
          name: "mydb",
        },
      },
      tmpDir,
    )

    const outputDir = path.join(tmpDir, "generated")
    await emitStaticPropsTypes(outputDir)

    const outFile = path.join(outputDir, "static-props.ts")
    const content = fs.readFileSync(outFile, "utf-8")

    expect(content).toContain("export interface Database {")
    expect(content).toContain("host: string")
    expect(content).toContain("port: number")
    expect(content).toContain("database: Database")
  })

  it("handles arrays correctly", async () => {
    const tmpDir = createTmpDir()
    createBridgeConfig(
      {
        tags: ["web", "python", "typescript"],
        numbers: [1, 2, 3],
        mixed: [1, "two", true],
      },
      tmpDir,
    )

    const outputDir = path.join(tmpDir, "generated")
    await emitStaticPropsTypes(outputDir)

    const outFile = path.join(outputDir, "static-props.ts")
    const content = fs.readFileSync(outFile, "utf-8")

    expect(content).toContain("tags: string[]")
    expect(content).toContain("numbers: number[]")
    expect(content).toContain("mixed: (number | string | boolean)[]")
  })

  it("handles null values", async () => {
    const tmpDir = createTmpDir()
    createBridgeConfig(
      {
        optionalValue: null,
      },
      tmpDir,
    )

    const outputDir = path.join(tmpDir, "generated")
    await emitStaticPropsTypes(outputDir)

    const outFile = path.join(outputDir, "static-props.ts")
    const content = fs.readFileSync(outFile, "utf-8")

    expect(content).toContain("optionalValue: null")
  })

  it("quotes invalid identifier keys", async () => {
    const tmpDir = createTmpDir()
    createBridgeConfig(
      {
        "valid-key": "value",
        "123invalid": "value",
        validKey: "value",
      },
      tmpDir,
    )

    const outputDir = path.join(tmpDir, "generated")
    await emitStaticPropsTypes(outputDir)

    const outFile = path.join(outputDir, "static-props.ts")
    const content = fs.readFileSync(outFile, "utf-8")

    // Invalid identifiers should be quoted in the interface
    expect(content).toContain('"valid-key": string')
    expect(content).toContain('"123invalid": string')
    // Valid identifiers should not be quoted
    expect(content).toContain("validKey: string")
    // Only valid identifiers should have named exports
    expect(content).toContain("export const validKey = staticProps.validKey")
    expect(content).not.toContain("export const valid-key")
    expect(content).not.toContain("export const 123invalid")
  })

  it("returns false when content unchanged", async () => {
    const tmpDir = createTmpDir()
    createBridgeConfig({ appName: "Test" }, tmpDir)

    const outputDir = path.join(tmpDir, "generated")

    // First call - creates file
    const firstResult = await emitStaticPropsTypes(outputDir)
    expect(firstResult).toBe(true)

    // Second call - file unchanged
    const secondResult = await emitStaticPropsTypes(outputDir)
    expect(secondResult).toBe(false)
  })

  it("handles empty objects", async () => {
    const tmpDir = createTmpDir()
    createBridgeConfig(
      {
        emptyConfig: {},
      },
      tmpDir,
    )

    const outputDir = path.join(tmpDir, "generated")
    await emitStaticPropsTypes(outputDir)

    const outFile = path.join(outputDir, "static-props.ts")
    const content = fs.readFileSync(outFile, "utf-8")

    expect(content).toContain("emptyConfig: Record<string, unknown>")
  })

  it("handles missing bridge config gracefully", async () => {
    const tmpDir = createTmpDir()
    const outputDir = path.join(tmpDir, "generated")

    // No bridge config created - should use defaults
    const changed = await emitStaticPropsTypes(outputDir)

    expect(changed).toBe(true)

    const outFile = path.join(outputDir, "static-props.ts")
    expect(fs.existsSync(outFile)).toBe(true)

    const content = fs.readFileSync(outFile, "utf-8")
    expect(content).toContain("export interface StaticProps {}")
  })
})
