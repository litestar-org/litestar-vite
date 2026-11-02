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
import { wsRoute } from "./generated/routes";
import { createTypedChannels } from "./generated/channels";

const socket = new WebSocket(wsRoute("notifications:ws"));
const channels = createTypedChannels(socket);

const unsubscribe = channels.on("ws__notifications", "OrderCreated", (payload) => {
  console.log(`Order ${payload.orderId}: $${payload.amountCents / 100}`);
});
```

---

## 3. Reactive Framework Hooks (`useEventStream` & `useWsChannel`)

For declarative UI components, import the reactive SSE and WebSocket composables from `litestar-vite-plugin/{react,vue,svelte}`:

=== "React (`litestar-vite-plugin/react`)"

    ```tsx title="src/components/LiveOrders.tsx"
    import { useEventStream } from "litestar-vite-plugin/react";

    interface OrderEvent {
      orderId: string;
      amountCents: number;
    }

    export function LiveOrders() {
      const { data, status, close } = useEventStream<OrderEvent>("/api/orders/stream");

      return (
        <div>
          <span>Stream status: {status}</span>
          {data && <p>Latest order: {data.orderId}</p>}
          <button onClick={close}>Disconnect</button>
        </div>
      );
    }
    ```

=== "Vue 3 (`litestar-vite-plugin/vue`)"

    ```vue title="src/components/LiveOrders.vue"
    <script setup lang="ts">
    import { useEventStream } from "litestar-vite-plugin/vue";

    const { data, status, close } = useEventStream<{ orderId: string }>("/api/orders/stream");
    </script>

    <template>
      <div>
        <span>Stream status: {{ status }}</span>
        <p v-if="data">Latest order: {{ data.orderId }}</p>
        <button @click="close">Disconnect</button>
      </div>
    </template>
    ```

=== "Svelte 5 (`litestar-vite-plugin/svelte`)"

    ```typescript title="src/lib/ordersStream.ts"
    import { createEventStreamStore } from "litestar-vite-plugin/svelte";

    export const ordersStream = createEventStreamStore<{ orderId: string }>(
      "/api/orders/stream",
    );
    ```
