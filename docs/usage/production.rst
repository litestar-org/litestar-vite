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
