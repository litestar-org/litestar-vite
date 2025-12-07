======================
Routing & Navigation
======================

How litestar-vite routing compares to Laravel/Ziggy and works with Inertia's standard APIs.

.. seealso::
   Official Inertia.js docs: `Links <https://inertiajs.com/links>`_ | `Manual Visits <https://inertiajs.com/manual-visits>`_

Key Differences from Laravel/Ziggy
----------------------------------

If you're coming from Laravel with Ziggy, here's what's different:

.. list-table::
   :widths: 30 35 35
   :header-rows: 1

   * - Feature
     - Laravel/Ziggy
     - litestar-vite
   * - Route helper
     - Global ``route()`` function
     - Imported ``route()`` from generated file
   * - Inertia router
     - Monkey-patched with Ziggy
     - Unmodified, standard Inertia
   * - Plain URLs
     - Work but bypass types
     - **First-class support**
   * - Type safety
     - Optional (TypeScript)
     - Full inference from Python

**The key principle**: litestar-vite provides type-safe route helpers as *optional utilities*,
not as a requirement. Inertia's standard router APIs work perfectly with plain URL strings.

Plain URLs Work Everywhere
--------------------------

You are **not required** to use the ``route()`` helper. Plain URL strings work with all Inertia APIs:

.. tab-set::

   .. tab-item:: Link Component

      .. code-block:: tsx

         import { Link } from "@inertiajs/react";

         // Both are valid:
         <Link href="/users">Users</Link>
         <Link href={route("users")}>Users</Link>

   .. tab-item:: Router.visit

      .. code-block:: typescript

         import { router } from "@inertiajs/react";

         // Both are valid:
         router.visit("/users/123");
         router.visit(route("user-profile", { userId: 123 }));

   .. tab-item:: Router Methods

      .. code-block:: typescript

         import { router } from "@inertiajs/react";

         // All standard Inertia methods work with plain URLs:
         router.get("/users");
         router.post("/users", { data: { name: "John" } });
         router.put("/users/123", { data: { name: "Jane" } });
         router.delete("/users/123");

Using the Route Helper
----------------------

The ``route()`` helper provides **optional type safety** for route names and parameters:

.. code-block:: typescript

   import { route } from "@/generated/routes";

   // Type-safe route names (autocomplete + compile-time checking)
   const url = route("user-profile", { userId: 123 });

   // TypeScript errors on invalid routes
   const url = route("invalid-route");  // Error: Route not found

   // TypeScript errors on missing parameters
   const url = route("user-profile");  // Error: Missing userId

Comparison Examples
-------------------

Here's the same navigation written two ways:

**1. Plain URLs (Always Works)**

.. code-block:: tsx

   import { Link } from "@inertiajs/react";
   import { router } from "@inertiajs/react";

   // Link
   <Link href="/users/123">View User</Link>

   // Programmatic navigation
   router.visit("/users/123");
   router.post("/users", { data: { name: "John" } });

**2. With route() Helper (Type-Safe)**

.. code-block:: tsx

   import { Link } from "@inertiajs/react";
   import { router } from "@inertiajs/react";
   import { route } from "@/generated/routes";

   // Link - route() returns a string URL
   <Link href={route("user-profile", { userId: 123 })}>View User</Link>

   // Programmatic navigation - standard Inertia router with type-safe URLs
   router.visit(route("user-profile", { userId: 123 }));
   router.post(route("users"), { data: { name: "John" } });

The ``route()`` helper just returns a plain string, so it works directly with Inertia's
standard ``router`` - no special wrappers needed.

Global Route (Ziggy-Style)
--------------------------

For a more Laravel/Ziggy-like experience, you can enable global registration of ``route()``:

.. code-block:: python

   from litestar_vite.config import TypeGenConfig

   ViteConfig(
       types=TypeGenConfig(
           global_route=True,  # Register route() on window
       ),
   )

When enabled, the generated ``routes.ts`` includes:

.. code-block:: typescript

   // Automatically added at end of routes.ts
   if (typeof window !== "undefined") {
     window.route = route
   }

Now you can use ``route()`` without imports:

.. code-block:: tsx

   // No import needed!
   <Link href={window.route("user-profile", { userId: 123 })}>View User</Link>

   // Or in vanilla JS
   router.visit(window.route("users"));

.. tip::
   For full TypeScript support with the global, add to your ``global.d.ts``:

   .. code-block:: typescript

      declare const route: typeof import("@/generated/routes").route

   This gives you autocomplete even without importing.

.. note::
   The default is ``global_route=False`` because explicit imports are better for:

   - **Tree-shaking**: Unused routes can be eliminated
   - **Explicitness**: Clear where ``route()`` comes from
   - **Testing**: Easier to mock in unit tests

Interoperability
----------------

The ``route()`` helper returns a plain string, so it works seamlessly with:

- Inertia's ``<Link>`` component
- Inertia's ``router.visit()``, ``router.get()``, ``router.post()``, etc.
- Standard ``fetch()`` calls
- Any function expecting a URL string

.. code-block:: typescript

   import { route } from "@/generated/routes";

   const url = route("user-profile", { userId: 123 });
   console.log(typeof url);  // "string"
   console.log(url);         // "/users/123"

   // Works with anything expecting a string
   fetch(url);
   window.location.href = url;
   router.visit(url);

Migration from Laravel/Ziggy
----------------------------

If you're migrating from Laravel with Ziggy:

1. **Replace the global**: Change ``route("name")`` to ``import { route } from "@/generated/routes"``

2. **Update imports**: The route helper is imported, not global

3. **Keep your URLs**: Plain URLs continue to work - you can migrate incrementally

.. code-block:: typescript

   // Before (Laravel/Ziggy - global)
   router.visit(route("users.show", { user: 123 }));

   // After (litestar-vite - imported)
   import { route } from "@/generated/routes";
   router.visit(route("user-profile", { userId: 123 }));

   // Or just use plain URLs (also valid!)
   router.visit("/users/123");

Route Naming Conventions
------------------------

litestar-vite uses kebab-case for route names by default (converted from Python function names):

.. code-block:: python

   @get("/users/{user_id}", component="UserProfile")
   async def user_profile(user_id: int) -> dict:
       ...  # Route name: "user-profile"

   @get("/users", component="Users")
   async def list_users() -> dict:
       ...  # Route name: "list-users"

This differs from Laravel's dot notation (``users.show``), but you can customize route names:

.. code-block:: python

   @get("/users/{user_id}", component="UserProfile", name="users.show")
   async def user_profile(user_id: int) -> dict:
       ...  # Route name: "users.show" (custom)

See Also
--------

- :doc:`links` - Link component and navigation helpers
- :doc:`typescript` - TypeScript integration overview
- :doc:`type-generation` - Route type generation config
- `Inertia.js Manual Visits <https://inertiajs.com/manual-visits>`_ - Official navigation docs
