=======
Polling
=======

Refresh page data on an interval for live updates.

.. seealso::
   Official Inertia.js docs: `Polling <https://inertiajs.com/docs/v2/data-props/polling>`_

What Is Polling?
----------------

Polling lets the client automatically refresh data on a timer. This is useful
for dashboards, notifications, and live metrics without WebSockets.

Frontend Usage
--------------

.. tab-set::

   .. tab-item:: React

      .. code-block:: tsx

         import { usePoll } from "@inertiajs/react";

         export default function Dashboard() {
           usePoll(
             5000,
             { only: ["stats"] },
             { keepAlive: true }
           );

           return <StatsPanel />;
         }

   .. tab-item:: Vue

      .. code-block:: vue

         <script setup lang="ts">
         import { usePoll } from "@inertiajs/vue3";

         usePoll(5000, { only: ["stats"] }, { keepAlive: true });
         </script>

         <template>
           <StatsPanel />
         </template>

Manual Start/Stop
-----------------

Disable auto-start and control polling manually:

.. tab-set::

   .. tab-item:: React

      .. code-block:: tsx

         import { usePoll } from "@inertiajs/react";

         const poll = usePoll(2000, {}, { autoStart: false });

         poll.start();
         poll.stop();

   .. tab-item:: Vue

      .. code-block:: vue

         <script setup lang="ts">
         import { usePoll } from "@inertiajs/vue3";

         const poll = usePoll(2000, {}, { autoStart: false });

        poll.start();
        poll.stop();
        </script>

Auto-Throttling
---------------

Polling is throttled when the page is in the background to reduce resource
usage. Set ``keepAlive`` to ``true`` to disable background throttling.

Backend Considerations
----------------------

No server changes are required. Consider using partial reloads (``only`` or
``except``) to keep polling responses small.

See Also
--------

- :doc:`partial-reloads` - Limit polling payloads
- :doc:`prefetching` - Preload data before visits
- :doc:`remembering-state` - Preserve UI state across visits
