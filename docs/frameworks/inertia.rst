==========
Inertia.js
==========

Inertia.js lets you build modern SPAs with server-side routing. No API layer needed -
your Litestar routes return page components directly.

At a Glance
-----------

- Templates: ``react-inertia`` / ``vue-inertia`` / ``svelte-inertia``
- Jinja examples: ``react-inertia-jinja`` / ``vue-inertia-jinja``
- Mode: ``hybrid`` (alias: ``inertia``)
- Source dir: ``resources/`` (Laravel-style)
- Dev: ``litestar run --reload`` (or ``litestar assets serve`` + ``litestar run``)

.. seealso::
   For comprehensive documentation, see the :doc:`/inertia/index` section.

Supported Frameworks
--------------------

- React: ``litestar assets init --template react-inertia``
- Vue: ``litestar assets init --template vue-inertia``
- Svelte: ``litestar assets init --template svelte-inertia``
- Template mode (examples): ``react-inertia-jinja`` / ``vue-inertia-jinja``

Quick Start
-----------

.. code-block:: python

   from typing import Any

   from litestar import Litestar, get
   from litestar_vite import ViteConfig, VitePlugin

   @get("/", component="Home")
   async def home() -> dict[str, Any]:
       return {"message": "Welcome!"}

   @get("/users", component="Users")
   async def users() -> dict[str, Any]:
       return {"users": [{"id": 1, "name": "Alice"}, {"id": 2, "name": "Bob"}]}

   app = Litestar(
       route_handlers=[home, users],
       plugins=[
           VitePlugin(config=ViteConfig(dev_mode=True, inertia=True)),
       ],
   )

Root Template
-------------

.. code-block:: html

   <!DOCTYPE html>
   <html>
   <head>
       {{ vite_hmr() }}
       {{ vite('resources/main.tsx') }}
   </head>
   <body>
       <div id="app" data-page="{{ inertia }}"></div>
   </body>
   </html>

React Entry Point
-----------------

.. code-block:: tsx

   import { createInertiaApp } from "@inertiajs/react";
   import { createRoot } from "react-dom/client";

   const pages = import.meta.glob("./pages/**/*.tsx", { eager: true });

   createInertiaApp({
     resolve: (name) => pages[`./pages/${name}.tsx`],
     setup({ el, App, props }) {
       createRoot(el).render(<App {...props} />);
     },
   });

Vue Entry Point
---------------

.. code-block:: typescript

   import { createInertiaApp } from "@inertiajs/vue3";
   import { createApp, h } from "vue";

   const pages = import.meta.glob("./pages/**/*.vue", { eager: true });

   createInertiaApp({
     resolve: (name) => pages[`./pages/${name}.vue`],
     setup({ el, App, props, plugin }) {
       createApp({ render: () => h(App, props) })
         .use(plugin)
         .mount(el);
     },
   });

Learn More
----------

.. grid:: 1 1 2 2
    :gutter: 2

    .. grid-item-card:: :octicon:`book` Full Documentation
        :link: /inertia/index
        :link-type: doc

        Configuration, helpers, responses, and more

    .. grid-item-card:: :octicon:`code-square` TypeScript Integration
        :link: /inertia/typescript
        :link-type: doc

        Type-safe routes and page props

    .. grid-item-card:: :octicon:`shield-check` Security
        :link: /inertia/csrf-protection
        :link-type: doc

        CSRF protection and history encryption

    .. grid-item-card:: :octicon:`beaker` Examples
        :link: https://github.com/litestar-org/litestar-fullstack-inertia
        :link-type: url

        Production-ready fullstack template

See Also
--------

- :doc:`/inertia/index` - Complete Inertia.js documentation
- :doc:`/inertia/installation` - Installation guide
- :doc:`/inertia/configuration` - Configuration reference
- `Inertia.js Documentation <https://inertiajs.com/>`_ - Official docs
