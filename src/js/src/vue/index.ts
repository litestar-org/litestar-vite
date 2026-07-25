/**
 * Vue bindings for generic and Litestar Queues event streams.
 *
 * @module
 */

import { createEventStream, createQueueEventStream, type EventStream, type EventStreamOptions, type QueueEventStreamOptions, type StreamGap } from "litestar-vite-plugin/helpers"
import { onMounted, onScopeDispose, ref, shallowRef, toValue, watch, type MaybeRefOrGetter, type Ref, type ShallowRef } from "vue"

export interface VueEventStreamState<TFrame> {
  healthy: Ref<boolean>
  lastEvent: ShallowRef<TFrame | null>
  lastGap: ShallowRef<StreamGap | null>
  events: ShallowRef<TFrame[]>
}

export type VueEventStreamOptions<TFrame> = EventStreamOptions<TFrame> & {
  key: MaybeRefOrGetter<string>
  bufferSize?: number
}

export type VueQueueEventStreamOptions<TFrame> = QueueEventStreamOptions<TFrame> & {
  key: MaybeRefOrGetter<string>
  bufferSize?: number
}

type AdapterOptions<TFrame> = VueEventStreamOptions<TFrame> | VueQueueEventStreamOptions<TFrame>
type StreamFactory = (options: never) => EventStream

function useStream<TFrame>(factory: StreamFactory, options: AdapterOptions<TFrame>): VueEventStreamState<TFrame> {
  const healthy = ref(false)
  const lastEvent = shallowRef<TFrame | null>(null)
  const lastGap = shallowRef<StreamGap | null>(null)
  const events = shallowRef<TFrame[]>([])
  let stream: EventStream | null = null

  const stop = (): void => {
    stream?.dispose()
    stream = null
  }

  const start = (): void => {
    stop()
    healthy.value = false
    const { bufferSize: _bufferSize, key: _key, ...streamOptions } = options
    stream = factory({
      ...streamOptions,
      onEvent: (frame: TFrame) => {
        options.onEvent(frame)
        lastEvent.value = frame
        const bufferSize = Math.max(0, options.bufferSize ?? 100)
        events.value = bufferSize === 0 ? [] : [...events.value, frame].slice(-bufferSize)
      },
      onGap: (gap: StreamGap) => {
        options.onGap?.(gap)
        lastGap.value = gap
      },
      onHealthChange: (value: boolean) => {
        options.onHealthChange?.(value)
        healthy.value = value
      },
    } as never)
    stream.connect()
  }

  onMounted(start)
  watch(
    () => [toValue(options.key), options.transport ?? "websocket"] as const,
    () => start(),
  )
  onScopeDispose(stop)

  return { events, healthy, lastEvent, lastGap }
}

/**
 * Subscribe a Vue scope to a generic event stream.
 */
export function useEventStream<TFrame = unknown>(options: VueEventStreamOptions<TFrame>): VueEventStreamState<TFrame> {
  return useStream(createEventStream as StreamFactory, options)
}

/**
 * Subscribe a Vue scope to a Litestar Queues event stream.
 */
export function useQueueEventStream<TFrame = unknown>(options: VueQueueEventStreamOptions<TFrame>): VueEventStreamState<TFrame> {
  return useStream(createQueueEventStream as StreamFactory, options)
}
