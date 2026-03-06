=============
Litestar Vite
=============

.. container:: hero-surface

   .. image:: https://raw.githubusercontent.com/litestar-org/branding/main/assets/Branding%20-%20SVG%20-%20Transparent/Vite%20-%20Banner%20-%20Inline%20-%20Light.svg
      :alt: Litestar Vite
      :class: landing-logo
      :width: 440px
      :align: center

   .. raw:: html

      <div id="badges" class="landing-badges">
         <img alt="PyPI - Version" src="https://img.shields.io/pypi/v/litestar-vite?labelColor=202235&color=edb641&logo=python&logoColor=edb641">
         <img alt="PyPI - Python Version" src="https://img.shields.io/pypi/pyversions/litestar-vite?logo=python&logoColor=edb641&labelColor=202235&color=edb641">
         <a href="https://github.com/litestar-org/litestar-vite/actions/workflows/ci.yml"><img alt="CI Status" src="https://img.shields.io/github/actions/workflow/status/litestar-org/litestar-vite/ci.yml?labelColor=202235&logo=github&logoColor=edb641&label=CI"></a>
         <img alt="Coverage" src="https://img.shields.io/codecov/c/github/litestar-org/litestar-vite?labelColor=202235&logo=codecov&logoColor=edb641">
      </div>

   Build frontends without splitting your stack.

   Litestar Vite keeps `Vite <https://vite.dev/>`_, your Litestar backend, and your frontend framework on one operational path. Use it for SPAs, server-rendered templates, Inertia apps, or framework proxy mode without inventing a second deployment story.

   .. grid:: 1 1 2 2
      :gutter: 2

      .. grid-item-card:: :octicon:`rocket` Get Started
         :link: usage/index
         :link-type: doc

         Install the plugin, wire the runtime, and ship your first app quickly.

      .. grid-item-card:: :octicon:`browser` Framework Guides
         :link: frameworks/index
         :link-type: doc

         Reach for React, Vue, Svelte, Angular, HTMX, or a meta-framework without changing the backend story.

      .. grid-item-card:: :octicon:`play` Demos
         :link: demos
         :link-type: doc

         See scaffolding, HMR, type generation, and production flows before you build your own app.

      .. grid-item-card:: :octicon:`code` API Reference
         :link: reference/index
         :link-type: doc

         Jump straight to configuration, plugin behavior, CLI commands, loader details, and Inertia internals.

Quick Install
-------------

.. container:: landing-section

   Start with the Python package, then scaffold or attach the frontend you actually want.

   .. code-block:: bash

      pip install litestar-vite

Featured Demos
--------------

.. grid:: 1 1 2 2
   :gutter: 2

   .. grid-item-card:: :octicon:`play` Project scaffolding
      :link: demos
      :link-type: doc
      :class-card: demo-frame

      .. image:: _static/demos/scaffolding.gif
         :alt: Project scaffolding demo
         :align: center
         :width: 100%

      Generate React, Vue, Svelte, HTMX, Inertia, Angular, Astro, Nuxt, or SvelteKit starters from the same CLI.

   .. grid-item-card:: :octicon:`zap` Hot Module Replacement
      :link: demos
      :link-type: doc
      :class-card: demo-frame

      .. image:: _static/demos/hmr.gif
         :alt: HMR demo
         :align: center
         :width: 100%

      Run Litestar once, keep one port, and let the Vite dev server stay behind the same application boundary.

.. toctree::
   :hidden:
   :titlesonly:

   usage/index
   frameworks/index
   inertia/index
   demos
   reference/index
   changelog
   contribution-guide
