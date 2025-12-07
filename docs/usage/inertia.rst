===================
Inertia Integration
===================

Litestar Vite provides optional integration with InertiaJS, allowing you to build modern single-page applications while keeping your server-side routing and controllers.

For a complete example of a fullstack application using Litestar with Inertia, check out the `Litestar Fullstack Inertia Template <https://github.com/litestar-org/litestar-fullstack-inertia>`_.

Installation
------------

Install the Inertia dependencies:

.. code-block:: bash

    pip install "litestar-vite"

For the frontend, install the Inertia client library for your framework and the Litestar Vite plugin, which provides the necessary helpers.

.. code-block:: bash

    # For Vue.js
    npm install @inertiajs/vue3 litestar-vite-plugin

    # For React
    npm install @inertiajs/react litestar-vite-plugin

    # For Svelte
    npm install @inertiajs/svelte litestar-vite-plugin

Configuration
-------------

1. Configure Inertia Plugin (`InertiaConfig`)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Add the `InertiaPlugin` to your Litestar application and configure it with the `InertiaConfig` object.

.. code-block:: python

    from litestar import Litestar
    from litestar.contrib.jinja import JinjaTemplateEngine
    from litestar.template.config import TemplateConfig
    from litestar_vite.inertia import InertiaConfig, InertiaPlugin
    from litestar_vite import VitePlugin

    app = Litestar(
        template_config=TemplateConfig(
            engine=JinjaTemplateEngine(
                directory="templates"
            )
        ),
        plugins=[
            VitePlugin(), # VitePlugin must be included
            InertiaPlugin(
                config=InertiaConfig(
                    # Add your configuration options here
                )
            )
        ]
    )

**Available `InertiaConfig` Parameters**:

.. list-table::
   :widths: 25 15 60
   :header-rows: 1

   * - Parameter
     - Type
     - Description
   * - `root_template`
     - `str`
     - The name of the root Jinja2 template. Defaults to `"index.html"`.
   * - `component_opt_keys`
     - `tuple[str, ...]`
     - Keys used in route handlers to specify the Inertia component. Checked in order. Defaults to `("component", "page")`.
   * - `exclude_from_js_routes_key`
     - `str`
     - The key used in route handlers to exclude a route from the generated JS routes file. Defaults to `"exclude_from_routes"`.
   * - `redirect_unauthorized_to`
     - `str | None`
     - A URL to redirect unauthorized requests to. Defaults to `None`.
   * - `redirect_404`
     - `str | None`
     - A URL to redirect `NotFoundException` (404) requests to. Defaults to `None`.
   * - `extra_static_page_props`
     - `dict[str, Any]`
     - A dictionary of props to share with every page.
   * - `extra_session_page_props`
     - `set[str]`
     - A set of session keys whose values will be shared with every page.
   * - `encrypt_history`
     - `bool`
     - Enable history encryption globally for all Inertia pages. Defaults to `False`.

2. Create Root Template
~~~~~~~~~~~~~~~~~~~~~~~

Create the Inertia root template (e.g., `templates/index.html`). The `js_routes` callable, which makes your Litestar routes available to the frontend, is automatically injected.

.. code-block:: html

    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1.0" />
        {{ vite('resources/main.ts') }}
        {{ js_routes }}
    </head>
    <body>
        <div id="app" data-page="{{ inertia }}"></div>
        {{ vite_hmr() }}
    </body>
    </html>

The injected script exports your routes as both ``window.serverRoutes`` (preferred, name → URI map) and ``window.routes``. Both are typed when you import the generated helpers.

3. Initialize Frontend
~~~~~~~~~~~~~~~~~~~~~~

Set up your frontend entry point (e.g., `resources/main.ts`). Use the `resolvePageComponent` helper from `litestar-vite-plugin/inertia-helpers` to dynamically import your page components.

.. code-block:: javascript
    :caption: resources/main.ts

    import { createInertiaApp } from '@inertiajs/vue3'
    import { createApp, h } from 'vue'
    import { resolvePageComponent } from 'litestar-vite-plugin/inertia-helpers'
    import Layout from './Layout.vue'

    createInertiaApp({
        resolve: async name => {
            const page = await resolvePageComponent(`./pages/${name}.vue`, import.meta.glob('./pages/**/*.vue'))
            page.default.layout = page.default.layout || Layout
            return page
        },
        setup({ el, App, props, plugin }) {
            createApp({ render: () => h(App, props) })
                .use(plugin)
                .mount(el)
        }
    })

Python Helpers
--------------

Route Handlers
~~~~~~~~~~~~~~

Create Inertia-powered route handlers by using the `component` parameter in your route decorator. This parameter specifies the client-side component to render from your pages directory (e.g., `resources/pages`).

The return value of the route handler will be passed as props to the component.

.. code-block:: python

    from litestar.handlers import get

    @get("/", component="Home")
    async def home() -> dict[str, str]:
        return {
            "title": "Welcome",
            "message": "Hello from Litestar!"
        }

Shared Data
~~~~~~~~~~~

Use the `share()` function to provide data that should be available on every page request. This is useful for request-specific shared data like user information or flash messages.

.. code-block:: python

    from litestar.handlers import get
    from litestar.requests import Request
    from litestar_vite.inertia import share

    @get("/")
    async def handler(request: Request) -> dict[str, str]:
        # This "user" prop will be available in all components
        share(request, "user", {"name": "John Doe"})
        return {"message": "Hello"}

For application-wide shared data (static) or session-based shared keys, you can also use the `extra_static_page_props` and `extra_session_page_props` options in `InertiaConfig`.

Lazy Props
~~~~~~~~~~

Use the `lazy()` function to mark props that should only be included during partial reloads, not on initial page load. This is useful for data that isn't immediately visible or that you want to load on demand.

.. code-block:: python

    from litestar.handlers import get
    from litestar_vite.inertia import lazy

    @get("/dashboard", component="Dashboard")
    async def dashboard() -> dict[str, Any]:
        return {
            "stats": {"visits": 100},           # Always included
            "notifications": lazy(get_notifications),  # Only on partial reload
        }

**Understanding Lazy Prop Behavior**:

There are two ways to use ``lazy()``:

1. **Static value** (bandwidth optimization): The value is computed immediately but only sent during partial reloads.

   .. code-block:: python

       lazy("key", expensive_result)  # Value already computed

2. **Callable** (bandwidth + CPU optimization): The callable is only invoked during partial reloads.

   .. code-block:: python

       lazy("key", expensive_function)  # Function called only when needed

.. warning::

    **Avoid the "False Lazy" pitfall!**

    .. code-block:: python

        # WRONG - function is called immediately (eager evaluation)
        lazy("stats", get_expensive_stats())

        # CORRECT - function reference passed, called only on partial reload
        lazy("stats", get_expensive_stats)

    With the wrong pattern, the expensive function runs on every request even though
    the result is only sent during partial reloads. Pass the function reference
    (without parentheses) to defer both computation and transmission.

Deferred Props
~~~~~~~~~~~~~~

Use the `defer()` function to defer loading of expensive data. This data will not be included in the initial page load. Instead, it will be fetched automatically by the client (if configured) or when explicitly requested via a partial reload.

.. code-block:: python

    from litestar.handlers import get
    from litestar_vite.inertia import defer

    async def get_posts():
        # Expensive database query
        return [{"title": "Post 1"}, {"title": "Post 2"}]

    @get("/dashboard", component="Dashboard")
    async def dashboard() -> dict[str, Any]:
        return {
            "stats": {"visits": 100},           # Loaded immediately
            "posts": defer(get_posts),          # Loaded on demand
        }

Merge Props
~~~~~~~~~~~

Use the `merge()` function to combine new data with existing props on the client side. This is particularly useful for infinite scrolling or pagination where you want to append new results to an existing list.

.. code-block:: python

    from litestar.handlers import get
    from litestar_vite.inertia import merge

    @get("/users", component="Users")
    async def users(page: int = 1) -> dict[str, Any]:
        new_users = await get_users(page)
        return {
            # Append new users to the existing list
            "users": merge(new_users, strategy="append"),
        }

Supported strategies are `"append"` (default), `"prepend"`, and `"deep"` (for recursive merging). You can also use `match_on` to update existing items instead of duplicating them:

.. code-block:: python

    # Update existing items if IDs match, otherwise append
    "users": merge(new_users, match_on="id")

Prop Filtering
~~~~~~~~~~~~~~

Use the ``only()`` and ``except_()`` helpers to create explicit prop filters. These are useful for controlling which props are included during partial reloads.

.. code-block:: python

    from litestar_vite.inertia import only, except_

    # Include only specific props
    filter_users = only("users", "pagination")

    # Exclude specific props
    filter_no_meta = except_("meta", "debug_info")

    # Use with should_include() method
    if filter_users.should_include("users"):  # True
        # Include this prop
        pass

    if filter_users.should_include("settings"):  # False
        # Skip this prop
        pass

These filters integrate with the Inertia partial reload mechanism to efficiently return only requested data.

Scroll Props (Infinite Scroll)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Use the ``scroll_props()`` helper to create pagination metadata for infinite scrolling. This works with the ``merge()`` function to enable seamless infinite scroll UIs.

.. code-block:: python

    from litestar_vite.inertia import scroll_props, merge

    @get("/posts", component="Posts")
    async def posts(page: int = 1) -> dict[str, Any]:
        posts_page = await get_posts(page=page, per_page=20)
        return {
            "posts": merge(posts_page.items, strategy="append"),
            "scroll": scroll_props(
                page_name="page",
                current_page=page,
                previous_page=page - 1 if page > 1 else None,
                next_page=page + 1 if posts_page.has_next else None,
            ),
        }

History Encryption
~~~~~~~~~~~~~~~~~~

Inertia v2 supports history encryption to protect sensitive data in the browser history. Use these parameters in ``InertiaResponse``:

.. code-block:: python

    from litestar_vite.inertia import InertiaResponse

    @get("/sensitive-data", component="SensitiveData")
    async def sensitive() -> InertiaResponse:
        return InertiaResponse(
            component="SensitiveData",
            props={"secret": "classified"},
            encrypt_history=True,   # Encrypt this page in browser history
        )

    @get("/logout", component="Logout")
    async def logout() -> InertiaResponse:
        return InertiaResponse(
            component="Logout",
            props={},
            clear_history=True,     # Clear encrypted history on this navigation
        )

You can also use the ``clear_history()`` helper to mark the session for history clearing:

.. code-block:: python

    from litestar_vite.inertia import clear_history

    @post("/logout")
    async def logout(request: Request) -> InertiaRedirect:
        clear_history(request)  # Mark session for history clearing
        return InertiaRedirect(request, "/login")

To enable history encryption globally, set it in ``InertiaConfig``:

.. code-block:: python

    InertiaConfig(
        encrypt_history=True,  # Encrypt all pages by default
    )

Navigation
----------

Redirects
~~~~~~~~~

To perform a server-side redirect that Inertia can handle, return an `InertiaRedirect` response.

.. code-block:: python

    from litestar.handlers import post
    from litestar.requests import Request
    from litestar_vite.inertia import InertiaRedirect

    @post("/logout")
    async def logout(request: Request) -> InertiaRedirect:
        # ... logout logic ...
        return InertiaRedirect(request, "/login")

Back Navigation
~~~~~~~~~~~~~~~

To redirect the user to their previous location in the browser history, return `InertiaBack`.

.. code-block:: python

    from litestar.handlers import post
    from litestar.requests import Request
    from litestar_vite.inertia import InertiaBack

    @post("/cancel")
    async def cancel(request: Request) -> InertiaBack:
        return InertiaBack(request)

Flash Messages
~~~~~~~~~~~~~~

The native Litestar `flash()` plugin is compatible with Inertia. Shared flash messages are automatically picked up and sent to the client.

.. code-block:: python

    from litestar.handlers import get
    from litestar.plugins.flash import flash
    from litestar.requests import Request

    @get("/profile", component="Profile")
    async def profile(request: Request) -> dict[str, Any]:
        flash(request, "Your profile was updated!", category="success")
        return {"profile": get_profile()}

JavaScript/TypeScript Helpers
-----------------------------

The `litestar-vite-plugin/inertia-helpers` module provides several functions to make working with your Litestar routes on the frontend easier.

`route()`
~~~~~~~~~

Generate a URL for a named Litestar route. It uses the routes generated by the `InertiaPlugin` and injected into your root template.

.. code-block:: javascript

    import { route } from 'litestar-vite-plugin/inertia-helpers';

    // Simple route
    const homeUrl = route('home'); // -> '/'

    // Route with parameters
    const userUrl = route('user-profile', { userId: 123 }); // -> '/users/123'

`isRoute()` and `isCurrentRoute()`
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Check if the current URL matches a given route name or pattern. This is useful for applying active states to navigation links.

.. code-block:: javascript

    import { isCurrentRoute } from 'litestar-vite-plugin/inertia-helpers';

    // Check against a specific route name
    const onUsersPage = isCurrentRoute('user-list');

    // Check against a pattern (wildcard)
    const inUserSection = isCurrentRoute('user-*');

`toRoute()` and `currentRoute()`
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Convert a full URL to its matching route name or get the route name for the current page.

.. code-block:: javascript

    import { toRoute, currentRoute } from 'litestar-vite-plugin/inertia-helpers';

    const routeName = toRoute('https://myapp.com/users/123'); // -> 'user-profile'

    const current = currentRoute(); // -> e.g., 'dashboard'

Protocol v2 Support
-------------------

Litestar Vite fully supports the Inertia.js v2 protocol:

*   **Deferred Props**: Using ``defer()`` and automatic partial reload handling.
*   **Infinite Scrolling**: Using ``merge()`` with 'append'/'prepend' strategies.
*   **History Encryption**: Support for ``encryptHistory`` and ``clearHistory``.
*   **Asset Versioning**: Automatic version checking using the Vite manifest hash.

The plugin automatically handles:

*   ``409 Conflict`` responses for asset version mismatches.
*   ``303 See Other`` for redirects.
*   ``Vary: Accept`` headers for proper caching.

Security
--------

CSRF Protection
~~~~~~~~~~~~~~~

Litestar's built-in CSRF protection is compatible with Inertia. Ensure the cookie name is set to `XSRF-TOKEN` and the header name is set to `X-XSRF-TOKEN` in your `CSRFConfig`, as this is what Inertia's Axios instance expects by default.

.. code-block:: python

    from litestar.config.csrf import CSRFConfig

    csrf_config = CSRFConfig(
        secret="your-secret",
        cookie_name="XSRF-TOKEN",
        header_name="X-XSRF-TOKEN"
    )
