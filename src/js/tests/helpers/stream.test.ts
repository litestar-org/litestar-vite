import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"
import * as helperExports from "../../src/helpers"
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

class FakeEventSource {
  static instances: FakeEventSource[] = []

  readonly url: string
  close = vi.fn()
  private readonly listeners = new Map<string, Set<EventListener>>()

  constructor(url: string | URL) {
    this.url = String(url)
    FakeEventSource.instances.push(this)
  }

  addEventListener(type: string, listener: EventListener): void {
    const listeners = this.listeners.get(type) ?? new Set<EventListener>()
    listeners.add(listener)
    this.listeners.set(type, listeners)
  }

  eventTypes(): string[] {
    return [...this.listeners.keys()]
  }

  simulateError(): void {
    this.dispatch("error", new Event("error"))
  }

  simulateEvent(type: string, data: string): void {
    this.dispatch(type, new MessageEvent(type, { data }))
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

const EventSourceCtor = FakeEventSource as unknown as typeof EventSource

function queueIsHeartbeat(frame: unknown): boolean {
  return (frame as { type?: string }).type === "ping"
}

function queueGetEventKey(frame: unknown): string | undefined {
  const value = frame as { eventKey?: unknown; id?: unknown }
  const key = value.eventKey ?? value.id
  return typeof key === "string" ? key : undefined
}

function queueGetSequence(frame: unknown): { stream: string; value: number } | undefined {
  const value = frame as { attempt?: unknown; sequence?: unknown; taskId?: unknown }
  if (typeof value.sequence !== "number" || typeof value.taskId !== "string" || (typeof value.attempt !== "string" && typeof value.attempt !== "number")) {
    return undefined
  }
  return { stream: `${value.taskId}:${value.attempt}`, value: value.sequence }
}

describe("stream helper exports", () => {
  it("exports createEventStream from the helpers entry point", () => {
    expect((helperExports as Record<string, unknown>).createEventStream).toBe(createEventStream)
  })
})

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

  it("resolves a relative url against the browser origin for every attempt", () => {
    const stream = createEventStream({
      url: "/events",
      onEvent: vi.fn(),
      WebSocketCtor,
    })

    stream.connect()

    expect(FakeWebSocket.instances[0]?.url).toBe("ws://localhost:3000/events")
  })

  it("delivers raw text frames when they are not JSON", () => {
    const onEvent = vi.fn()
    const stream = createEventStream({
      buildUrl: () => "/events",
      onEvent,
      WebSocketCtor,
    })

    stream.connect()
    FakeWebSocket.instances[0].simulateMessage("plain text")

    expect(onEvent).toHaveBeenCalledWith("plain text")
  })

  it("does not apply queue envelope semantics by default", () => {
    const onEvent = vi.fn()
    const onGap = vi.fn()
    const stream = createEventStream({
      buildUrl: () => "/events",
      onEvent,
      onGap,
      WebSocketCtor,
    })

    stream.connect()
    FakeWebSocket.instances[0].simulateMessage('{"type":"ping","id":"same","taskId":"task-1","attempt":1,"sequence":1}')
    FakeWebSocket.instances[0].simulateMessage('{"type":"ping","id":"same","taskId":"task-1","attempt":1,"sequence":3}')

    expect(onEvent).toHaveBeenCalledTimes(2)
    expect(onGap).not.toHaveBeenCalled()
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

  it("reports the resolved URL on open and closes once on disposal", () => {
    const onOpen = vi.fn()
    const onClose = vi.fn()
    const stream = createEventStream({
      url: "/events",
      onClose,
      onEvent: vi.fn(),
      onOpen,
      WebSocketCtor,
    })

    stream.connect()
    FakeWebSocket.instances[0].simulateOpen()
    stream.dispose()
    FakeWebSocket.instances[0].simulateClose(1000)

    expect(onOpen).toHaveBeenCalledWith("ws://localhost:3000/events")
    expect(onClose).toHaveBeenCalledOnce()
  })

  it("filters heartbeat frames before delivery", () => {
    const onEvent = vi.fn()
    const stream = createEventStream({
      buildUrl: () => "ws://example.test/events",
      isHeartbeat: queueIsHeartbeat,
      onEvent,
      WebSocketCtor,
    })

    stream.connect()
    FakeWebSocket.instances[0].simulateMessage('{"type":"ping","id":"heartbeat-1"}')

    expect(onEvent).not.toHaveBeenCalled()
  })

  it("drops duplicate event keys", () => {
    const onEvent = vi.fn()
    const stream = createEventStream({
      buildUrl: () => "ws://example.test/events",
      getEventKey: queueGetEventKey,
      onEvent,
      WebSocketCtor,
    })

    stream.connect()
    FakeWebSocket.instances[0].simulateMessage('{"type":"task.progress","eventKey":"event-1","payload":{"percent":25}}')
    FakeWebSocket.instances[0].simulateMessage('{"type":"task.progress","eventKey":"event-1","payload":{"percent":25}}')

    expect(onEvent).toHaveBeenCalledOnce()
  })

  it("keeps the deduplication window across reconnects", () => {
    const onEvent = vi.fn()
    const stream = createEventStream({
      buildUrl: () => "ws://example.test/events",
      getEventKey: queueGetEventKey,
      onEvent,
      WebSocketCtor,
    })

    stream.connect()
    FakeWebSocket.instances[0].simulateMessage('{"type":"task.progress","id":"event-1"}')
    FakeWebSocket.instances[0].simulateClose(1006)
    vi.advanceTimersByTime(500)
    FakeWebSocket.instances[1].simulateMessage('{"type":"task.progress","id":"event-1"}')

    expect(onEvent).toHaveBeenCalledOnce()
  })

  it("evicts deduplication keys in FIFO order", () => {
    const onEvent = vi.fn()
    const stream = createEventStream({
      buildUrl: () => "ws://example.test/events",
      dedupWindow: 2,
      getEventKey: queueGetEventKey,
      onEvent,
      WebSocketCtor,
    })

    stream.connect()
    FakeWebSocket.instances[0].simulateMessage('{"type":"task.progress","id":"event-1"}')
    FakeWebSocket.instances[0].simulateMessage('{"type":"task.progress","id":"event-2"}')
    FakeWebSocket.instances[0].simulateMessage('{"type":"task.progress","id":"event-3"}')
    FakeWebSocket.instances[0].simulateMessage('{"type":"task.progress","id":"event-2"}')
    FakeWebSocket.instances[0].simulateMessage('{"type":"task.progress","id":"event-1"}')

    expect(onEvent).toHaveBeenCalledTimes(4)
  })

  it("supports custom heartbeat and event-key selectors", () => {
    const onEvent = vi.fn()
    const stream = createEventStream<{ event_type: string; idempotency_key?: string }>({
      buildUrl: () => "ws://example.test/events",
      getEventKey: (frame) => frame.idempotency_key,
      isHeartbeat: (frame) => frame.event_type === "heartbeat",
      onEvent,
      WebSocketCtor,
    })

    stream.connect()
    FakeWebSocket.instances[0].simulateMessage('{"event_type":"heartbeat","idempotency_key":"ping-1"}')
    FakeWebSocket.instances[0].simulateMessage('{"event_type":"progress","idempotency_key":"event-1"}')
    FakeWebSocket.instances[0].simulateMessage('{"event_type":"progress","idempotency_key":"event-1"}')

    expect(onEvent).toHaveBeenCalledOnce()
  })

  it("keeps a contiguous sequence chain silent", () => {
    const onGap = vi.fn()
    const stream = createEventStream({
      buildUrl: () => "ws://example.test/events",
      getSequence: queueGetSequence,
      onEvent: vi.fn(),
      onGap,
      WebSocketCtor,
    })

    stream.connect()
    FakeWebSocket.instances[0].simulateMessage('{"taskId":"task-1","attempt":1,"sequence":1}')
    FakeWebSocket.instances[0].simulateMessage('{"taskId":"task-1","attempt":1,"sequence":2}')
    FakeWebSocket.instances[0].simulateMessage('{"taskId":"task-1","attempt":1,"sequence":3}')

    expect(onGap).not.toHaveBeenCalled()
    FakeWebSocket.instances[0].simulateMessage('{"taskId":"task-1","attempt":1,"sequence":5}')
    expect(onGap).toHaveBeenCalledWith({
      stream: "task-1:1",
      from: 3,
      to: 5,
      missing: 1,
    })
  })

  it("reports a sequence jump exactly once", () => {
    const onGap = vi.fn()
    const stream = createEventStream({
      buildUrl: () => "ws://example.test/events",
      getSequence: queueGetSequence,
      onEvent: vi.fn(),
      onGap,
      WebSocketCtor,
    })

    stream.connect()
    FakeWebSocket.instances[0].simulateMessage('{"taskId":"task-1","attempt":1,"sequence":5}')
    FakeWebSocket.instances[0].simulateMessage('{"taskId":"task-1","attempt":1,"sequence":8}')
    FakeWebSocket.instances[0].simulateMessage('{"taskId":"task-1","attempt":1,"sequence":9}')

    expect(onGap).toHaveBeenCalledOnce()
    expect(onGap).toHaveBeenCalledWith({
      stream: "task-1:1",
      from: 5,
      to: 8,
      missing: 2,
    })
  })

  it("ignores null sequence frames without breaking the chain", () => {
    const onGap = vi.fn()
    const stream = createEventStream({
      buildUrl: () => "ws://example.test/events",
      getSequence: queueGetSequence,
      onEvent: vi.fn(),
      onGap,
      WebSocketCtor,
    })

    stream.connect()
    FakeWebSocket.instances[0].simulateMessage('{"taskId":"task-1","attempt":1,"sequence":5}')
    FakeWebSocket.instances[0].simulateMessage('{"taskId":"task-1","attempt":1,"sequence":null,"type":"task.completed"}')
    FakeWebSocket.instances[0].simulateMessage('{"taskId":"task-1","attempt":1,"sequence":6}')

    expect(onGap).not.toHaveBeenCalled()
    FakeWebSocket.instances[0].simulateMessage('{"taskId":"task-1","attempt":1,"sequence":8}')
    expect(onGap).toHaveBeenCalledWith({
      stream: "task-1:1",
      from: 6,
      to: 8,
      missing: 1,
    })
  })

  it("tracks retry attempts as separate sequence chains", () => {
    const onGap = vi.fn()
    const stream = createEventStream({
      buildUrl: () => "ws://example.test/events",
      getSequence: queueGetSequence,
      onEvent: vi.fn(),
      onGap,
      WebSocketCtor,
    })

    stream.connect()
    FakeWebSocket.instances[0].simulateMessage('{"taskId":"task-1","attempt":1,"sequence":7}')
    FakeWebSocket.instances[0].simulateMessage('{"taskId":"task-1","attempt":2,"sequence":1}')

    expect(onGap).not.toHaveBeenCalled()
    FakeWebSocket.instances[0].simulateMessage('{"taskId":"task-1","attempt":2,"sequence":3}')
    expect(onGap).toHaveBeenCalledWith({
      stream: "task-1:2",
      from: 1,
      to: 3,
      missing: 1,
    })
  })

  it("ignores non-advancing sequence values", () => {
    const onGap = vi.fn()
    const stream = createEventStream({
      buildUrl: () => "ws://example.test/events",
      getSequence: queueGetSequence,
      onEvent: vi.fn(),
      onGap,
      WebSocketCtor,
    })

    stream.connect()
    FakeWebSocket.instances[0].simulateMessage('{"taskId":"task-1","attempt":1,"sequence":5}')
    FakeWebSocket.instances[0].simulateMessage('{"taskId":"task-1","attempt":1,"sequence":4}')
    FakeWebSocket.instances[0].simulateMessage('{"taskId":"task-1","attempt":1,"sequence":6}')

    expect(onGap).not.toHaveBeenCalled()
    FakeWebSocket.instances[0].simulateMessage('{"taskId":"task-1","attempt":1,"sequence":8}')
    expect(onGap).toHaveBeenCalledWith({
      stream: "task-1:1",
      from: 6,
      to: 8,
      missing: 1,
    })
  })

  it("stays silent when reconnect replay covers the sequence", () => {
    const onEvent = vi.fn()
    const onGap = vi.fn()
    const stream = createEventStream({
      buildUrl: () => "ws://example.test/events",
      getEventKey: queueGetEventKey,
      getSequence: queueGetSequence,
      onEvent,
      onGap,
      WebSocketCtor,
    })

    stream.connect()
    FakeWebSocket.instances[0].simulateMessage('{"id":"event-1","taskId":"task-1","attempt":1,"sequence":1}')
    FakeWebSocket.instances[0].simulateMessage('{"id":"event-2","taskId":"task-1","attempt":1,"sequence":2}')
    FakeWebSocket.instances[0].simulateClose(1006)
    vi.advanceTimersByTime(500)
    FakeWebSocket.instances[1].simulateMessage('{"id":"event-1","taskId":"task-1","attempt":1,"sequence":1}')
    FakeWebSocket.instances[1].simulateMessage('{"id":"event-2","taskId":"task-1","attempt":1,"sequence":2}')
    FakeWebSocket.instances[1].simulateMessage('{"id":"event-3","taskId":"task-1","attempt":1,"sequence":3}')

    expect(onGap).not.toHaveBeenCalled()
    expect(onEvent).toHaveBeenCalledTimes(3)
    FakeWebSocket.instances[1].simulateMessage('{"id":"event-5","taskId":"task-1","attempt":1,"sequence":5}')
    expect(onGap).toHaveBeenCalledWith({
      stream: "task-1:1",
      from: 3,
      to: 5,
      missing: 1,
    })
  })

  it("supports a custom sequence selector", () => {
    const onGap = vi.fn()
    const stream = createEventStream<{ chain: string; offset: number }>({
      buildUrl: () => "ws://example.test/events",
      getSequence: (frame) => ({ stream: frame.chain, value: frame.offset }),
      onEvent: vi.fn(),
      onGap,
      WebSocketCtor,
    })

    stream.connect()
    FakeWebSocket.instances[0].simulateMessage('{"chain":"workspace-1","offset":2}')
    FakeWebSocket.instances[0].simulateMessage('{"chain":"workspace-1","offset":4}')

    expect(onGap).toHaveBeenCalledWith({
      stream: "workspace-1",
      from: 2,
      to: 4,
      missing: 1,
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

  it("calls onReconnect only after the first successful open", () => {
    const onReconnect = vi.fn()
    const stream = createEventStream({
      buildUrl: () => "ws://example.test/events",
      onEvent: vi.fn(),
      onReconnect,
      WebSocketCtor,
    })

    stream.connect()
    FakeWebSocket.instances[0].simulateOpen()
    expect(onReconnect).not.toHaveBeenCalled()

    FakeWebSocket.instances[0].simulateClose(1006)
    vi.advanceTimersByTime(500)
    FakeWebSocket.instances[1].simulateOpen()
    expect(onReconnect).toHaveBeenCalledOnce()

    FakeWebSocket.instances[1].simulateClose(1006)
    vi.advanceTimersByTime(500)
    FakeWebSocket.instances[2].simulateOpen()
    expect(onReconnect).toHaveBeenCalledTimes(2)
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

describe("createEventStream SSE transport", () => {
  beforeEach(() => {
    FakeEventSource.instances = []
    vi.useFakeTimers()
    vi.spyOn(Math, "random").mockReturnValue(0.5)
  })

  afterEach(() => {
    vi.useRealTimers()
    vi.restoreAllMocks()
  })

  it("listens for unnamed message events by default", () => {
    const stream = createEventStream({
      buildUrl: () => "/events",
      EventSourceCtor,
      onEvent: vi.fn(),
      transport: "sse",
    })

    stream.connect()

    const registeredTypes = FakeEventSource.instances[0].eventTypes()
    expect(registeredTypes.filter((eventType) => eventType !== "open" && eventType !== "error")).toEqual(["message"])
  })

  it("replaces the default event names with caller-supplied names", () => {
    const stream = createEventStream({
      buildUrl: () => "/events",
      EventSourceCtor,
      onEvent: vi.fn(),
      sseEvents: ["custom.started", "custom.finished"],
      transport: "sse",
    })

    stream.connect()

    const registeredTypes = FakeEventSource.instances[0].eventTypes()
    expect(registeredTypes.filter((eventType) => eventType !== "open" && eventType !== "error")).toEqual(["custom.started", "custom.finished"])
  })

  it("parses named SSE messages and forwards the frame", () => {
    const onEvent = vi.fn()
    const stream = createEventStream({
      buildUrl: () => "/events",
      EventSourceCtor,
      onEvent,
      sseEvents: ["custom.progress"],
      transport: "sse",
    })

    stream.connect()
    FakeEventSource.instances[0].simulateEvent("custom.progress", '{"type":"custom.progress","payload":{"percent":75}}')

    expect(onEvent).toHaveBeenCalledWith({
      type: "custom.progress",
      payload: { percent: 75 },
    })
  })

  it("closes the native EventSource and schedules one library-owned reconnect", () => {
    const stream = createEventStream({
      buildUrl: () => "/events",
      EventSourceCtor,
      onEvent: vi.fn(),
      transport: "sse",
    })

    stream.connect()
    FakeEventSource.instances[0].simulateError()
    FakeEventSource.instances[0].simulateError()

    expect(FakeEventSource.instances[0].close).toHaveBeenCalledOnce()
    vi.advanceTimersByTime(499)
    expect(FakeEventSource.instances).toHaveLength(1)
    vi.advanceTimersByTime(1)
    expect(FakeEventSource.instances).toHaveLength(2)
  })
})
