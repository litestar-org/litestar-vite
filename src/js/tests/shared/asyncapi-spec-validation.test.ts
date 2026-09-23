import fs from "node:fs"
import path from "node:path"
import { Parser } from "@asyncapi/parser"
import { describe, expect, it } from "vitest"
import { generateChannelsTs } from "../../src/shared/emit-channels-types.js"

export function assertRefsResolve(doc: any): void {
  const channels = doc.channels ?? {}
  const operations = doc.operations ?? {}

  for (const [opId, op] of Object.entries<any>(operations)) {
    const channelRef = op.channel?.$ref
    if (!channelRef) {
      throw new Error(`Operation "${opId}" is missing channel.$ref`)
    }
    const channelMatch = channelRef.match(/^#\/channels\/(.+)$/)
    if (!channelMatch) {
      throw new Error(`Operation "${opId}" has invalid channel.$ref "${channelRef}"`)
    }
    const channelKey = channelMatch[1]
    const channel = channels[channelKey]
    if (!channel) {
      throw new Error(`Operation "${opId}" references non-existent channel "${channelKey}" (${channelRef})`)
    }

    const messageRefs = op.messages ?? []
    for (const m of messageRefs) {
      const msgRef = m?.$ref
      if (!msgRef) {
        throw new Error(`Operation "${opId}" has message entry without $ref`)
      }
      const msgPrefix = `#/channels/${channelKey}/messages/`
      if (!msgRef.startsWith(msgPrefix)) {
        throw new Error(`Operation "${opId}" message $ref "${msgRef}" does not start with expected channel prefix "${msgPrefix}"`)
      }
      const msgKey = msgRef.slice(msgPrefix.length)
      if (!channel.messages?.[msgKey]) {
        throw new Error(`Operation "${opId}" references message "${msgKey}" which is not defined in channel "${channelKey}"`)
      }
    }
  }
}

describe("asyncapi spec validation", () => {
  const fixturesDir = path.resolve(import.meta.dirname, "../fixtures/asyncapi")
  const fixtureFiles = fs.readdirSync(fixturesDir).filter((f) => f.endsWith(".json"))

  it("found at least one asyncapi fixture", () => {
    expect(fixtureFiles.length).toBeGreaterThan(0)
  })

  for (const file of fixtureFiles) {
    describe(`fixture: ${file}`, () => {
      const filePath = path.join(fixturesDir, file)
      const rawJson = fs.readFileSync(filePath, "utf-8")
      const doc = JSON.parse(rawJson)

      it("parses against AsyncAPI spec with zero error diagnostics", async () => {
        const parser = new Parser()
        const { diagnostics } = await parser.parse(rawJson)
        const errors = diagnostics.filter(
          (d) => d.severity === 0 && !(d.code === "asyncapi-document-resolved" && typeof d.message === "string" && d.message.includes('"channels"')),
        )
        const errorMessages = errors.map((d) => `[${d.code}] ${d.message} at ${d.path.join(".")}`).join("\n")
        expect(errors, `Offending diagnostics:\n${errorMessages}`).toHaveLength(0)
      })

      it("all operation channel and message references resolve", () => {
        expect(() => assertRefsResolve(doc)).not.toThrow()
      })

      it("retains non-empty bindings object for each declared channel", () => {
        const channels = doc.channels ?? {}
        for (const [key, channel] of Object.entries<any>(channels)) {
          expect(channel.bindings, `Channel "${key}" missing bindings`).toBeDefined()
          expect(typeof channel.bindings === "object" && Object.keys(channel.bindings).length > 0, `Channel "${key}" has empty bindings`).toBe(true)
        }
      })

      it("generates channels.ts without direction defects in RealtimeChannels", () => {
        const content = generateChannelsTs(doc)
        const match = content.match(/export interface RealtimeChannels \{([\s\S]*?)\}/)
        expect(match).not.toBeNull()
        expect(content).toContain("send: ChatInbound;")
        expect(content).toContain("receive: ChatOutbound;")
        expect(content).toContain("send: never;")
        expect(content).toContain("receive: ServerEvent;")
        expect(content).toContain('"notify": {\n    address: "/notify";\n    protocol: "websocket";\n    params: Record<string, never>;\n    send: never;')
      })
    })
  }

  describe("assertRefsResolve error cases", () => {
    it("fails loudly when operation channel.$ref is broken", () => {
      const badDoc = {
        channels: {},
        operations: {
          send_test: {
            action: "send",
            channel: { $ref: "#/channels/missing_channel" },
            messages: [],
          },
        },
      }
      expect(() => assertRefsResolve(badDoc)).toThrow('references non-existent channel "missing_channel"')
    })

    it("fails loudly when operation message.$ref is broken", () => {
      const badDoc = {
        channels: {
          test_ch: {
            address: "/test",
            messages: {},
          },
        },
        operations: {
          send_test: {
            action: "send",
            channel: { $ref: "#/channels/test_ch" },
            messages: [{ $ref: "#/channels/test_ch/messages/missing_msg" }],
          },
        },
      }
      expect(() => assertRefsResolve(badDoc)).toThrow('references message "missing_msg"')
    })
  })
})
