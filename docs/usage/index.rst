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

   from litestar import Litestar
   from litestar_vite import VitePlugin

   app = Litestar(plugins=[VitePlugin()])

.. code-block:: bash
   :caption: bootstrap a frontend

   litestar assets init --template react-inertia
   litestar assets install
   litestar run --reload

``VitePlugin()`` selects development or production behavior without application-side
``VITE_DEV_MODE`` parsing. It also receives the effective host and port from either
the built-in Uvicorn ``litestar run`` command or the Granian replacement.

For optional Rust-native production static serving with Granian 0.16+, add
``GranianPlugin(static="auto")`` without changing the Vite configuration:

.. code-block:: python
   :caption: app.py

   from litestar import Litestar
   from litestar_granian import GranianPlugin
   from litestar_vite import VitePlugin

   app = Litestar(
       plugins=[
           VitePlugin(),
           GranianPlugin(static="auto"),
       ]
   )

The Litestar static route remains available on every server. See
:doc:`production` for eligibility, fallback behavior, and the server matrix.

.. toctree::
   :titlesonly:
   :maxdepth: 2
   :hidden:

   vite
   development
   production
   streams
   static-props
   modes
   types
