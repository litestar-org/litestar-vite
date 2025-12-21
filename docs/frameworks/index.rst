==================
Framework Examples
==================

Litestar Vite supports a wide variety of frontend frameworks. This section provides
working examples for each supported framework.

.. grid:: 1 1 2 3
    :gutter: 3

    .. grid-item-card:: :octicon:`browser` React
        :link: react
        :link-type: doc

        React 18+ with Vite

    .. grid-item-card:: :octicon:`browser` Vue
        :link: vue
        :link-type: doc

        Vue 3 with Composition API

    .. grid-item-card:: :octicon:`browser` Svelte
        :link: svelte
        :link-type: doc

        Svelte 5 with Vite

    .. grid-item-card:: :octicon:`browser` Angular
        :link: angular
        :link-type: doc

        Angular 18+ (Vite or CLI)

    .. grid-item-card:: :octicon:`plug` Inertia.js
        :link: inertia
        :link-type: doc

        SPAs with server-side routing

    .. grid-item-card:: :octicon:`code` HTMX
        :link: htmx
        :link-type: doc

        Hypermedia-driven applications

Meta-Frameworks
~~~~~~~~~~~~~~~

.. grid:: 1 1 2 3
    :gutter: 3

    .. grid-item-card:: :octicon:`rocket` Nuxt
        :link: nuxt
        :link-type: doc

        Universal Vue 3 SSR framework

    .. grid-item-card:: :octicon:`rocket` SvelteKit
        :link: sveltekit
        :link-type: doc

        Full-stack Svelte framework

    .. grid-item-card:: :octicon:`rocket` Astro
        :link: astro
        :link-type: doc

        Content-focused multi-framework SSG/SSR

Real-World Example
------------------

.. grid:: 1
    :gutter: 3

    .. grid-item-card:: :octicon:`repo` Litestar Fullstack
        :link: https://github.com/litestar-org/litestar-fullstack
        :link-type: url

        Production-ready fullstack application template using Litestar, Vite, and React.
        Demonstrates authentication, team management, type-safe routing, and best practices.

Quick Scaffold
--------------

Use the CLI to scaffold any framework:

.. code-block:: bash

    # React (SPA)
    litestar assets init --template react

    # React with routing (new in v0.15)
    litestar assets init --template react-router
    litestar assets init --template react-tanstack

    # Vue
    litestar assets init --template vue

    # Svelte
    litestar assets init --template svelte

    # Angular (Vite-based)
    litestar assets init --template angular

    # Angular CLI (traditional)
    litestar assets init --template angular-cli

    # HTMX
    litestar assets init --template htmx

    # Meta-frameworks
    litestar assets init --template nuxt
    litestar assets init --template sveltekit
    litestar assets init --template astro

    # With Inertia.js
    litestar assets init --template react-inertia
    litestar assets init --template vue-inertia
    litestar assets init --template svelte-inertia  # New in v0.15
    # Template-mode examples (Jinja)
    # react-inertia-jinja / vue-inertia-jinja

Framework Comparison
--------------------

.. list-table::
   :widths: 20 15 25 20 20
   :header-rows: 1

   * - Framework
     - Source Dir
     - Dev Server
     - Inertia Support
     - Best For
   * - React
     - ``src/``
     - Vite + HMR
     - Yes
     - SPAs, complex UIs
   * - Vue
     - ``src/``
     - Vite + HMR
     - Yes
     - SPAs, progressive enhancement
   * - Svelte
     - ``src/``
     - Vite + HMR
     - Yes
     - Lightweight SPAs
   * - Angular
     - ``src/``
     - Vite (Analog)
     - No
     - Enterprise apps
   * - Angular CLI
     - ``src/``
     - ng serve
     - No
     - Standard Angular workflow
   * - HTMX
     - ``src/``
     - Vite + HMR
     - No
     - Server-rendered, minimal JS
   * - Nuxt
     - ``pages/``
     - Nuxt dev
     - No
     - Universal SSR, auto-routing
   * - SvelteKit
     - ``src/routes/``
     - SvelteKit dev
     - No
     - Full-stack Svelte, SSR
   * - Astro
     - ``src/pages/``
     - Astro dev
     - No
     - Static sites, islands architecture

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
