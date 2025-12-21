===========
Shared Data
===========

Share data with every page in your application.

.. seealso::
   Official Inertia.js docs: `Shared Data <https://inertiajs.com/shared-data>`_

The share() Helper
------------------

Use ``share()`` to provide data to all pages during a request:

.. code-block:: python

   from typing import Any

   from litestar import Request, get
   from litestar_vite.inertia import share

   @get("/dashboard", component="Dashboard")
   async def dashboard(request: Request) -> dict[str, Any]:
       # Share user data with all components
       share(request, "user", {"name": "Alice", "email": "alice@example.com"})
       share(request, "permissions", ["read", "write"])

       return {"stats": {...}}

Shared data is merged with page props and available in every component.

Lazy Shared Props
------------------

Shared props can be lazy to optimize partial reloads:

.. code-block:: python

   from typing import Any

   from litestar import Request, get
   from litestar_vite.inertia import share, lazy

   @get("/dashboard", component="Dashboard")
   async def dashboard(request: Request) -> dict[str, Any]:
       # Share expensive data lazily
       share(request, "permissions", lazy("permissions", get_all_permissions))
       share(request, "notifications", lazy("notifications", get_notifications))

       return {"stats": {...}}

Lazy shared props are only included when explicitly requested via partial reload,
reducing the initial page load size.

Guards and Middleware
---------------------

Share data in guards for authentication patterns:

.. code-block:: python

   from litestar import Request
   from litestar.connection import ASGIConnection
   from litestar.handlers import BaseRouteHandler
   from litestar_vite.inertia import share

   async def auth_guard(
       connection: ASGIConnection,
       _: BaseRouteHandler,
   ) -> None:
       if connection.user:
           share(connection, "auth", {
               "user": connection.user,
               "isAuthenticated": True,
           })
       else:
           share(connection, "auth", {
               "user": None,
               "isAuthenticated": False,
           })

Static Page Props
-----------------

For data that never changes, use ``extra_static_page_props``:

.. code-block:: python

   from litestar_vite.inertia import InertiaConfig

   InertiaConfig(
       extra_static_page_props={
           "app_name": "My Application",
           "version": "1.0.0",
           "support_email": "help@example.com",
       },
   )

These props are included in every response without any code in handlers.

Session Page Props
------------------

Automatically include session keys as props:

.. code-block:: python

   InertiaConfig(
       extra_session_page_props={"locale", "theme", "timezone"},
   )

   # In a route handler or middleware
   request.session["locale"] = "en"
   request.session["theme"] = "dark"

   # These are automatically included in every page's props

Frontend Usage
--------------

Access shared data in your components:

.. tab-set::

   .. tab-item:: React

      .. code-block:: tsx

         import { usePage } from "@inertiajs/react";

         interface SharedProps {
           auth: { user: User | null; isAuthenticated: boolean };
           app_name: string;
           flash: { [category: string]: string[] };
         }

         export default function Layout({ children }) {
           const { auth, app_name } = usePage<SharedProps>().props;

           return (
             <div>
               <header>
                 <h1>{app_name}</h1>
                 {auth.isAuthenticated && <span>Hi, {auth.user.name}</span>}
               </header>
               {children}
             </div>
           );
         }

   .. tab-item:: Vue

      .. code-block:: vue

         <script setup lang="ts">
         import { usePage } from "@inertiajs/vue3";

         interface SharedProps {
           auth: { user: User | null; isAuthenticated: boolean };
           app_name: string;
         }

         const { auth, app_name } = usePage<SharedProps>().props;
         </script>

         <template>
           <header>
             <h1>{{ app_name }}</h1>
             <span v-if="auth.isAuthenticated">Hi, {{ auth.user.name }}</span>
           </header>
           <slot />
         </template>

Built-in Shared Props
---------------------

These props are automatically included:

.. list-table::
   :widths: 20 80
   :header-rows: 1

   * - Prop
     - Description
   * - ``flash``
     - Flash messages by category (e.g., ``{"success": ["Saved!"]}``)
   * - ``errors``
     - Validation errors by field
   * - ``csrf_token``
     - CSRF token for form submissions

Partial Reload Filtering
-------------------------

Shared props respect partial reload filters (v2 feature). When using
``only`` or ``except`` in partial reloads, shared props are filtered too:

.. code-block:: python

   # Static shared prop
   InertiaConfig(extra_static_page_props={"app_name": "My App"})

   # Session shared prop
   InertiaConfig(extra_session_page_props={"locale"})

   # Client requests only specific props
   router.reload({ only: ["users"] })
   # Result: Only "users" is included, shared props are excluded

   # Client excludes specific props
   router.reload({ except: ["debug"] })
   # Result: All props including shared props, except "debug"

This applies to:

- ``extra_static_page_props`` - filtered by key
- ``extra_session_page_props`` - filtered by key
- Props set via ``share()`` - filtered by key

See Also
--------

- :doc:`shared-props-typing` - TypeScript types for shared props
- :doc:`partial-reloads` - Filtering shared data on partial reloads
