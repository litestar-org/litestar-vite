=====================
Install and Configure
=====================

Litestar Vite provides a guided Vite integration instead of making you stitch together Python, frontend tooling, and dev-server state by hand.

At a Glance
-----------

- Python configuration is the source of truth; ``.litestar.json`` bridges settings to Vite.
- Development: ``litestar run --reload`` proxies the Vite dev server automatically.
- Production: ``litestar assets build`` then ``litestar run`` serves built assets.
- Use ``litestar assets init`` and ``litestar assets install`` for setup.

.. grid:: 1
   :gutter: 2

   .. grid-item-card:: :octicon:`tools` Assets CLI workflow
      :class-card: demo-frame

      .. image:: /_static/demos/assets-cli.gif
         :alt: Assets CLI demo
         :align: center
         :width: 100%

      Use ``litestar assets init``, ``install``, ``serve``, ``build``, and ``doctor`` from the same operational path.

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

    # Available templates:
    # SPA: react, react-router, react-tanstack, vue, svelte
    # Inertia: react-inertia, vue-inertia, svelte-inertia
    # Inertia template-mode examples (Jinja): react-inertia-jinja, vue-inertia-jinja
    # SSR: sveltekit, nuxt, astro
    # Other: angular, angular-cli, htmx

    # Inertia templates keep Laravel-style paths under resources/
    litestar assets init --template vue-inertia

    # Non-Inertia templates default to src/; place everything under web/
    litestar assets init --template react-router --frontend-dir web

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

Runtime Bridge File (``.litestar.json``)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Litestar writes a deterministic ``.litestar.json`` file from your Python config.
The Vite plugin reads it to avoid duplicating configuration values on the JS side.
The file is created or updated on app startup and when running
``litestar assets generate-types``.

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
                        dev_mode=True,
                    ),
                    mode="spa",  # or "template", "htmx", "hybrid", "framework", "external"
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
     - `str | None`
     - Operation mode: `"spa"`, `"template"`, `"htmx"`, `"hybrid"`, `"framework"`, `"ssr"`, `"ssg"`, or `"external"`. Auto-detected if not set.
   * - `paths`
     - `PathConfig`
     - File system paths configuration.
   * - `runtime`
     - `RuntimeConfig`
     - Runtime execution settings.
   * - `types`
     - `TypeGenConfig | bool | None`
     - Type generation settings. `True` enables with defaults, `False`/`None` disables.
   * - `inertia`
     - `InertiaConfig | bool | None`
     - Inertia.js settings. `True` enables with defaults, `False`/`None` disables.
   * - `spa`
     - `SPAConfig | bool | None`
     - SPA transformation settings.
   * - `dev_mode`
     - `bool`
     - Shortcut for `runtime.dev_mode`. Defaults to `False`.
   * - `base_url`
     - `str | None`
     - Public base URL where the frontend entry point is served (e.g. ``https://app.example.com/``). This does not affect asset URLs. Reads from ``VITE_BASE_URL``.
   * - `deploy`
     - `DeployConfig | bool`
     - Deployment configuration for CDN publishing.

**`SPAConfig` Parameters**:

.. list-table::
   :widths: 25 15 60
   :header-rows: 1

   * - Parameter
     - Type
     - Description
   * - `inject_csrf`
     - `bool`
     - Inject CSRF token into HTML as `window.__LITESTAR_CSRF__`. Defaults to `True`.
   * - `csrf_var_name`
     - `str`
     - Global variable name for CSRF token. Defaults to `"__LITESTAR_CSRF__"`.
   * - `app_selector`
     - `str`
     - CSS selector for the app root element (used for data attributes). Defaults to `"#app"`.
   * - `cache_transformed_html`
     - `bool`
     - Cache transformed HTML in production. Automatically disabled when `inject_csrf=True` since CSRF tokens are per-request. Defaults to `True`.

**`ExternalDevServer` Parameters**:

.. list-table::
   :widths: 25 15 60
   :header-rows: 1

   * - Parameter
     - Type
     - Description
   * - `target`
     - `str | None`
     - URL of the external dev server (e.g., `"http://localhost:4200"` for Angular CLI). If `None`, reads from hotfile (for SSR frameworks using Vite internally).
   * - `command`
     - `list[str] | None`
     - Custom command to start the dev server (e.g., `["ng", "serve"]`). If `None`, uses executor's default start command.
   * - `build_command`
     - `list[str] | None`
     - Custom command to build for production (e.g., `["ng", "build"]`). If `None`, uses executor's default build command.
   * - `http2`
     - `bool`
     - Enable HTTP/2 for proxy connections. Defaults to `False`.
   * - `enabled`
     - `bool`
     - Whether the external proxy is enabled. Defaults to `True`.

**`PathConfig` Parameters**:

.. list-table::
   :widths: 25 15 60
   :header-rows: 1

   * - Parameter
     - Type
     - Description
   * - `root`
     - `Path | str`
     - Root directory of the project. Defaults to current working directory.
   * - `bundle_dir`
     - `Path | str`
     - Location of compiled assets and manifest.json. Defaults to `"public"`.
   * - `resource_dir`
     - `Path | str`
     - TypeScript/JavaScript source directory. Defaults to `"src"` (use `"resources"` for Inertia templates).
   * - `static_dir`
     - `Path | str`
     - Static public assets directory (served as-is by Vite). Defaults to `"public"` but auto-adjusts to ``{resource_dir}/public`` when it would otherwise collide with ``bundle_dir``.
   * - `manifest_name`
     - `str`
     - Name of the Vite manifest file. Defaults to `"manifest.json"`.
   * - `hot_file`
     - `str`
     - Name of the hot file indicating dev server URL. Defaults to `"hot"`.
   * - `asset_url`
     - `str`
     - Base URL for static asset references in both dev and production. Can be a path (``/static/``) or an absolute URL (CDN/object storage). Defaults to ``/static/`` or ``ASSET_URL``.
   * - `ssr_output_dir`
     - `Path | str | None`
     - SSR output directory. Defaults to `None`.

**`RuntimeConfig` Parameters**:

.. list-table::
   :widths: 25 15 60
   :header-rows: 1

   * - Parameter
     - Type
     - Description
   * - `dev_mode`
     - `bool`
     - Enable development mode with HMR/watch. Reads from `VITE_DEV_MODE` env var.
   * - `proxy_mode`
     - `str | None`
     - Proxy handling mode: `"vite"` (default, whitelist - proxies Vite assets only), `"direct"` (expose Vite port directly, no proxy), `"proxy"` (blacklist - proxies everything except Litestar routes, used for meta-frameworks), or `None` (disabled, production mode).
   * - `external_dev_server`
     - `ExternalDevServer | str | None`
     - Configuration for external dev servers (for example Angular CLI or another standalone frontend server). Can be a string URL (e.g., `"http://localhost:4200"`) or an `ExternalDevServer` object with `target`, `command`, `build_command`, `http2`, and `enabled` fields. When set, automatically switches `proxy_mode` to `"proxy"` if not explicitly configured.
   * - `host`
     - `str`
     - Host for Vite dev server. Defaults to `"127.0.0.1"` or `VITE_HOST` env var.
   * - `port`
     - `int`
     - Port for Vite dev server. Defaults to `5173` or `VITE_PORT` env var.
   * - `protocol`
     - `str`
     - Protocol for dev server: `"http"` or `"https"`. Defaults to `"http"`.
   * - `executor`
     - `str | None`
     - JS executor: `"node"`, `"bun"`, `"deno"`, `"yarn"`, or `"pnpm"`. Defaults to `"node"`.
   * - `is_react`
     - `bool`
     - Enable React Fast Refresh support. Defaults to `False`.
   * - `http2`
     - `bool`
     - Enable HTTP/2 for proxy HTTP requests (better connection multiplexing). WebSocket/HMR uses a separate connection. Requires `h2` package. Defaults to `True`.
   * - `trusted_proxies`
     - `list[str] | str | None`
     - Trusted proxy hosts/CIDRs for `ProxyHeadersMiddleware`. Set to `"*"` or a list of IPs/CIDRs. Defaults to `None` (disabled). Reads from `LITESTAR_TRUSTED_PROXIES` env var.
   * - `start_dev_server`
     - `bool`
     - Auto-start dev server process managed by Litestar. Set to `False` if managing the dev server externally. Defaults to `True`.
   * - `spa_handler`
     - `bool`
     - Auto-register catch-all SPA route when mode="spa". Defaults to `True`.
   * - `set_environment`
     - `bool`
     - Set Vite-related environment variables and write `.litestar.json` on startup. Defaults to `True`.
   * - `set_static_folders`
     - `bool`
     - Automatically configure static file serving. Defaults to `True`.
   * - `detect_nodeenv`
     - `bool`
     - Detect and use nodeenv in virtualenv. Defaults to `False`.
   * - `health_check`
     - `bool`
     - Enable health check for dev server startup. Defaults to `False`.

Vite Plugin Configuration (`litestar-vite-plugin`)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

You configure the Vite frontend build process in your `vite.config.ts` (or `.js`).

When running via the Litestar CLI (`litestar run` or `litestar assets serve`), Python writes a `.litestar.json` file that the Vite plugin reads automatically. This means **only `input` is required** - all other settings are inherited from Python:

.. code-block:: javascript

    import { defineConfig } from 'vite'
    import litestar from 'litestar-vite-plugin'

    export default defineConfig({
        plugins: [
            litestar({ input: ['src/main.ts'] })
        ]
    })

For standalone Vite usage (without Litestar), you can specify paths explicitly:

.. code-block:: javascript

    // Only needed when NOT using Litestar CLI
    litestar({
        input: ['src/main.ts'],
        assetUrl: '/static/',
        bundleDir: 'public',
        resourceDir: 'src',
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
   * - `deployAssetUrl`
     - `string | null`
     - Optional asset URL used only during production builds. Typically populated from Python ``DeployConfig.asset_url``.
   * - `bundleDir`
     - `string`
     - The directory where compiled assets and `manifest.json` are written. Defaults to `'public'`.
   * - `resourceDir`
     - `string`
     - The directory for source assets. Defaults to `'src'` (Inertia templates typically use `'resources'`).
   * - `staticDir`
     - `string`
     - Directory for static, unprocessed assets (maps to Vite's `publicDir`). Defaults to `'${resourceDir}/public'`.
   * - `hotFile`
     - `string`
     - The path to the "hot" file. Defaults to `'${bundleDir}/hot'`.
   * - `ssr`
     - `string | string[]`
     - The path of the SSR entry point.
   * - `ssrOutDir`
     - `string`
     - The directory where the SSR bundle should be written. Defaults to `'${bundleDir}/bootstrap/ssr'`.
   * - `refresh`
     - `boolean | string | string[] | RefreshConfig`
     - Configuration for full page refresh on file changes. Defaults to `false`.
   * - `detectTls`
     - `string | boolean | null`
     - Utilize TLS certificates. Defaults to `null`.
   * - `autoDetectIndex`
     - `boolean`
     - Automatically detect and serve `index.html`. Defaults to `true`.
   * - `inertiaMode`
     - `boolean`
     - Enable Inertia mode (disables `index.html` auto-detection). Auto-detected from `.litestar.json` when Python configured Inertia. Defaults to `false`.
   * - `types`
     - `boolean | "auto" | TypesConfig`
     - Type generation configuration. `"auto"` or `undefined` reads from `.litestar.json` (recommended). `true` enables with hardcoded defaults. `false` disables. Object allows fine-grained control with fields: `enabled`, `output`, `openapiPath`, `routesPath`, `pagePropsPath`, `schemasTsPath`, `generateZod`, `generateSdk`, `generateRoutes`, `generatePageProps`, `generateSchemas`, `globalRoute`, `debounce`. Defaults to `undefined` (auto-detect).
   * - `executor`
     - `string`
     - JavaScript runtime: `"node"`, `"bun"`, `"deno"`, `"yarn"`, or `"pnpm"`. Auto-detected from Python config.

Diagnostics (`litestar assets doctor`)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

When something feels “off” (HMR not connecting, types not generating, manifest missing), run:

.. code-block:: bash

    litestar assets doctor

For a full config dump (including ``.litestar.json`` and the extracted ``litestar({ ... })`` block), add:

.. code-block:: bash

    litestar assets doctor --show-config

To attempt safe auto-fixes (writes backups next to the edited files):

.. code-block:: bash

    litestar assets doctor --fix

Runtime-state checks are opt-in (useful when you expect Vite to already be running):

.. code-block:: bash

    litestar assets doctor --runtime-checks

What it checks (high level):

- Your ``vite.config.*`` contains a ``litestar({ ... })`` plugin config
- ``.litestar.json`` exists/is valid/is in sync with Python (when ``runtime.set_environment=True``)
- Python vs explicit Vite plugin overrides (``assetUrl``, ``bundleDir``, ``resourceDir``, ``staticDir``, ``hotFile``, typegen flags)
- Core paths exist (``resource_dir``, ``static_dir``) and entrypoint ``input`` files exist
- Dev/production artifacts (manifest in prod; hotfile/Vite reachability only with ``--runtime-checks``)
- Environment variables that override runtime (``VITE_PORT``, ``VITE_HOST``, ``VITE_PROXY_MODE``, ``VITE_BASE_URL``)
- Proxy-mode bypass risks (for example, ``server.origin`` set in ``vite.config`` while ``proxy_mode`` is ``vite``/``proxy``)

Common warning: ``Proxy Mode Origin Override``
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

When Doctor reports this warning, your ``vite.config`` is forcing ``server.origin`` while Python is configured for proxy mode.
That can cause CSS/imported assets (fonts, ``node_modules`` URLs) to bypass Litestar and hit the Vite port directly.

Recommended fix:

- Proxy mode (default): remove ``server.origin`` so URLs stay same-origin through Litestar.
- Direct/two-port workflow: switch to ``runtime.proxy_mode="direct"`` and keep explicit ``server.origin`` if needed.

.. note::
    When ``runtime.set_environment=True`` (the default), Litestar writes ``.litestar.json`` on startup. If Doctor reports a stale/mismatched
    bridge file, simply restarting your app (``litestar run``) will overwrite it; deleting the file is not required.

Advanced Asset Handling
~~~~~~~~~~~~~~~~~~~~~~~

For assets that are not entry points but still need to be referenced (e.g., images processed by Vite), you can use the `vite_static` template callable:

.. code-block:: html

    <img src="{{ vite_static('src/images/logo.png') }}" alt="Logo" />

This resolves the correct URL whether you are in development mode (served by Vite) or production mode (hashed URL from manifest).

See Also
--------

- :doc:`/usage/development` - HMR, proxy mode, and manual dev-server workflow
- :doc:`/usage/production` - Production build and deploy flow
- :doc:`/usage/static-props` - Static props and generated declarations
- :doc:`/frameworks/inertia/index` - Inertia integration guide
- :doc:`/usage/modes` - Operation modes and aliases
- :doc:`/usage/types` - Type generation pipeline
- :doc:`/frameworks/index` - Framework templates and examples
