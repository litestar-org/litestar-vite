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
    Nodeenv integration is opt-in. To let litestar-vite provision Node inside your virtualenv, install with ``litestar-vite[nodeenv]`` and enable nodeenv detection (for example ``runtime.detect_nodeenv=True`` or ``make install NODEENV=1``). Otherwise, ensure Node/npm is available on your system.

Setup Options
-------------

There are two ways to set up Vite with Litestar:

1. Using the CLI (Recommended)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The CLI provides a streamlined setup process:

.. code-block:: bash

    # Initialize a new Vite project (React default)
    litestar assets init

    # Inertia templates keep Laravel-style paths under resources/
    litestar assets init --template vue-inertia

    # Non-Inertia templates default to src/; place everything under web/
    litestar assets init --template react --frontend-dir web

This command will:

- Create a new Vite project structure
- Install necessary dependencies
- Set up configuration files
- Create example templates

The generated project structure will look like this:

.. code-block:: text

    my_project/
    ├── public/           # Compiled assets
    ├── src/              # Frontend source (default for non-Inertia)
    ├── resources/        # Frontend source (Inertia templates only)
    ├── package.json      # Node.js dependencies
    ├── vite.config.js    # Vite configuration
    └── pyproject.toml    # Python dependencies

2. Manual Setup
~~~~~~~~~~~~~~~

If you prefer more control, you can set up Vite manually:

1. Initialize the frontend project:

.. code-block:: bash

    npm init -y
    npm install vite
    npm install -D litestar-vite-plugin

You can also install the frontend dependencies through the Litestar CLI once your Python config is in place:

.. code-block:: bash

    litestar assets install

2. Create ``vite.config.js``:

.. code-block:: javascript

    import { defineConfig } from 'vite'
    import litestar from 'litestar-vite-plugin'

    export default defineConfig({
        plugins: [
            litestar({
                input: ['src/main.ts'],
            })
        ]
    })
    // For Inertia templates, use resources/main.ts instead

Configuration
-------------

The integration is configured in two places: the Python backend via the `VitePlugin` and the frontend via the `litestar-vite-plugin` in your `vite.config.ts`.

Python Configuration (`ViteConfig`)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

You configure the Litestar backend using the `ViteConfig` object passed to the `VitePlugin`. The configuration is now organized into nested objects.

.. code-block:: python

    from litestar import Litestar
    from litestar_vite import ViteConfig, VitePlugin
    from litestar_vite.config import PathConfig, RuntimeConfig

    app = Litestar(
        plugins=[
            VitePlugin(
                config=ViteConfig(
                    paths=PathConfig(
                        bundle_dir="public",
                        resource_dir="src",  # use "resources" for Inertia templates
                    ),
                    runtime=RuntimeConfig(
                        port=5173,
                        hot_reload=True,
                    ),
                    mode="spa", # or "template", "htmx"
                )
            )
        ]
    )

**Root `ViteConfig` Parameters**:

.. list-table::
   :widths: 25 15 60
   :header-rows: 1

   * - Parameter
     - Type
     - Description
   * - `mode`
     - `str`
     - Operation mode: `"spa"`, `"template"`, or `"htmx"`. Defaults to `"spa"`.
   * - `paths`
     - `PathConfig`
     - File system paths configuration.
   * - `runtime`
     - `RuntimeConfig`
     - Runtime execution settings.
   * - `types`
     - `TypeGenConfig | bool`
     - Type generation settings.
   * - `inertia`
     - `InertiaConfig | bool`
     - Inertia.js settings.
   * - `dev_mode`
     - `bool`
     - Shortcut to enable development mode.

**`PathConfig` Parameters**:

.. list-table::
   :widths: 25 15 60
   :header-rows: 1

   * - Parameter
     - Type
     - Description
   * - `bundle_dir`
     - `Path | str`
     - Location of compiled assets. Defaults to `"public"`.
   * - `resource_dir`
     - `Path | str`
     - Directory for source files. Defaults to `"src"` (use `"resources"` for Inertia templates).
   * - `public_dir`
     - `Path | str`
     - The public directory Vite serves assets from. Defaults to `"public"`.
   * - `manifest_name`
     - `str`
     - Name of the Vite manifest file. Defaults to `"manifest.json"`.
   * - `hot_file`
     - `str`
     - Name of the hot file. Defaults to `"hot"`.
   * - `asset_url`
     - `str`
     - Base URL for static assets. Defaults to `"/static/"`.

**`RuntimeConfig` Parameters**:

.. list-table::
   :widths: 25 15 60
   :header-rows: 1

   * - Parameter
     - Type
     - Description
   * - `dev_mode`
     - `bool`
     - Enable development mode.
   * - `hot_reload`
     - `bool`
     - Enable Hot Module Replacement.
   * - `host`
     - `str`
     - Host for Vite dev server. Defaults to `"localhost"`.
   * - `port`
     - `int`
     - Port for Vite dev server. Defaults to `5173`.
   * - `executor`
     - `str`
     - JS executor (`"node"`, `"bun"`, `"deno"`). Defaults to `"node"`.

Vite Plugin Configuration (`litestar-vite-plugin`)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

You configure the Vite frontend build process in your `vite.config.ts` (or `.js`).

.. code-block:: javascript

    import { defineConfig } from 'vite'
    import litestar from 'litestar-vite-plugin'

    export default defineConfig({
        plugins: [
            litestar({ input: ['src/main.ts'] })  // use resources/main.ts for Inertia templates
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
     - The directory where compiled assets and `manifest.json` are written. Defaults to `'public'`.
   * - `resourceDirectory`
     - `string`
     - The directory for source assets. Defaults to `'src'` (use `'resources'` for Inertia templates).
   * - `hotFile`
     - `string`
     - The path to the "hot" file. Defaults to `${bundleDirectory}/hot`.
   * - `types`
     - `object | boolean`
     - Type generation configuration.

Template Integration
~~~~~~~~~~~~~~~~~~~~

Use the `vite()` and `vite_hmr()` callables in your Jinja2 templates to include the assets (in Template Mode).

.. code-block:: html

    <!DOCTYPE html>
    <html>
    <head>
        {{ vite('src/css/styles.css') }}
    </head>
    <body>
        <div id="app"></div>
        {{ vite_hmr() }}
        {{ vite('src/js/main.js') }}
    </body>
    </html>

Angular options
---------------

Litestar Vite supports Angular in two ways:

- **Angular (Vite / Analog)** – `litestar assets init --template angular`

  - Uses `@analogjs/vite-plugin-angular` together with `litestar-vite-plugin`.
  - Source dir: `src/`; hotfile at `public/hot`; single-port proxy/HMR enabled by default.
  - Typed routes/OpenAPI generation on by default (writes to `src/generated`).

- **Angular CLI (non-Vite)** – `litestar assets init --template angular-cli`

  - Runs via Angular CLI `ng serve` with `proxy.conf.json` targeting Litestar.
  - Source dir: `src/`; does **not** use `litestar-vite-plugin` or the typed-routes pipeline.
  - Use the standard Angular CLI commands (`npm start` / `ng build`) and serve `dist/browser/` via Litestar static files.

Troubleshooting (Angular)
~~~~~~~~~~~~~~~~~~~~~~~~~

- HMR not connecting (Analog): ensure `/vite-hmr` and `/@analogjs/` are proxied; stay in single-port mode or expose Vite directly.
- Types not generating (Analog): install `@hey-api/openapi-ts` or set `types.enabled=false` in `vite.config.ts`.
- Angular CLI path: confirm backend runs on port 8000 (or update `proxy.conf.json` targets).

Framework comparison (scaffolds)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

===================== =================== =============================== ===========================
Framework             Source dir          Dev server / proxy              Type generation
===================== =================== =============================== ===========================
React/Vue/Svelte      src/                Vite + litestar-vite proxy      Enabled by default
Inertia variants      resources/          Vite + litestar-vite proxy      Enabled by default
Angular (Analog)      src/                Vite (Analog) + proxy           Enabled by default
Angular CLI           src/                Angular CLI + proxy.conf.json   Disabled (CLI handles dev)
HTMX                  src/                Vite + litestar-vite proxy      Disabled (JS optional)
===================== =================== =============================== ===========================

Advanced Asset Handling
~~~~~~~~~~~~~~~~~~~~~~~

For assets that are not entry points but still need to be referenced (e.g., images processed by Vite), you can use the `vite_static` template callable:

.. code-block:: html

    <img src="{{ vite_static('src/images/logo.png') }}" alt="Logo" />

This resolves the correct URL whether you are in development mode (served by Vite) or production mode (hashed URL from manifest).

Development Workflow
--------------------

Development Server
~~~~~~~~~~~~~~~~~~

When `use_server_lifespan` is set to `True` (default when `dev_mode=True`), the Litestar CLI will automatically manage the Vite development server.

.. code-block:: bash

    litestar run

Proxy vs direct modes:

- **Proxy (default):** Litestar proxies Vite HTTP + WS/HMR through the ASGI port. Vite binds to loopback with an auto-picked port if `VITE_PORT` is unset, writes `public/hot` with its URL, and the JS plugin reads it. Paths like `/@vite/client`, `/@fs/`, `/node_modules/.vite/`, `/src/`, `/__vite_ping` are forwarded, including WebSockets.
- **Direct:** classic two-port setup; Vite is exposed on `VITE_HOST:VITE_PORT` and Litestar does not proxy it.

Switch with `VITE_PROXY_MODE=proxy|direct` (or `ViteConfig.runtime.proxy_mode`).

If you prefer to manage the Vite server manually, keep `dev_mode=True` but start Vite yourself (useful for two-port setups):

.. code-block:: bash
    :caption: Terminal 1: Start Vite Dev Server via the Litestar CLI

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
