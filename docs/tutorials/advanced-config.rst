======================
Advanced Configuration
======================

This tutorial covers advanced configuration options for litestar-vite, including
custom Vite settings, environment-specific configurations, and optimization strategies.

ViteConfig Options
------------------

The ``ViteConfig`` class accepts several configuration options:

.. code-block:: python

    from litestar_vite import ViteConfig, VitePlugin
    from litestar_vite.config import PathConfig, RuntimeConfig

    vite = VitePlugin(
        config=ViteConfig(
            dev_mode=True,
            paths=PathConfig(
                bundle_dir=Path("public"),
                resource_dir=Path("resources"),
                asset_url="/static/",
                hot_file=Path("public/hot"),
            ),
            runtime=RuntimeConfig(
                host="localhost",
                port=5173,
            ),
        )
    )

PathConfig
~~~~~~~~~~

Controls file and URL paths:

- ``bundle_dir``: Directory for production builds (default: ``public``)
- ``resource_dir``: Directory containing source files (default: ``resources``)
- ``asset_url``: URL prefix for assets (default: ``/static/``)
- ``hot_file``: Path to the hot file for dev server detection (default: ``public/hot``)
- ``manifest_path``: Path to manifest.json (default: ``bundle_dir/.vite/manifest.json``)

RuntimeConfig
~~~~~~~~~~~~~

Controls development server settings:

- ``host``: Dev server host (default: ``localhost``)
- ``port``: Dev server port (default: ``5173``)
- ``dev_mode``: Enable development mode (default: from environment)

Environment-Based Configuration
-------------------------------

Use environment variables for different deployment contexts:

.. code-block:: python
    :caption: app.py

    import os
    from pathlib import Path
    from litestar_vite import ViteConfig, VitePlugin
    from litestar_vite.config import PathConfig

    IS_DEV = os.getenv("LITESTAR_DEBUG", "false").lower() == "true"

    vite = VitePlugin(
        config=ViteConfig(
            dev_mode=IS_DEV,
            paths=PathConfig(
                bundle_dir=Path("public"),
                resource_dir=Path("resources"),
                asset_url=os.getenv("ASSET_URL", "/static/"),
            ),
        )
    )

Or use a configuration factory:

.. code-block:: python

    def create_vite_config() -> ViteConfig:
        env = os.getenv("ENVIRONMENT", "development")

        if env == "production":
            return ViteConfig(
                dev_mode=False,
                paths=PathConfig(
                    bundle_dir=Path("dist"),
                    asset_url="https://cdn.example.com/",
                ),
            )
        else:
            return ViteConfig(
                dev_mode=True,
                paths=PathConfig(
                    bundle_dir=Path("public"),
                    resource_dir=Path("resources"),
                ),
            )

Custom Vite Configuration
-------------------------

Multiple Entry Points
~~~~~~~~~~~~~~~~~~~~~

For applications with multiple entry points:

.. code-block:: typescript
    :caption: vite.config.ts

    import { defineConfig } from "vite";
    import litestar from "@litestar/vite-plugin";

    export default defineConfig({
      plugins: [
        litestar({
          input: [
            "resources/main.ts",
            "resources/admin.ts",
            "resources/dashboard.ts",
          ],
          assetUrl: "/static/",
          bundleDir: "public",
          resourceDir: "resources",
        }),
      ],
    });

Use them in templates:

.. code-block:: jinja

    {# Main site #}
    {{ vite('resources/main.ts') }}

    {# Admin panel #}
    {{ vite('resources/admin.ts') }}

CSS Code Splitting
~~~~~~~~~~~~~~~~~~

Vite automatically code-splits CSS. You can customize this:

.. code-block:: typescript
    :caption: vite.config.ts

    import { defineConfig } from "vite";
    import litestar from "@litestar/vite-plugin";

    export default defineConfig({
      plugins: [
        litestar({
          input: ["resources/main.ts"],
          assetUrl: "/static/",
          bundleDir: "public",
          resourceDir: "resources",
        }),
      ],
      build: {
        cssCodeSplit: true,  // Default: true
        cssMinify: "lightningcss",  // Use Lightning CSS for faster minification
      },
      css: {
        devSourcemap: true,
      },
    });

Custom Build Output
~~~~~~~~~~~~~~~~~~~

Control chunk naming and structure:

.. code-block:: typescript
    :caption: vite.config.ts

    import { defineConfig } from "vite";
    import litestar from "@litestar/vite-plugin";

    export default defineConfig({
      plugins: [
        litestar({
          input: ["resources/main.ts"],
          assetUrl: "/static/",
          bundleDir: "public",
          resourceDir: "resources",
        }),
      ],
      build: {
        rollupOptions: {
          output: {
            // Custom chunk file names
            chunkFileNames: "js/[name]-[hash].js",
            entryFileNames: "js/[name]-[hash].js",
            assetFileNames: (assetInfo) => {
              const info = assetInfo.name?.split(".") ?? [];
              const ext = info[info.length - 1];
              if (/png|jpe?g|svg|gif|tiff|bmp|ico/i.test(ext)) {
                return "images/[name]-[hash][extname]";
              }
              if (/css/i.test(ext)) {
                return "css/[name]-[hash][extname]";
              }
              return "assets/[name]-[hash][extname]";
            },
            // Manual chunk splitting
            manualChunks: {
              vendor: ["vue", "react", "react-dom"],
            },
          },
        },
      },
    });

Proxy Configuration
-------------------

Single-Port Mode
~~~~~~~~~~~~~~~~

Run everything through Litestar (recommended for production-like development):

.. code-block:: python

    vite = VitePlugin(
        config=ViteConfig(
            dev_mode=True,
            paths=PathConfig(
                bundle_dir=Path("public"),
                resource_dir=Path("resources"),
                asset_url="/static/",
            ),
        )
    )

In this mode, Litestar proxies requests to the Vite dev server.

Multi-Port Mode
~~~~~~~~~~~~~~~

Run Vite and Litestar on separate ports:

.. code-block:: typescript
    :caption: vite.config.ts

    export default defineConfig({
      server: {
        port: 5173,
        proxy: {
          "/api": {
            target: "http://localhost:8000",
            changeOrigin: true,
          },
        },
      },
      plugins: [
        litestar({
          input: ["resources/main.ts"],
          assetUrl: "/static/",
          bundleDir: "public",
          resourceDir: "resources",
        }),
      ],
    });

Asset Optimization
------------------

Image Optimization
~~~~~~~~~~~~~~~~~~

Use Vite plugins for image optimization:

.. code-block:: bash

    npm install -D vite-imagetools

.. code-block:: typescript
    :caption: vite.config.ts

    import { defineConfig } from "vite";
    import { imagetools } from "vite-imagetools";
    import litestar from "@litestar/vite-plugin";

    export default defineConfig({
      plugins: [
        imagetools(),
        litestar({
          input: ["resources/main.ts"],
          assetUrl: "/static/",
          bundleDir: "public",
          resourceDir: "resources",
        }),
      ],
    });

Import optimized images:

.. code-block:: typescript

    import heroImage from "./images/hero.jpg?w=800&format=webp";

Compression
~~~~~~~~~~~

Enable gzip/brotli compression for production:

.. code-block:: bash

    npm install -D vite-plugin-compression

.. code-block:: typescript
    :caption: vite.config.ts

    import { defineConfig } from "vite";
    import compression from "vite-plugin-compression";
    import litestar from "@litestar/vite-plugin";

    export default defineConfig({
      plugins: [
        litestar({
          input: ["resources/main.ts"],
          assetUrl: "/static/",
          bundleDir: "public",
          resourceDir: "resources",
        }),
        compression({
          algorithm: "brotli",
        }),
      ],
    });

TypeScript Path Aliases
-----------------------

Configure path aliases for cleaner imports:

.. code-block:: typescript
    :caption: vite.config.ts

    import { defineConfig } from "vite";
    import path from "path";
    import litestar from "@litestar/vite-plugin";

    export default defineConfig({
      plugins: [
        litestar({
          input: ["resources/main.ts"],
          assetUrl: "/static/",
          bundleDir: "public",
          resourceDir: "resources",
        }),
      ],
      resolve: {
        alias: {
          "@": path.resolve(__dirname, "resources"),
          "@components": path.resolve(__dirname, "resources/components"),
          "@utils": path.resolve(__dirname, "resources/utils"),
        },
      },
    });

Update ``tsconfig.json`` to match:

.. code-block:: json
    :caption: tsconfig.json

    {
      "compilerOptions": {
        "baseUrl": ".",
        "paths": {
          "@/*": ["resources/*"],
          "@components/*": ["resources/components/*"],
          "@utils/*": ["resources/utils/*"]
        }
      }
    }

Now import with aliases:

.. code-block:: typescript

    import Button from "@components/Button";
    import { formatDate } from "@utils/helpers";

Environment Variables
---------------------

Vite exposes environment variables prefixed with ``VITE_``:

.. code-block:: text
    :caption: .env

    VITE_API_URL=http://localhost:8000
    VITE_APP_TITLE=My App

Access in code:

.. code-block:: typescript

    const apiUrl = import.meta.env.VITE_API_URL;
    const title = import.meta.env.VITE_APP_TITLE;

Type definitions for custom env variables:

.. code-block:: typescript
    :caption: resources/env.d.ts

    /// <reference types="vite/client" />

    interface ImportMetaEnv {
      readonly VITE_API_URL: string;
      readonly VITE_APP_TITLE: string;
    }

    interface ImportMeta {
      readonly env: ImportMetaEnv;
    }

Troubleshooting
---------------

Common Issues
~~~~~~~~~~~~~

**Assets not loading in production**

Ensure ``dev_mode=False`` and the manifest.json exists:

.. code-block:: bash

    ls public/.vite/manifest.json

**HMR not working**

Check that:

1. The hot file path matches in both Vite and Litestar configs
2. WebSocket connections aren't blocked by proxies
3. Both servers are running

**CORS errors in development**

Configure CORS in both Vite and Litestar:

.. code-block:: typescript
    :caption: vite.config.ts

    export default defineConfig({
      server: {
        cors: true,
      },
    });

.. code-block:: python

    from litestar.config.cors import CORSConfig

    app = Litestar(
        cors_config=CORSConfig(
            allow_origins=["http://localhost:5173"],
        ),
    )

**Manifest file not found**

Ensure you've run ``npm run build`` and the output directory matches your config.

Debug Mode
~~~~~~~~~~

Enable verbose logging:

.. code-block:: python

    import logging

    logging.getLogger("litestar_vite").setLevel(logging.DEBUG)

Next Steps
----------

- :doc:`/usage/index` - Complete usage reference
- :doc:`/reference/config` - Full configuration API
- `Vite Documentation <https://vitejs.dev/>`_ - Official Vite docs
