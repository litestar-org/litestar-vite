/**
 * Svelte stores for generic and Litestar Queues event streams.
 *
 * @module
 */

import { createEventStream, createQueueEventStream, type EventStream, type EventStreamOptions, type QueueEventStreamOptions, type StreamGap } from "litestar-vite-plugin/helpers"
import { readable, type Readable } from "svelte/store"

export interface EventStreamStoreState<TFrame> {
  healthy: boolean
  lastEvent: TFrame | null
  lastGap: StreamGap | null
  events: TFrame[]
}

export type SvelteEventStreamOptions<TFrame> = EventStreamOptions<TFrame> & { bufferSize?: number }
export type SvelteQueueEventStreamOptions<TFrame> = QueueEventStreamOptions<TFrame> & { bufferSize?: number }

type AdapterOptions<TFrame> = SvelteEventStreamOptions<TFrame> | SvelteQueueEventStreamOptions<TFrame>
type StreamFactory = (options: never) => EventStream

function initialState<TFrame>(): EventStreamStoreState<TFrame> {
  return { events: [], healthy: false, lastEvent: null, lastGap: null }
}

function createStreamStore<TFrame>(factory: StreamFactory, options: AdapterOptions<TFrame>): Readable<EventStreamStoreState<TFrame>> {
  return readable(initialState<TFrame>(), (set) => {
    let state = initialState<TFrame>()
    const update = (next: Partial<EventStreamStoreState<TFrame>>): void => {
      state = { ...state, ...next }
      set(state)
    }
    const { bufferSize: _bufferSize, ...streamOptions } = options
    const stream = factory({
      ...streamOptions,
      onEvent: (frame: TFrame) => {
        options.onEvent(frame)
        const bufferSize = Math.max(0, options.bufferSize ?? 100)
        const events = bufferSize === 0 ? [] : [...state.events, frame].slice(-bufferSize)
        update({ events, lastEvent: frame })
      },
      onGap: (gap: StreamGap) => {
        options.onGap?.(gap)
        update({ lastGap: gap })
      },
      onHealthChange: (healthy: boolean) => {
        options.onHealthChange?.(healthy)
        update({ healthy })
      },
    } as never)
    stream.connect()
    return () => stream.dispose()
  })
}

/**
 * Create a readable store backed by a generic event stream.
 */
export function createEventStreamStore<TFrame = unknown>(options: SvelteEventStreamOptions<TFrame>): Readable<EventStreamStoreState<TFrame>> {
  return createStreamStore(createEventStream as StreamFactory, options)
}

/**
 * Create a readable store backed by a Litestar Queues event stream.
 */
export function createQueueEventStreamStore<TFrame = unknown>(options: SvelteQueueEventStreamOptions<TFrame>): Readable<EventStreamStoreState<TFrame>> {
  return createStreamStore(createQueueEventStream as StreamFactory, options)
}
