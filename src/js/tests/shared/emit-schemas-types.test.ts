import fs from "node:fs"
import path from "node:path"
import ts from "typescript"
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

  it("maps multi-method routes on the same URL path without clobbering each other", async () => {
    const tmpDir = createTmpDir()
    const outputDir = path.join(tmpDir, "generated")
    const apiDir = path.join(outputDir, "api")
    fs.mkdirSync(apiDir, { recursive: true })

    const routesPath = path.join(tmpDir, "routes.json")
    const routesJson = {
      routes: {
        "api:users_list": {
          uri: "/api/users",
          method: "GET",
          methods: ["GET"],
        },
        "api:users_create": {
          uri: "/api/users",
          method: "POST",
          methods: ["POST"],
        },
      },
    }
    fs.writeFileSync(routesPath, JSON.stringify(routesJson, null, 2))

    const typesGen = [
      "export type UsersListData = {",
      "  method: 'get';",
      "  url: '/api/users';",
      "  query: { limit?: number };",
      "}",
      "export type UsersListResponses = { 200: Array<{ id: string }> }",
      "export type UsersCreateData = {",
      "  method: 'post';",
      "  url: '/api/users';",
      "  body: { name: string };",
      "}",
      "export type UsersCreateResponses = { 201: { id: string; name: string } }",
      "",
    ].join("\n")
    fs.writeFileSync(path.join(apiDir, "types.gen.ts"), typesGen)

    const changed = await emitSchemasTypes(routesPath, outputDir)

    expect(changed).toBe(true)

    const content = fs.readFileSync(path.join(outputDir, "schemas.ts"), "utf-8")
    expect(content).toContain("'api:users_list': UsersListData")
    expect(content).toContain("'api:users_list': UsersListResponses")
    expect(content).toContain("'api:users_create': UsersCreateData")
    expect(content).toContain("'api:users_create': UsersCreateResponses")
  })

  it("preserves optional schema types in FormInput and QueryParams without collapsing to never", async () => {
    const tmpDir = createTmpDir()
    const outputDir = path.join(tmpDir, "generated")
    const apiDir = path.join(outputDir, "api")
    fs.mkdirSync(apiDir, { recursive: true })

    const routesPath = path.join(tmpDir, "routes.json")
    const routesJson = {
      routes: {
        "api:search": {
          uri: "/api/search",
          method: "POST",
          methods: ["POST"],
        },
      },
    }
    fs.writeFileSync(routesPath, JSON.stringify(routesJson, null, 2))

    const typesGen = [
      "export type SearchData = {",
      "  url: '/api/search';",
      "  body?: { query?: string };",
      "  query?: { limit?: number };",
      "  path?: { scope?: string };",
      "}",
      "export type SearchResponses = { 200: { results: string[] } }",
      "",
    ].join("\n")
    fs.writeFileSync(path.join(apiDir, "types.gen.ts"), typesGen)

    const changed = await emitSchemasTypes(routesPath, outputDir)
    expect(changed).toBe(true)

    const schemasPath = path.join(outputDir, "schemas.ts")
    const testUsagePath = path.join(outputDir, "test-usage.ts")
    const testUsage = [
      'import type { FormInput, QueryParams, PathParams, HasBody, HasQueryParams, HasPathParams } from "./schemas"',
      'type Input = FormInput<"api:search">',
      'type Query = QueryParams<"api:search">',
      'type Path = PathParams<"api:search">',
      'const _input: Input = { query: "test" }',
      'const _query: Query = { limit: 10 }',
      'const _path: Path = { scope: "global" }',
      'const _hasBody: HasBody<"api:search"> = true',
      'const _hasQuery: HasQueryParams<"api:search"> = true',
      'const _hasPath: HasPathParams<"api:search"> = true',
    ].join("\n")
    fs.writeFileSync(testUsagePath, testUsage)

    const program = ts.createProgram([testUsagePath, schemasPath], {
      noEmit: true,
      strict: true,
      exactOptionalPropertyTypes: true,
      target: ts.ScriptTarget.ES2022,
      moduleResolution: ts.ModuleResolutionKind.Bundler,
    })
    const diagnostics = ts.getPreEmitDiagnostics(program)
    expect(diagnostics).toHaveLength(0)
  })
})


