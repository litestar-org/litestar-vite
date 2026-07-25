export interface StreamGap {
  stream: string
  from: number
  to: number
  missing: number
}

export interface EventStreamOptions<TFrame = unknown> {
  buildUrl: () => string
  transport?: "websocket" | "sse"
  sseEvents?: readonly string[]
  onEvent: (frame: TFrame) => void
  onHealthChange?: (healthy: boolean) => void
  shouldReconnect?: (closeCode: number) => boolean
  isHeartbeat?: (frame: TFrame) => boolean
  getEventKey?: (frame: TFrame) => string | undefined
  baseDelayMs?: number
  maxDelayMs?: number
  dedupWindow?: number
  WebSocketCtor?: typeof WebSocket
  EventSourceCtor?: typeof EventSource
}

export interface EventStream {
  connect(): void
  dispose(): void
  readonly healthy: boolean
}

const DEFAULT_BASE_DELAY_MS = 1000
const DEFAULT_MAX_DELAY_MS = 10_000
const DEFAULT_DEDUP_WINDOW = 1024
const DEFAULT_SSE_EVENTS = [
  "task.started",
  "task.progress",
  "task.log",
  "task.event",
  "task.completed",
  "task.failed",
  "task.cancelled",
  "task.claim_lost",
  "task.stale_failed",
  "worker.heartbeat",
  "worker.stale_recovery",
] as const

function asRecord(value: unknown): Record<string, unknown> | undefined {
  return typeof value === "object" && value !== null ? (value as Record<string, unknown>) : undefined
}

function defaultIsHeartbeat(frame: unknown): boolean {
  return asRecord(frame)?.type === "ping"
}

function defaultGetEventKey(frame: unknown): string | undefined {
  const record = asRecord(frame)
  const key = record?.eventKey ?? record?.id
  return typeof key === "string" ? key : undefined
}

export function createEventStream<TFrame = unknown>(options: EventStreamOptions<TFrame>): EventStream {
  const {
    buildUrl,
    transport = "websocket",
    sseEvents = DEFAULT_SSE_EVENTS,
    onEvent,
    onHealthChange,
    shouldReconnect = (closeCode) => closeCode !== 1000,
    isHeartbeat = defaultIsHeartbeat,
    getEventKey = defaultGetEventKey,
    baseDelayMs = DEFAULT_BASE_DELAY_MS,
    maxDelayMs = DEFAULT_MAX_DELAY_MS,
    dedupWindow = DEFAULT_DEDUP_WINDOW,
  } = options

  let connection: WebSocket | EventSource | null = null
  let attempt = 0
  let timer: ReturnType<typeof setTimeout> | null = null
  let disposed = false
  let lastHealthy: boolean | null = null
  const seenKeys: string[] = []
  const seenKeySet = new Set<string>()

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

  function handleOpen(): void {
    attempt = 0
    clearTimer()
    emitHealth(true)
  }

  function handleMessage(event: MessageEvent): void {
    const frame = JSON.parse(String(event.data)) as TFrame
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

    onEvent(frame)
  }

  function openWebSocket(): void {
    const WebSocketCtor = options.WebSocketCtor ?? window.WebSocket
    const next = new WebSocketCtor(buildUrl())
    connection = next
    next.addEventListener("open", () => {
      handleOpen()
    })
    next.addEventListener("message", (event) => {
      handleMessage(event)
    })
    next.addEventListener("close", (event) => {
      if (connection !== next) {
        return
      }
      connection = null
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
    const next = new EventSourceCtor(buildUrl())
    connection = next
    next.addEventListener("open", () => {
      handleOpen()
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
      current?.close()
    },
    get healthy(): boolean {
      return lastHealthy ?? false
    },
  }
}
