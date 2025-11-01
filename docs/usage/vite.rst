================
Vite Integration
================

Litestar Vite provides seamless integration with Vite, a modern frontend build tool.

Installation
------------

Install the package:

.. code-block:: bash

    pip install litestar-vite

.. note::
    If you do not have an existing node environment, you can use `nodeenv` to automatically configure one for you by using the ``litestar-vite[nodeenv]`` extras option.

Setup Options
-------------

There are two ways to set up Vite with Litestar:

1. Using the CLI (Recommended)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The CLI provides a streamlined setup process:

.. code-block:: bash

    # Initialize a new Vite project
    litestar assets init

This command will:

- Create a new Vite project structure
- Install necessary dependencies
- Set up configuration files
- Create example templates

The generated project structure will look like this:

.. code-block:: text

    my_project/
    ├── public/           # Compiled assets
    ├── resources/        # Source assets
    │   ├── js/
    │   ├── css/
    │   └── templates/
    ├── src/             # Python source code
    ├── package.json     # Node.js dependencies
    ├── vite.config.js   # Vite configuration
    └── pyproject.toml   # Python dependencies

2. Manual Setup
~~~~~~~~~~~~~~~

If you prefer more control, you can set up Vite manually:

1. Initialize the frontend project:

.. code-block:: bash

    npm init -y
    npm install vite
    npm install -D litestar-vite-plugin

2. Create ``vite.config.js``:

.. code-block:: javascript

    import { defineConfig } from 'vite'
    import litestar from 'litestar-vite-plugin'

    export default defineConfig({
        plugins: [
            litestar({
                input: ['resources/main.ts'],
            })
        ]
    })

Configuration
-------------

The integration is configured in two places: the Python backend via the `VitePlugin` and the frontend via the `litestar-vite-plugin` in your `vite.config.ts`.

Python Configuration (`ViteConfig`)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

You configure the Litestar backend using the `ViteConfig` object passed to the `VitePlugin`.

.. code-block:: python

    from litestar import Litestar
    from litestar_vite import ViteConfig, VitePlugin

    app = Litestar(
        plugins=[
            VitePlugin(
                config=ViteConfig(
                    # Add your configuration options here
                )
            )
        ]
    )

**Available `ViteConfig` Parameters**:

.. list-table::
   :widths: 25 15 60
   :header-rows: 1

   * - Parameter
     - Type
     - Description
   * - `bundle_dir`
     - `Path | str`
     - Location of compiled assets from Vite. Defaults to `"public"`.
   * - `resource_dir`
     - `Path | str`
     - Directory for TypeScript/JavaScript source files. Defaults to `"resources"`.
   * - `public_dir`
     - `Path | str`
     - The public directory Vite serves assets from. Defaults to `"public"`.
   * - `manifest_name`
     - `str`
     - Name of the Vite manifest file. Defaults to `"manifest.json"`.
   * - `hot_file`
     - `str`
     - Name of the file that contains the Vite server URL for HMR. Defaults to `"hot"`.
   * - `hot_reload`
     - `bool`
     - Enable or disable Hot Module Replacement (HMR). Defaults to `True` in dev mode.
   * - `ssr_enabled`
     - `bool`
     - Enable Server-Side Rendering (SSR). Defaults to `False`.
   * - `ssr_output_dir`
     - `Path | str | None`
     - Directory for SSR output. Required if `ssr_enabled` is `True`.
   * - `root_dir`
     - `Path | str | None`
     - Base path of your application. Defaults to the current working directory.
   * - `is_react`
     - `bool`
     - Enable React-specific features. Defaults to `False`.
   * - `asset_url`
     - `str`
     - Base URL for static assets. Defaults to `"/static/"`.
   * - `host`
     - `str`
     - Host for the Vite dev server. Defaults to `"localhost"`.
   * - `protocol`
     - `str`
     - Protocol for the Vite dev server (`http` or `https`). Defaults to `"http"`.
   * - `port`
     - `int`
     - Port for the Vite dev server. Defaults to `5173`.
   * - `run_command`
     - `list[str]`
     - Command to run the Vite dev server. Defaults to `["npm", "run", "dev"]`.
   * - `build_watch_command`
     - `list[str]`
     - Command for development builds. Defaults to `["npm", "run", "watch"]`.
   * - `build_command`
     - `list[str]`
     - Command for production builds. Defaults to `["npm", "run", "build"]`.
   * - `install_command`
     - `list[str]`
     - Command to install frontend dependencies. Defaults to `["npm", "install"]`.
   * - `use_server_lifespan`
     - `bool`
     - Manage the Vite dev server lifecycle with the Litestar app. Defaults to `False`.
   * - `dev_mode`
     - `bool`
     - Enables development mode, which runs Vite with HMR or watch build. Defaults to `False`.
   * - `detect_nodeenv`
     - `bool`
     - If `True`, the plugin will install and configure `nodeenv` if available. Defaults to `True`.
   * - `set_environment`
     - `bool`
     - If `True`, sets the plugin configuration as environment variables. Defaults to `True`.
   * - `set_static_folders`
     - `bool`
     - If `True`, automatically configures Litestar to serve static assets. Defaults to `True`.

Vite Plugin Configuration (`litestar-vite-plugin`)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

You configure the Vite frontend build process in your `vite.config.ts` (or `.js`).

.. code-block:: javascript

    import { defineConfig } from 'vite'
    import litestar from 'litestar-vite-plugin'

    export default defineConfig({
        plugins: [
            litestar({
                // Add your configuration options here
                input: ['resources/main.ts'],
            })
        ]
    })

**Available Plugin Parameters**:

.. list-table::
   :widths: 25 15 60
   :header-rows: 1

   * - Parameter
     - Type
     - Description
   * - `input`
     - `string | string[]`
     - **Required**. The path or paths of the entry points to compile.
   * - `assetUrl`
     - `string`
     - The base path for asset URLs. Defaults to `'/static/'`.
   * - `bundleDirectory`
     - `string`
     - The directory where compiled assets are written. Defaults to `'public/dist'`.
   * - `resourceDirectory`
     - `string`
     - The directory for source assets. Defaults to `'resources'`.
   * - `hotFile`
     - `string`
     - The path to the "hot" file. Defaults to `${bundleDirectory}/hot`.
   * - `ssr`
     - `string | string[]`
     - The path of the SSR entry point.
   * - `ssrOutputDirectory`
     - `string`
     - The directory where the SSR bundle is written. Defaults to `'${bundleDirectory}/bootstrap/ssr'`.
   * - `refresh`
     - `boolean | string | string[] | RefreshConfig | RefreshConfig[]`
     - Configuration for performing a full page refresh on file changes. Defaults to `false`.
   * - `detectTls`
     - `string | boolean | null`
     - Automatically detect and use TLS certificates. Defaults to `null`.
   * - `autoDetectIndex`
     - `boolean`
     - Automatically detect `index.html` as the entry point. Defaults to `True`.
   * - `transformOnServe`
     - `(code: string, url: DevServerUrl) => string`
     - A function to transform code while serving.

Template Integration
~~~~~~~~~~~~~~~~~~~~

Use the `vite()` and `vite_hmr()` callables in your Jinja2 templates to include the assets.

.. code-block:: html

    <!DOCTYPE html>
    <html>
    <head>
        {{ vite('resources/css/styles.css') }}
    </head>
    <body>
        <div id="app"></div>
        {{ vite_hmr() }}
        {{ vite('resources/js/main.js') }}
    </body>
    </html>

Development Workflow
--------------------

Development Server
~~~~~~~~~~~~~~~~~~

When `use_server_lifespan` is set to `True` in `ViteConfig`, the Litestar CLI will automatically manage the Vite development server alongside your Litestar application.

.. code-block:: bash

    litestar run

If you prefer to manage the Vite server manually, set `use_server_lifespan` to `False` and run the servers in separate terminals:

.. code-block:: bash
    :caption: Terminal 1: Start Vite Dev Server

    litestar assets serve

.. code-block:: bash
    :caption: Terminal 2: Run Litestar App

    litestar run

Production
----------

Building Assets
~~~~~~~~~~~~~~~

Build your assets for production using the CLI:

.. code-block:: bash

    litestar assets build

This command bundles and optimizes all assets, generates a manifest file, and outputs the files to the configured `bundle_dir`.

For more information about Inertia integration, refer to the :doc:`Inertia </usage/inertia>` documentation.
