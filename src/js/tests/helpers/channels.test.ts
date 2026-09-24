import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"
import * as helperExports from "../../src/helpers"
import { createChannelsStream, createTypedChannels, type ChannelMap } from "../../src/helpers/channels"

class FakeWebSocket {
  static instances: FakeWebSocket[] = []

  readonly url: string
  close = vi.fn()
  readyState = 0
  sent: string[] = []
  private readonly listeners = new Map<string, Set<EventListener>>()

  constructor(url: string | URL) {
    this.url = String(url)
    FakeWebSocket.instances.push(this)
  }

  send(data: string): void {
    this.sent.push(data)
  }

  addEventListener(type: string, listener: EventListener): void {
    const listeners = this.listeners.get(type) ?? new Set<EventListener>()
    listeners.add(listener)
    this.listeners.set(type, listeners)
  }

  simulateClose(code: number): void {
    this.readyState = 3
    this.dispatch("close", { code } as CloseEvent)
  }

  simulateMessage(data: string): void {
    this.dispatch("message", new MessageEvent("message", { data }))
  }

  simulateOpen(): void {
    this.readyState = 1
    this.dispatch("open", new Event("open"))
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

  it("interpolates channel path parameters into WebSocket URL", () => {
    const stream = createChannelsStream({
      basePath: "/ws",
      channel: "chat/{room_id}",
      params: { room_id: 123 },
      onEvent: vi.fn(),
      WebSocketCtor,
    })

    stream.connect()

    expect(FakeWebSocket.instances[0]?.url).toBe("ws://localhost:3000/ws/chat/123")
  })

  it("interpolates multiple channel parameters and URL encodes parameter values", () => {
    const stream = createChannelsStream({
      basePath: "/ws/",
      channel: "rooms/{room_id}/messages/{user_id}",
      params: { room_id: "general room", user_id: 42 },
      onEvent: vi.fn(),
      WebSocketCtor,
    })

    stream.connect()

    expect(FakeWebSocket.instances[0]?.url).toBe("ws://localhost:3000/ws/rooms/general%20room/messages/42")
  })

  it("supports channel function with params", () => {
    const stream = createChannelsStream({
      basePath: "/ws",
      channel: () => "topics/{topic}",
      params: { topic: "tech" },
      onEvent: vi.fn(),
      WebSocketCtor,
    })

    stream.connect()

    expect(FakeWebSocket.instances[0]?.url).toBe("ws://localhost:3000/ws/topics/tech")
  })
})

interface TestChannelMap extends ChannelMap {
  "chat/{room_id}": {
    address: "/ws/chat/{room_id}"
    protocol: "websocket"
    params: { room_id: string }
    send: { message: string }
    receive: { message: string; user: string }
  }
  broadcast: {
    address: "/ws/broadcast"
    protocol: "channels"
    params: Record<string, string>
    send: { text: string }
    receive: { text: string }
  }
}

describe("createTypedChannels", () => {
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
    expect((helperExports as Record<string, unknown>).createTypedChannels).toBe(createTypedChannels)
  })

  it("createTypedChannels builds the same url as createChannelsStream", () => {
    const client = createTypedChannels<TestChannelMap>({ basePath: "/ws" })
    const stream = client.stream("chat/{room_id}", {
      params: { room_id: "lobby" },
      onEvent: vi.fn(),
      WebSocketCtor,
    })

    stream.connect()

    expect(FakeWebSocket.instances[0]?.url).toBe("ws://localhost:3000/ws/chat/lobby")
  })

  it("createTypedChannels send delegates to the underlying socket", () => {
    const client = createTypedChannels<TestChannelMap>({ basePath: "/ws" })
    const stream = client.stream("broadcast", {
      onEvent: vi.fn(),
      WebSocketCtor,
    })

    stream.connect()
    FakeWebSocket.instances[0].simulateOpen()

    const sent = stream.send({ text: "hello world" })
    expect(sent).toBe(true)
    expect(FakeWebSocket.instances[0].sent).toEqual([JSON.stringify({ text: "hello world" })])
  })
})
