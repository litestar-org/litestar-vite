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

.. literalinclude:: /../examples/react-inertia-jinja/templates/index.html
   :language: jinja
   :caption: templates/index.html

Key features:

- ``<title inertia>`` - Enables dynamic title updates via Inertia's ``<Head>`` component
- ``<script type="application/json" id="app_page" data-page="app">`` - Script-element bootstrap payload for the current default transport
- ``{{ inertia | safe }}`` - JSON-encoded page payload (use ``| safe`` to prevent escaping)
- ``{{ vite_hmr() }}`` and ``{{ vite() }}`` - Vite asset injection

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
   * - ``{{ inertia | safe }}``
     - JSON-encoded page payload for ``data-page`` or the script-element bootstrap
   * - ``{{ csrf_input }}``
     - Hidden CSRF input field
   * - ``{{ csrf_token }}``
     - Raw CSRF token value

Script Element Bootstrap
------------------------

By default, litestar-vite keeps the app root element empty and emits the JSON payload in a
matching script element:

.. code-block:: html

   <div id="app"></div>
   <script type="application/json" id="app_page" data-page="app">{{ inertia | safe }}</script>

For Inertia v2 clients, your browser entry must opt into the same transport:

.. code-block:: tsx

   createInertiaApp({
     defaults: {
       future: {
         useScriptElementForInitialPage: true,
       },
     },
     // resolve/setup...
   })

If ``InertiaConfig(ssr=True)`` is also enabled for an Inertia v2 client, mirror the same
``defaults.future.useScriptElementForInitialPage`` setting in ``resources/ssr.tsx`` or
``resources/ssr.ts`` so the Node SSR entry and the browser entry hydrate from the same payload.

.. note::
   Inertia v3 uses the script-element bootstrap by default, so the extra ``defaults.future`` block
   is only needed when you pin an Inertia v2 client.

Classic ``data-page`` Bootstrap
-------------------------------

The ``{{ inertia | safe }}`` helper can also be used directly with the older ``data-page`` attribute:

.. code-block:: json

   {
     "component": "Dashboard",
     "props": {"user": {"name": "Alice"}},
     "url": "/dashboard",
     "version": "abc123"
   }

.. important::

   Always use ``| safe`` with the inertia helper to prevent HTML escaping:

   .. code-block:: html

      <div id="app" data-page='{{ inertia | safe }}'></div>

   Without ``| safe``, special characters in props will be escaped, breaking JSON parsing.

Use this attribute form only when you set ``use_script_element=False``.

Dynamic Titles
--------------

Add the ``inertia`` attribute to ``<title>`` for dynamic title support:

.. code-block:: html

   <title inertia>Default Title</title>

Then update titles from your components using Inertia's ``<Head>`` component:

.. code-block:: tsx

   import { Head } from '@inertiajs/react';

   function Dashboard() {
     return (
       <>
         <Head title="Dashboard - My App" />
         {/* page content */}
       </>
     );
   }

SPA Mode (No Templates)
-----------------------

In SPA mode, you don't need Jinja templates. The ``index.html`` from
your Vite project is used directly:

.. code-block:: python

   ViteConfig(
       inertia=InertiaConfig(),
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

Litestar-Vite automatically injects the Inertia bootstrap payload and CSRF token.

Customizing the App Selector
----------------------------

Change the root element selector:

.. code-block:: python

   InertiaConfig(
       app_selector="#root",  # Default: "#app"
   )

.. code-block:: html

   <div id="root"></div>
   <script type="application/json" id="app_page" data-page="root">{{ inertia | safe }}</script>

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
   <div id="app" data-page='{{ inertia | safe }}'></div>
   {% endblock %}

See Also
--------

- :doc:`configuration` - Template configuration options
- :doc:`/usage/vite` - Vite asset helpers
