import { describe, expect, it, vi } from "vitest"
import { getIslandClientScript, wrapIsland } from "../src/fragments/island.js"
import { renderFragment } from "../src/fragments/renderer.js"
import { manageSsrCache } from "../src/shared/ssr-cache.js"

describe("UI Fragment Rendering & Island Wrapping", () => {
  it("escapes double quotes in serialized island props and generates hydration script", () => {
    const wrapped = wrapIsland("<button>Count</button>", {
      component: "components/Counter.tsx",
      props: { label: 'Say "Hello"', count: 3 },
      islandId: "island-test123",
    })

    expect(wrapped).toContain('id="island-test123"')
    expect(wrapped).toContain('data-island-component="components/Counter.tsx"')
    expect(wrapped).toContain('data-island-props="{&quot;label&quot;:&quot;Say \\&quot;Hello\\&quot;&quot;,&quot;count&quot;:3}"')
    expect(wrapped).toContain("<button>Count</button></litestar-island>")
    expect(getIslandClientScript()).toContain('customElements.define("litestar-island"')
  })

  it("throws an informative error for unsupported fragment extensions", async () => {
    await expect(renderFragment({ componentPath: "components/Unknown.xyz", props: {} }, async () => ({ default: () => "ok" }))).rejects.toThrow(
      "Unsupported component extension for fragment rendering: .xyz",
    )
  })
})

describe("SSR ModuleRunner Cache Invalidation", () => {
  it("recursively invalidates parent importer modules when a leaf module updates", () => {
    const invalidated: string[] = []
    const parentNode = {
      id: "/resources/pages/Dashboard.vue",
      importers: new Set<string>(),
    }
    const childNode = {
      id: "/resources/components/UserCard.vue",
      importers: new Set<string>(["/resources/pages/Dashboard.vue"]),
    }
    const nodeMap = new Map([
      [parentNode.id, parentNode],
      [childNode.id, childNode],
    ])

    const runner = {
      evaluatedModules: {
        getModulesByFile: (file: string) => (file === "/resources/components/UserCard.vue" ? new Set([childNode]) : undefined),
        getModuleById: (id: string) => nodeMap.get(id),
        invalidateModule: (mod: { id: string }) => {
          invalidated.push(mod.id)
        },
        clear: vi.fn(),
      },
    }

    let changeHandler: ((file: string) => void) | undefined
    const server = {
      watcher: {
        on: (event: string, cb: (file: string) => void) => {
          if (event === "change") {
            changeHandler = cb
          }
        },
        off: vi.fn(),
      },
    } as any

    const manager = manageSsrCache(runner as any, server)
    expect(changeHandler).toBeDefined()
    changeHandler!("/resources/components/UserCard.vue")

    expect(invalidated).toContain("/resources/components/UserCard.vue")
    expect(invalidated).toContain("/resources/pages/Dashboard.vue")

    manager.clearAll()
    expect(runner.evaluatedModules.clear).toHaveBeenCalledOnce()
    manager.dispose()
  })
})
