import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"
import { defineStreamElement, type LitestarStreamElement } from "../../src/helpers/stream-element"

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

  simulateClose(code = 1000): void {
    this.dispatch("close", { code } as CloseEvent)
  }

  simulateMessage(data: string): void {
    this.dispatch("message", new MessageEvent("message", { data }))
  }

  simulateOpen(): void {
    this.dispatch("open", new Event("open"))
  }

  private dispatch(type: string, event: Event): void {
    for (const listener of this.listeners.get(type) ?? []) {
      listener(event)
    }
  }
}

const WebSocketCtor = FakeWebSocket as unknown as typeof WebSocket
const tagName = "litestar-stream-test"

function createElement(attributes: Record<string, string> = { url: "/events" }): LitestarStreamElement {
  const element = document.createElement(tagName) as LitestarStreamElement
  element.WebSocketCtor = WebSocketCtor
  for (const [name, value] of Object.entries(attributes)) {
    element.setAttribute(name, value)
  }
  return element
}

describe("LitestarStreamElement", () => {
  beforeEach(() => {
    defineStreamElement({ tagName })
    FakeWebSocket.instances = []
    document.body.replaceChildren()
    vi.useFakeTimers()
    vi.spyOn(Math, "random").mockReturnValue(0.5)
  })

  afterEach(() => {
    document.body.replaceChildren()
    vi.useRealTimers()
    vi.restoreAllMocks()
  })

  it("binds the connection to DOM lifetime and reconnects on reinsertion", () => {
    const element = createElement()

    document.body.append(element)
    expect(FakeWebSocket.instances).toHaveLength(1)
    expect(element.shadowRoot).toBeNull()

    element.remove()
    expect(FakeWebSocket.instances[0].close).toHaveBeenCalledOnce()

    document.body.append(element)
    expect(FakeWebSocket.instances).toHaveLength(2)
  })

  it("waits while disabled and connects when enabled", () => {
    const element = createElement({ disabled: "", url: "/events" })

    document.body.append(element)
    expect(FakeWebSocket.instances).toHaveLength(0)

    element.removeAttribute("disabled")
    expect(FakeWebSocket.instances).toHaveLength(1)
  })

  it("reconnects for connection attributes but not swap changes", () => {
    const element = createElement()
    document.body.append(element)

    element.setAttribute("swap", "json")
    expect(FakeWebSocket.instances).toHaveLength(1)

    element.setAttribute("url", "/other")
    expect(FakeWebSocket.instances).toHaveLength(2)

    element.setAttribute("preset", "queues")
    expect(FakeWebSocket.instances).toHaveLength(3)
  })

  it("rehydrates own properties that shadow prototype accessors during upgrade", () => {
    const element = createElement()
    const onEvent = vi.fn()
    Object.defineProperty(element, "onEvent", {
      configurable: true,
      value: onEvent,
      writable: true,
    })
    ;(element as unknown as { upgradeProperty: (property: string) => void }).upgradeProperty("onEvent")
    document.body.append(element)
    FakeWebSocket.instances.at(-1)?.simulateMessage('{"message":"ready"}')

    expect(onEvent).toHaveBeenCalledWith({ message: "ready" })
  })

  it("prefers buildUrl and dispatches lifecycle and frame events", () => {
    const element = createElement()
    element.buildUrl = () => "/built"
    const onEvent = vi.fn()
    element.onEvent = onEvent
    const received: Event[] = []
    for (const type of ["litestar:stream-open", "litestar:stream-event", "litestar:stream-health", "litestar:stream-close"]) {
      element.addEventListener(type, (event) => received.push(event))
    }

    document.body.append(element)
    const socket = FakeWebSocket.instances[0]
    socket.simulateOpen()
    socket.simulateMessage('{"message":"ready"}')
    element.remove()

    expect(socket.url).toBe("ws://localhost:3000/built")
    expect(onEvent).toHaveBeenCalledWith({ message: "ready" })
    expect(received.map((event) => event.type)).toEqual([
      "litestar:stream-health",
      "litestar:stream-open",
      "litestar:stream-event",
      "litestar:stream-close",
      "litestar:stream-health",
    ])
    for (const event of received) {
      expect(event.bubbles).toBe(true)
      expect(event.composed).toBe(false)
    }
  })

  it("uses queue semantics only for the queues preset", () => {
    const generic = createElement()
    const genericEvent = vi.fn()
    generic.onEvent = genericEvent
    document.body.append(generic)
    FakeWebSocket.instances[0].simulateMessage('{"type":"ping"}')

    const queues = createElement({ preset: "queues", url: "/queue-events" })
    const queueEvent = vi.fn()
    queues.onEvent = queueEvent
    document.body.append(queues)
    FakeWebSocket.instances[1].simulateMessage('{"type":"ping"}')

    expect(genericEvent).toHaveBeenCalledOnce()
    expect(queueEvent).not.toHaveBeenCalled()
  })

  it("dispatches gap details and renders queue frames in light DOM", () => {
    const element = createElement({ preset: "queues", swap: "json", url: "/events" })
    element.innerHTML = '<template ls-for="item in $data.payload"><p>${item}</p></template>'
    const gaps: CustomEvent[] = []
    element.addEventListener("litestar:stream-gap", (event) => gaps.push(event as CustomEvent))
    document.body.append(element)

    const socket = FakeWebSocket.instances[0]
    socket.simulateMessage('{"id":"1","taskId":"demo","attempt":1,"sequence":1,"payload":["first"]}')
    socket.simulateMessage('{"id":"3","taskId":"demo","attempt":1,"sequence":3,"payload":["third"]}')

    expect(element.querySelectorAll("p")).toHaveLength(1)
    expect(element.querySelector("p")?.textContent).toBe("third")
    expect(gaps).toHaveLength(1)
    expect(gaps[0].detail).toEqual({ stream: "demo:1", from: 1, to: 3, missing: 1 })
  })

  it("registers idempotently", () => {
    expect(() => defineStreamElement({ tagName })).not.toThrow()
  })
})
