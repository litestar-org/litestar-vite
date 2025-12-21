===========
Prefetching
===========

Preload pages before users navigate to them.

.. seealso::
   Official Inertia.js docs: `Prefetching <https://inertiajs.com/docs/v2/data-props/prefetching>`_

What Is Prefetching?
--------------------

Prefetching proactively loads a page in the background, so navigation feels
instant when the user clicks a link.

Link Prefetching
----------------

Enable prefetching on individual links:

.. tab-set::

   .. tab-item:: React

      .. code-block:: tsx

         import { Link } from "@inertiajs/react";

         <Link href="/reports" prefetch>
           Reports
         </Link>

   .. tab-item:: Vue

      .. code-block:: vue

         <template>
           <Link href="/reports" prefetch>Reports</Link>
         </template>

Prefetching defaults to ``hover`` and caches responses for a short period.
Choose when prefetching happens with ``prefetch`` and ``cacheFor``:

.. tab-set::

   .. tab-item:: React

      .. code-block:: tsx

         <Link href="/reports" prefetch="mount" cacheFor={30}>
           Reports
         </Link>

   .. tab-item:: Vue

      .. code-block:: vue

         <template>
           <Link href="/reports" prefetch="mount" :cache-for="30">Reports</Link>
         </template>

Programmatic Prefetching
------------------------

Prefetch routes from code:

.. tab-set::

   .. tab-item:: React

      .. code-block:: tsx

         import { router } from "@inertiajs/react";

         router.prefetch("/users", { cacheFor: 60 });

   .. tab-item:: Vue

      .. code-block:: typescript

         import { router } from "@inertiajs/vue3";

         router.prefetch("/users", { cacheFor: 60 });

Backend Considerations
----------------------

Prefetch requests hit your existing routes. Use partial reloads to limit
payload size when prefetching large pages.

See Also
--------

- :doc:`polling` - Keep data fresh on a timer
- :doc:`partial-reloads` - Tune prefetch payloads
- :doc:`remembering-state` - Preserve UI state
