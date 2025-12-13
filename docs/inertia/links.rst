=====
Links
=====

Client-side navigation and route helpers.

.. seealso::
   Official Inertia.js docs: `Links <https://inertiajs.com/links>`_

.. tip::
   **Plain URLs work everywhere!** You're not required to use the ``route()`` helper.
   See :doc:`routing` for details on how litestar-vite compares to Laravel/Ziggy.

Inertia Link Component
----------------------

Use the Inertia Link component for SPA navigation. Both plain URLs and the ``route()`` helper work:

.. tab-set::

   .. tab-item:: React

      .. code-block:: tsx

         import { Link } from "@inertiajs/react";

         <Link href="/users">Users</Link>
         <Link href="/users" method="post">Create User</Link>
         <Link href="/logout" method="post" as="button">Logout</Link>

   .. tab-item:: Vue

      .. code-block:: vue

         <script setup>
         import { Link } from "@inertiajs/vue3";
         </script>

         <template>
           <Link href="/users">Users</Link>
           <Link href="/users" method="post">Create User</Link>
           <Link href="/logout" method="post" as="button">Logout</Link>
         </template>

Route Helper
------------

Generate URLs for named routes using the ``route()`` helper:

.. code-block:: typescript

   // Import from your generated routes file (output is driven by TypeGenConfig.output)
   import { route } from "./generated/routes";

   // Simple route
   const homeUrl = route("home");  // "/"

   // Route with parameters
   const userUrl = route("user-profile", { userId: 123 });  // "/users/123"

.. code-block:: tsx

   // Use with Link
   <Link href={route("user-profile", { userId: 123 })}>View Profile</Link>

Setup
-----

Routes are generated at build/dev time into ``TypeGenConfig.output``.
Import the generated module in application code where you need route helpers.

See Also
--------

- :doc:`routing` - Comparison with Laravel/Ziggy, plain URL support
- :doc:`type-generation` - Typed routes
- `Inertia.js Links <https://inertiajs.com/links>`_ - Official docs
- `Inertia.js Manual Visits <https://inertiajs.com/manual-visits>`_ - Programmatic navigation
