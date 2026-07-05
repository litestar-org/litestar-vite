import fs from "node:fs"
import path from "node:path"
import { afterEach, describe, expect, it } from "vitest"

import { emitSchemasTypes } from "../../src/shared/emit-schemas-types"

const tmpDirs: string[] = []

const createTmpDir = (): string => {
  const dir = fs.mkdtempSync(path.join(process.cwd(), "vitest-schemas-"))
  tmpDirs.push(dir)
  return dir
}

afterEach(() => {
  for (const dir of tmpDirs) {
    fs.rmSync(dir, { recursive: true, force: true })
  }
  tmpDirs.length = 0
})

describe("emitSchemasTypes", () => {
  it("writes schemas.ts to a custom path with correct import", async () => {
    const tmpDir = createTmpDir()
    const outputDir = path.join(tmpDir, "generated")
    const apiDir = path.join(outputDir, "api")
    fs.mkdirSync(apiDir, { recursive: true })

    const routesPath = path.join(tmpDir, "routes.json")
    const routesJson = {
      routes: {
        "api:login": {
          uri: "/api/login",
          method: "POST",
          methods: ["POST"],
        },
      },
    }
    fs.writeFileSync(routesPath, JSON.stringify(routesJson, null, 2))

    const typesGen = [
      "export type LoginData = { url: '/api/login'; body: { username: string } }",
      "export type LoginResponses = { 200: { token: string } }",
      "export type LoginErrors = LoginResponses[400]",
      "",
    ].join("\n")
    fs.writeFileSync(path.join(apiDir, "types.gen.ts"), typesGen)

    const customOut = path.join(tmpDir, "custom", "schemas.ts")
    const changed = await emitSchemasTypes(routesPath, outputDir, customOut)

    expect(changed).toBe(true)
    expect(fs.existsSync(customOut)).toBe(true)

    const content = fs.readFileSync(customOut, "utf-8")
    expect(content).toContain('export * from "../generated/api/types.gen"')
    expect(content).toContain('from "../generated/api/types.gen"')
  })

  it("maps hey-api Data types with nested object bodies", async () => {
    const tmpDir = createTmpDir()
    const outputDir = path.join(tmpDir, "generated")
    const apiDir = path.join(outputDir, "api")
    fs.mkdirSync(apiDir, { recursive: true })

    const routesPath = path.join(tmpDir, "routes.json")
    const routesJson = {
      routes: {
        "api:profile_update": {
          uri: "/api/profile",
          method: "PATCH",
          methods: ["PATCH"],
        },
      },
    }
    fs.writeFileSync(routesPath, JSON.stringify(routesJson, null, 2))

    const typesGen = [
      "export type ProfileUpdateData = {",
      "  body: {",
      "    profile: {",
      "      name: string;",
      "      address: { city: string; postalCode: string };",
      "    };",
      "  };",
      "  url: '/api/profile';",
      "}",
      "export type ProfileUpdateResponses = { 200: { ok: boolean } }",
      "",
    ].join("\n")
    fs.writeFileSync(path.join(apiDir, "types.gen.ts"), typesGen)

    const changed = await emitSchemasTypes(routesPath, outputDir)

    expect(changed).toBe(true)

    const content = fs.readFileSync(path.join(outputDir, "schemas.ts"), "utf-8")
    expect(content).toContain("'api:profile_update': ProfileUpdateData")
    expect(content).toContain("'api:profile_update': ProfileUpdateResponses")
    expect(content).toContain("export type FormInput<T extends OperationName>")
  })
})
