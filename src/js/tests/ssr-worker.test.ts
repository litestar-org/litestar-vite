import { describe, expect, it } from "vitest"
import { dispatchSsrRequest } from "../src/ssr-worker.js"

describe("SSR worker dispatch", () => {
  it("renders application pages and dispatches fragments separately", async () => {
    const options = {
      render: (page: any) => `<main>${page.component}</main>`,
      renderFragment: (params: Record<string, unknown>) => ({ html: `<aside>${params.component}</aside>` }),
    }
    await expect(dispatchSsrRequest({ method: "render", params: { page: { component: "Home" } } }, options)).resolves.toEqual({ head: [], body: "<main>Home</main>" })
    await expect(dispatchSsrRequest({ method: "render_fragment", params: { component: "Card.tsx" } }, options)).resolves.toEqual({ html: "<aside>Card.tsx</aside>" })
  })

  it("preserves direct Python Inertia page parameters including their props", async () => {
    const page = { component: "Home", props: { message: "SSR body" }, url: "/", version: "1" }
    let received: unknown
    const result = await dispatchSsrRequest(
      { id: 1, method: "render", params: page },
      {
        render: (value) => {
          received = value
          return `<main>${value.component}: ${value.props.message}</main>`
        },
      },
    )
    expect(received).toBe(page)
    expect(result).toEqual({ head: [], body: "<main>Home: SSR body</main>" })
  })

  it("propagates failures instead of returning placeholder HTML", async () => {
    await expect(dispatchSsrRequest({ method: "render" })).rejects.toThrow("SSR requires")
    await expect(dispatchSsrRequest({ method: "render", params: { entrypoint: "missing-render-module" } })).rejects.toThrow("missing-render-module")
    await expect(
      dispatchSsrRequest(
        { method: "render" },
        {
          render: () => {
            throw new Error("render failed")
          },
        },
      ),
    ).rejects.toThrow("render failed")
    await expect(dispatchSsrRequest({ method: "render_fragment", params: { component: "Card.tsx" } })).rejects.toThrow("compiled component registry")
    await expect(dispatchSsrRequest({ method: "unknown" })).rejects.toThrow("Unsupported method")
  })
})
