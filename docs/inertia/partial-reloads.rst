===============
Partial Reloads
===============

Optimize performance by reloading only specific props.

.. seealso::
   Official Inertia.js docs: `Partial Reloads <https://inertiajs.com/partial-reloads>`_

What Are Partial Reloads?
-------------------------

Partial reloads let you request only specific props instead of the entire
page data. This reduces payload size and server processing.

Lazy Props
----------

Use ``lazy()`` to mark props that should only load during partial reloads:

.. code-block:: python

   from typing import Any

   from litestar import get
   from litestar_vite.inertia import lazy

   @get("/dashboard", component="Dashboard")
   async def dashboard() -> dict[str, Any]:
       return {
           "stats": get_stats(),                    # Always included
           "notifications": lazy("notifications", get_notifications),  # Partial only
           "activity": lazy("activity", get_activity_feed),            # Partial only
       }

Lazy props are excluded from the initial page load and only sent when
explicitly requested via partial reload.

Static vs Callable Lazy Props
-----------------------------

**Static value** - computed eagerly, sent lazily:

.. code-block:: python

   # Value computed now, but only sent during partial reload
   lazy("count", len(expensive_query()))

**Callable** - computed and sent lazily:

.. code-block:: python

   # Function only called during partial reload
   lazy("count", lambda: len(expensive_query()))
   lazy("data", expensive_async_function)  # Async works too

.. warning::
   **Avoid the "False Lazy" pitfall:**

   .. code-block:: python

      # WRONG - function called immediately!
      lazy("data", get_expensive_data())

      # CORRECT - function reference passed
      lazy("data", get_expensive_data)

Once Props
----------

Use ``once()`` to cache props client-side after the first response:

.. code-block:: python

   from typing import Any

   from litestar import get
   from litestar_vite.inertia import once

   @get("/settings", component="Settings")
   async def settings() -> dict[str, Any]:
       return {
           "preferences": once("preferences", get_preferences),
           "feature_flags": once("feature_flags", get_feature_flags),
       }

Once props are included in initial loads, but the client caches their values
and reuses them on subsequent visits.

Optional Props (WhenVisible)
----------------------------

Optional props are only included when explicitly requested:

.. code-block:: python

   from typing import Any

   from litestar import get
   from litestar_vite.inertia import optional

   @get("/posts/{post_id}", component="Posts/Show")
   async def show_post(post_id: int) -> dict[str, Any]:
       return {
           "post": await Post.get(post_id),
           "comments": optional("comments", lambda: Comment.for_post(post_id)),
       }

These work well with the ``WhenVisible`` component to load data as it enters
the viewport.

Always Props
------------

Use ``always()`` for data that must be included in every response, even when
partial reloads filter props:

.. code-block:: python

   from typing import Any

   from litestar import get
   from litestar.request import Request
   from litestar_vite.inertia import always, lazy

   @get("/dashboard", component="Dashboard")
   async def dashboard(request: Request) -> dict[str, Any]:
       return {
           "auth": always("auth", {"user": request.user}),
           "stats": lazy("stats", get_stats),
       }

Prop Type Comparison
--------------------

.. list-table::
   :widths: 18 22 30 30
   :header-rows: 1

   * - Type
     - Initial Load
     - Partial Reloads
     - Typical Use
   * - ``lazy()``
     - Excluded
     - Included when requested
     - Heavy data on demand
   * - ``optional()``
     - Excluded
     - Only when explicitly requested
     - WhenVisible / viewport loading
   * - ``once()``
     - Included, cached
     - Reused unless requested
     - Rarely changing data
   * - ``always()``
     - Included
     - Included even when filtered
     - Critical auth/context

Frontend Partial Reloads
------------------------

Request specific props from the client:

.. tab-set::

   .. tab-item:: React

      .. code-block:: tsx

         import { router } from "@inertiajs/react";

         // Reload only specific props
         router.reload({ only: ["notifications"] });

         // Exclude specific props
         router.reload({ except: ["stats"] });

   .. tab-item:: Vue

      .. code-block:: typescript

         import { router } from "@inertiajs/vue3";

         router.reload({ only: ["notifications"] });
         router.reload({ except: ["stats"] });

Prop Filtering Helpers
----------------------

Use ``only()`` and ``except_()`` for server-side filtering:

.. code-block:: python

   from litestar_vite.inertia import only, except_

   # Include only specific props
   filter_users = only("users", "pagination")

   # Exclude specific props
   filter_no_debug = except_("debug_info", "internal_stats")

   # Check if a key should be included
   if filter_users.should_include("users"):  # True
       pass
   if filter_users.should_include("settings"):  # False
       pass

Protocol Headers
----------------

The v2 protocol uses these headers for partial reloads:

.. list-table::
   :widths: 30 70
   :header-rows: 1

   * - Header
     - Description
   * - ``X-Inertia-Partial-Data``
     - Comma-separated list of props to include (e.g., ``users,teams``)
   * - ``X-Inertia-Partial-Except``
     - Comma-separated list of props to exclude (takes precedence over Partial-Data)
   * - ``X-Inertia-Reset``
     - Comma-separated list of props to reset/remove from shared state

When ``X-Inertia-Partial-Except`` is present, it takes precedence over
``X-Inertia-Partial-Data``. This matches the v2 protocol behavior where
exclusion is stronger than inclusion.

Reset Props
-----------

The ``X-Inertia-Reset`` header removes specified props from the shared state:

.. code-block:: typescript

   // Client-side: reset specific props during partial reload
   router.reload({
     only: ["users"],
     reset: ["flash", "errors"]  // Clear flash and errors
   })

On the backend, reset props are removed from ``shared_props`` before
building the page response. This is useful for clearing one-time data
like flash messages or validation errors.

Example Use Case
----------------

Dashboard with heavy charts data:

.. code-block:: python

   from typing import Any

   from litestar import get
   from litestar_vite.inertia import lazy

   @get("/dashboard", component="Dashboard")
   async def dashboard() -> dict[str, Any]:
       return {
           "user": get_current_user(),              # Always needed
           "summary": get_summary_stats(),          # Always needed
           "charts": lazy("charts", get_chart_data),  # Load on demand
           "activity": lazy("activity", get_activity),  # Load on demand
       }

Frontend:

.. code-block:: tsx

   // Initial load: only user and summary
   // Click "Load Charts" button:
   router.reload({ only: ["charts"] });

See Also
--------

- :doc:`deferred-props` - Auto-loaded deferred props
- :doc:`responses` - InertiaResponse options
- :doc:`once-props` - Client-cached props
- :doc:`load-when-visible` - Optional props with WhenVisible
