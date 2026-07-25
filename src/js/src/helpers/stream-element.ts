/**
 * Declarative lifecycle binding for JSON WebSocket and SSE streams.
 *
 * This element replaces `htmx-ext-ws` and `htmx-ext-sse` for JSON streams.
 * Do not layer both reconnect implementations on the same endpoint.
 *
 * @example
 * ```html
 * <litestar-stream url="/events" transport="sse" swap="json">
 *   <template ls-for="item in $data.items"><p>${item}</p></template>
 * </litestar-stream>
 * ```
 *
 * @module
 */

import { swapJson } from "./htmx.js"
import { createQueueEventStream } from "./queues.js"
import { createEventStream, type EventStream, type EventStreamConfig, type EventStreamTransport, type StreamGap } from "./stream.js"

type StreamCallbackConfig = Pick<
  EventStreamConfig,
  "EventSourceCtor" | "WebSocketCtor" | "getEventKey" | "getSequence" | "isHeartbeat" | "onEvent" | "onGap" | "onHealthChange" | "onReconnect" | "parseFrame" | "shouldReconnect"
>

type HTMLElementConstructor = new (...args: never[]) => HTMLElement
const HTMLElementBase = (typeof HTMLElement === "undefined" ? class {} : HTMLElement) as HTMLElementConstructor

export interface StreamElementOptions {
  tagName?: string
}

export class LitestarStreamElement extends HTMLElementBase {
  static readonly observedAttributes = ["url", "transport", "sse-events", "preset", "swap", "disabled"]

  private stream: EventStream | null = null
  private _buildUrl: (() => string | URL) | undefined
  private _onEvent: StreamCallbackConfig["onEvent"] | undefined
  private _onGap: StreamCallbackConfig["onGap"]
  private _onHealthChange: StreamCallbackConfig["onHealthChange"]
  private _onReconnect: StreamCallbackConfig["onReconnect"]
  private _shouldReconnect: StreamCallbackConfig["shouldReconnect"]
  private _isHeartbeat: StreamCallbackConfig["isHeartbeat"]
  private _getEventKey: StreamCallbackConfig["getEventKey"]
  private _getSequence: StreamCallbackConfig["getSequence"]
  private _parseFrame: StreamCallbackConfig["parseFrame"]
  private _WebSocketCtor: StreamCallbackConfig["WebSocketCtor"]
  private _EventSourceCtor: StreamCallbackConfig["EventSourceCtor"]

  constructor() {
    super()
    for (const property of [
      "buildUrl",
      "onEvent",
      "onGap",
      "onHealthChange",
      "onReconnect",
      "shouldReconnect",
      "isHeartbeat",
      "getEventKey",
      "getSequence",
      "parseFrame",
      "WebSocketCtor",
      "EventSourceCtor",
    ]) {
      this.upgradeProperty(property)
    }
  }

  get buildUrl(): (() => string | URL) | undefined {
    return this._buildUrl
  }

  set buildUrl(value: (() => string | URL) | undefined) {
    this._buildUrl = value
    this.restart()
  }

  get onEvent(): StreamCallbackConfig["onEvent"] | undefined {
    return this._onEvent
  }

  set onEvent(value: StreamCallbackConfig["onEvent"] | undefined) {
    this._onEvent = value
  }

  get onGap(): StreamCallbackConfig["onGap"] {
    return this._onGap
  }

  set onGap(value: StreamCallbackConfig["onGap"]) {
    this._onGap = value
  }

  get onHealthChange(): StreamCallbackConfig["onHealthChange"] {
    return this._onHealthChange
  }

  set onHealthChange(value: StreamCallbackConfig["onHealthChange"]) {
    this._onHealthChange = value
  }

  get onReconnect(): StreamCallbackConfig["onReconnect"] {
    return this._onReconnect
  }

  set onReconnect(value: StreamCallbackConfig["onReconnect"]) {
    this._onReconnect = value
  }

  get shouldReconnect(): StreamCallbackConfig["shouldReconnect"] {
    return this._shouldReconnect
  }

  set shouldReconnect(value: StreamCallbackConfig["shouldReconnect"]) {
    this._shouldReconnect = value
  }

  get isHeartbeat(): StreamCallbackConfig["isHeartbeat"] {
    return this._isHeartbeat
  }

  set isHeartbeat(value: StreamCallbackConfig["isHeartbeat"]) {
    this._isHeartbeat = value
  }

  get getEventKey(): StreamCallbackConfig["getEventKey"] {
    return this._getEventKey
  }

  set getEventKey(value: StreamCallbackConfig["getEventKey"]) {
    this._getEventKey = value
  }

  get getSequence(): StreamCallbackConfig["getSequence"] {
    return this._getSequence
  }

  set getSequence(value: StreamCallbackConfig["getSequence"]) {
    this._getSequence = value
  }

  get parseFrame(): StreamCallbackConfig["parseFrame"] {
    return this._parseFrame
  }

  set parseFrame(value: StreamCallbackConfig["parseFrame"]) {
    this._parseFrame = value
  }

  get WebSocketCtor(): StreamCallbackConfig["WebSocketCtor"] {
    return this._WebSocketCtor
  }

  set WebSocketCtor(value: StreamCallbackConfig["WebSocketCtor"]) {
    this._WebSocketCtor = value
  }

  get EventSourceCtor(): StreamCallbackConfig["EventSourceCtor"] {
    return this._EventSourceCtor
  }

  set EventSourceCtor(value: StreamCallbackConfig["EventSourceCtor"]) {
    this._EventSourceCtor = value
  }

  get healthy(): boolean {
    return this.stream?.healthy ?? false
  }

  connectedCallback(): void {
    this.start()
  }

  disconnectedCallback(): void {
    this.stop()
  }

  attributeChangedCallback(name: string, oldValue: string | null, newValue: string | null): void {
    if (oldValue === newValue || name === "swap") {
      return
    }
    this.restart()
  }

  private upgradeProperty(property: string): void {
    if (!Object.prototype.hasOwnProperty.call(this, property)) {
      return
    }
    const value = (this as unknown as Record<string, unknown>)[property]
    delete (this as unknown as Record<string, unknown>)[property]
    ;(this as unknown as Record<string, unknown>)[property] = value
  }

  private start(): void {
    if (!this.isConnected || this.hasAttribute("disabled") || this.stream !== null) {
      return
    }
    const url = this.getAttribute("url")
    if (this._buildUrl === undefined && url === null) {
      return
    }

    const transport = this.getAttribute("transport") === "sse" ? "sse" : "websocket"
    const sseEvents = this.getAttribute("sse-events")
      ?.split(",")
      .map((event) => event.trim())
      .filter(Boolean)
    const config = {
      EventSourceCtor: this._EventSourceCtor,
      WebSocketCtor: this._WebSocketCtor,
      getEventKey: this._getEventKey,
      getSequence: this._getSequence,
      isHeartbeat: this._isHeartbeat,
      onClose: () => this.dispatchStreamEvent("litestar:stream-close", {}),
      onEvent: (frame: unknown) => {
        this._onEvent?.(frame)
        this.dispatchStreamEvent("litestar:stream-event", frame)
        if (this.getAttribute("swap") === "json") {
          swapJson(this, frame)
        }
      },
      onGap: (gap: StreamGap) => {
        this._onGap?.(gap)
        this.dispatchStreamEvent("litestar:stream-gap", gap)
      },
      onHealthChange: (healthy: boolean) => {
        this._onHealthChange?.(healthy)
        this.dispatchStreamEvent("litestar:stream-health", { healthy })
      },
      onOpen: (resolvedUrl: string) => this.dispatchStreamEvent("litestar:stream-open", { url: resolvedUrl }),
      onReconnect: () => this._onReconnect?.(),
      parseFrame: this._parseFrame,
      shouldReconnect: this._shouldReconnect,
      sseEvents,
      transport: transport as EventStreamTransport,
    }
    const endpoint = this._buildUrl === undefined ? { url: url as string } : { buildUrl: this._buildUrl }
    this.stream = this.getAttribute("preset") === "queues" ? createQueueEventStream({ ...config, ...endpoint }) : createEventStream({ ...config, ...endpoint })
    this.stream.connect()
  }

  private stop(): void {
    const stream = this.stream
    this.stream = null
    stream?.dispose()
  }

  private restart(): void {
    if (!this.isConnected) {
      return
    }
    this.stop()
    this.start()
  }

  private dispatchStreamEvent(type: string, detail: unknown): void {
    this.dispatchEvent(new CustomEvent(type, { bubbles: true, composed: false, detail }))
  }
}

/**
 * Register the declarative stream element.
 *
 * @param options - Optional custom tag name.
 */
export function defineStreamElement(options: StreamElementOptions = {}): void {
  if (typeof window === "undefined" || typeof customElements === "undefined") {
    return
  }
  const tagName = options.tagName ?? "litestar-stream"
  if (customElements.get(tagName) !== undefined) {
    return
  }
  const ElementClass = tagName === "litestar-stream" ? LitestarStreamElement : class extends LitestarStreamElement {}
  customElements.define(tagName, ElementClass)
}
