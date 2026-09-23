/**
 * Generate strongly typed channel definitions from AsyncAPI 3.0 specification.
 *
 * This module generates `channels.ts` which provides typed contracts for:
 * - WebSocket routes (@websocket, @websocket_listener)
 * - ChannelsPlugin broadcast topics
 * - ServerSentEvent streams
 */
import fs from "node:fs"
import path from "node:path"

import { writeIfChanged } from "./write-if-changed.js"

interface AsyncAPIMessageDoc {
  name?: string
  title?: string
  summary?: string
  description?: string
  contentType?: string
  payload?: any
}

interface AsyncAPIChannelDoc {
  address?: string
  title?: string
  summary?: string
  description?: string
  parameters?: Record<string, { description?: string }>
  messages?: Record<string, AsyncAPIMessageDoc>
  bindings?: Record<string, Record<string, unknown>>
}

interface AsyncAPIOperationDoc {
  action?: "send" | "receive"
  channel?: { $ref?: string }
  messages?: { $ref?: string }[]
}

interface AsyncAPIDoc {
  asyncapi: string
  info?: {
    title?: string
    version?: string
    description?: string
  }
  channels?: Record<string, AsyncAPIChannelDoc>
  operations?: Record<string, AsyncAPIOperationDoc>
  components?: {
    schemas?: Record<string, any>
  }
}

function formatPropName(name: string): string {
  if (/^[a-zA-Z_$][a-zA-Z0-9_$]*$/.test(name)) {
    return name
  }
  return JSON.stringify(name)
}

function jsonSchemaToTs(schema: any, indentLevel = 0): string {
  if (!schema || typeof schema !== "object") return "unknown"

  if (schema.$ref) {
    const ref = String(schema.$ref)
    return ref.replace(/^#\/(components\/schemas|\$defs|definitions)\//, "")
  }

  if (schema.enum && Array.isArray(schema.enum)) {
    return schema.enum.map((v: any) => JSON.stringify(v)).join(" | ") || "never"
  }

  if (schema.anyOf && Array.isArray(schema.anyOf)) {
    return schema.anyOf.map((s: any) => `(${jsonSchemaToTs(s, indentLevel)})`).join(" | ")
  }

  if (schema.oneOf && Array.isArray(schema.oneOf)) {
    return schema.oneOf.map((s: any) => `(${jsonSchemaToTs(s, indentLevel)})`).join(" | ")
  }

  if (schema.allOf && Array.isArray(schema.allOf)) {
    return schema.allOf.map((s: any) => `(${jsonSchemaToTs(s, indentLevel)})`).join(" & ")
  }

  const type = schema.type
  if (type === "string") return "string"
  if (type === "number" || type === "integer") return "number"
  if (type === "boolean") return "boolean"
  if (type === "null") return "null"

  if (type === "array") {
    const items = schema.items ? jsonSchemaToTs(schema.items, indentLevel) : "unknown"
    return `(${items})[]`
  }

  if (type === "object" || schema.properties) {
    const props = schema.properties || {}
    const required = Array.isArray(schema.required) ? new Set(schema.required) : new Set()
    const propKeys = Object.keys(props)

    if (propKeys.length === 0) {
      if (schema.additionalProperties && typeof schema.additionalProperties === "object") {
        return `Record<string, ${jsonSchemaToTs(schema.additionalProperties, indentLevel)}>`
      }
      return "Record<string, unknown>"
    }

    const indent = "  ".repeat(indentLevel + 1)
    const closingIndent = "  ".repeat(indentLevel)
    const lines = propKeys.map((key) => {
      const isReq = required.has(key)
      const propTs = jsonSchemaToTs(props[key], indentLevel + 1)
      return `${indent}${formatPropName(key)}${isReq ? "" : "?"}: ${propTs};`
    })
    return `{\n${lines.join("\n")}\n${closingIndent}}`
  }

  return "unknown"
}

function renderComponentSchemas(schemas: Record<string, any>): string[] {
  const lines: string[] = []

  for (const [name, schema] of Object.entries(schemas)) {
    if (schema.type === "object" && schema.properties && Object.keys(schema.properties).length > 0) {
      const required = Array.isArray(schema.required) ? new Set(schema.required) : new Set()
      const propLines = Object.keys(schema.properties).map((propName) => {
        const isReq = required.has(propName)
        const propTs = jsonSchemaToTs(schema.properties[propName], 1)
        return `  ${formatPropName(propName)}${isReq ? "" : "?"}: ${propTs};`
      })
      lines.push(`export interface ${name} {\n${propLines.join("\n")}\n}`, "")
    } else {
      lines.push(`export type ${name} = ${jsonSchemaToTs(schema)};`, "")
    }
  }

  return lines
}

/**
 * Resolve client-perspective send and receive message keys for a channel.
 *
 * Operations in AsyncAPI 3.0 use application-relative action semantics:
 * - `action: "receive"` means inbound to the server, which is client `send`.
 * - `action: "send"` means outbound from the server, which is client `receive`.
 *
 * Fallback behavior when no operation in `doc.operations` references this channel:
 * - If `channel.messages` has exactly one entry:
 *   - If the channel has `bindings.http` (SSE, unidirectional server-to-client),
 *     that single key is assigned to `clientReceiveKeys`, while `clientSendKeys` remains empty.
 *   - Otherwise, that single key is assigned to both `clientSendKeys` and `clientReceiveKeys`.
 * - If `channel.messages` has zero or multiple messages and no matching operations,
 *   returns empty arrays for both directions (resulting in `never`).
 */
function resolveChannelDirections(
  channelKey: string,
  doc: AsyncAPIDoc,
): { clientSendKeys: string[]; clientReceiveKeys: string[] } {
  const operations = Object.entries(doc.operations ?? {})
  const targetChannelRef = `#/channels/${channelKey}`
  const targetMessagePrefix = `#/channels/${channelKey}/messages/`

  const matchingOps = operations.filter(([, op]) => op.channel?.$ref === targetChannelRef)

  if (matchingOps.length > 0) {
    const sendKeySet = new Set<string>()
    const receiveKeySet = new Set<string>()

    for (const [, op] of matchingOps) {
      const messageRefs = op.messages ?? []
      for (const m of messageRefs) {
        if (m.$ref && m.$ref.startsWith(targetMessagePrefix)) {
          const msgKey = m.$ref.slice(targetMessagePrefix.length)
          if (op.action === "receive") {
            sendKeySet.add(msgKey)
          } else if (op.action === "send") {
            receiveKeySet.add(msgKey)
          }
        }
      }
    }

    return {
      clientSendKeys: [...sendKeySet].toSorted(),
      clientReceiveKeys: [...receiveKeySet].toSorted(),
    }
  }

  const channel = doc.channels?.[channelKey]
  const messageEntries = Object.keys(channel?.messages ?? {})

  if (messageEntries.length === 1) {
    const singleKey = messageEntries[0]
    if (channel?.bindings?.http) {
      return {
        clientSendKeys: [],
        clientReceiveKeys: [singleKey],
      }
    }
    return {
      clientSendKeys: [singleKey],
      clientReceiveKeys: [singleKey],
    }
  }

  return {
    clientSendKeys: [],
    clientReceiveKeys: [],
  }
}

export function generateChannelsTs(doc: AsyncAPIDoc): string {
  const sections: string[] = [
    "/**",
    " * Generated Realtime Channels and Message Types from AsyncAPI 3.0.",
    " *",
    " * DO NOT EDIT DIRECTLY. This file is automatically generated by litestar-vite.",
    " */",
    "",
  ]

  const schemas = doc.components?.schemas
  if (schemas && Object.keys(schemas).length > 0) {
    sections.push("// --- Component Schemas ---", "")
    sections.push(...renderComponentSchemas(schemas))
  }

  const channels = doc.channels || {}
  const channelEntries: string[] = []
  const metadataEntries: string[] = []

  for (const [key, channel] of Object.entries(channels)) {
    const address = channel.address || key
    let protocol: "websocket" | "sse" | "channels" = "channels"
    if (channel.bindings?.ws) {
      protocol = "websocket"
    } else if (channel.bindings?.http) {
      protocol = "sse"
    }

    const params = Object.keys(channel.parameters || {})
    const paramsType =
      params.length > 0
        ? `{\n${params.map((p) => `      ${formatPropName(p)}: string;`).join("\n")}\n    }`
        : "Record<string, never>"

    const { clientSendKeys, clientReceiveKeys } = resolveChannelDirections(key, doc)

    const payloadUnion = (messageKeys: string[]): string => {
      const renderedTypes = new Set<string>()
      for (const msgKey of messageKeys) {
        const payload = channel.messages?.[msgKey]?.payload
        if (payload !== undefined && payload !== null) {
          renderedTypes.add(jsonSchemaToTs(payload, 2))
        }
      }
      if (renderedTypes.size === 0) {
        return "never"
      }
      return Array.from(renderedTypes).join(" | ")
    }

    const sendType = payloadUnion(clientSendKeys)
    const receiveType = payloadUnion(clientReceiveKeys)

    channelEntries.push(
      `  ${JSON.stringify(key)}: {`,
      `    address: ${JSON.stringify(address)};`,
      `    protocol: ${JSON.stringify(protocol)};`,
      `    params: ${paramsType};`,
      `    send: ${sendType};`,
      `    receive: ${receiveType};`,
      `  };`,
    )

    metadataEntries.push(`  ${JSON.stringify(key)}: { address: ${JSON.stringify(address)}, protocol: ${JSON.stringify(protocol)} },`)
  }

  sections.push(
    "// --- Realtime Channels Registry ---",
    "",
    "export interface RealtimeChannels {",
    ...channelEntries,
    "}",
    "",
    "export type ChannelKey = keyof RealtimeChannels;",
    "",
    "export type ChannelAddress = RealtimeChannels[ChannelKey][\"address\"];",
    "",
    "export type ChannelProtocol<K extends ChannelKey = ChannelKey> = RealtimeChannels[K][\"protocol\"];",
    "",
    "export type ChannelParams<K extends ChannelKey = ChannelKey> = RealtimeChannels[K][\"params\"];",
    "",
    "export type ChannelSendPayload<K extends ChannelKey = ChannelKey> = RealtimeChannels[K][\"send\"];",
    "",
    "export type ChannelReceivePayload<K extends ChannelKey = ChannelKey> = RealtimeChannels[K][\"receive\"];",
    "",
    "export interface ChannelMetadata {",
    "  address: string;",
    '  protocol: "websocket" | "sse" | "channels";',
    "}",
    "",
    "export const CHANNEL_METADATA: Record<ChannelKey, ChannelMetadata> = {",
    ...metadataEntries,
    "} as const;",
    "",
  )

  return sections.join("\n")
}

export async function emitChannelsTypes(
  asyncapiPath: string,
  outputDir: string,
  channelsTsPath?: string,
  projectRoot?: string,
): Promise<boolean> {
  const root = projectRoot ?? process.cwd()
  const resolvedAsyncapiPath = path.isAbsolute(asyncapiPath) ? asyncapiPath : path.resolve(root, asyncapiPath)

  if (!fs.existsSync(resolvedAsyncapiPath)) {
    return false
  }

  const rawContent = await fs.promises.readFile(resolvedAsyncapiPath, "utf-8")
  let doc: AsyncAPIDoc
  try {
    doc = JSON.parse(rawContent) as AsyncAPIDoc
  } catch {
    return false
  }

  const content = generateChannelsTs(doc)

  const outFile = channelsTsPath
    ? path.isAbsolute(channelsTsPath)
      ? channelsTsPath
      : path.resolve(root, channelsTsPath)
    : path.resolve(outputDir.startsWith("/") ? outputDir : path.resolve(root, outputDir), "channels.ts")

  await fs.promises.mkdir(path.dirname(outFile), { recursive: true })
  const result = await writeIfChanged(outFile, content, { encoding: "utf-8" })

  return result.changed
}
