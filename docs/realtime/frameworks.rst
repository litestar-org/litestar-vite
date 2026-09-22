====================
UI Frameworks
====================

``litestar-vite-plugin`` provides dedicated reactive primitives for React, Vue 3, and Svelte 5 to seamlessly bind UI state to server-driven realtime streams without manual event listener wiring or memory leaks.

React: ``useQueueEventStream``
------------------------------

In React applications, ``useQueueEventStream`` manages background task tracking with state updates and automatic cleanup:

.. code-block:: tsx

   import React from "react";
   import { useQueueEventStream } from "litestar-vite-plugin/react";

   interface ProcessingStatus {
     percentage: number;
     status: string;
   }

   export function JobTracker({ jobId }: { jobId: string }) {
     const { data, status, error, isComplete } = useQueueEventStream<ProcessingStatus>({
       taskId: jobId,
       url: `/api/jobs/${jobId}/events`,
     });

     if (error) {
       return <div className="text-red-500">Error: {error.message}</div>;
     }

     return (
       <div className="p-4 border rounded">
         <h3 className="font-bold">Job Status: {status}</h3>
         {data && (
           <div className="mt-2">
             <div className="w-full bg-gray-200 h-2 rounded">
               <div
                 className="bg-blue-600 h-2 rounded transition-all"
                 style={{ width: `${data.percentage}%` }}
               />
             </div>
             <p className="text-sm mt-1">{data.status} ({data.percentage}%)</p>
           </div>
         )}
         {isComplete && <p className="text-green-600 mt-2">Processing finished!</p>}
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

   const { data, status, error, close } = useEventStream<MarketQuote>({
     url: "/api/market/feed",
     sseEvents: ["quote"],
   });
   </script>

   <template>
     <div class="market-card">
       <h2>Live Market Ticker ({{ status }})</h2>
       <div v-if="error" class="error">{{ error.message }}</div>
       <div v-else-if="data" class="quote">
         <span class="ticker">{{ data.ticker }}</span>
         <span class="price">${{ data.price.toFixed(2) }}</span>
         <span :class="data.change >= 0 ? 'up' : 'down'">
           {{ data.change >= 0 ? '+' : '' }}{{ data.change.toFixed(2) }}%
         </span>
       </div>
       <div v-else>Connecting to feed...</div>
     </div>
   </template>

The composable hooks into Vue's ``onScopeDispose()`` lifecycle to close the stream when the component unmounts.

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

     const notifications = createEventStreamStore<Notification[]>({
       url: "/api/notifications/stream",
       initialData: [],
     });
   </script>

   <div class="notifications-panel">
     <h3>Notifications ({$notifications.data.length})</h3>
     <ul>
       {#each $notifications.data as item (item.id)}
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
