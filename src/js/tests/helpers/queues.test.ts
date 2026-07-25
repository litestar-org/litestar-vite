import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"
import * as helperExports from "../../src/helpers"
import { createQueueEventStream, QUEUE_SSE_EVENTS, type QueueStreamTarget } from "../../src/helpers/queues"

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

  simulateMessage(data: string): void {
    this.dispatch("message", new MessageEvent("message", { data }))
  }

  private dispatch(type: string, event: Event): void {
    for (const listener of this.listeners.get(type) ?? []) {
      listener(event)
    }
  }
}

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
}

const WebSocketCtor = FakeWebSocket as unknown as typeof WebSocket
const EventSourceCtor = FakeEventSource as unknown as typeof EventSource

const routeCases: ReadonlyArray<{
  target: QueueStreamTarget
  websocket: string
  sse: string
}> = [
  {
    target: { scope: "task", taskId: "task one" },
    websocket: "/queues/events/tasks/task%20one",
    sse: "/queues/events/sse/tasks/task%20one",
  },
  {
    target: { scope: "queue", queue: "priority" },
    websocket: "/queues/events/queues/priority",
    sse: "/queues/events/sse/queues/priority",
  },
  {
    target: { scope: "worker", workerId: "worker-1" },
    websocket: "/queues/events/workers/worker-1",
    sse: "/queues/events/sse/workers/worker-1",
  },
  {
    target: { scope: "global" },
    websocket: "/queues/events/global",
    sse: "/queues/events/sse/global",
  },
  {
    target: { scope: "custom", scopeKey: "tenant:one" },
    websocket: "/queues/events/custom/tenant%3Aone",
    sse: "/queues/events/sse/custom/tenant%3Aone",
  },
]

describe("createQueueEventStream", () => {
  beforeEach(() => {
    FakeWebSocket.instances = []
    FakeEventSource.instances = []
    vi.useFakeTimers()
    vi.spyOn(Math, "random").mockReturnValue(0.5)
  })

  afterEach(() => {
    vi.useRealTimers()
    vi.restoreAllMocks()
  })

  it("is exported from the helpers entry point", () => {
    expect((helperExports as Record<string, unknown>).createQueueEventStream).toBe(createQueueEventStream)
  })

  it.each(routeCases)("builds the $target.scope WebSocket route", ({ target, websocket }) => {
    const stream = createQueueEventStream({
      ...target,
      onEvent: vi.fn(),
      WebSocketCtor,
    })

    stream.connect()

    expect(new URL(FakeWebSocket.instances[0].url).pathname).toBe(websocket)
  })

  it.each(routeCases)("builds the $target.scope SSE route", ({ target, sse }) => {
    const stream = createQueueEventStream({
      ...target,
      EventSourceCtor,
      onEvent: vi.fn(),
      transport: "sse",
    })

    stream.connect()

    expect(new URL(FakeEventSource.instances[0].url).pathname).toBe(sse)
  })

  it("registers every named queue event for SSE", () => {
    const stream = createQueueEventStream({
      scope: "global",
      EventSourceCtor,
      onEvent: vi.fn(),
      transport: "sse",
    })

    stream.connect()

    const eventTypes = FakeEventSource.instances[0].eventTypes()
    expect(eventTypes.filter((eventType) => eventType !== "open" && eventType !== "error")).toEqual(QUEUE_SSE_EVENTS)
  })

  it("applies queue heartbeat, deduplication, and sequence defaults", () => {
    const onEvent = vi.fn()
    const onGap = vi.fn()
    const stream = createQueueEventStream({
      scope: "task",
      taskId: "task-1",
      onEvent,
      onGap,
      WebSocketCtor,
    })

    stream.connect()
    FakeWebSocket.instances[0].simulateMessage('{"type":"ping"}')
    FakeWebSocket.instances[0].simulateMessage('{"id":"event-1","taskId":"task-1","attempt":1,"sequence":1}')
    FakeWebSocket.instances[0].simulateMessage('{"id":"event-1","taskId":"task-1","attempt":1,"sequence":1}')
    FakeWebSocket.instances[0].simulateMessage('{"id":"event-3","taskId":"task-1","attempt":1,"sequence":3}')

    expect(onEvent).toHaveBeenCalledTimes(2)
    expect(onGap).toHaveBeenCalledWith({
      stream: "task-1:1",
      from: 1,
      to: 3,
      missing: 1,
    })
  })

  it("supports custom paths, event names, and frame selectors", () => {
    const onEvent = vi.fn()
    const stream = createQueueEventStream<{ kind: string; key: string }>({
      scope: "custom",
      scopeKey: "tenant",
      basePath: "/events/",
      EventSourceCtor,
      getEventKey: (frame) => frame.key,
      isHeartbeat: (frame) => frame.kind === "keepalive",
      onEvent,
      sseEvents: ["custom.event"],
      transport: "sse",
    })

    stream.connect()

    expect(new URL(FakeEventSource.instances[0].url).pathname).toBe("/events/sse/custom/tenant")
    const eventTypes = FakeEventSource.instances[0].eventTypes()
    expect(eventTypes.filter((eventType) => eventType !== "open" && eventType !== "error")).toEqual(["custom.event"])
  })

  it("accepts a direct endpoint while retaining queue defaults", () => {
    const onEvent = vi.fn()
    const stream = createQueueEventStream({
      url: "/custom/queue-events",
      onEvent,
      WebSocketCtor,
    })

    stream.connect()
    FakeWebSocket.instances[0].simulateMessage('{"type":"ping"}')
    FakeWebSocket.instances[0].simulateMessage('{"id":"event-1"}')

    expect(new URL(FakeWebSocket.instances[0].url).pathname).toBe("/custom/queue-events")
    expect(onEvent).toHaveBeenCalledOnce()
  })

  it("re-evaluates target values and transforms the URL on reconnect", () => {
    let taskId = "task-1"
    let token = "token-1"
    const stream = createQueueEventStream({
      scope: "task",
      taskId: () => taskId,
      onEvent: vi.fn(),
      transformUrl: (url) => {
        url.searchParams.set("token", token)
        return url
      },
      WebSocketCtor,
    })

    stream.connect()
    expect(FakeWebSocket.instances[0].url).toContain("/queues/events/tasks/task-1?token=token-1")

    taskId = "task-2"
    token = "token-2"
    FakeWebSocket.instances[0].simulateClose(1006)
    vi.advanceTimersByTime(500)

    expect(FakeWebSocket.instances[1].url).toContain("/queues/events/tasks/task-2?token=token-2")
  })
})
