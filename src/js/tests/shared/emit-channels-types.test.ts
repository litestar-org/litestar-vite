import fs from "node:fs"
import path from "node:path"
import { afterEach, describe, expect, it } from "vitest"

import { emitChannelsTypes } from "../../src/shared/emit-channels-types.js"

const tmpDirs: string[] = []

const createTmpDir = (): string => {
  const dir = fs.mkdtempSync(path.join(process.cwd(), "vitest-channels-emit-"))
  tmpDirs.push(dir)
  return dir
}

afterEach(() => {
  for (const dir of tmpDirs) {
    try {
      fs.rmSync(dir, { recursive: true, force: true })
    } catch {
      // ignore
    }
  }
  tmpDirs.length = 0
})

describe("emitChannelsTypes", () => {
  it("returns false if asyncapi.json does not exist", async () => {
    const tmpDir = createTmpDir()
    const nonExistentPath = path.join(tmpDir, "missing-asyncapi.json")
    const result = await emitChannelsTypes(nonExistentPath, tmpDir)
    expect(result).toBe(false)
  })

  it("returns false if asyncapi.json contains invalid JSON", async () => {
    const tmpDir = createTmpDir()
    const badPath = path.join(tmpDir, "bad-asyncapi.json")
    fs.writeFileSync(badPath, "{ invalid json", "utf-8")
    const result = await emitChannelsTypes(badPath, tmpDir)
    expect(result).toBe(false)
  })

  it("generates channels.ts from complete AsyncAPI document", async () => {
    const tmpDir = createTmpDir()
    const asyncapiPath = path.join(tmpDir, "asyncapi.json")

    const doc = {
      asyncapi: "3.0.0",
      info: {
        title: "Chat & Notifications Realtime API",
        version: "2.1.0",
      },
      channels: {
        ws_chat: {
          address: "/ws/chat/{room_id}",
          title: "chat_handler Channel",
          parameters: {
            room_id: { description: "Path parameter room_id" },
          },
          messages: {
            inbound: {
              name: "ws_chatInbound",
              payload: { $ref: "#/components/schemas/InboundMessage" },
            },
            outbound: {
              name: "ws_chatOutbound",
              payload: { $ref: "#/components/schemas/OutboundMessage" },
            },
          },
          bindings: {
            ws: {},
          },
        },
        notifications: {
          address: "notifications",
          title: "Notifications Channel",
          messages: {
            message: {
              name: "notificationsMessage",
              payload: { type: "string" },
            },
          },
        },
        stream_events: {
          address: "/stream/events",
          title: "Events SSE Stream",
          messages: {
            event: {
              name: "stream_eventsEvent",
              payload: { $ref: "#/components/schemas/ServerEvent" },
            },
          },
          bindings: {
            http: {},
          },
        },
      },
      components: {
        schemas: {
          InboundMessage: {
            type: "object",
            properties: {
              room_id: { type: "string" },
              content: { type: "string" },
            },
            required: ["room_id", "content"],
          },
          OutboundMessage: {
            type: "object",
            properties: {
              id: { type: "integer" },
              content: { type: "string" },
              timestamp: { type: "number" },
            },
            required: ["id", "content"],
          },
          ServerEvent: {
            type: "object",
            properties: {
              event_type: { enum: ["join", "leave", "alert"] },
              metadata: { type: "object" },
            },
            required: ["event_type"],
          },
        },
      },
      operations: {
        receive_ws_chat: { action: "receive", channel: { $ref: "#/channels/ws_chat" }, messages: [{ $ref: "#/channels/ws_chat/messages/inbound" }] },
        send_ws_chat: { action: "send", channel: { $ref: "#/channels/ws_chat" }, messages: [{ $ref: "#/channels/ws_chat/messages/outbound" }] },
        send_notifications: { action: "send", channel: { $ref: "#/channels/notifications" }, messages: [{ $ref: "#/channels/notifications/messages/message" }] },
        receive_notifications: { action: "receive", channel: { $ref: "#/channels/notifications" }, messages: [{ $ref: "#/channels/notifications/messages/message" }] },
        stream_stream_events: { action: "send", channel: { $ref: "#/channels/stream_events" }, messages: [{ $ref: "#/channels/stream_events/messages/event" }] },
      },
    }

    fs.writeFileSync(asyncapiPath, JSON.stringify(doc, null, 2), "utf-8")

    const changed = await emitChannelsTypes(asyncapiPath, tmpDir)
    expect(changed).toBe(true)

    const outFile = path.join(tmpDir, "channels.ts")
    expect(fs.existsSync(outFile)).toBe(true)
    const content = fs.readFileSync(outFile, "utf-8")

    // Component schemas
    expect(content).toContain("export interface InboundMessage {")
    expect(content).toContain("room_id: string;")
    expect(content).toContain("content: string;")

    expect(content).toContain("export interface OutboundMessage {")
    expect(content).toContain("id: number;")
    expect(content).toContain("timestamp?: number;")

    expect(content).toContain("export interface ServerEvent {")
    expect(content).toContain('event_type: "join" | "leave" | "alert";')
    expect(content).toContain("metadata?: Record<string, unknown>;")

    // RealtimeChannels registry
    expect(content).toContain("export interface RealtimeChannels {")
    expect(content).toContain('"ws_chat": {')
    expect(content).toContain('address: "/ws/chat/{room_id}";')
    expect(content).toContain('protocol: "websocket";')
    expect(content).toContain("room_id: string;")
    expect(content).toContain("send: InboundMessage;")
    expect(content).toContain("receive: OutboundMessage;")

    expect(content).toContain('"notifications": {')
    expect(content).toContain('address: "notifications";')
    expect(content).toContain('protocol: "channels";')
    expect(content).toContain("params: Record<string, never>;")
    expect(content).toContain("send: string;")
    expect(content).toContain("receive: string;")

    expect(content).toContain('"stream_events": {')
    expect(content).toContain('address: "/stream/events";')
    expect(content).toContain('protocol: "sse";')
    expect(content).toContain("send: never;")
    expect(content).toContain("receive: ServerEvent;")

    // Helpers
    expect(content).toContain("export type ChannelKey = keyof RealtimeChannels;")
    expect(content).toContain('export type ChannelAddress = RealtimeChannels[ChannelKey]["address"];')
    expect(content).toContain("export const CHANNEL_METADATA: Record<ChannelKey, ChannelMetadata> = {")
    expect(content).toContain('"ws_chat": { address: "/ws/chat/{room_id}", protocol: "websocket" }')
  })

  it("writes to custom channelsTsPath", async () => {
    const tmpDir = createTmpDir()
    const asyncapiPath = path.join(tmpDir, "asyncapi.json")
    const customOut = path.join(tmpDir, "custom", "my-channels.ts")

    const doc = {
      asyncapi: "3.0.0",
      channels: {},
    }
    fs.writeFileSync(asyncapiPath, JSON.stringify(doc), "utf-8")

    const changed = await emitChannelsTypes(asyncapiPath, tmpDir, customOut)
    expect(changed).toBe(true)
    expect(fs.existsSync(customOut)).toBe(true)
  })

  it("reports false when file is unchanged on subsequent run", async () => {
    const tmpDir = createTmpDir()
    const asyncapiPath = path.join(tmpDir, "asyncapi.json")
    const doc = {
      asyncapi: "3.0.0",
      channels: {
        feed: {
          address: "feed",
        },
      },
    }
    fs.writeFileSync(asyncapiPath, JSON.stringify(doc), "utf-8")

    const firstRun = await emitChannelsTypes(asyncapiPath, tmpDir)
    expect(firstRun).toBe(true)

    const secondRun = await emitChannelsTypes(asyncapiPath, tmpDir)
    expect(secondRun).toBe(false)
  })

  it("falls back to a single message when the document has no operations", async () => {
    const tmpDir = createTmpDir()
    const asyncapiPath = path.join(tmpDir, "asyncapi.json")

    const doc = {
      asyncapi: "3.0.0",
      channels: {
        chat: {
          address: "/chat",
          bindings: { ws: {} },
          messages: {
            msg: {
              name: "ChatMessage",
              payload: { type: "string" },
            },
          },
        },
        sse_feed: {
          address: "/sse/feed",
          bindings: { http: {} },
          messages: {
            item: {
              name: "FeedItem",
              payload: { type: "number" },
            },
          },
        },
      },
    }
    fs.writeFileSync(asyncapiPath, JSON.stringify(doc, null, 2), "utf-8")

    const changed = await emitChannelsTypes(asyncapiPath, tmpDir)
    expect(changed).toBe(true)

    const outFile = path.join(tmpDir, "channels.ts")
    const content = fs.readFileSync(outFile, "utf-8")

    expect(content).toContain('"chat": {')
    expect(content).toContain("send: string;")
    expect(content).toContain("receive: string;")

    expect(content).toContain('"sse_feed": {')
    expect(content).toContain("send: never;")
    expect(content).toContain("receive: number;")
  })

  it("emits never for a channel with no resolvable operations or messages", async () => {
    const tmpDir = createTmpDir()
    const asyncapiPath = path.join(tmpDir, "asyncapi.json")

    const doc = {
      asyncapi: "3.0.0",
      channels: {
        empty_channel: {
          address: "/empty",
          bindings: { ws: {} },
        },
      },
    }
    fs.writeFileSync(asyncapiPath, JSON.stringify(doc, null, 2), "utf-8")

    const changed = await emitChannelsTypes(asyncapiPath, tmpDir)
    expect(changed).toBe(true)

    const outFile = path.join(tmpDir, "channels.ts")
    const content = fs.readFileSync(outFile, "utf-8")

    expect(content).toContain('"empty_channel": {')
    expect(content).toContain("send: never;")
    expect(content).toContain("receive: never;")

    const registryMatch = content.match(/export interface RealtimeChannels \{([\s\S]*?)\}/)
    expect(registryMatch).not.toBeNull()
    expect(registryMatch![1]).not.toContain("unknown")
  })
})

