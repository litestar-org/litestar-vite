=========
Responses
=========

Working with InertiaResponse for advanced page rendering.

.. seealso::
   Official Inertia.js docs: `Responses <https://inertiajs.com/responses>`_

Basic Usage
-----------

For most cases, use the ``component`` decorator parameter:

.. code-block:: python

   @get("/dashboard", component="Dashboard")
   async def dashboard() -> dict:
       return {"stats": {"users": 100}}

InertiaResponse
---------------

Use ``InertiaResponse`` for more control:

.. code-block:: python

   from litestar_vite.inertia import InertiaResponse

   @get("/dashboard")
   async def dashboard() -> InertiaResponse:
       return InertiaResponse(
           content={"stats": {"users": 100}},
           # Optional parameters
           encrypt_history=True,
           clear_history=False,
       )

InertiaResponse Parameters
--------------------------

.. list-table::
   :widths: 25 15 60
   :header-rows: 1

   * - Parameter
     - Type
     - Description
   * - ``content``
     - ``T``
     - Props to pass to the component
   * - ``template_name``
     - ``str | None``
     - Override root template name
   * - ``encrypt_history``
     - ``bool | None``
     - Enable history encryption for this page
   * - ``clear_history``
     - ``bool``
     - Clear encrypted history on navigation
   * - ``scroll_props``
     - ``ScrollPropsConfig | None``
     - Pagination config for infinite scroll
   * - ``context``
     - ``dict[str, Any] | None``
     - Additional template context
   * - ``headers``
     - ``ResponseHeaders | None``
     - Custom response headers
   * - ``cookies``
     - ``ResponseCookies | None``
     - Response cookies

Non-Inertia Responses
---------------------

``InertiaResponse`` automatically handles both Inertia and non-Inertia requests:

- **Inertia request** (``X-Inertia: true``): Returns JSON
- **Non-Inertia request**: Returns rendered HTML template

.. code-block:: python

   # Works for both browser and Inertia navigation
   @get("/dashboard", component="Dashboard")
   async def dashboard() -> dict:
       return {"stats": {...}}

Pagination Containers
---------------------

Return pagination objects directly - they're automatically unwrapped:

.. code-block:: python

   from litestar.pagination import OffsetPagination

   @get("/users", component="Users")
   async def list_users(offset: int = 0, limit: int = 20) -> OffsetPagination:
       users, total = await User.paginate(offset, limit)
       return OffsetPagination(
           items=users,
           limit=limit,
           offset=offset,
           total=total,
       )

The ``items`` are extracted and included in props. Use ``key`` opt to customize:

.. code-block:: python

   @get("/users", component="Users", key="users")
   async def list_users(...) -> OffsetPagination:
       ...  # Props will have "users" instead of "items"

See Also
--------

- :doc:`redirects` - Redirect responses
- :doc:`merging-props` - Infinite scroll patterns
- :doc:`history-encryption` - History encryption
