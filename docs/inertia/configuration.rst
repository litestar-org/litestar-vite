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
     - ``set[str] | dict[str, type]``
     - Session keys to include in page props. Default: ``set()``
   * - ``encrypt_history``
     - ``bool``
     - Enable history encryption globally. Default: ``False``
   * - ``type_gen``
     - ``InertiaTypeGenConfig | None``
     - Type generation options. Default: ``None``
   * - ``use_script_element``
     - ``bool``
     - Use script element for page data instead of data-page attribute. Default: ``False``

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

Script Element Optimization (Inertia v2.3+)
-------------------------------------------

The ``use_script_element`` parameter enables a performance optimization introduced in Inertia.js v2.3+.
When enabled, page data is embedded in a ``<script type="application/json" id="app_page">`` element
instead of a ``data-page`` attribute on the app element.

**Benefits:**

- **~37% payload reduction** for large pages by avoiding HTML entity escaping
- Better performance for pages with complex props
- Cleaner HTML output

**Requirements:**

This feature requires **both** server-side and client-side configuration:

.. code-block:: python

   # Server-side configuration
   from litestar_vite import InertiaConfig

   InertiaConfig(
       use_script_element=True,  # Enable script element mode
   )

.. code-block:: typescript

   // Client-side configuration (REQUIRED)
   import { createInertiaApp } from '@inertiajs/react'  // or vue/svelte

   createInertiaApp({
     // v2.3+ optimization: read page data from script element
     useScriptElementForInitialPage: true,
     // ... rest of config
   })

.. warning::

   Both configurations must be enabled together. If you enable ``use_script_element=True``
   on the server but forget the client-side configuration, the Inertia app will fail to
   initialize because it won't find the page data.

.. note::

   This feature is disabled by default (``use_script_element=False``) for backward
   compatibility with existing Inertia.js clients. Enable it if you're using Inertia v2.3+.

Flash Data Protocol (Inertia v2.3+)
-----------------------------------

Starting in v0.15, litestar-vite aligns with the Inertia.js v2.3+ protocol for flash messages.
Flash data is now sent as a **top-level** ``page.flash`` property instead of ``page.props.flash``.

**Why this matters:**

- Flash messages no longer persist in browser history
- Prevents flash messages from reappearing when navigating back/forward
- Matches the behavior of official Inertia adapters (Laravel, Rails, Django)

**Python side** (using flash helper):

.. code-block:: python

   from litestar_vite.inertia import flash

   @post("/submit")
   async def submit_form(request: Request) -> InertiaBack:
       flash(request, "success", "Form submitted!")
       return InertiaBack(request)

**Client side** (accessing flash data):

.. code-block:: typescript

   // v2.3+ protocol - flash is at top level
   import { usePage } from '@inertiajs/react'

   const { flash } = usePage()

   if (flash?.success) {
     console.log(flash.success)  // ["Form submitted!"]
   }

.. note::

   Flash messages are always sent as a dictionary mapping category names to lists of strings:
   ``{ "success": ["Message 1"], "error": ["Error 1", "Error 2"] }``

   An empty flash object is sent as ``{}`` (not ``null``) to support client-side operations
   like ``router.flash((current) => ({ ...current, success: ["New message"] }))``.

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
   declare module 'litestar-vite-plugin/inertia' {
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
   declare module 'litestar-vite-plugin/inertia' {
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
