import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"
import * as helperExports from "../../src/helpers"
import { createChannelsStream } from "../../src/helpers/channels"

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

const WebSocketCtor = FakeWebSocket as unknown as typeof WebSocket

describe("createChannelsStream", () => {
  beforeEach(() => {
    FakeWebSocket.instances = []
    vi.useFakeTimers()
    vi.spyOn(Math, "random").mockReturnValue(0.5)
  })

  afterEach(() => {
    vi.useRealTimers()
    vi.restoreAllMocks()
  })

  it("is exported from the helpers entry point", () => {
    expect((helperExports as Record<string, unknown>).createChannelsStream).toBe(createChannelsStream)
  })

  it("uses the default ChannelsPlugin route for an arbitrary channel", () => {
    const stream = createChannelsStream({
      channel: "notifications",
      onEvent: vi.fn(),
      WebSocketCtor,
    })

    stream.connect()

    expect(FakeWebSocket.instances[0]?.url).toBe("ws://localhost:3000/notifications")
  })

  it("matches a custom ws_handler_base_path and encodes one channel segment", () => {
    const stream = createChannelsStream({
      basePath: "/ws",
      channel: "workspace:one/two",
      onEvent: vi.fn(),
      WebSocketCtor,
    })

    stream.connect()

    expect(FakeWebSocket.instances[0]?.url).toBe("ws://localhost:3000/ws/workspace%3Aone%2Ftwo")
  })

  it("re-evaluates the channel and URL transform before reconnecting", () => {
    let channel = "first"
    let token = "token-1"
    const transformUrl = vi.fn((url: URL) => {
      url.searchParams.set("token", token)
      return url
    })
    const stream = createChannelsStream({
      basePath: "/ws/",
      channel: () => channel,
      onEvent: vi.fn(),
      transformUrl,
      WebSocketCtor,
    })

    stream.connect()
    expect(FakeWebSocket.instances[0]?.url).toBe("ws://localhost:3000/ws/first?token=token-1")

    channel = "second"
    token = "token-2"
    FakeWebSocket.instances[0].simulateClose(1006)
    vi.advanceTimersByTime(500)

    expect(FakeWebSocket.instances[1]?.url).toBe("ws://localhost:3000/ws/second?token=token-2")
    expect(transformUrl).toHaveBeenCalledTimes(2)
  })

  it("forwards JSON and raw ChannelsPlugin payloads", () => {
    const onEvent = vi.fn()
    const stream = createChannelsStream({
      channel: "notifications",
      onEvent,
      WebSocketCtor,
    })

    stream.connect()
    FakeWebSocket.instances[0].simulateMessage('{"type":"notification","value":1}')
    FakeWebSocket.instances[0].simulateMessage("plain notification")

    expect(onEvent.mock.calls).toEqual([[{ type: "notification", value: 1 }], ["plain notification"]])
  })
})
