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

   from litestar_vite.inertia import lazy

   @get("/dashboard", component="Dashboard")
   async def dashboard() -> dict:
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
     - Comma-separated list of props to include
   * - ``X-Inertia-Partial-Except``
     - Comma-separated list of props to exclude (takes precedence)
   * - ``X-Inertia-Reset``
     - Props to reset to initial values

Example Use Case
----------------

Dashboard with heavy charts data:

.. code-block:: python

   @get("/dashboard", component="Dashboard")
   async def dashboard() -> dict:
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
