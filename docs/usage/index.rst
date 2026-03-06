=====
Usage
=====

Use these guides to move from installation to production runtime without bouncing between scattered examples.

.. grid:: 1 1 2 2
   :gutter: 2

   .. grid-item-card:: :octicon:`rocket` Install and Wire It
      :link: vite
      :link-type: doc

      Start with the plugin, path configuration, asset serving model, and the development runtime.

   .. grid-item-card:: :octicon:`gear` Choose a Runtime Mode
      :link: modes
      :link-type: doc

      Pick SPA, template, hybrid, or framework proxy mode based on how much frontend runtime you want.

   .. grid-item-card:: :octicon:`code-square` Generate Types
      :link: types
      :link-type: doc

      Export OpenAPI, routes, and Inertia page props into frontend-friendly TypeScript outputs.

   .. grid-item-card:: :octicon:`plug` Inertia Integration
      :link: inertia
      :link-type: doc

      Build server-driven SPAs with the same plugin and runtime model instead of a separate API stack.

Quick Start
-----------

.. code-block:: python
   :caption: app.py

   from pathlib import Path

   from litestar import Litestar
   from litestar_vite import PathConfig, ViteConfig, VitePlugin

   app = Litestar(
       plugins=[
           VitePlugin(
               config=ViteConfig(
                   dev_mode=True,
                   paths=PathConfig(root=Path(__file__).parent),
               )
           )
       ]
   )

.. code-block:: bash
   :caption: bootstrap a frontend

   litestar assets init --template react-inertia
   litestar assets install
   litestar run --reload

Migration Guide
---------------

.. grid:: 1 1 2 2
   :gutter: 2

   .. grid-item-card:: :octicon:`git-compare` 0.15 Migration Notes
      :link: migration-v015
      :link-type: doc

      Review the nested configuration changes and current CLI/runtime conventions before updating older projects.

.. toctree::
   :titlesonly:
   :maxdepth: 2
   :hidden:

   vite
   modes
   types
   inertia
   migration-v015
