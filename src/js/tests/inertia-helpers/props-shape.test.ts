import { describe, expect, it } from "vitest"

import { resolvePageComponent, unwrapPageProps } from "../../src/inertia-helpers"

describe("inertia-helpers props shape", () => {
  it("unwraps mapping content to top-level keys", () => {
    const props = unwrapPageProps({ content: { books: [1, 2], summary: "ok" }, shared: true })
    expect(props.books).toEqual([1, 2])
    expect(props.summary).toBe("ok")
    expect(props.shared).toBe(true)
  })

  it("leaves non-mapping content nested", () => {
    const props = unwrapPageProps({ content: [1, 2, 3], shared: true })
    expect(props.content).toEqual([1, 2, 3])
    expect(props.shared).toBe(true)
    expect((props as Record<string, unknown>).books).toBeUndefined()
  })

  it("is a no-op when content is absent", () => {
    const props = unwrapPageProps({ books: [1], summary: "fine" })
    expect(props.books).toEqual([1])
    expect(props.summary).toBe("fine")
  })

  it("wraps components resolved via resolvePageComponent and unwraps props", async () => {
    const pages = {
      "./pages/Home.tsx": Promise.resolve({
        default: (received: Record<string, unknown>) => received,
      }),
    }

    const component = await resolvePageComponent("./pages/Home.tsx", pages)

    const rendered = (component as (props: Record<string, unknown>) => Record<string, unknown>)({
      content: { books: [1] },
      hello: "world",
    })

    expect(rendered.books).toEqual([1])
    expect(rendered.hello).toBe("world")
    expect(rendered.content).toBeUndefined()
  })

  // Regression for litestar-vite-8u9: Inertia's Pages.set() calls resolveComponent
  // on every navigation/partial-reload. If the resolved component identity changes
  // across calls, React's reconciler sees a different element type and unmounts the
  // page subtree, wiping useState and re-running effects (looks like an auto-reload).
  it("returns identical component reference across repeated resolves of the same path", async () => {
    const Original = (received: Record<string, unknown>) => received
    const pages = {
      "./pages/Home.tsx": Promise.resolve({ default: Original }),
    }

    const first = await resolvePageComponent("./pages/Home.tsx", pages)
    const second = await resolvePageComponent("./pages/Home.tsx", pages)

    expect(first).toBe(second)
  })

  it("returns identical reference for direct function exports across resolves", async () => {
    const pages = {
      "./pages/Direct.tsx": Promise.resolve(
        ((received: Record<string, unknown>) => received) as unknown as {
          default: (props: Record<string, unknown>) => unknown
        },
      ),
    }

    const first = await resolvePageComponent("./pages/Direct.tsx", pages)
    const second = await resolvePageComponent("./pages/Direct.tsx", pages)

    expect(first).toBe(second)
  })
})
