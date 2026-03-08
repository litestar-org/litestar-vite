=============
Litestar Vite
=============

.. container:: hero-surface

   .. raw:: html

      <div class="landing-logo-stack">
        <img
          src="https://raw.githubusercontent.com/litestar-org/branding/main/assets/Branding%20-%20SVG%20-%20Transparent/Vite%20-%20Banner%20-%20Inline%20-%20Light.svg"
          alt="Litestar Vite"
          class="landing-logo landing-logo--light"
          width="440"
        />
        <img
          src="https://raw.githubusercontent.com/litestar-org/branding/main/assets/Branding%20-%20SVG%20-%20Transparent/Vite%20-%20Banner%20-%20Inline%20-%20Dark.svg"
          alt="Litestar Vite"
          class="landing-logo landing-logo--dark"
          width="440"
        />
      </div>

   .. raw:: html

      <div id="badges" class="landing-badges">
         <img alt="PyPI - Version" src="https://img.shields.io/pypi/v/litestar-vite?labelColor=202235&color=edb641&logo=python&logoColor=edb641">
         <img alt="PyPI - Python Version" src="https://img.shields.io/pypi/pyversions/litestar-vite?logo=python&logoColor=edb641&labelColor=202235&color=edb641">
         <a href="https://github.com/litestar-org/litestar-vite/actions/workflows/ci.yml"><img alt="CI Status" src="https://img.shields.io/github/actions/workflow/status/litestar-org/litestar-vite/ci.yml?labelColor=202235&logo=github&logoColor=edb641&label=CI"></a>
         <img alt="Coverage" src="https://img.shields.io/codecov/c/github/litestar-org/litestar-vite?labelColor=202235&logo=codecov&logoColor=edb641">
      </div>

   Keep Litestar in charge while Vite runs the frontend.

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

         Choose React, Vue, Svelte, Angular, HTMX, Inertia, or an SSR/meta-framework without changing the backend story.

      .. grid-item-card:: :octicon:`plug` Inertia Guide
         :link: frameworks/inertia/index
         :link-type: doc

         Follow the dedicated server-driven SPA guide without bouncing between framework and usage pages.

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

Choose a Path
-------------

.. grid:: 1 1 2 2
   :gutter: 2

   .. grid-item-card:: :octicon:`workflow` Vite Workflow
      :link: usage/vite
      :link-type: doc

      Install the plugin, understand the bridge file, and use the assets CLI without starting from a blank Vite setup.

   .. grid-item-card:: :octicon:`zap` Development Workflow
      :link: usage/development
      :link-type: doc

      Keep one public app entry point while Vite HMR, proxy mode, and two-port workflows stay understandable.

Developer Resources
-------------------

.. grid:: 1 1 2 2
   :gutter: 2

   .. grid-item-card:: :octicon:`git-compare` Changelog
      :link: changelog
      :link-type: doc

      Review release notes and migration-sensitive changes before updating existing projects.

   .. grid-item-card:: :octicon:`repo` Contribution Guide
      :link: contribution-guide
      :link-type: doc

      Work from the project contribution guidance instead of jumping out to the repository immediately.

.. toctree::
   :hidden:
   :titlesonly:
   :caption: Documentation

   usage/index
   frameworks/index
   reference/index

.. toctree::
   :hidden:
   :titlesonly:
   :caption: Developers

   contribution-guide
   changelog
