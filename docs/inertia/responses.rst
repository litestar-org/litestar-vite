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
   * - ``prop_filter``
     - ``PropFilter | None``
     - Server-side prop filtering for partial reloads
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

API Client Access (Content Negotiation)
----------------------------------------

Routes with ``component`` can also serve API clients (Scalar, Postman, curl) by
sending ``Accept: application/json`` headers. This allows the same endpoint to
work as both an Inertia page and a plain JSON API.

.. code-block:: python

   @get("/books", component="Books")
   async def books() -> dict:
       return {
           "books": [
               {"id": 1, "title": "Python Patterns"},
               {"id": 2, "title": "Web APIs"},
           ],
           "total": 2,
       }

**Different clients, different responses:**

.. tab-set::

    .. tab-item:: Browser (Inertia)

        .. code-block:: bash

           # Inertia client request
           curl -H "X-Inertia: true" http://localhost:8000/books

        Returns Inertia JSON format:

        .. code-block:: json

           {
             "component": "Books",
             "props": {
               "books": [...],
               "total": 2
             },
             "url": "/books",
             "version": "abc123"
           }

    .. tab-item:: API Client (JSON)

        .. code-block:: bash

           # API client with Accept header
           curl -H "Accept: application/json" http://localhost:8000/books

        Returns raw JSON:

        .. code-block:: json

           {
             "books": [
               {"id": 1, "title": "Python Patterns"},
               {"id": 2, "title": "Web APIs"}
             ],
             "total": 2
           }

    .. tab-item:: Browser (First Load)

        .. code-block:: bash

           # Browser initial page load
           curl http://localhost:8000/books

        Returns rendered HTML with embedded Inertia data.

**How it works:**

1. Request includes ``Accept: application/json`` → Returns raw JSON
2. Request includes ``X-Inertia: true`` → Returns Inertia protocol JSON
3. Otherwise → Returns HTML page

This is useful when:

- Testing endpoints with Scalar/Swagger UI
- Accessing from Postman or other API clients
- Using curl for debugging
- Building mobile apps that share backend with web app

.. note::

   If you need a pure API endpoint (no Inertia), omit the ``component`` parameter:

   .. code-block:: python

      @get("/api/books")  # No component = always JSON
      async def api_books() -> list[Book]:
          return Book.all()

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

Prop Filtering
--------------

Filter which props are sent during partial reloads using ``only()`` and ``except_()``:

.. code-block:: python

   from litestar_vite.inertia import InertiaResponse, only, except_

   @get("/users", component="Users")
   async def list_users(request: InertiaRequest) -> InertiaResponse:
       return InertiaResponse(
           content={
               "users": User.all(),
               "teams": Team.all(),
               "stats": expensive_stats(),
           },
           # Only send "users" prop during partial reloads
           prop_filter=only("users"),
       )

   @get("/dashboard", component="Dashboard")
   async def dashboard(request: InertiaRequest) -> InertiaResponse:
       return InertiaResponse(
           content={
               "summary": get_summary(),
               "charts": get_charts(),
               "debug_info": get_debug_info(),
           },
           # Send all props except "debug_info" during partial reloads
           prop_filter=except_("debug_info"),
       )

Note: This is server-side filtering. Clients should use Inertia's
``router.reload({ only: [...] })`` for client-initiated filtering.

See Also
--------

- :doc:`partial-reloads` - Prop filtering and lazy props
- :doc:`redirects` - Redirect responses
- :doc:`merging-props` - Infinite scroll patterns
- :doc:`history-encryption` - History encryption
