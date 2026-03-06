=====
Demos
=====

Litestar Vite ships with a small set of focused demos so you can evaluate the integration surface before wiring a real application.

.. grid:: 1 1 2 2
   :gutter: 2

   .. grid-item-card:: :octicon:`play` Project scaffolding
      :class-card: demo-frame

      .. image:: _static/demos/scaffolding.gif
         :alt: Project scaffolding demo
         :align: center
         :width: 100%

      Use ``litestar assets init --template ...`` to scaffold owned starters for SPA, Inertia, template, and framework modes.

   .. grid-item-card:: :octicon:`zap` Integrated HMR
      :class-card: demo-frame

      .. image:: _static/demos/hmr.gif
         :alt: HMR demo
         :align: center
         :width: 100%

      Keep the Litestar server as the public entry point while Vite HMR stays proxied behind it in development.

   .. grid-item-card:: :octicon:`package` Type generation
      :class-card: demo-frame

      .. image:: _static/demos/type-generation.gif
         :alt: Type generation demo
         :align: center
         :width: 100%

      Export OpenAPI, routes, and Inertia page props metadata into a frontend-friendly type generation pipeline.

   .. grid-item-card:: :octicon:`tools` Assets CLI workflow
      :class-card: demo-frame

      .. image:: _static/demos/assets-cli.gif
         :alt: Assets CLI demo
         :align: center
         :width: 100%

      Use ``litestar assets install``, ``serve``, ``build``, and ``doctor`` instead of stitching together ad hoc frontend commands.

   .. grid-item-card:: :octicon:`shield-check` Production build
      :class-card: demo-frame

      .. image:: _static/demos/production-build.gif
         :alt: Production build demo
         :align: center
         :width: 100%

      Build assets with ``litestar assets build`` and hand a manifest-backed production bundle back to Litestar for serving.

Try It Locally
--------------

.. code-block:: bash

   litestar assets init --template react
   litestar assets install
   litestar run --reload
   litestar assets build
