==========
Once Props
==========

Cache props client-side after the first resolution.

.. seealso::
   Official Inertia.js docs: `Once Props <https://inertiajs.com/docs/v2/data-props/once-props>`_

What Are Once Props?
--------------------

Once props are included in the initial page response, but the Inertia client
caches their value after the first resolution. Subsequent visits reuse the
cached value unless the prop is explicitly requested again.

Why Use Once Props?
-------------------

Use once props for data that is expensive to compute and rarely changes, like
feature flags, account settings, or reference data.

Backend Usage
-------------

.. code-block:: python

   from typing import Any

   from litestar import get
   from litestar_vite.inertia import once

   @get("/dashboard", component="Dashboard")
   async def dashboard() -> dict[str, Any]:
       return {
           "user": get_current_user(),
           "feature_flags": once("feature_flags", get_feature_flags),
           "settings": once("settings", lambda: Settings.for_user("alice")),
       }

Refreshing Once Props
---------------------

The client will reuse cached values. To force a refresh, request the prop in a
partial reload:

.. tab-set::

   .. tab-item:: React

      .. code-block:: tsx

         import { router } from "@inertiajs/react";

         router.reload({ only: ["settings"] });

   .. tab-item:: Vue

      .. code-block:: typescript

         import { router } from "@inertiajs/vue3";

         router.reload({ only: ["settings"] });

Deferred + Once
---------------

Combine deferred props with caching for "load later, remember forever":

.. code-block:: python

   from typing import Any

   from litestar import get
   from litestar_vite.inertia import defer

   @get("/reports", component="Reports")
   async def reports() -> dict[str, Any]:
       return {
           "summary": defer("summary", build_summary).once(),
       }

Comparison of Prop Types
------------------------

.. list-table::
   :widths: 18 22 30 30
   :header-rows: 1

   * - Type
     - Initial Load
     - Partial Reloads
     - Typical Use
   * - ``once()``
     - Included, cached
     - Reused unless requested
     - Rarely changing data
   * - ``lazy()``
     - Excluded
     - Included when requested
     - On-demand data
   * - ``optional()``
     - Excluded
     - Only when explicitly requested
     - WhenVisible / viewport loading
   * - ``always()``
     - Included
     - Included even when filtered
     - Critical auth/context

See Also
--------

- :doc:`partial-reloads` - Client-side reload controls
- :doc:`deferred-props` - Deferred loading after render
- :doc:`load-when-visible` - Optional props with WhenVisible
