=============
Configuration
=============

Complete reference for InertiaConfig options.

.. seealso::
   Official Inertia.js docs: `Server-Side Setup <https://inertiajs.com/server-side-setup>`_

Quick Start
-----------

Enable Inertia with defaults:

.. code-block:: python

   from litestar_vite import ViteConfig, VitePlugin

   VitePlugin(config=ViteConfig(
       dev_mode=True,
       inertia=True,  # Shortcut - enables with all defaults
   ))

Or with custom configuration:

.. code-block:: python

   from litestar_vite import ViteConfig, VitePlugin
   from litestar_vite.inertia import InertiaConfig

   VitePlugin(config=ViteConfig(
       dev_mode=True,
       inertia=InertiaConfig(
           root_template="index.html",
           redirect_unauthorized_to="/login",
       ),
   ))

InertiaConfig Reference
-----------------------

.. list-table::
   :widths: 25 15 60
   :header-rows: 1

   * - Parameter
     - Type
     - Description
   * - ``root_template``
     - ``str``
     - Jinja2 template name for initial page loads. Default: ``"index.html"``
   * - ``component_opt_keys``
     - ``tuple[str, ...]``
     - Route decorator keys for component names. Default: ``("component", "page")``
   * - ``exclude_from_js_routes_key``
     - ``str``
     - Route opt key to exclude from JS routes. Default: ``"exclude_from_routes"``
   * - ``redirect_unauthorized_to``
     - ``str | None``
     - URL for unauthorized (401/403) redirects. Default: ``None``
   * - ``redirect_404``
     - ``str | None``
     - URL for 404 redirects. Default: ``None``
   * - ``extra_static_page_props``
     - ``dict[str, Any]``
     - Props shared with every page. Default: ``{}``
   * - ``extra_session_page_props``
     - ``set[str]``
     - Session keys to include in page props. Default: ``set()``
   * - ``spa_mode``
     - ``bool``
     - Use SPA mode without Jinja2 templates. Default: ``False``
   * - ``app_selector``
     - ``str``
     - CSS selector for app root element. Default: ``"#app"``
   * - ``encrypt_history``
     - ``bool``
     - Enable history encryption globally. Default: ``False``
   * - ``type_gen``
     - ``InertiaTypeGenConfig | None``
     - Type generation options. Default: ``None``

Component Opt Keys
------------------

The ``component_opt_keys`` parameter controls which decorator keys specify the component:

.. code-block:: python

   # Both are equivalent with default config
   @get("/", component="Home")
   async def home() -> dict: ...

   @get("/", page="Home")
   async def home() -> dict: ...

   # Custom keys
   InertiaConfig(component_opt_keys=("view", "component", "page"))

   @get("/", view="Home")  # Now works
   async def home() -> dict: ...

SPA Mode
--------

SPA mode uses HTML transformation instead of Jinja2 templates:

.. code-block:: python

   ViteConfig(
       mode="hybrid",  # Auto-detected when inertia=True
       inertia=InertiaConfig(spa_mode=True),
   )

In SPA mode, the ``index.html`` from your Vite project is used directly,
with page props injected via the ``data-page`` attribute.

Static Page Props
-----------------

Share data with every page without explicit ``share()`` calls:

.. code-block:: python

   InertiaConfig(
       extra_static_page_props={
           "app_name": "My App",
           "version": "1.0.0",
       },
   )

Session Page Props
------------------

Automatically include session keys in page props:

.. code-block:: python

   InertiaConfig(
       extra_session_page_props={"locale", "theme"},
   )

   # In a route handler
   request.session["locale"] = "en"  # Auto-included in props

InertiaTypeGenConfig Reference
------------------------------

Controls TypeScript type generation for Inertia page props (new in v0.15).

.. list-table::
   :widths: 25 15 60
   :header-rows: 1

   * - Parameter
     - Type
     - Description
   * - ``include_default_auth``
     - ``bool``
     - Include default User/AuthData interfaces. Default: ``True``
   * - ``include_default_flash``
     - ``bool``
     - Include default FlashMessages interface. Default: ``True``

When ``include_default_auth=True`` (default), the generated ``page-props.ts`` includes:

- ``User`` interface: ``{ id: string, email: string, name?: string | null }``
- ``AuthData`` interface: ``{ isAuthenticated: boolean, user?: User }``

You can extend these via TypeScript module augmentation:

.. code-block:: typescript

   // Standard auth (95% of users) - extend defaults
   declare module 'litestar-vite/inertia' {
     interface User {
       avatarUrl?: string
       roles: Role[]
     }
   }

For non-standard user models (e.g., ``uuid`` instead of ``id``, ``username`` instead of ``email``), disable defaults:

.. code-block:: python

   from litestar_vite.config import InertiaTypeGenConfig

   InertiaConfig(
       type_gen=InertiaTypeGenConfig(
           include_default_auth=False,  # Custom user model
       ),
   )

Then define your own User interface in TypeScript:

.. code-block:: typescript

   // Custom auth (5% of users) - define from scratch
   declare module 'litestar-vite/inertia' {
     interface User {
       uuid: string      // No id!
       username: string  // No email!
     }
   }

Vite Plugin Auto-Detection
--------------------------

When you enable Inertia (`inertia=True`), the Python backend writes a `.litestar.json` file
with `mode: "inertia"`. The Vite plugin automatically reads this file and enables `inertiaMode`,
which:

- Disables auto-detection of `index.html` in the project
- Shows a placeholder page when accessing Vite directly, directing users to the backend URL
- Displays "Index Mode: Inertia" in the dev server console

This ensures users access your app through Litestar (where Inertia responses are generated)
rather than directly through Vite.

You can also explicitly set `inertiaMode: true` in your `vite.config.ts`:

.. code-block:: javascript

   litestar({
     input: ['resources/main.tsx'],
     inertiaMode: true,  // Explicit (normally auto-detected)
   })

See Also
--------

- :doc:`templates` - Root template setup
- :doc:`typescript` - TypeScript integration
- :doc:`history-encryption` - History encryption configuration
