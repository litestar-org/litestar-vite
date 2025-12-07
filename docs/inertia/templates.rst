=========
Templates
=========

Configure the root template for Inertia applications.

.. seealso::
   Official Inertia.js docs: `Server-Side Setup <https://inertiajs.com/server-side-setup>`_

Root Template
-------------

The root template is the HTML shell for your Inertia application.
It's rendered on initial page loads with page data embedded.

.. code-block:: html
   :caption: templates/index.html

   <!DOCTYPE html>
   <html lang="en">
   <head>
       <meta charset="utf-8" />
       <meta name="viewport" content="width=device-width, initial-scale=1" />
       <title>My App</title>
       {{ vite('resources/main.ts') }}
       {{ vite_hmr() }}
   </head>
   <body>
       <div id="app" data-page="{{ inertia }}"></div>
       {{ js_routes }}
   </body>
   </html>

Template Helpers
----------------

These helpers are automatically available in your templates:

.. list-table::
   :widths: 30 70
   :header-rows: 1

   * - Helper
     - Description
   * - ``{{ vite('path') }}``
     - Include Vite assets (JS, CSS)
   * - ``{{ vite_hmr() }}``
     - HMR client script (dev mode)
   * - ``{{ inertia }}``
     - JSON-encoded page props for ``data-page``
   * - ``{{ js_routes }}``
     - Route definitions script
   * - ``{{ csrf_input }}``
     - Hidden CSRF input field
   * - ``{{ csrf_token }}``
     - Raw CSRF token value

The inertia Helper
------------------

The ``{{ inertia }}`` helper outputs JSON for the ``data-page`` attribute:

.. code-block:: json

   {
     "component": "Dashboard",
     "props": {"user": {"name": "Alice"}},
     "url": "/dashboard",
     "version": "abc123"
   }

Always use it in the ``data-page`` attribute:

.. code-block:: html

   <div id="app" data-page="{{ inertia }}"></div>

The js_routes Helper
--------------------

``{{ js_routes }}`` injects route definitions as a script:

.. code-block:: html

   <script type="module">
   globalThis.routes = JSON.parse('{"home":"/","users":"/users",...}')
   </script>

Routes are available as ``window.routes`` for the ``route()`` helper.

SPA Mode (No Templates)
-----------------------

In SPA mode, you don't need Jinja templates. The ``index.html`` from
your Vite project is used directly:

.. code-block:: python

   ViteConfig(
       mode="hybrid",  # Auto-detected with inertia=True
       inertia=InertiaConfig(spa_mode=True),
   )

Your ``index.html`` (in ``resource_dir``):

.. code-block:: html

   <!DOCTYPE html>
   <html>
   <head>
       <script type="module" src="/resources/main.ts"></script>
   </head>
   <body>
       <div id="app"></div>
   </body>
   </html>

Litestar-Vite automatically injects ``data-page`` and CSRF token.

Customizing the App Selector
----------------------------

Change the root element selector:

.. code-block:: python

   InertiaConfig(
       app_selector="#root",  # Default: "#app"
   )

.. code-block:: html

   <div id="root" data-page="{{ inertia }}"></div>

Multiple Templates
------------------

Use different templates for different sections:

.. code-block:: python

   @get("/admin/dashboard", component="Admin/Dashboard")
   async def admin_dashboard() -> InertiaResponse:
       return InertiaResponse(
           content={...},
           template_name="admin.html",  # Override default
       )

Template Organization
---------------------

Recommended structure:

.. code-block:: text

   templates/
   ├── index.html       # Main Inertia template
   ├── admin.html       # Admin section template
   └── partials/
       └── head.html    # Shared head content

Using template inheritance:

.. code-block:: html
   :caption: templates/base.html

   <!DOCTYPE html>
   <html>
   <head>
       {% block head %}
       {{ vite('resources/main.ts') }}
       {{ vite_hmr() }}
       {% endblock %}
   </head>
   <body>
       {% block body %}{% endblock %}
   </body>
   </html>

.. code-block:: html
   :caption: templates/index.html

   {% extends "base.html" %}

   {% block body %}
   <div id="app" data-page="{{ inertia }}"></div>
   {{ js_routes }}
   {% endblock %}

See Also
--------

- :doc:`configuration` - Template configuration options
- :doc:`/usage/vite` - Vite asset helpers
