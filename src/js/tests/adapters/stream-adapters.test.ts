import { act, createElement, type ReactNode } from "react"
import { createRoot, type Root } from "react-dom/client"
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"
import { createApp, defineComponent, h, nextTick, ref } from "vue"
import { useEventStream as useReactEventStream, useQueueEventStream as useReactQueueEventStream } from "../../src/react"
import { createEventStreamStore, createQueueEventStreamStore } from "../../src/svelte"
import { useEventStream as useVueEventStream, useQueueEventStream as useVueQueueEventStream } from "../../src/vue"

class FakeWebSocket {
  static instances: FakeWebSocket[] = []

  readonly url: string
  close = vi.fn()
  private readonly listeners = new Map<string, Set<EventListener>>()

  constructor(url: string | URL) {
    this.url = String(url)
    FakeWebSocket.instances.push(this)
  }

  addEventListener(type: string, listener: EventListener): void {
    const listeners = this.listeners.get(type) ?? new Set<EventListener>()
    listeners.add(listener)
    this.listeners.set(type, listeners)
  }

  simulateMessage(data: string): void {
    for (const listener of this.listeners.get("message") ?? []) {
      listener(new MessageEvent("message", { data }))
    }
  }
}

const WebSocketCtor = FakeWebSocket as unknown as typeof WebSocket

beforeEach(() => {
  FakeWebSocket.instances = []
  document.body.replaceChildren()
  ;(globalThis as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true
})

afterEach(() => {
  document.body.replaceChildren()
  vi.restoreAllMocks()
})

describe("React stream adapters", () => {
  let root: Root | undefined

  afterEach(async () => {
    if (root !== undefined) {
      await act(() => root?.unmount())
      root = undefined
    }
  })

  function Harness({ callback, queue = false, streamKey = "stable" }: { callback: (frame: unknown) => void; queue?: boolean; streamKey?: string }): ReactNode {
    const options = {
      bufferSize: 2,
      key: streamKey,
      onEvent: callback,
      url: "/events",
      WebSocketCtor,
    }
    const state = queue ? useReactQueueEventStream(options) : useReactEventStream(options)
    return createElement("output", null, JSON.stringify(state))
  }

  it("keeps one connection across callback changes and disposes on unmount", async () => {
    const container = document.createElement("div")
    document.body.append(container)
    root = createRoot(container)

    await act(() => root?.render(createElement(Harness, { callback: vi.fn() })))
    await act(() => root?.render(createElement(Harness, { callback: vi.fn() })))
    expect(FakeWebSocket.instances).toHaveLength(1)

    await act(() => root?.render(createElement(Harness, { callback: vi.fn(), streamKey: "next" })))
    expect(FakeWebSocket.instances).toHaveLength(2)

    await act(() => root?.unmount())
    root = undefined
    expect(FakeWebSocket.instances[1].close).toHaveBeenCalledOnce()
  })

  it("retains queue heartbeat filtering in the queue hook", async () => {
    const container = document.createElement("div")
    document.body.append(container)
    root = createRoot(container)
    await act(() => root?.render(createElement(Harness, { callback: vi.fn(), queue: true })))

    await act(() => FakeWebSocket.instances[0].simulateMessage('{"type":"ping"}'))
    await act(() => FakeWebSocket.instances[0].simulateMessage('{"id":"event-1"}'))

    expect(container.textContent).toContain('"id":"event-1"')
    expect(container.textContent).not.toContain("ping")
  })
})

describe("Vue stream adapters", () => {
  it("reconnects only when the key changes and disposes with the app", async () => {
    const key = ref("one")
    const callback = vi.fn()
    const component = defineComponent({
      setup() {
        const state = useVueEventStream({
          key,
          onEvent: callback,
          url: "/events",
          WebSocketCtor,
        })
        return () => h("output", JSON.stringify(state.events.value))
      },
    })
    const container = document.createElement("div")
    const app = createApp(component)
    app.mount(container)
    await nextTick()
    expect(FakeWebSocket.instances).toHaveLength(1)

    key.value = "two"
    await nextTick()
    expect(FakeWebSocket.instances).toHaveLength(2)

    app.unmount()
    expect(FakeWebSocket.instances[1].close).toHaveBeenCalledOnce()
  })

  it("exposes the queue-specific composable", async () => {
    const container = document.createElement("div")
    const component = defineComponent({
      setup() {
        const state = useVueQueueEventStream({
          key: "queue",
          onEvent: vi.fn(),
          url: "/events",
          WebSocketCtor,
        })
        return () => h("output", JSON.stringify(state.events.value))
      },
    })
    const app = createApp(component)
    app.mount(container)
    await nextTick()
    FakeWebSocket.instances[0].simulateMessage('{"type":"ping"}')
    FakeWebSocket.instances[0].simulateMessage('{"id":"event-1"}')
    await nextTick()

    expect(container.textContent).toContain('"id":"event-1"')
    expect(container.textContent).not.toContain("ping")
    app.unmount()
  })
})

describe("Svelte stream adapters", () => {
  it("shares one connection and disposes after the last subscriber", () => {
    const store = createEventStreamStore({
      onEvent: vi.fn(),
      url: "/events",
      WebSocketCtor,
    })
    const first = vi.fn()
    const second = vi.fn()

    const unsubscribeFirst = store.subscribe(first)
    const unsubscribeSecond = store.subscribe(second)
    expect(FakeWebSocket.instances).toHaveLength(1)

    unsubscribeFirst()
    expect(FakeWebSocket.instances[0].close).not.toHaveBeenCalled()
    unsubscribeSecond()
    expect(FakeWebSocket.instances[0].close).toHaveBeenCalledOnce()
  })

  it("exposes matching state fields and queue semantics", () => {
    const store = createQueueEventStreamStore({
      onEvent: vi.fn(),
      url: "/events",
      WebSocketCtor,
    })
    let state: Record<string, unknown> = {}
    const unsubscribe = store.subscribe((value) => {
      state = value as unknown as Record<string, unknown>
    })

    FakeWebSocket.instances[0].simulateMessage('{"type":"ping"}')
    FakeWebSocket.instances[0].simulateMessage('{"id":"event-1"}')

    expect(Object.keys(state).toSorted()).toEqual(["events", "healthy", "lastEvent", "lastGap"])
    expect(state.lastEvent).toEqual({ id: "event-1" })
    unsubscribe()
  })
})
