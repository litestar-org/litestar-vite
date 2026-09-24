====================
UI Frameworks
====================

``litestar-vite-plugin`` provides dedicated reactive primitives for React, Vue 3, and Svelte 5 to seamlessly bind UI state to server-driven realtime streams without manual event listener wiring or memory leaks.

React: ``useQueueEventStream``
------------------------------

In React applications, ``useQueueEventStream`` manages background task tracking with state updates and automatic cleanup:

.. code-block:: tsx

   import { useQueueEventStream } from "litestar-vite-plugin/react";

   interface ProcessingStatus {
     percentage: number;
     status: string;
   }

   export function JobTracker({ jobId }: { jobId: string }) {
     const { healthy, lastEvent } = useQueueEventStream<ProcessingStatus>({
       key: `job-${jobId}`,
       scope: "task",
       taskId: jobId,
       onEvent: (event: ProcessingStatus) => {
         console.log("Job update:", event);
       },
     });

     if (!healthy) {
       return <div className="text-yellow-500">Connecting to job feed...</div>;
     }

     return (
       <div className="p-4 border rounded">
         <h3 className="font-bold">Job Status: {lastEvent?.status ?? "Initializing"}</h3>
         {lastEvent && (
           <div className="mt-2">
             <div className="w-full bg-gray-200 h-2 rounded">
               <div
                 className="bg-blue-600 h-2 rounded transition-all"
                 style={{ width: `${lastEvent.percentage}%` }}
               />
             </div>
             <p className="text-sm mt-1">{lastEvent.status} ({lastEvent.percentage}%)</p>
           </div>
         )}
         {lastEvent?.percentage === 100 && <p className="text-green-600 mt-2">Processing finished!</p>}
       </div>
     );
   }

The hook automatically tears down event listeners and disconnects the underlying transport when the component unmounts or when ``jobId`` changes.

Vue 3: ``useEventStream``
-------------------------

In Vue 3, ``useEventStream`` returns reactive ``ref`` values that update as events stream in from the server:

.. code-block:: vue

   <script setup lang="ts">
   import { useEventStream } from "litestar-vite-plugin/vue";

   interface MarketQuote {
     ticker: string;
     price: number;
     change: number;
   }

   const { healthy, lastEvent } = useEventStream<MarketQuote>({
     key: "market-feed",
     url: "/api/market/feed",
     transport: "sse",
     sseEvents: ["quote"],
     onEvent: (quote: MarketQuote) => {
       console.log("Received quote:", quote);
     },
   });
   </script>

   <template>
     <div class="market-card">
       <h2>Live Market Ticker ({{ healthy ? "Connected" : "Disconnected" }})</h2>
       <div v-if="lastEvent" class="quote">
         <span class="ticker">{{ lastEvent.ticker }}</span>
         <span class="price">${{ lastEvent.price.toFixed(2) }}</span>
         <span :class="lastEvent.change >= 0 ? 'up' : 'down'">
           {{ lastEvent.change >= 0 ? '+' : '' }}{{ lastEvent.change.toFixed(2) }}%
         </span>
       </div>
       <div v-else>Connecting to feed...</div>
     </div>
   </template>

The composable hooks into Vue's ``onScopeDispose()`` lifecycle to clean up the stream when the component unmounts.

Svelte 5: ``createEventStreamStore``
------------------------------------

In Svelte applications, ``createEventStreamStore`` returns a subscription store compatible with Svelte's auto-subscription syntax (``$store``) or Svelte 5 runes:

.. code-block:: svelte

   <script lang="ts">
     import { createEventStreamStore } from "litestar-vite-plugin/svelte";

     interface Notification {
       id: string;
       title: string;
       body: string;
     }

     const notifications = createEventStreamStore<Notification>({
       url: "/api/notifications/stream",
       onEvent: (item: Notification) => {
         console.log("New notification:", item);
       },
     });
   </script>

   <div class="notifications-panel">
     <h3>Notifications ({$notifications.events.length})</h3>
     <ul>
       {#each $notifications.events as item (item.id)}
         <li>
           <strong>{item.title}</strong>
           <p>{item.body}</p>
         </li>
       {/each}
     </ul>
   </div>

Next Steps
----------

- Review the full API reference: :doc:`../reference/index`
- Explore the Inertia.js integration guides: :doc:`../frameworks/inertia/index`
