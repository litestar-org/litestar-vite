=====================
Production and Deploy
=====================

Move from a development hotfile workflow to a manifest-backed production bundle without changing the Litestar integration model.

.. grid:: 1
   :gutter: 2

   .. grid-item-card:: :octicon:`shield-check` Production build
      :class-card: demo-frame

      .. image:: /_static/demos/production-build.gif
         :alt: Production build demo
         :align: center
         :width: 100%

      Build assets with the Litestar CLI, produce a manifest, and hand the compiled bundle back to the backend cleanly.

Building Assets
---------------

Build your assets for production using the CLI:

.. code-block:: bash

    litestar assets build

This command bundles and optimizes all assets, generates a manifest file, and outputs the files to the configured `bundle_dir`.

Serving Production Assets
-------------------------

The beginner configuration is server-neutral:

.. code-block:: python

    from litestar import Litestar
    from litestar_vite import VitePlugin

    app = Litestar(plugins=[VitePlugin()])

Litestar always registers the production static route. Test clients, Uvicorn,
Hypercorn, Daphne, and other ASGI servers therefore serve the same bundle
without server-specific application settings.

Granian 0.16+ can add native static serving as an optimization:

.. code-block:: python

    from litestar import Litestar
    from litestar_granian import GranianPlugin
    from litestar_vite import VitePlugin

    app = Litestar(
        plugins=[
            VitePlugin(),
            GranianPlugin(static="auto"),
        ]
    )

``static="auto"`` discovers Vite's server-neutral production bundle description.
An eligible build has one local, non-root asset route, a non-empty bundle with a
valid manifest or built ``index.html``, public assets, and no custom
``StaticFilesConfig``. Vite advertises no directory index, matching its existing
Litestar static route; SPA fallback remains the application handler's job.

Granian uses native serving only when these semantics are safe. Otherwise it
logs one INFO reason and leaves the request to Litestar. A native miss also
continues to the retained Litestar route and normal error handling.

.. warning::

   A Granian-native file hit does not enter ASGI. It bypasses Litestar
   middleware, guards, compression, custom response headers, exception
   handlers, and Python access logging. Protected assets
   (``exclude_static_from_auth=False``) and any user-supplied
   ``StaticFilesConfig`` automatically stay on the Litestar path.

Server Matrix
~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 34 66

   * - Server and configuration
     - Production asset owner
   * - Granian 0.16+ with ``static="auto"`` and an eligible bundle
     - Granian intercepts matching file hits; the Litestar route remains registered as fallback.
   * - Granian auto mode with an ineligible bundle or native miss
     - Litestar serves the route and preserves ASGI behavior.
   * - Granian with explicit static CLI flags
     - The explicit Granian route and mount win; provider discovery is disabled.
   * - Uvicorn, Hypercorn, Daphne, TestClient, or another ASGI server
     - Litestar serves the unchanged static route.
   * - A process started outside the Litestar CLI
     - Its external launcher owns that process; Litestar Vite does not adopt it.

Both built-in and Granian-backed ``litestar run`` commands pass their effective
``--host`` and ``--port`` values into ``LITESTAR_HOST``, ``LITESTAR_PORT``,
``APP_URL``, and the ``.litestar.json`` bridge before Vite or SSR sidecars start.

Advanced Configurations
~~~~~~~~~~~~~~~~~~~~~~~

Keep using the nested ``ViteConfig``, ``PathConfig``, ``RuntimeConfig``, and
``StaticFilesConfig`` options for nonstandard roots, CDN URLs, protected files,
custom static hooks, framework/SSR routing, and raw server flags. External or
root asset URLs, framework mode, custom static behavior, and protected assets
deliberately use Litestar rather than native interception.

Deploying Assets (`litestar assets deploy`)
-------------------------------------------

Deployment has two distinct concepts:

- **Where files are synced to** (fsspec target): ``DeployConfig.storage_backend`` (e.g. ``s3://bucket/assets``)
- **What URLs the browser should use** (public URL): ``DeployConfig.asset_url`` (e.g. ``https://cdn.example.com/assets/``)

Do **not** set ``asset_url`` to an ``s3://`` URL. Browsers can only fetch ``http(s)`` URLs.

``DeployConfig.asset_url`` is written to ``.litestar.json`` as ``deployAssetUrl`` and used by the Vite plugin as the ``base`` during
``vite build``. If Litestar serves HTML (template/hybrid/AppHandler transforms), also set ``PathConfig.asset_url`` to the same public URL.

.. code-block:: python

    from litestar_vite import DeployConfig, ViteConfig, VitePlugin

    VitePlugin(
        config=ViteConfig(
            deploy=DeployConfig(
                storage_backend="s3://bucket/assets",
                asset_url="https://cdn.example.com/assets/",
            )
        )
    )

See Also
--------

- :doc:`/usage/vite` - Installation and configuration
- :doc:`/usage/development` - Development and HMR workflow
- :doc:`/reference/deploy` - Deployment API reference
