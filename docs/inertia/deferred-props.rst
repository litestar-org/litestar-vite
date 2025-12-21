==============
Deferred Props
==============

Props that load automatically after the initial page render.

.. seealso::
   Official Inertia.js docs: `Deferred Props <https://inertiajs.com/deferred-props>`_

What Are Deferred Props?
------------------------

Deferred props are excluded from the initial page load and automatically
fetched by the client after the page renders. This improves perceived
performance for slow-loading data.

The defer() Helper
------------------

.. code-block:: python

   from typing import Any

   from litestar import get
   from litestar_vite.inertia import defer

   @get("/dashboard", component="Dashboard")
   async def dashboard() -> dict[str, Any]:
       return {
           "user": get_current_user(),                    # Immediate
           "stats": defer("stats", get_dashboard_stats),  # Deferred
           "chart": defer("chart", get_chart_data),       # Deferred
       }

The client automatically requests deferred props after mounting.

Grouped Deferred Props
----------------------

Group related props to fetch them together:

.. code-block:: python

   from typing import Any

   from litestar import get
   from litestar_vite.inertia import defer

   @get("/users/{id}", component="Users/Show")
   async def show_user(id: int) -> dict[str, Any]:
       return {
           "user": get_user(id),                                       # Immediate

           # Analytics group - fetched together
           "pageViews": defer("pageViews", get_page_views, group="analytics"),
           "engagement": defer("engagement", get_engagement, group="analytics"),

           # Activity group - fetched together
           "comments": defer("comments", get_comments, group="activity"),
           "likes": defer("likes", get_likes, group="activity"),
       }

Props in the same group are fetched in a single request.

Async Callbacks
---------------

``defer()`` supports both sync and async callbacks:

.. code-block:: python

   # Sync callback
   defer("count", lambda: User.count())

   # Async callback
   async def get_slow_data():
       await asyncio.sleep(1)
       return {"slow": "data"}

   defer("slow", get_slow_data)

Deferred Once Props
-------------------

You can combine deferred loading with client-side caching:

.. code-block:: python

   from litestar_vite.inertia import defer

   @get("/reports", component="Reports")
   async def reports() -> dict[str, Any]:
       return {
           "summary": defer("summary", build_summary).once(),
       }

The prop is fetched after the initial render, then cached for later visits.

Frontend Handling
-----------------

The Inertia client shows loading states for deferred props:

.. tab-set::

   .. tab-item:: React

      .. code-block:: tsx

         import { usePage, Deferred } from "@inertiajs/react";

         export default function Dashboard() {
           return (
             <div>
               {/* Immediate data */}
               <h1>Welcome, {usePage().props.user.name}</h1>

               {/* Deferred data with loading fallback */}
               <Deferred data="stats" fallback={<Spinner />}>
                 <Stats />
               </Deferred>
             </div>
           );
         }

   .. tab-item:: Vue

      .. code-block:: text

         <script setup>
         import { Deferred } from "@inertiajs/vue3";
         </script>

         <template>
           <div>
             <h1>Welcome, {{ $page.props.user.name }}</h1>

             <Deferred data="stats">
               <template #fallback><Spinner /></template>
               <Stats />
             </Deferred>
           </div>
         </template>

Defer vs Lazy
-------------

.. list-table::
   :widths: 20 40 40
   :header-rows: 1

   * - Feature
     - ``lazy()``
     - ``defer()``
   * - Loading
     - Manual (partial reload)
     - Automatic (after mount)
   * - Grouping
     - No
     - Yes
   * - Use Case
     - On-demand data
     - Slow initial data
   * - Caching
     - No
     - Optional via ``.once()``

Protocol Response
-----------------

Deferred props are included in the ``deferredProps`` field:

.. code-block:: json

   {
     "component": "Dashboard",
     "props": {"user": {"name": "Alice"}},
     "deferredProps": {
       "default": ["stats"],
       "analytics": ["pageViews", "engagement"]
     }
   }

Advanced: Helper Utilities
---------------------------

For advanced use cases, litestar-vite provides helper utilities:

.. code-block:: python

   from litestar_vite.inertia import extract_deferred_props

   # Extract deferred props metadata from props dict
   props = {
       "users": [...],
       "teams": defer("teams", get_teams, group="attributes"),
       "projects": defer("projects", get_projects, group="attributes"),
       "permissions": defer("permissions", get_permissions),  # default group
   }

   groups = extract_deferred_props(props)
   # Result: {"default": ["permissions"], "attributes": ["teams", "projects"]}

This is used internally by ``InertiaResponse`` to build the page object
with the ``deferredProps`` field for the Inertia v2 protocol.

See Also
--------

- :doc:`partial-reloads` - Manual partial reloads with lazy()
- :doc:`merging-props` - Infinite scroll patterns
- :doc:`once-props` - Client-cached props
