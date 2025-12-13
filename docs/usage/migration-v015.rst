========================
Migration Guide (v0.15)
========================

This guide helps you upgrade to v0.15.0 from earlier versions.

.. note::
   v0.15 includes new features and improvements with minimal breaking changes.
   Most applications can upgrade by updating dependencies and adding new features incrementally.

.. contents:: Table of Contents
   :local:
   :depth: 2

Breaking Changes
================

Configuration Structure
-----------------------

v0.15 introduces nested configuration for better organization:

**Before v0.15:**

.. code-block:: python

    ViteConfig(
        bundle_dir="public",
        resource_dir="resources",
        hot_reload=True,
        port=5173,
    )

**v0.15+:**

.. code-block:: python

    from litestar_vite import ViteConfig
    from litestar_vite.config import PathConfig, RuntimeConfig

    ViteConfig(
        paths=PathConfig(
            bundle_dir="public",
            resource_dir="resources",
        ),
        runtime=RuntimeConfig(
            hot_reload=True,
            port=5173,
        ),
    )

Template Engine Removal
-----------------------

The ``ViteTemplateEngine`` has been removed. Use the standard Litestar Jinja engine:

.. code-block:: python

    from litestar.contrib.jinja import JinjaTemplateEngine
    from litestar.template.config import TemplateConfig

    app = Litestar(
        template_config=TemplateConfig(
            engine=JinjaTemplateEngine(directory="templates")
        ),
        plugins=[VitePlugin(...)]
    )

CLI Command Group
-----------------

Commands are now under the ``assets`` group:

- ``litestar assets init`` - Initialize a new project
- ``litestar assets build`` - Build assets
- ``litestar assets serve`` - Serve assets
- ``litestar assets generate-types`` - Generate TypeScript types
- ``litestar assets doctor`` - Diagnose configuration issues
- ``litestar assets deploy`` - Deploy assets to CDN
- ``litestar assets status`` - Check Vite integration status

Proxy Mode Default Change
-------------------------

The ``proxy_mode`` now has smarter auto-detection:

- Default is still ``"vite"`` (whitelist mode - proxies Vite assets only)
- When ``ExternalDevServer`` is configured, automatically switches to ``"proxy"`` mode

**Impact:**

If you were relying on implicit behavior with external dev servers (Angular CLI, Next.js),
the mode now auto-configures correctly. No action needed in most cases.

To explicitly set the mode:

.. code-block:: python

   from litestar_vite import ViteConfig, RuntimeConfig

   ViteConfig(
       runtime=RuntimeConfig(
           proxy_mode="vite",  # Explicit whitelist mode
       )
   )

Mode Aliases
------------

v0.15 introduces mode aliases for convenience:

.. list-table::
   :widths: 30 30 40
   :header-rows: 1

   * - Alias
     - Normalized To
     - Use Case
   * - ``"inertia"``
     - ``"hybrid"``
     - Inertia.js SPA with server-side routing
   * - ``"ssg"``
     - ``"ssr"``
     - Static Site Generation (same proxy behavior as SSR)

**Recommended usage:**

.. code-block:: python

   # For Inertia.js applications
   ViteConfig(mode="inertia")

   # For SSG frameworks (Astro, etc.)
   ViteConfig(mode="ssg")

New Features
============

Vite 7.x Support
----------------

v0.15 adds support for Vite 7.x while maintaining compatibility with Vite 6.x.

**Package.json Update:**

.. code-block:: json

   {
     "peerDependencies": {
       "vite": "^6.0.0 || ^7.0.0"
     }
   }

**Migration:**

Upgrade Vite in your frontend:

.. code-block:: bash

   # npm
   npm install -D vite@^7.0.0

   # yarn
   yarn add -D vite@^7.0.0

   # pnpm
   pnpm add -D vite@^7.0.0

   # bun
   bun add -D vite@^7.0.0

Inertia v2 Features
-------------------

v0.15 adds support for Inertia.js v2 features:

History Encryption
~~~~~~~~~~~~~~~~~~

Enable browser history encryption globally:

.. code-block:: python

   from litestar_vite.inertia import InertiaConfig

   InertiaConfig(
       encrypt_history=True,  # New in v0.15
   )

This prevents sensitive data from being visible in browser history after logout.
See: :doc:`../inertia/history-encryption`

**New Helper:**

.. code-block:: python

   from litestar_vite.inertia import clear_history

   @post("/logout")
   async def logout(request: Request) -> InertiaRedirect:
       request.session.clear()
       clear_history(request)  # Regenerate encryption key
       return InertiaRedirect(request, redirect_to="/login")

Deferred Props with Grouping
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The new ``defer()`` helper supports grouped deferred props:

.. code-block:: python

   from litestar_vite.inertia import defer, InertiaResponse

   @get("/dashboard", component="Dashboard")
   async def dashboard() -> InertiaResponse:
       return InertiaResponse({
           "user": current_user,
           # Deferred props loaded after page render
           "teams": defer("teams", lambda: Team.all(), group="attributes"),
           "projects": defer("projects", lambda: Project.all(), group="attributes"),
           "permissions": defer("permissions", lambda: Permission.all()),
       })

Props in the same group are fetched together in a single request.

Merge Props
~~~~~~~~~~~

New ``merge()`` helper for combining data during partial reloads:

.. code-block:: python

   from litestar_vite.inertia import merge, InertiaResponse

   @get("/posts", component="Posts")
   async def list_posts(page: int = 1) -> InertiaResponse:
       posts = await Post.paginate(page=page, per_page=20)
       return InertiaResponse({
           # Append new posts to existing list
           "posts": merge("posts", posts.items),
       })

Supports strategies: ``"append"`` (default), ``"prepend"``, ``"deep"``.

New Inertia Helpers
~~~~~~~~~~~~~~~~~~~

.. list-table::
   :widths: 30 70
   :header-rows: 1

   * - Helper
     - Description
   * - ``error(request, key, message)``
     - Set validation errors in session
   * - ``only(*keys)``
     - Filter props to include only specified keys
   * - ``except_(*keys)``
     - Filter props to exclude specified keys
   * - ``scroll_props()``
     - Create infinite scroll configuration

**Example:**

.. code-block:: python

   from litestar_vite.inertia import error, only, except_, scroll_props

   # Validation errors
   @post("/users")
   async def create_user(request: Request, data: UserCreate) -> InertiaResponse:
       if not data.email:
           error(request, "email", "Email is required")
           return InertiaRedirect(request, "/users/new")

   # Prop filtering
   @get("/users", component="Users")
   async def list_users() -> InertiaResponse:
       return InertiaResponse(
           {"users": [...], "teams": [...], "stats": [...]},
           prop_filter=only("users"),  # Only send users prop
       )

   # Infinite scroll
   @get("/posts", component="Posts")
   async def list_posts(page: int = 1) -> InertiaResponse:
       posts = await Post.paginate(page=page, per_page=20)
       return InertiaResponse(
           {"posts": merge("posts", posts.items)},
           scroll_props=scroll_props(
               current_page=page,
               previous_page=page - 1 if page > 1 else None,
               next_page=page + 1 if posts.has_more else None,
           ),
       )

Automatic Pagination Support
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

v0.15 automatically detects pagination containers and generates scroll props:

.. code-block:: python

   from litestar.pagination import OffsetPagination
   from litestar_vite.inertia import InertiaResponse

   @get("/posts", component="Posts")
   async def list_posts(limit: int = 10, offset: int = 0) -> InertiaResponse:
       # Returns OffsetPagination with items, total, limit, offset
       posts = await Post.paginate(limit=limit, offset=offset)

       # Automatically unwraps items and generates scroll_props
       return InertiaResponse({"posts": posts})

Supports:
- ``litestar.pagination.OffsetPagination``
- ``litestar.pagination.ClassicPagination``
- ``advanced_alchemy.service.OffsetPagination``
- Any object with ``items`` attribute and pagination metadata

Inertia Type Generation
-----------------------

New type generation options for Inertia page props:

**InertiaTypeGenConfig:**

.. code-block:: python

   from litestar_vite.config import InertiaConfig, InertiaTypeGenConfig

   InertiaConfig(
       type_gen=InertiaTypeGenConfig(
           include_default_auth=True,   # Include User/AuthData interfaces
           include_default_flash=True,  # Include FlashMessages interface
       ),
   )

**Default Types (when ``include_default_auth=True``):**

.. code-block:: typescript

   export interface User {
     id: string
     email: string
     name?: string | null
   }

   export interface AuthData {
     isAuthenticated: boolean
     user?: User
   }

**Extending Defaults:**

.. code-block:: typescript

   // Extend via module augmentation
   declare module 'litestar-vite-plugin/inertia' {
     interface User {
       avatarUrl?: string | null
       roles: Role[]
       teams: Team[]
     }
   }

**Custom User Models:**

If your user model has different required fields (e.g., ``uuid`` instead of ``id``):

.. code-block:: python

   InertiaConfig(
       type_gen=InertiaTypeGenConfig(
           include_default_auth=False,  # Disable defaults
       ),
   )

Then define your own User interface in TypeScript:

.. code-block:: typescript

   declare module 'litestar-vite-plugin/inertia' {
     interface User {
       uuid: string
       username: string
     }
   }

TypeScript Enhancements
-----------------------

**Enhanced TypeGenConfig:**

New options for type generation:

.. list-table::
   :widths: 30 15 55
   :header-rows: 1

   * - Option
     - Type
     - Description
   * - ``generate_page_props``
     - ``bool``
     - Generate Inertia page props types (default: ``True``)
   * - ``page_props_path``
     - ``Path | None``
     - Path for page props metadata JSON
   * - ``routes_ts_path``
     - ``Path | None``
     - Path for typed routes TypeScript file
   * - ``fallback_type``
     - ``Literal["unknown", "any"]``
     - Fallback value type for untyped dict/list in Inertia page props (default: ``unknown``)
   * - ``type_import_paths``
     - ``dict[str, str]``
     - Map props type names to TypeScript import paths for schemas excluded from OpenAPI

**Example:**

.. code-block:: python

   from litestar_vite.config import TypeGenConfig

   ViteConfig(
       types=TypeGenConfig(
           output=Path("src/generated"),
           generate_page_props=True,     # Enable page props generation
           page_props_path=Path("src/generated/inertia-pages.json"),
           routes_ts_path=Path("src/generated/routes.ts"),
       ),
   )

**TypeScript Helpers:**

New TypeScript utilities in ``litestar-vite-plugin``:

*HTMX Utilities:*

.. code-block:: typescript

   import {
     addDirective,
     registerHtmxExtension,
     setHtmxDebug,
     swapJson,
   } from 'litestar-vite-plugin/helpers'

   // Add HTMX directive
   addDirective('my-directive', (element) => { ... })

   // Register HTMX extension
   // Note: Registration is explicit (no auto-registration)
   registerHtmxExtension()

   // Enable HTMX debug mode
   setHtmxDebug(true)

   // Swap JSON response into element
   swapJson(element, { data: 'value' })

*Inertia Helpers:*

.. code-block:: typescript

   import { unwrapPageProps } from 'litestar-vite-plugin/inertia-helpers'

   // Unwrap page props from Inertia response
   const props = unwrapPageProps(pageData)

Runtime Configuration
---------------------

**New RuntimeConfig Options:**

.. list-table::
   :widths: 25 15 60
   :header-rows: 1

   * - Option
     - Type
     - Description
   * - ``http2``
     - ``bool``
     - Enable HTTP/2 for proxy connections (default: ``True``)
   * - ``start_dev_server``
     - ``bool``
     - Control dev server startup (default: ``True``)

**HTTP/2 Support:**

.. code-block:: python

   ViteConfig(
       runtime=RuntimeConfig(
           http2=True,  # Better multiplexing for proxy requests
       ),
   )

HTTP/2 improves proxy performance by allowing multiple requests over a single connection.
WebSocket traffic (HMR) uses a separate connection and is unaffected.

SPA Configuration
-----------------

**New SPAConfig Options:**

.. list-table::
   :widths: 30 15 55
   :header-rows: 1

   * - Option
     - Type
     - Description
   * - ``cache_transformed_html``
     - ``bool``
     - Cache transformed HTML in production (default: ``True``)

**Example:**

.. code-block:: python

   from litestar_vite.config import SPAConfig

   ViteConfig(
       spa=SPAConfig(
           inject_csrf=True,
           cache_transformed_html=True,  # Cache for performance
       ),
   )

Note: Caching is automatically disabled when ``inject_csrf=True`` because CSRF tokens are per-request.

External Dev Server Enhancements
--------------------------------

Enhanced configuration for external dev servers (Angular CLI, Next.js, etc.):

.. list-table::
   :widths: 25 15 60
   :header-rows: 1

   * - Option
     - Type
     - Description
   * - ``target``
     - ``str | None``
     - URL of external dev server
   * - ``command``
     - ``list[str] | None``
     - Custom command to start dev server
   * - ``build_command``
     - ``list[str] | None``
     - Custom build command
   * - ``http2``
     - ``bool``
     - Enable HTTP/2 for proxy (default: ``False``)
   * - ``enabled``
     - ``bool``
     - Enable/disable external proxy (default: ``True``)

**Example:**

.. code-block:: python

   from litestar_vite.config import ExternalDevServer

   ViteConfig(
       runtime=RuntimeConfig(
           external_dev_server=ExternalDevServer(
               target="http://localhost:4200",  # Angular CLI
               command=["ng", "serve"],
               build_command=["ng", "build"],
               http2=True,  # Better performance
           ),
       ),
   )

New CLI Templates
-----------------

v0.15 adds new framework templates for ``litestar assets init``:

.. list-table::
   :widths: 30 70
   :header-rows: 1

   * - Template
     - Description
   * - ``react-router``
     - React with React Router 7+
   * - ``react-tanstack``
     - React with TanStack Router
   * - ``svelte-inertia``
     - Svelte 5 with Inertia.js

**Usage:**

.. code-block:: bash

   litestar assets init --template react-router myapp
   litestar assets init --template react-tanstack myapp
   litestar assets init --template svelte-inertia myapp

Troubleshooting
===============

Common Migration Issues
-----------------------

Issue: Type Generation Not Working
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Symptom:**

Type generation doesn't run after upgrading to v0.15.

**Solution:**

Check that your Python backend is exporting the new metadata files:

.. code-block:: bash

   # Check for generated files
   ls src/generated/inertia-pages.json
   ls src/generated/routes.json

If missing, ensure type generation is enabled:

.. code-block:: python

   ViteConfig(
       types=TypeGenConfig(
           generate_page_props=True,
       ),
   )

Issue: Inertia History Encryption Not Working
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Symptom:**

``encrypt_history=True`` doesn't encrypt history.

**Solution:**

History encryption is a client-side feature. Ensure you're using Inertia.js v2:

.. code-block:: bash

   npm install @inertiajs/react@^2.0.0  # or vue3/svelte

Then update your frontend code to support history encryption.

Issue: Pagination Auto-Detection Conflicts
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Symptom:**

Pagination container is unwrapped but you want the full object.

**Solution:**

Manually construct the response props:

.. code-block:: python

   @get("/posts", component="Posts")
   async def list_posts() -> InertiaResponse:
       pagination = await Post.paginate(limit=10, offset=0)

       # Manually control what's sent
       return InertiaResponse({
           "items": pagination.items,
           "total": pagination.total,
           "limit": pagination.limit,
           "offset": pagination.offset,
       })

Issue: Unknown Mode Error
~~~~~~~~~~~~~~~~~~~~~~~~~

**Symptom:**

Error about unknown mode when using old mode names.

**Solution:**

v0.15 supports these modes: ``spa``, ``template``, ``htmx``, ``hybrid``, ``ssr``, ``external``.

You can also use aliases: ``inertia`` (for ``hybrid``) and ``ssg`` (for ``ssr``).

.. code-block:: python

   # Recommended for Inertia.js
   ViteConfig(mode="inertia")

   # Recommended for SSG frameworks
   ViteConfig(mode="ssg")

Upgrade Checklist
=================

.. list-table::
   :widths: 10 90
   :header-rows: 1

   * - ☑
     - Task
   * - ☐
     - Update ``litestar-vite`` to v0.15.0
   * - ☐
     - Migrate to nested configuration (``PathConfig``, ``RuntimeConfig``)
   * - ☐
     - Replace ``ViteTemplateEngine`` with ``JinjaTemplateEngine`` (if applicable)
   * - ☐
     - Update CLI commands to use ``litestar assets`` prefix
   * - ☐
     - Upgrade Vite to 6.x or 7.x
   * - ☐
     - Update Inertia.js to v2 (if using Inertia features)
   * - ☐
     - Review proxy mode configuration (usually auto-detected correctly)
   * - ☐
     - Test type generation (run ``litestar assets generate-types``)
   * - ☐
     - Run ``make test`` to verify everything works
   * - ☐
     - Run ``make lint`` to check for issues

Next Steps
==========

- Review new Inertia v2 features: :doc:`../inertia/index`
- Explore type generation: :doc:`types`
- Configure history encryption: :doc:`../inertia/history-encryption`
- Set up pagination: :doc:`../inertia/responses`

Getting Help
============

If you encounter issues during migration:

- Check the `GitHub Issues <https://github.com/litestar-org/litestar-vite/issues>`_
- Join the `Litestar Discord <https://discord.gg/litestar>`_
- Review the `documentation <https://docs.litestar.dev/vite/>`_
