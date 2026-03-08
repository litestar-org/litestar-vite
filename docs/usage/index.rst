===============
Getting Started
===============

Use these guides to move from installation to production runtime without bouncing between framework pages, demos, and reference docs.

.. grid:: 1 1 2 2
   :gutter: 2

   .. grid-item-card:: :octicon:`rocket` Install and Wire It
      :link: vite
      :link-type: doc

      Start with the plugin, the bridge file, path configuration, and the assets CLI.

   .. grid-item-card:: :octicon:`zap` Development Workflow
      :link: development
      :link-type: doc

      Keep HMR, proxy mode, direct mode, and manual dev-server workflows on one page.

   .. grid-item-card:: :octicon:`gear` Choose a Runtime Mode
      :link: modes
      :link-type: doc

      Pick SPA, template, hybrid, or framework proxy mode based on how much frontend runtime you want.

   .. grid-item-card:: :octicon:`code-square` Generate Types
      :link: types
      :link-type: doc

      Export OpenAPI, routes, and Inertia page props into frontend-friendly TypeScript outputs.

   .. grid-item-card:: :octicon:`shield-check` Production and Deploy
      :link: production
      :link-type: doc

      Build assets, publish them, and hand manifest-backed bundles back to Litestar cleanly.

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

.. toctree::
   :titlesonly:
   :maxdepth: 2
   :hidden:

   vite
   development
   production
   static-props
   modes
   types
