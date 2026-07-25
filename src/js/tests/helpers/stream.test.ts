import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"
import { createEventStream } from "../../src/helpers/stream"

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

  simulateClose(code: number): void {
    this.dispatch("close", { code } as CloseEvent)
  }

  simulateError(): void {
    this.dispatch("error", new Event("error"))
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

describe("createEventStream websocket transport", () => {
  const originalWindow = globalThis.window

  beforeEach(() => {
    FakeWebSocket.instances = []
    vi.useFakeTimers()
    vi.spyOn(Math, "random").mockReturnValue(0.5)
  })

  afterEach(() => {
    globalThis.window = originalWindow
    vi.useRealTimers()
    vi.restoreAllMocks()
  })

  it("builds the URL immediately before every connection attempt", () => {
    let token = "first"
    const buildUrl = vi.fn(() => `ws://example.test/events?token=${token}`)
    const stream = createEventStream({
      buildUrl,
      onEvent: vi.fn(),
      WebSocketCtor,
    })

    stream.connect()
    expect(FakeWebSocket.instances[0]?.url).toContain("token=first")

    token = "rotated"
    FakeWebSocket.instances[0].simulateClose(1006)
    vi.advanceTimersByTime(500)

    expect(buildUrl).toHaveBeenCalledTimes(2)
    expect(FakeWebSocket.instances[1]?.url).toContain("token=rotated")
  })

  it("does not reconnect after a normal close by default", () => {
    const stream = createEventStream({
      buildUrl: () => "ws://example.test/events",
      onEvent: vi.fn(),
      WebSocketCtor,
    })

    stream.connect()
    FakeWebSocket.instances[0].simulateClose(1000)
    vi.runAllTimers()

    expect(FakeWebSocket.instances).toHaveLength(1)
  })

  it("parses websocket messages and forwards the frame", () => {
    const onEvent = vi.fn()
    const stream = createEventStream({
      buildUrl: () => "ws://example.test/events",
      onEvent,
      WebSocketCtor,
    })

    stream.connect()
    FakeWebSocket.instances[0].simulateMessage('{"type":"task.progress","payload":{"percent":50}}')

    expect(onEvent).toHaveBeenCalledWith({
      type: "task.progress",
      payload: { percent: 50 },
    })
  })

  it("grows and caps full-jitter backoff, then resets after opening", () => {
    vi.spyOn(Math, "random").mockReturnValue(1)
    const stream = createEventStream({
      baseDelayMs: 1000,
      buildUrl: () => "ws://example.test/events",
      maxDelayMs: 2500,
      onEvent: vi.fn(),
      WebSocketCtor,
    })

    stream.connect()
    FakeWebSocket.instances[0].simulateClose(1006)
    vi.advanceTimersByTime(999)
    expect(FakeWebSocket.instances).toHaveLength(1)
    vi.advanceTimersByTime(1)
    expect(FakeWebSocket.instances).toHaveLength(2)

    FakeWebSocket.instances[1].simulateClose(1006)
    vi.advanceTimersByTime(1999)
    expect(FakeWebSocket.instances).toHaveLength(2)
    vi.advanceTimersByTime(1)
    expect(FakeWebSocket.instances).toHaveLength(3)

    FakeWebSocket.instances[2].simulateClose(1006)
    vi.advanceTimersByTime(2499)
    expect(FakeWebSocket.instances).toHaveLength(3)
    vi.advanceTimersByTime(1)
    expect(FakeWebSocket.instances).toHaveLength(4)

    FakeWebSocket.instances[3].simulateOpen()
    FakeWebSocket.instances[3].simulateClose(1006)
    vi.advanceTimersByTime(999)
    expect(FakeWebSocket.instances).toHaveLength(4)
    vi.advanceTimersByTime(1)
    expect(FakeWebSocket.instances).toHaveLength(5)
  })

  it("suppresses a pending reconnect after disposal", () => {
    const stream = createEventStream({
      buildUrl: () => "ws://example.test/events",
      onEvent: vi.fn(),
      WebSocketCtor,
    })

    stream.connect()
    FakeWebSocket.instances[0].simulateClose(1006)
    stream.dispose()
    vi.runAllTimers()

    expect(FakeWebSocket.instances).toHaveLength(1)
  })

  it("ignores late close events from a replaced socket", () => {
    const onHealthChange = vi.fn()
    const stream = createEventStream({
      buildUrl: () => "ws://example.test/events",
      onEvent: vi.fn(),
      onHealthChange,
      WebSocketCtor,
    })

    stream.connect()
    stream.connect()
    FakeWebSocket.instances[1].simulateOpen()
    FakeWebSocket.instances[0].simulateClose(1006)
    vi.runAllTimers()

    expect(FakeWebSocket.instances).toHaveLength(2)
    expect(onHealthChange).toHaveBeenCalledOnce()
    expect(onHealthChange).toHaveBeenCalledWith(true)
  })

  it("reports health only when the value changes", () => {
    const onHealthChange = vi.fn()
    const stream = createEventStream({
      buildUrl: () => "ws://example.test/events",
      onEvent: vi.fn(),
      onHealthChange,
      WebSocketCtor,
    })

    stream.connect()
    FakeWebSocket.instances[0].simulateError()
    FakeWebSocket.instances[0].simulateError()
    FakeWebSocket.instances[0].simulateOpen()
    FakeWebSocket.instances[0].simulateError()
    FakeWebSocket.instances[0].simulateClose(1000)

    expect(onHealthChange.mock.calls).toEqual([[false], [true], [false]])
  })

  it("does not connect during server-side rendering", () => {
    // @ts-expect-error - Testing SSR without a window global.
    globalThis.window = undefined
    const stream = createEventStream({
      buildUrl: () => "ws://example.test/events",
      onEvent: vi.fn(),
      WebSocketCtor,
    })

    stream.connect()

    expect(FakeWebSocket.instances).toHaveLength(0)
  })
})
