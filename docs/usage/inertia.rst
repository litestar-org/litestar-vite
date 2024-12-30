===================
Inertia Integration
===================

Litestar Vite provides optional integration with InertiaJS, allowing you to build modern single-page applications
while keeping your server-side routing and controllers. This integration is completely optional and can be added
to an existing Litestar Vite project.

For a complete example of a fullstack application using Litestar with Inertia, check out the
`Litestar Fullstack Inertia Template <https://github.com/litestar-org/litestar-fullstack-inertia>`_.

Installation
------------

Install the Inertia dependencies:

.. code-block:: bash

    pip install "litestar-vite"

For the frontend, install the Inertia client library for your framework:

.. code-block:: bash

    # For Vue.js
    npm install @inertiajs/vue3

    # For React
    npm install @inertiajs/react

    # For Svelte
    npm install @inertiajs/svelte

Basic Setup
-----------

1. Configure Inertia Plugin
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Add the Inertia plugin to your Litestar application:

.. code-block:: python

    from litestar import Litestar
    from litestar.contrib.jinja import JinjaTemplateEngine
    from litestar.template.config import TemplateConfig
    from litestar_vite.inertia import InertiaConfig, InertiaPlugin

    app = Litestar(
        template_config=TemplateConfig(
            engine=JinjaTemplateEngine(
                directory="templates"
            )
        ),
        plugins=[
            # ... VitePlugin configuration ...
            InertiaPlugin(
                config=InertiaConfig(
                    root_template="index.html",
                    redirect_unauthorized_to="/login"
                )
            )
        ]
    )

2. Create Root Template
~~~~~~~~~~~~~~~~~~~~~~~

Create the Inertia root template (templates/index.html):

.. code-block:: html

    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1.0" />
        {{ vite('resources/css/app.css') }}
        {{ js_routes }}
    </head>
    <body>
        <div id="app" data-page="{{ inertia | escape }}"></div>
        {{ vite_hmr() }}
        {{ vite('resources/js/app.js') }}
    </body>
    </html>

3. Initialize Frontend
~~~~~~~~~~~~~~~~~~~~~~

Set up your frontend entry point (resources/js/app.js):

.. code-block:: javascript

    import { createInertiaApp } from '@inertiajs/vue3'
    import { createApp, h } from 'vue'
    import Layout from './Layout.vue'

    createInertiaApp({
        resolve: name => {
            const pages = import.meta.glob('./pages/**/*.vue', { eager: true })
            const page = pages[`./pages/${name}.vue`]
            page.default.layout = page.default.layout || Layout
            return page
        },
        setup({ el, App, props, plugin }) {
            createApp({ render: () => h(App, props) })
                .use(plugin)
                .mount(el)
        }
    })

Features
--------

Route Handlers
~~~~~~~~~~~~~~

Create Inertia-powered route handlers, but using the `component` parameter to specify the client side component to render.

This parameter maps to the path (minus the .vue extension) of the component to render within the `resources/js/pages` directory.

The return value of any Litestar route will be serialized as normal and passed to the client side component as the `data.content` property.

.. code-block:: python

    from litestar import get

    @get("/", component="Home")
    async def home() -> dict[str, str]:
        return {
            "title": "Welcome",
            "message": "Hello from Litestar!"
        }

Shared Data
~~~~~~~~~~~

If you would like to share additional data with your client on any given route, you can use the `share` function.

This data will automatically serialized to JSON and passed to the client side component in a property named the same as the key you provide to the `share` function.

.. code-block:: python

    from litestar_vite.inertia import share

    @get("/")
    async def handler(request) -> dict[str, str]:
        # Available in all responses
        share(request, "user", {"name": "John"})
        return {"message": "Hello"}

Lazy Loading
~~~~~~~~~~~~

If you would like to conditionally return data to the client based on the reuqest using Inertia deferred data, you can use the `lazy` function.

This mehtod allows for deferred execution of methods.  Under normal cases, the data or callable referened in the lazy function will not be executed.  However, if the client requests the partial data or component, the element will be executed and rendered in the response.

It works with sync and async callables as well as static values.

.. code-block:: python

    from litestar_vite.inertia import lazy

    @get("/dashboard", component="Dashboard")
    async def dashboard():
        return {
            "stats": {"visits": 100},           # Loaded immediately
            "posts": lazy("posts", get_posts),  # Loaded on demand
        }

Navigation
----------

Redirects
~~~~~~~~~

Handle redirects with Inertia:

.. code-block:: python

    from litestar_vite.inertia import InertiaRedirect

    @post("/logout")
    async def logout(request):
        # ... logout logic ...
        return InertiaRedirect(request, "/login")

Back Navigation
~~~~~~~~~~~~~~~

Support browser back navigation:

.. code-block:: python

    from litestar_vite.inertia import InertiaBack

    @post("/cancel")
    async def cancel(request):
        return InertiaBack(request)

Error Handling
~~~~~~~~~~~~~~


To send error messages to the client, you can use the ``error`` function:

.. code-block:: python

    from litestar_vite.inertia import error

    @get("/profile")
    async def profile(request):
        if not request.user:
            error(request, "Please login first")
            return InertiaRedirect(request, "/login")
        return {"profile": get_profile()}

Flash Messages
~~~~~~~~~~~~~~

The native Flash plugin in Litestar is compatible with Inertia.  You can use the ``flash`` function to send messages to the client.

.. code-block:: python

    from litestar.plugins.flash import flash
    from litestar_vite.inertia import InertiaRedirect

    @get("/profile")
    async def profile(request: Request) -> dict[str, str] | InertiaRedirect:
        last_login = await get_last_login()
        if datetime.now() - last_login > timedelta(days=7):
            flash(request, "Hey, stranger!", category="info")
        return {"profile": get_profile()}


Security
--------

CSRF Protection
~~~~~~~~~~~~~~~

If you would like to use drop-in CSRF protection with the Inertia plugin, you can use the built in Litestar CSRF protection with the cookie_name set to ``csrftoken`` or with a header name set to ``x-csrftoken``.

If you use any other value, be sure to refernce the configuration details in the `Inertia documentation <https://inertiajs.com/csrf-protection>`_.


For more examples and best practices, refer to the
`Litestar Fullstack Inertia Template <https://github.com/litestar-org/litestar-fullstack-inertia>`_
and the `official InertiaJS documentation <https://inertiajs.com/>`_.
