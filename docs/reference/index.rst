=============
API Reference
=============

Use the reference set when you need the exact config surface, runtime behavior, or internal API details rather than a narrative guide.

Reference Paths
---------------

.. grid:: 1 1 2 3
   :gutter: 2

   .. grid-item-card:: :octicon:`tools` Configuration
      :link: config
      :link-type: doc

      `ViteConfig`, nested config dataclasses, runtime options, path settings, deploy settings, SPA settings, and Inertia config.

   .. grid-item-card:: :octicon:`plug` Plugin and Middleware
      :link: plugin
      :link-type: doc

      The plugin lifecycle, proxy behavior, static handling, CLI integration, and middleware touch points.

   .. grid-item-card:: :octicon:`file-directory` Loader and HTML Transform
      :link: loader
      :link-type: doc

      Manifest lookup, asset tag generation, and HTML transform helpers used around templates and SSR responses.

   .. grid-item-card:: :octicon:`code-square` Code Generation
      :link: codegen
      :link-type: doc

      Export OpenAPI, routes, and Inertia page prop metadata into frontend-consumable outputs.

   .. grid-item-card:: :octicon:`terminal` CLI and Commands
      :link: cli
      :link-type: doc

      Assets CLI commands, init scaffolding, build/serve workflows, doctor output, and deployment helpers.

   .. grid-item-card:: :octicon:`device-desktop` Inertia Reference
      :link: inertia/index
      :link-type: doc

      Inertia request/response types, helpers, middleware, plugin hooks, and SSR-specific reference material.

.. toctree::
   :titlesonly:
   :hidden:

   cli
   commands
   config
   deploy
   exceptions
   html_transform
   inertia/index
   loader
   plugin
   spa
   codegen
