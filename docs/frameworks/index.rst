==================
Framework Examples
==================

Litestar Vite supports a wide range of frontend runtimes without forcing a single app shape.

.. grid:: 1 1 2 3
   :gutter: 2

   .. grid-item-card:: :octicon:`browser` React
      :link: react
      :link-type: doc

      Vite-first React apps with type generation and optional Inertia integration.

   .. grid-item-card:: :octicon:`browser` Vue
      :link: vue
      :link-type: doc

      Composition API, SSR entrypoints, and current Vite-aligned Vue structure.

   .. grid-item-card:: :octicon:`browser` Svelte
      :link: svelte
      :link-type: doc

      Lean Svelte apps with owned templates and current runtime wiring.

   .. grid-item-card:: :octicon:`browser` Angular
      :link: angular
      :link-type: doc

      Standalone Angular via Vite/Analog plus Angular CLI coverage where you need it.

   .. grid-item-card:: :octicon:`plug` Inertia.js
      :link: inertia
      :link-type: doc

      React, Vue, and Svelte server-driven SPA patterns with stable v2 protocol support.

   .. grid-item-card:: :octicon:`code` HTMX
      :link: htmx
      :link-type: doc

      Server-rendered flows with small JavaScript surfaces and fast iteration.

Meta-Frameworks
---------------

.. grid:: 1 1 3 3
   :gutter: 2

   .. grid-item-card:: :octicon:`rocket` Nuxt
      :link: nuxt
      :link-type: doc

      Proxy Nuxt through Litestar in development while preserving a clean API boundary.

   .. grid-item-card:: :octicon:`rocket` SvelteKit
      :link: sveltekit
      :link-type: doc

      Keep SvelteKit's app structure while sharing type generation and proxy integration.

   .. grid-item-card:: :octicon:`rocket` Astro
      :link: astro
      :link-type: doc

      Use Astro's static or server output while Litestar owns backend routes and APIs.

Quick Scaffold
--------------

.. tab-set::

   .. tab-item:: SPA & Templates

      .. code-block:: bash

         litestar assets init --template react
         litestar assets init --template vue
         litestar assets init --template svelte
         litestar assets init --template angular
         litestar assets init --template angular-cli
         litestar assets init --template htmx

   .. tab-item:: Inertia

      .. code-block:: bash

         litestar assets init --template react-inertia
         litestar assets init --template vue-inertia
         litestar assets init --template svelte-inertia
         # Template-mode examples: react-inertia-jinja / vue-inertia-jinja

   .. tab-item:: Meta-Frameworks

      .. code-block:: bash

         litestar assets init --template astro
         litestar assets init --template nuxt
         litestar assets init --template sveltekit

Real-World Example
------------------

.. grid:: 1
   :gutter: 2

   .. grid-item-card:: :octicon:`repo` Litestar Fullstack
      :link: https://github.com/litestar-org/litestar-fullstack
      :link-type: url

      Production-oriented reference application using Litestar, Vite, and React with authentication, team workflows, and type-safe frontend contracts.

.. toctree::
   :maxdepth: 2
   :hidden:

   react
   vue
   svelte
   angular
   htmx
   nuxt
   sveltekit
   astro
   inertia
