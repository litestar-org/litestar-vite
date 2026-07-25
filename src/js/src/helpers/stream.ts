/**
 * Resilient WebSocket and SSE helpers for Litestar event streams.
 *
 * @example
 * ```ts
 * import { createEventStream } from "litestar-vite-plugin/helpers"
 *
 * const stream = createEventStream({
 *   url: "/events",
 *   onEvent: (event) => console.log(event),
 * })
 *
 * stream.connect()
 * ```
 *
 * @module
 */

export interface StreamGap {
  stream: string
  from: number
  to: number
  missing: number
}

export type EventStreamTransport = "websocket" | "sse"
export type StreamUrl = string | URL | (() => string | URL)

export interface EventStreamConfig<TFrame = unknown> {
  transport?: "websocket" | "sse"
  sseEvents?: readonly string[]
  onEvent: (frame: TFrame) => void
  onOpen?: (url: string) => void
  onClose?: () => void
  onHealthChange?: (healthy: boolean) => void
  onReconnect?: () => void
  onGap?: (gap: StreamGap) => void
  shouldReconnect?: (closeCode: number) => boolean
  isHeartbeat?: (frame: TFrame) => boolean
  getEventKey?: (frame: TFrame) => string | undefined
  getSequence?: (frame: TFrame) => { stream: string; value: number } | undefined
  baseDelayMs?: number
  maxDelayMs?: number
  dedupWindow?: number
  parseFrame?: (data: string) => TFrame
  WebSocketCtor?: typeof WebSocket
  EventSourceCtor?: typeof EventSource
}

export type EventStreamOptions<TFrame = unknown> = EventStreamConfig<TFrame> &
  (
    | {
        url: StreamUrl
        buildUrl?: never
      }
    | {
        url?: never
        buildUrl: () => string | URL
      }
  )

export interface EventStream {
  connect(): void
  dispose(): void
  readonly healthy: boolean
}

const DEFAULT_BASE_DELAY_MS = 1000
const DEFAULT_MAX_DELAY_MS = 10_000
const DEFAULT_DEDUP_WINDOW = 1024
const DEFAULT_SSE_EVENTS = ["message"] as const

function defaultParseFrame(data: string): unknown {
  try {
    return JSON.parse(data)
  } catch {
    return data
  }
}

/**
 * Resolve a stream endpoint against the browser origin.
 *
 * @param value - Absolute or same-origin relative endpoint.
 * @param transport - Transport whose URL protocol should be used.
 * @param baseUrl - Resolution base. Defaults to the current browser location.
 * @returns An absolute transport URL.
 */
export function resolveStreamUrl(value: string | URL, transport: EventStreamTransport, baseUrl: string | URL = window.location.href): string {
  const resolved = new URL(value, baseUrl)
  if (transport === "websocket") {
    if (resolved.protocol === "http:") {
      resolved.protocol = "ws:"
    } else if (resolved.protocol === "https:") {
      resolved.protocol = "wss:"
    }
  } else if (resolved.protocol === "ws:") {
    resolved.protocol = "http:"
  } else if (resolved.protocol === "wss:") {
    resolved.protocol = "https:"
  }
  return resolved.toString()
}

/**
 * Create a reconnecting, transport-agnostic Litestar event stream.
 *
 * @param options - Stream transport, lifecycle, and frame-processing options.
 * @returns A disposable stream that connects only when `connect()` is called.
 */
export function createEventStream<TFrame = unknown>(options: EventStreamOptions<TFrame>): EventStream {
  const {
    transport = "websocket",
    sseEvents = DEFAULT_SSE_EVENTS,
    onEvent,
    onOpen,
    onClose,
    onHealthChange,
    onReconnect,
    onGap,
    shouldReconnect = (closeCode) => closeCode !== 1000,
    isHeartbeat = () => false,
    getEventKey = () => undefined,
    getSequence = () => undefined,
    baseDelayMs = DEFAULT_BASE_DELAY_MS,
    maxDelayMs = DEFAULT_MAX_DELAY_MS,
    dedupWindow = DEFAULT_DEDUP_WINDOW,
    parseFrame = defaultParseFrame as (data: string) => TFrame,
  } = options

  let connection: WebSocket | EventSource | null = null
  let attempt = 0
  let timer: ReturnType<typeof setTimeout> | null = null
  let disposed = false
  let lastHealthy: boolean | null = null
  let hasOpened = false
  const seenKeys: string[] = []
  const seenKeySet = new Set<string>()
  const sequenceByStream = new Map<string, number>()

  function emitHealth(healthy: boolean): void {
    if (lastHealthy === healthy) {
      return
    }
    lastHealthy = healthy
    onHealthChange?.(healthy)
  }

  function clearTimer(): void {
    if (timer !== null) {
      clearTimeout(timer)
      timer = null
    }
  }

  function scheduleReconnect(): void {
    clearTimer()
    attempt += 1
    const ceiling = Math.min(baseDelayMs * 2 ** (attempt - 1), maxDelayMs)
    const delay = Math.random() * ceiling
    timer = setTimeout(() => {
      timer = null
      if (!disposed) {
        open()
      }
    }, delay)
  }

  function handleOpen(url: string): void {
    attempt = 0
    clearTimer()
    emitHealth(true)
    onOpen?.(url)
    if (hasOpened) {
      onReconnect?.()
    } else {
      hasOpened = true
    }
  }

  function handleMessage(event: MessageEvent): void {
    const frame = parseFrame(String(event.data))
    if (isHeartbeat(frame)) {
      return
    }

    const eventKey = getEventKey(frame)
    if (eventKey !== undefined && dedupWindow > 0) {
      if (seenKeySet.has(eventKey)) {
        return
      }
      seenKeys.push(eventKey)
      seenKeySet.add(eventKey)
      if (seenKeys.length > dedupWindow) {
        const evicted = seenKeys.shift()
        if (evicted !== undefined) {
          seenKeySet.delete(evicted)
        }
      }
    }

    const sequence = getSequence(frame)
    if (sequence !== undefined && Number.isFinite(sequence.value)) {
      const last = sequenceByStream.get(sequence.stream)
      if (last === undefined) {
        sequenceByStream.set(sequence.stream, sequence.value)
      } else if (sequence.value > last) {
        sequenceByStream.set(sequence.stream, sequence.value)
        if (sequence.value > last + 1) {
          onGap?.({
            stream: sequence.stream,
            from: last,
            to: sequence.value,
            missing: sequence.value - last - 1,
          })
        }
      }
    }

    onEvent(frame)
  }

  function buildConnectionUrl(): string {
    const value = options.buildUrl === undefined ? options.url : options.buildUrl()
    const endpoint = typeof value === "function" ? value() : value
    return resolveStreamUrl(endpoint, transport)
  }

  function openWebSocket(): void {
    const WebSocketCtor = options.WebSocketCtor ?? window.WebSocket
    const url = buildConnectionUrl()
    const next = new WebSocketCtor(url)
    connection = next
    next.addEventListener("open", () => {
      handleOpen(url)
    })
    next.addEventListener("message", (event) => {
      handleMessage(event)
    })
    next.addEventListener("close", (event) => {
      if (connection !== next) {
        return
      }
      connection = null
      onClose?.()
      emitHealth(false)
      if (disposed || !shouldReconnect(event.code)) {
        return
      }
      scheduleReconnect()
    })
    next.addEventListener("error", () => {
      emitHealth(false)
    })
  }

  function openEventSource(): void {
    const EventSourceCtor = options.EventSourceCtor ?? window.EventSource
    const url = buildConnectionUrl()
    const next = new EventSourceCtor(url)
    connection = next
    next.addEventListener("open", () => {
      handleOpen(url)
    })
    for (const eventType of sseEvents) {
      next.addEventListener(eventType, (event) => {
        handleMessage(event as MessageEvent)
      })
    }
    next.addEventListener("error", () => {
      if (connection !== next) {
        return
      }
      connection = null
      next.close()
      onClose?.()
      emitHealth(false)
      if (disposed || !shouldReconnect(1006)) {
        return
      }
      scheduleReconnect()
    })
  }

  function open(): void {
    if (disposed || typeof window === "undefined") {
      return
    }
    if (transport === "sse") {
      openEventSource()
      return
    }
    openWebSocket()
  }

  return {
    connect(): void {
      if (disposed || typeof window === "undefined") {
        return
      }
      attempt = 0
      clearTimer()
      open()
    },
    dispose(): void {
      disposed = true
      clearTimer()
      const current = connection
      connection = null
      if (current !== null) {
        onClose?.()
        emitHealth(false)
        current.close()
      }
    },
    get healthy(): boolean {
      return lastHealthy ?? false
    },
  }
}
