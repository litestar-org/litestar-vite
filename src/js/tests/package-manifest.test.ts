import fs from "node:fs"
import path from "node:path"
import { describe, expect, it } from "vitest"

describe("package manifest", () => {
  it("declares @hey-api/openapi-ts as an optional peer dependency", () => {
    const packageJson = JSON.parse(fs.readFileSync(path.resolve(process.cwd(), "package.json"), "utf-8")) as {
      peerDependencies?: Record<string, string>
      peerDependenciesMeta?: Record<string, { optional?: boolean }>
    }

    expect(packageJson.peerDependencies?.["@hey-api/openapi-ts"]).toMatch(/^\^0\.98\./)
    expect(packageJson.peerDependenciesMeta?.["@hey-api/openapi-ts"]?.optional).toBe(true)
  })
})
