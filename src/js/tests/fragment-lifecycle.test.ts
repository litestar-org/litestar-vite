import { expect, it, vi } from "vitest"
import { hydrateIslands } from "../src/fragments/client.js"

it("cancels disconnected loads, waits for teardown, and hydrates reinserted islands once", async () => {
  let finishLoad!: (value: { default: object }) => void
  let finishTeardown!: () => void
  const teardown = vi.fn(
    () =>
      new Promise<void>((resolve) => {
        finishTeardown = resolve
      }),
  )
  const hydrate = vi.fn((_component, target: HTMLElement) => {
    expect(target.innerHTML).toBe("<button>SSR</button>")
    target.innerHTML = "<button>Interactive</button>"
    return teardown
  })
  const load = vi.fn(
    () =>
      new Promise<{ default: object }>((resolve) => {
        finishLoad = resolve
      }),
  )
  hydrateIslands({ counter: { load, hydrate } })
  const island = document.createElement("litestar-island")
  island.setAttribute("data-island-component", "counter")
  island.innerHTML = "<button>SSR</button>"
  document.body.append(island)
  await vi.waitFor(() => expect(load).toHaveBeenCalledTimes(1))
  island.remove()
  finishLoad({ default: {} })
  await new Promise((resolve) => setTimeout(resolve, 0))
  expect(hydrate).not.toHaveBeenCalled()
  document.body.append(island)
  await vi.waitFor(() => expect(load).toHaveBeenCalledTimes(2))
  finishLoad({ default: {} })
  await vi.waitFor(() => expect(hydrate).toHaveBeenCalledTimes(1))
  island.remove()
  await vi.waitFor(() => expect(teardown).toHaveBeenCalledTimes(1))
  document.body.append(island)
  await new Promise((resolve) => setTimeout(resolve, 0))
  expect(load).toHaveBeenCalledTimes(2)
  finishTeardown()
  await vi.waitFor(() => expect(load).toHaveBeenCalledTimes(3))
  finishLoad({ default: {} })
  await vi.waitFor(() => expect(hydrate).toHaveBeenCalledTimes(2))
  island.remove()
  await vi.waitFor(() => expect(teardown).toHaveBeenCalledTimes(2))
  finishTeardown()
})
