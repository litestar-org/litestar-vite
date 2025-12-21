=================
Remembering State
=================

Persist client state across visits and browser history.

.. seealso::
   Official Inertia.js docs: `Remembering State <https://inertiajs.com/docs/v2/data-props/remembering-state>`_

What Is Remembering State?
--------------------------

Remembered state lets your components persist data (filters, form drafts,
expanded panels) when the user navigates away and comes back.

useRemember Hook
----------------

.. tab-set::

   .. tab-item:: React

      .. code-block:: tsx

         import { useRemember } from "@inertiajs/react";

         export default function Users() {
           const [filters, setFilters] = useRemember(
             { search: "", role: "all" },
             "users:filters"
           );

           return <Filters value={filters} onChange={setFilters} />;
         }

   .. tab-item:: Vue

      .. code-block:: vue

         <script setup lang="ts">
         import { useRemember } from "@inertiajs/vue3";

         const filters = useRemember({ search: "", role: "all" }, "users:filters");
         </script>

         <template>
           <Filters :value="filters" @change="(next) => (filters.value = next)" />
         </template>

Remembered Forms
----------------

The Inertia form helpers accept a remember key:

.. tab-set::

   .. tab-item:: React

      .. code-block:: tsx

         import { useForm } from "@inertiajs/react";

         const form = useForm("profile", {
           name: "",
           email: "",
         });

   .. tab-item:: Vue

      .. code-block:: vue

         <script setup lang="ts">
         import { useForm } from "@inertiajs/vue3";

         const form = useForm("profile", {
           name: "",
           email: "",
         });
         </script>

Manual Remember/Restore
-----------------------

You can also remember arbitrary values manually:

.. tab-set::

   .. tab-item:: React

      .. code-block:: tsx

         import { router } from "@inertiajs/react";

         router.remember({ tab: "billing" }, "settings:tab");
         const restored = router.restore("settings:tab");

   .. tab-item:: Vue

      .. code-block:: typescript

         import { router } from "@inertiajs/vue3";

         router.remember({ tab: "billing" }, "settings:tab");
         const restored = router.restore("settings:tab");

Backend Considerations
----------------------

No server changes are required. Remembered state is stored client-side.

See Also
--------

- :doc:`forms` - Form helpers and submissions
- :doc:`prefetching` - Preload pages
- :doc:`polling` - Refresh data on intervals
