/**
 * Tests for the shared emitRouteTypes utility.
 *
 * This module tests the route type generation functionality used by
 * the main plugin and framework integrations (Astro, Nuxt, SvelteKit).
 */

import * as fs from "node:fs"
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"
import { emitRouteTypes } from "../../src/shared/emit-route-types.js"

// Mock fs and path
vi.mock("node:fs", () => ({
  promises: {
    readFile: vi.fn(),
    writeFile: vi.fn(),
    mkdir: vi.fn(),
  },
}))

describe("emitRouteTypes", () => {
  const mockRoutesJson = {
    routes: {
      home: {
        uri: "/",
        parameters: [],
      },
      "user:detail": {
        uri: "/users/{user_id}",
        parameters: ["user_id"],
      },
      "posts:list": {
        uri: "/posts",
        parameters: [],
      },
    },
  }

  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(fs.promises.readFile).mockResolvedValue(JSON.stringify(mockRoutesJson))
    vi.mocked(fs.promises.writeFile).mockResolvedValue(undefined)
    vi.mocked(fs.promises.mkdir).mockResolvedValue(undefined)
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it("reads routes.json and writes routes.ts", async () => {
    await emitRouteTypes("/path/to/routes.json", "src/generated")

    expect(fs.promises.readFile).toHaveBeenCalledWith("/path/to/routes.json", "utf-8")
    expect(fs.promises.mkdir).toHaveBeenCalled()
    expect(fs.promises.writeFile).toHaveBeenCalled()
  })

  it("generates correct route name union type", async () => {
    await emitRouteTypes("/path/to/routes.json", "src/generated")

    const writeCall = vi.mocked(fs.promises.writeFile).mock.calls[0]
    const generatedContent = writeCall[1] as string

    // Check that route names are in the union type
    expect(generatedContent).toContain('"home"')
    expect(generatedContent).toContain('"user:detail"')
    expect(generatedContent).toContain('"posts:list"')
  })

  it("generates parameter types for routes with params", async () => {
    await emitRouteTypes("/path/to/routes.json", "src/generated")

    const writeCall = vi.mocked(fs.promises.writeFile).mock.calls[0]
    const generatedContent = writeCall[1] as string

    // Check parameter type generation
    expect(generatedContent).toContain("user_id: string | number")
    // Routes without params should have Record<string, never>
    expect(generatedContent).toContain('"home": Record<string, never>')
  })

  it("includes global route registration when globalRoute option is true", async () => {
    await emitRouteTypes("/path/to/routes.json", "src/generated", { globalRoute: true })

    const writeCall = vi.mocked(fs.promises.writeFile).mock.calls[0]
    const generatedContent = writeCall[1] as string

    expect(generatedContent).toContain("window.route = route")
  })

  it("does not include global route registration when globalRoute is false", async () => {
    await emitRouteTypes("/path/to/routes.json", "src/generated", { globalRoute: false })

    const writeCall = vi.mocked(fs.promises.writeFile).mock.calls[0]
    const generatedContent = writeCall[1] as string

    expect(generatedContent).not.toContain("window.route = route")
  })

  it("declares global vars when declareGlobalVars option is true", async () => {
    await emitRouteTypes("/path/to/routes.json", "src/generated", { declareGlobalVars: true })

    const writeCall = vi.mocked(fs.promises.writeFile).mock.calls[0]
    const generatedContent = writeCall[1] as string

    expect(generatedContent).toContain("var routes:")
    expect(generatedContent).toContain("var serverRoutes:")
  })

  it("does not declare global vars when declareGlobalVars is false", async () => {
    await emitRouteTypes("/path/to/routes.json", "src/generated", { declareGlobalVars: false })

    const writeCall = vi.mocked(fs.promises.writeFile).mock.calls[0]
    const generatedContent = writeCall[1] as string

    // Should not have the global var declarations (the eslint comment is a marker)
    const varDeclarationCount = (generatedContent.match(/var routes:/g) || []).length
    expect(varDeclarationCount).toBe(0)
  })

  it("exports route helper function", async () => {
    await emitRouteTypes("/path/to/routes.json", "src/generated")

    const writeCall = vi.mocked(fs.promises.writeFile).mock.calls[0]
    const generatedContent = writeCall[1] as string

    expect(generatedContent).toContain("export function route<T extends RouteName>")
  })

  it("exports hasRoute type guard", async () => {
    await emitRouteTypes("/path/to/routes.json", "src/generated")

    const writeCall = vi.mocked(fs.promises.writeFile).mock.calls[0]
    const generatedContent = writeCall[1] as string

    expect(generatedContent).toContain("export function hasRoute(name: string): name is RouteName")
  })

  it("re-exports CSRF helpers", async () => {
    await emitRouteTypes("/path/to/routes.json", "src/generated")

    const writeCall = vi.mocked(fs.promises.writeFile).mock.calls[0]
    const generatedContent = writeCall[1] as string

    expect(generatedContent).toContain('export { getCsrfToken, csrfHeaders, csrfFetch } from "litestar-vite-plugin/helpers"')
  })

  it("handles empty routes object", async () => {
    vi.mocked(fs.promises.readFile).mockResolvedValue(JSON.stringify({ routes: {} }))

    await emitRouteTypes("/path/to/routes.json", "src/generated")

    const writeCall = vi.mocked(fs.promises.writeFile).mock.calls[0]
    const generatedContent = writeCall[1] as string

    expect(generatedContent).toContain("export type RouteName = never")
  })

  it("handles routes.json without routes wrapper", async () => {
    // Some configs might have routes at root level
    const rootLevelRoutes = {
      home: { uri: "/", parameters: [] },
    }
    vi.mocked(fs.promises.readFile).mockResolvedValue(JSON.stringify(rootLevelRoutes))

    await emitRouteTypes("/path/to/routes.json", "src/generated")

    const writeCall = vi.mocked(fs.promises.writeFile).mock.calls[0]
    const generatedContent = writeCall[1] as string

    expect(generatedContent).toContain('"home"')
  })
})
