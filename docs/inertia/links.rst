=====
Links
=====

Client-side navigation and route helpers.

.. seealso::
   Official Inertia.js docs: `Links <https://inertiajs.com/links>`_

Inertia Link Component
----------------------

Use the Inertia Link component for SPA navigation:

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

.. code-block:: javascript

   import { route } from "litestar-vite-plugin/inertia-helpers";

   // Simple route
   const homeUrl = route("home");  // "/"

   // Route with parameters
   const userUrl = route("user-profile", { userId: 123 });  // "/users/123"

.. code-block:: tsx

   // Use with Link
   <Link href={route("user-profile", { userId: 123 })}>View Profile</Link>

Route Checking
--------------

Check the current route:

.. code-block:: typescript

   import { isCurrentRoute, currentRoute } from "litestar-vite-plugin/inertia-helpers";

   // Check if on specific route
   const onDashboard = isCurrentRoute("dashboard");

   // Check with wildcard pattern
   const inUsersSection = isCurrentRoute("users-*");

   // Get current route name
   const routeName = currentRoute();  // e.g., "user-profile"

URL to Route Conversion
-----------------------

Convert URLs to route names:

.. code-block:: typescript

   import { toRoute } from "litestar-vite-plugin/inertia-helpers";

   const routeName = toRoute("/users/123");  // "user-profile"

Setup
-----

Routes are automatically injected into your root template via the
``{{ js_routes }}`` helper:

.. code-block:: html

   <head>
     {{ vite('resources/main.ts') }}
     {{ js_routes }}
   </head>

Excluding Routes
----------------

Exclude routes from the generated routes file:

.. code-block:: python

   @get("/internal", exclude_from_routes=True)
   async def internal() -> dict:
       ...

Or use the configured key:

.. code-block:: python

   InertiaConfig(exclude_from_js_routes_key="private")

   @get("/internal", private=True)
   async def internal() -> dict:
       ...

See Also
--------

- :doc:`type-generation` - Typed routes
- `Inertia.js Links <https://inertiajs.com/links>`_ - Official docs
- `Inertia.js Manual Visits <https://inertiajs.com/manual-visits>`_ - Programmatic navigation
