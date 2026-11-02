# Browser & Framework Event Streams

The `litestar-vite-plugin` package provides a zero-dependency event stream runtime across Server-Sent Events (`EventSource`), WebSockets, and `ChannelsPlugin` streams — with reactive adapters for **React**, **Vue 3**, **Svelte 5**, and **HTMX / Jinja**.

---

## Browser Stream Primitives

Import the core stream factories from `litestar-vite-plugin/helpers`:

| Helper | Purpose |
| --- | --- |
| [`createEventStream`](../reference/typescript/helpers.md) | Managed SSE (`EventSource`) or WebSocket connection with exponential backoff, jitter, `Last-Event-ID` sequence tracking, gap detection (`onGap`), and bounded ring buffer (`maxEvents`). |
| [`createChannelsStream`](../reference/typescript/helpers.md) | Connects to a Litestar `ChannelsPlugin` WebSocket route (`{basePath}/{channel}`) using `createEventStream`. |
| [`createQueueEventStream`](../reference/typescript/helpers.md) | Pre-configured SSE or WebSocket stream for `litestar-queues` background task events (`"all"`, `"queue"`, or `"task"` scope). |

```typescript title="src/streams.ts"
import {
  createChannelsStream,
  createEventStream,
  createQueueEventStream,
} from "litestar-vite-plugin/helpers";

// 1. Managed SSE or WebSocket stream with gap detection
const orderStream = createEventStream<{ orderId: string; status: string }>({
  url: "/api/orders/stream",
  onEvent: (frame) => {
    console.log("Order:", frame.orderId, "Status:", frame.status);
  },
  onGap: ({ stream, from, to, missing }) => {
    console.warn(`Stream ${stream} missed ${missing} events (${from}..${to})`);
  },
});

// 2. Litestar ChannelsPlugin WebSocket stream
const roomStream = createChannelsStream<{ user: string; text: string }>({
  basePath: "/ws",
  channel: "chat_general",
  onEvent: (frame) => {
    console.log(frame.user, frame.text);
  },
});

// 3. Background queue task status stream
const taskStream = createQueueEventStream({
  scope: "task",
  taskId: "task-9812",
  transport: "sse",
  onEvent: (frame) => {
    console.log("Task frame:", frame);
  },
});
```

---

## Reactive Framework Hooks

Import framework-native wrappers from `litestar-vite-plugin/{react,vue,svelte}` that automatically manage subscription lifecycles on component mount and unmount:

=== "React"

    ```tsx title="src/components/LiveOrders.tsx"
    import { useEventStream, useQueueEventStream } from "litestar-vite-plugin/react";

    export function LiveOrders({ taskId }: { taskId: string }) {
      const orders = useEventStream<{ orderId: string }>({
        key: "orders-stream",
        url: "/api/orders/stream",
        onEvent: (frame) => console.log("Order:", frame.orderId),
      });
      const job = useQueueEventStream({
        key: `task-${taskId}`,
        scope: "task",
        taskId,
        onEvent: (frame) => console.log("Queue task:", frame),
      });

      return (
        <p>
          Orders healthy: {String(orders.healthy)} · Task healthy: {String(job.healthy)}
        </p>
      );
    }
    ```

=== "Vue 3"

    ```vue title="src/components/LiveOrders.vue"
    <script setup lang="ts">
    import { useEventStream, useQueueEventStream } from "litestar-vite-plugin/vue";

    const props = defineProps<{ taskId: string }>();
    const { healthy, lastEvent } = useEventStream<{ orderId: string }>({
      key: "orders-stream",
      url: "/api/orders/stream",
      onEvent: (frame) => console.log("Order:", frame.orderId),
    });
    const job = useQueueEventStream({
      key: () => `task-${props.taskId}`,
      scope: "task",
      taskId: () => props.taskId,
      onEvent: (frame) => console.log("Queue task:", frame),
    });
    </script>

    <template>
      <p>Orders: {{ lastEvent?.orderId }} (healthy: {{ healthy }} · task: {{ job.healthy.value }})</p>
    </template>
    ```

=== "Svelte 5"

    ```svelte title="src/components/LiveOrders.svelte"
    <script lang="ts">
      import { createEventStreamStore, createQueueEventStreamStore } from "litestar-vite-plugin/svelte";

      let { taskId }: { taskId: string } = $props();
      const orders = createEventStreamStore<{ orderId: string }>({
        url: "/api/orders/stream",
        onEvent: (frame) => console.log("Order:", frame.orderId),
      });
      const job = createQueueEventStreamStore({
        scope: "task",
        taskId,
        onEvent: (frame) => console.log("Queue task:", frame),
      });
    </script>

    <p>Orders healthy: {$orders.healthy} · Task healthy: {$job.healthy}</p>
    ```

---

## Declarative Stream Custom Element

For server-rendered Jinja2 and HTMX pages, call `defineStreamElement()` once in your entrypoint and use `<litestar-stream>` with a `<template>` child to render incoming JSON events without writing imperative JavaScript:

```html title="templates/dashboard.html.j2"
<script type="module">
  import { defineStreamElement, registerHtmxExtension } from "litestar-vite-plugin/helpers";
  registerHtmxExtension();
  defineStreamElement();
</script>

<litestar-stream
  url="/api/orders/stream"
  target="#orders-feed"
  swap="json"
  max-events="50"
>
  <template>
    <div class="order-row">
      <strong ls-text="$data.orderId"></strong>:
      <span ls-text="$data.status"></span>
    </div>
  </template>
</litestar-stream>

<div id="orders-feed"></div>
```

- **Queue Preset (`preset="queues"`)**: `<litestar-stream preset="queues" scope="task" task-id="123" target="#job-status">` connects to `/queues/events/tasks/123` automatically.
- **Lifecycle DOM Events**: Dispatches bubbling `litestar:stream-event`, `litestar:stream-health`, `litestar:stream-gap`, `litestar:stream-open`, and `litestar:stream-close` custom events.
- **Avoid Duplicate Transports**: Do not attach HTMX's `hx-ext="ws"` or `hx-ext="sse"` to the same element managed by `<litestar-stream>`.

---

## Authentication, Reconnection & Replay

### Rotating Signed Tickets

Browser `EventSource` and `WebSocket` constructors cannot send custom `Authorization: Bearer ...` headers across origins. When you cannot use same-origin `HttpOnly` session cookies, pass an async or sync `buildUrl` callback so every reconnect fetches or signs a fresh short-lived ticket:

```typescript
import { createEventStream } from "litestar-vite-plugin/helpers";

declare function currentTicket(): string;

const stream = createEventStream({
  buildUrl: () => `/ws/notifications?ticket=${encodeURIComponent(currentTicket())}`,
  onEvent: (frame) => {
    console.log("Notification:", frame);
  },
  shouldReconnect: (closeCode) => {
    // Do not retry on 4003 Forbidden; allow reconnect on 4001 Expired Ticket
    return closeCode !== 4003;
  },
});
```

### Sequence Tracking & Replay Recovery

When the server includes monotonic `seq` numbers (or SSE `id:` fields) and backs `ChannelsPlugin` with `MemoryChannelsBackend(history=200)` or `RedisChannelsStreamBackend`, `createEventStream` tracks `lastSeq` automatically and fires `onGap({ stream, from, to, missing })` if a sequence jump is detected.
