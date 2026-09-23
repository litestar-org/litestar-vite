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

export interface EventStreamConfig<TFrame = unknown, TSend = never> {
  transport?: "websocket" | "sse"
  sseEvents?: readonly string[]
  onEvent: (frame: TFrame) => void
  onOpen?: (url: string) => void
  onClose?: () => void
  onHealthChange?: (healthy: boolean) => void
  onReconnect?: () => void
  onGap?: (gap: StreamGap) => void
  onStale?: () => void
  shouldReconnect?: (closeCode: number) => boolean
  isHeartbeat?: (frame: TFrame) => boolean
  getEventKey?: (frame: TFrame) => string | undefined
  getSequence?: (frame: TFrame) => { stream: string; value: number } | undefined
  baseDelayMs?: number
  maxDelayMs?: number
  dedupWindow?: number
  heartbeatTimeoutMs?: number
  heartbeatIntervalMs?: number
  maxTrackedStreams?: number
  parseFrame?: (data: string) => TFrame
  serializeFrame?: (payload: TSend) => string
  WebSocketCtor?: typeof WebSocket
  EventSourceCtor?: typeof EventSource
}

export type EventStreamOptions<TFrame = unknown, TSend = never> = EventStreamConfig<TFrame, TSend> &
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

export interface EventStream<TSend = never> {
  /**
   * Connect or reconnect the stream session.
   *
   * A manual `connect()` call starts a fresh session and resets deduplication
   * and sequence tracking state. In contrast, automatic reconnects preserve
   * tracking state so that message deduplication and gap detection function
   * across transient disconnects.
   */
  connect(): void
  dispose(): void
  /**
   * Send a payload across the stream.
   *
   * @param payload - Outbound frame data to serialize and transmit.
   * @returns true if the payload was handed to an open WebSocket; false if
   *   the stream uses SSE, no connection is active, or the socket is not in OPEN state.
   */
  send(payload: TSend): boolean
  readonly healthy: boolean
}

const DEFAULT_BASE_DELAY_MS = 1000
const DEFAULT_MAX_DELAY_MS = 10_000
const DEFAULT_DEDUP_WINDOW = 1024
const DEFAULT_MAX_TRACKED_STREAMS = 256
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
export function createEventStream<TFrame = unknown, TSend = never>(options: EventStreamOptions<TFrame, TSend>): EventStream<TSend> {
  const {
    transport = "websocket",
    sseEvents = DEFAULT_SSE_EVENTS,
    onEvent,
    onOpen,
    onClose,
    onHealthChange,
    onReconnect,
    onGap,
    onStale,
    shouldReconnect = (closeCode) => closeCode !== 1000,
    isHeartbeat = () => false,
    getEventKey = () => undefined,
    getSequence = () => undefined,
    baseDelayMs = DEFAULT_BASE_DELAY_MS,
    maxDelayMs = DEFAULT_MAX_DELAY_MS,
    dedupWindow = DEFAULT_DEDUP_WINDOW,
    heartbeatTimeoutMs = 0,
    heartbeatIntervalMs = heartbeatTimeoutMs > 0 ? Math.max(1000, Math.floor(heartbeatTimeoutMs / 2)) : 1000,
    maxTrackedStreams = DEFAULT_MAX_TRACKED_STREAMS,
    parseFrame = defaultParseFrame as (data: string) => TFrame,
    serializeFrame = JSON.stringify as (payload: TSend) => string,
  } = options

  let connection: WebSocket | EventSource | null = null
  let attempt = 0
  let timer: ReturnType<typeof setTimeout> | null = null
  let watchdog: ReturnType<typeof setInterval> | null = null
  let lastFrameAt = 0
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

  function clearWatchdog(): void {
    if (watchdog !== null) {
      clearInterval(watchdog)
      watchdog = null
    }
  }

  function closeCurrentConnection(): void {
    clearWatchdog()
    const current = connection
    connection = null
    if (current !== null) {
      current.close()
    }
  }

  function armWatchdog(): void {
    if (heartbeatTimeoutMs <= 0) {
      return
    }
    clearWatchdog()
    lastFrameAt = Date.now()
    watchdog = setInterval(() => {
      if (Date.now() - lastFrameAt >= heartbeatTimeoutMs) {
        onStale?.()
        emitHealth(false)
        clearWatchdog()
        closeCurrentConnection()
        if (!disposed) {
          scheduleReconnect()
        }
      }
    }, heartbeatIntervalMs)
  }

  function resetTracking(): void {
    sequenceByStream.clear()
    seenKeySet.clear()
    seenKeys.length = 0
  }

  function evictOldestTrackedStreams(): void {
    while (sequenceByStream.size > maxTrackedStreams) {
      const oldest = sequenceByStream.keys().next().value
      if (oldest === undefined) {
        break
      }
      sequenceByStream.delete(oldest)
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
    armWatchdog()
  }

  function handleMessage(event: MessageEvent): void {
    lastFrameAt = Date.now()
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
        evictOldestTrackedStreams()
      } else if (sequence.value > last) {
        sequenceByStream.set(sequence.stream, sequence.value)
        evictOldestTrackedStreams()
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
    closeCurrentConnection()
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
      clearWatchdog()
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
    closeCurrentConnection()
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
      clearWatchdog()
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
      resetTracking()
      open()
    },
    dispose(): void {
      disposed = true
      clearTimer()
      clearWatchdog()
      resetTracking()
      const current = connection
      connection = null
      if (current !== null) {
        onClose?.()
        emitHealth(false)
        current.close()
      }
    },
    send(payload: TSend): boolean {
      const current = connection
      if (disposed || current === null || transport === "sse" || !("send" in current)) {
        return false
      }
      const socket = current as WebSocket
      // Numeric readyState 1 corresponds to WebSocket.OPEN without requiring global WebSocket
      if (socket.readyState !== 1) {
        return false
      }
      socket.send(serializeFrame(payload))
      return true
    },
    get healthy(): boolean {
      return lastHealthy ?? false
    },
  }
}
