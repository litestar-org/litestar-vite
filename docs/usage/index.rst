=====
Usage
=====

The usage documentation is for end users of the library. It provides a high-level
overview of what features are available and how to use them.

Core Features
-------------

.. toctree::
    :titlesonly:
    :maxdepth: 2

    vite
    modes
    types
    inertia

Migration Guide
---------------

.. toctree::
    :titlesonly:
    :maxdepth: 1

    migration-v015

Getting Started
---------------

1. Installation
~~~~~~~~~~~~~~~

Install litestar-vite using your preferred package manager:

.. code-block:: bash

    pip install litestar-vite

**Note:** Nodeenv support is optional and off by default. To have litestar-vite provision Node inside your virtualenv, install with ``litestar-vite[nodeenv]`` and enable nodeenv detection (for example ``runtime.detect_nodeenv=True`` or ``make install NODEENV=1``). Otherwise, ensure you already have Node/npm installed.

2. Basic Configuration
~~~~~~~~~~~~~~~~~~~~~~

``dev_mode=True`` starts a Vite dev server for you and proxies HTTP + HMR traffic through Litestar on the same port. In production (``dev_mode=False``) Litestar serves prebuilt assets from ``paths.bundle_dir`` using ``manifest_name`` (defaults to ``public/manifest.json``) and prepends ``asset_url`` (default ``/static/``).

Use the nested configuration objects that shipped in 0.14+:

.. code-block:: python

    from litestar import Litestar
    from litestar_vite import ViteConfig, VitePlugin
    from litestar_vite.config import PathConfig, RuntimeConfig

    app = Litestar(
        plugins=[VitePlugin(config=ViteConfig(dev_mode=True))]
    )

3. Bootstrap the Typescript Environment
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

If you do not have an existing vite application, you can create a new one for your Litestar application with the following command:

.. code-block:: bash

    litestar assets init
    # Inertia (resources/) example
    litestar assets init --template react-inertia
    # Non-Inertia (src/) example under custom frontend dir
    litestar assets init --template react --frontend-dir web
    litestar assets install  # preferred over npm/pnpm/yarn install

During development run ``litestar run --reload`` (Vite dev server is launched and proxied automatically) or ``litestar assets serve`` if you want to run Vite alone. Build production assets with ``litestar assets build``.

For more detailed information about specific features, refer to the sections in the sidebar.
