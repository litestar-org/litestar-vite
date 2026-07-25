export interface StreamGap {
  stream: string
  from: number
  to: number
  missing: number
}

export interface EventStreamOptions<TFrame = unknown> {
  buildUrl: () => string
  onEvent: (frame: TFrame) => void
  onHealthChange?: (healthy: boolean) => void
  shouldReconnect?: (closeCode: number) => boolean
  baseDelayMs?: number
  maxDelayMs?: number
  WebSocketCtor?: typeof WebSocket
}

export interface EventStream {
  connect(): void
  dispose(): void
  readonly healthy: boolean
}

const DEFAULT_BASE_DELAY_MS = 1000
const DEFAULT_MAX_DELAY_MS = 10_000

export function createEventStream<TFrame = unknown>(options: EventStreamOptions<TFrame>): EventStream {
  const { buildUrl, onEvent, onHealthChange, shouldReconnect = (closeCode) => closeCode !== 1000, baseDelayMs = DEFAULT_BASE_DELAY_MS, maxDelayMs = DEFAULT_MAX_DELAY_MS } = options

  let socket: WebSocket | null = null
  let attempt = 0
  let timer: ReturnType<typeof setTimeout> | null = null
  let disposed = false
  let lastHealthy: boolean | null = null

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

  function open(): void {
    if (disposed || typeof window === "undefined") {
      return
    }

    const WebSocketCtor = options.WebSocketCtor ?? window.WebSocket
    const next = new WebSocketCtor(buildUrl())
    socket = next

    next.addEventListener("open", () => {
      attempt = 0
      clearTimer()
      emitHealth(true)
    })
    next.addEventListener("message", (event) => {
      onEvent(JSON.parse(String(event.data)) as TFrame)
    })
    next.addEventListener("close", (event) => {
      if (socket !== next) {
        return
      }
      socket = null
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
      const current = socket
      socket = null
      current?.close()
    },
    get healthy(): boolean {
      return lastHealthy ?? false
    },
  }
}
