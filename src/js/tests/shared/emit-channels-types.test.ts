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
    expect(content).toContain("send: OutboundMessage;")
    expect(content).toContain("receive: InboundMessage;")

    expect(content).toContain('"notifications": {')
    expect(content).toContain('address: "notifications";')
    expect(content).toContain('protocol: "channels";')
    expect(content).toContain("params: Record<string, never>;")
    expect(content).toContain("send: string;")
    expect(content).toContain("receive: string;")

    expect(content).toContain('"stream_events": {')
    expect(content).toContain('address: "/stream/events";')
    expect(content).toContain('protocol: "sse";')
    expect(content).toContain("send: ServerEvent;")
    expect(content).toContain("receive: never;")

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
})
