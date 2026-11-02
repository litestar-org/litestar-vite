# AsyncAPI & Realtime Channels (`channels.ts`)

When your Litestar application registers `litestar-asyncapi`'s `AsyncAPIPlugin` (for WebSockets, `ChannelsPlugin`, or Server-Sent Events), `litestar-vite` automatically extracts and normalizes the AsyncAPI 3.0 document into `src/generated/asyncapi.json` and generates a zero-dependency typed WebSocket client in `src/generated/channels.ts`.

---

## 1. AsyncAPI Normalization & `TypeGenConfig`

`litestar_vite.codegen.normalize_asyncapi_document()` normalizes AsyncAPI 3.0 channel addresses, collision-safe channel keys, and JSON Schema message payloads:

```python title="docs/examples/typegen/asyncapi_channels.py"
--8<-- "docs/examples/typegen/asyncapi_channels.py"
```

---

## 2. Using `createTypedChannels()` in TypeScript

`src/generated/channels.ts` exports `createTypedChannels()`, which wraps any standard `WebSocket` (or custom transport) with strongly typed `subscribe()`, `send()`, and `onMessage()` methods keyed by channel name and message type:

```typescript title="src/realtime.ts"
import { createTypedChannels } from "litestar-vite-plugin/helpers";
import { CHANNEL_METADATA, type RealtimeChannels } from "./generated/channels";

const channels = createTypedChannels<RealtimeChannels>(CHANNEL_METADATA);
const stream = channels.stream("ws__notifications", {
  onEvent: (payload: { orderId: string; amountCents: number }) => {
    console.log(payload.orderId);
  },
});
```

---

## 3. Reactive Framework Hooks (`useEventStream` & `createEventStreamStore`)

For declarative UI components, import the reactive SSE composables from `litestar-vite-plugin/{react,vue,svelte}`:

=== "React (`litestar-vite-plugin/react`)"

    ```tsx title="src/components/LiveOrders.tsx"
    import { useEventStream } from "litestar-vite-plugin/react";

    interface OrderEvent {
      orderId: string;
      amountCents: number;
    }

    export function LiveOrders() {
      const { healthy, lastEvent, events } = useEventStream<OrderEvent>({
        key: "orders",
        url: "/api/orders/stream",
        onEvent: () => {},
      });

      return (
        <div>
          <span>Stream healthy: {String(healthy)}</span>
          {lastEvent && <p>Latest order: {lastEvent.orderId} ({events.length} total)</p>}
        </div>
      );
    }
    ```

=== "Vue 3 (`litestar-vite-plugin/vue`)"

    ```vue title="src/components/LiveOrders.vue"
    <script setup lang="ts">
    import { useEventStream } from "litestar-vite-plugin/vue";

    const { healthy, lastEvent } = useEventStream<{ orderId: string }>({
      key: "orders",
      url: "/api/orders/stream",
      onEvent: () => {},
    });
    </script>

    <template>
      <div>
        <span>Stream healthy: {{ healthy }}</span>
        <p v-if="lastEvent">Latest order: {{ lastEvent.orderId }}</p>
      </div>
    </template>
    ```

=== "Svelte 5 (`litestar-vite-plugin/svelte`)"

    ```typescript title="src/lib/ordersStream.ts"
    import { createEventStreamStore } from "litestar-vite-plugin/svelte";

    export const ordersStream = createEventStreamStore<{ orderId: string }>({
      url: "/api/orders/stream",
      onEvent: () => {},
    });
    ```
