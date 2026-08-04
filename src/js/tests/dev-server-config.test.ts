import fs from "node:fs"
import path from "node:path"
import { describe, expect, it } from "vitest"

describe("Vite configs", () => {
  it.each(["../vitest.config.ts", "../src/dev-server/vite.config.ts", "../src/server-starting/vite.config.ts"])("%s uses ESM-native directory paths", (relativePath) => {
    const configPath = path.resolve(import.meta.dirname, relativePath)
    const config = fs.readFileSync(configPath, "utf-8")

    expect(config).toContain("import.meta.dirname")
    expect(config).not.toContain("__dirname")
  })
})
