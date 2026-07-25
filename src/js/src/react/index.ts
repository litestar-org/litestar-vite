/**
 * React bindings for generic and Litestar Queues event streams.
 *
 * @module
 */

import { createEventStream, createQueueEventStream, type EventStream, type EventStreamOptions, type QueueEventStreamOptions, type StreamGap } from "litestar-vite-plugin/helpers"
import { useEffect, useRef, useState } from "react"

export interface EventStreamState<TFrame> {
  healthy: boolean
  lastEvent: TFrame | null
  lastGap: StreamGap | null
  events: TFrame[]
}

export type ReactEventStreamOptions<TFrame> = EventStreamOptions<TFrame> & {
  key: string
  bufferSize?: number
}

export type ReactQueueEventStreamOptions<TFrame> = QueueEventStreamOptions<TFrame> & {
  key: string
  bufferSize?: number
}

type AdapterOptions<TFrame> = ReactEventStreamOptions<TFrame> | ReactQueueEventStreamOptions<TFrame>
type StreamFactory = (options: never) => EventStream

function initialState<TFrame>(): EventStreamState<TFrame> {
  return { events: [], healthy: false, lastEvent: null, lastGap: null }
}

function useStream<TFrame>(factory: StreamFactory, options: AdapterOptions<TFrame>): EventStreamState<TFrame> {
  const optionsRef = useRef(options)
  optionsRef.current = options
  const [state, setState] = useState<EventStreamState<TFrame>>(initialState)
  const transport = options.transport ?? "websocket"

  useEffect(() => {
    setState(initialState)
    const { bufferSize: _bufferSize, key: _key, ...streamOptions } = optionsRef.current
    const stream = factory({
      ...streamOptions,
      onEvent: (frame: TFrame) => {
        optionsRef.current.onEvent(frame)
        setState((current) => {
          const bufferSize = Math.max(0, optionsRef.current.bufferSize ?? 100)
          const events = bufferSize === 0 ? [] : [...current.events, frame].slice(-bufferSize)
          return { ...current, events, lastEvent: frame }
        })
      },
      onGap: (gap: StreamGap) => {
        optionsRef.current.onGap?.(gap)
        setState((current) => ({ ...current, lastGap: gap }))
      },
      onHealthChange: (healthy: boolean) => {
        optionsRef.current.onHealthChange?.(healthy)
        setState((current) => ({ ...current, healthy }))
      },
    } as never)
    stream.connect()
    return () => stream.dispose()
  }, [factory, options.key, transport])

  return state
}

/**
 * Subscribe a React component to a generic event stream.
 */
export function useEventStream<TFrame = unknown>(options: ReactEventStreamOptions<TFrame>): EventStreamState<TFrame> {
  return useStream(createEventStream as StreamFactory, options)
}

/**
 * Subscribe a React component to a Litestar Queues event stream.
 */
export function useQueueEventStream<TFrame = unknown>(options: ReactQueueEventStreamOptions<TFrame>): EventStreamState<TFrame> {
  return useStream(createQueueEventStream as StreamFactory, options)
}
