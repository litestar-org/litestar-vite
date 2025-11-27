=======================
Advanced Configuration
=======================

This tutorial covers advanced configuration options for optimizing and customizing your Litestar Vite setup.

Prerequisites
-------------

- Completed :doc:`getting-started` tutorial
- Familiarity with Vite configuration
- Understanding of build optimization concepts

ViteConfig Options
------------------

The ``ViteConfig`` class provides extensive configuration options:

.. code-block:: python
    :caption: app.py

    from pathlib import Path
    from litestar_vite import ViteConfig, VitePlugin

    vite = VitePlugin(
        config=ViteConfig(
            # Asset directories
            bundle_dir=Path("public"),
            resource_dir=Path("resources"),

            # Development settings
            hot_reload=True,
            dev_mode=True,
            port=5173,
            host="localhost",

            # Production settings
            use_server_lifespan=True,
            is_react_enabled=False,

            # Asset loading
            manifest_name="manifest.json",
        )
    )

Configuration Reference
~~~~~~~~~~~~~~~~~~~~~~~

.. list-table::
   :widths: 25 20 55
   :header-rows: 1

   * - Option
     - Type
     - Description
   * - ``bundle_dir``
     - ``Path``
     - Directory for built assets (default: ``public``)
   * - ``resource_dir``
     - ``Path``
     - Source files directory (default: ``resources``)
   * - ``hot_reload``
     - ``bool``
     - Enable HMR in development (default: ``True``)
   * - ``dev_mode``
     - ``bool``
     - Use Vite dev server (default: auto-detected)
   * - ``port``
     - ``int``
     - Vite dev server port (default: ``5173``)
   * - ``host``
     - ``str``
     - Vite dev server host (default: ``localhost``)
   * - ``manifest_name``
     - ``str``
     - Asset manifest filename (default: ``manifest.json``)

Custom Vite Configuration
--------------------------

Environment-Specific Settings
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Create separate configs for development and production:

.. code-block:: typescript
    :caption: vite.config.ts

    import { defineConfig, loadEnv } from 'vite';
    import litestar from '@litestar/vite-plugin';

    export default defineConfig(({ mode }) => {
      const env = loadEnv(mode, process.cwd(), '');

      return {
        plugins: [
          litestar({
            input: 'resources/main.ts',
            bundleDirectory: 'public',
          }),
        ],
        server: {
          port: parseInt(env.VITE_PORT || '5173'),
          host: env.VITE_HOST || 'localhost',
        },
        build: {
          // Production optimizations
          minify: 'terser',
          sourcemap: mode === 'development',
          rollupOptions: {
            output: {
              manualChunks: {
                'vendor': ['react', 'react-dom'],
              },
            },
          },
        },
      };
    });

Create ``.env.development`` and ``.env.production``:

.. code-block:: bash
    :caption: .env.development

    VITE_PORT=5173
    VITE_HOST=localhost

.. code-block:: bash
    :caption: .env.production

    VITE_PORT=5174
    VITE_HOST=0.0.0.0

Code Splitting Strategies
~~~~~~~~~~~~~~~~~~~~~~~~~~

Optimize bundle size with manual code splitting:

.. code-block:: typescript
    :caption: vite.config.ts

    export default defineConfig({
      build: {
        rollupOptions: {
          output: {
            manualChunks(id) {
              // Vendor chunk for node_modules
              if (id.includes('node_modules')) {
                return 'vendor';
              }

              // Separate chunk for large libraries
              if (id.includes('react')) {
                return 'react-vendor';
              }

              // Components chunk
              if (id.includes('/components/')) {
                return 'components';
              }
            },
          },
        },
      },
    });

Asset Optimization
~~~~~~~~~~~~~~~~~~

Configure asset handling:

.. code-block:: typescript
    :caption: vite.config.ts

    export default defineConfig({
      build: {
        assetsInlineLimit: 4096,  // Inline assets < 4KB
        chunkSizeWarningLimit: 500,  // Warning at 500KB
        cssCodeSplit: true,  // Split CSS per chunk
      },

      // Image optimization
      optimizeDeps: {
        include: ['@imagemin/jpegtran', '@imagemin/optipng'],
      },
    });

Production Optimization
-----------------------

Asset Versioning
~~~~~~~~~~~~~~~~

Vite automatically versions assets in production. Access them in templates:

.. code-block:: jinja
    :caption: templates/index.html

    <!-- Development: resources/main.ts -->
    <!-- Production: public/main.abc123.js -->
    {{ vite('resources/main.ts') }}

Caching Strategy
~~~~~~~~~~~~~~~~

Configure caching headers in Litestar:

.. code-block:: python
    :caption: app.py

    from litestar import Litestar, get
    from litestar.config.response_cache import ResponseCacheConfig
    from litestar.middleware.response_cache import ResponseCacheBackend

    cache_config = ResponseCacheConfig(
        default_expiration=3600,  # 1 hour
    )

    app = Litestar(
        route_handlers=[...],
        response_cache_config=cache_config,
    )

Static Asset Compression
~~~~~~~~~~~~~~~~~~~~~~~~

Enable compression in production:

.. code-block:: typescript
    :caption: vite.config.ts

    import viteCompression from 'vite-plugin-compression';

    export default defineConfig({
      plugins: [
        litestar({ /* ... */ }),
        viteCompression({
          algorithm: 'gzip',
          ext: '.gz',
        }),
        viteCompression({
          algorithm: 'brotliCompress',
          ext: '.br',
        }),
      ],
    });

Install the plugin:

.. code-block:: bash

    npm install -D vite-plugin-compression

Multiple Entry Points
---------------------

For complex applications with multiple pages:

.. code-block:: typescript
    :caption: vite.config.ts

    import litestar from '@litestar/vite-plugin';

    export default defineConfig({
      plugins: [
        litestar({
          input: [
            'resources/main.ts',
            'resources/admin.ts',
            'resources/dashboard.ts',
          ],
          bundleDirectory: 'public',
        }),
      ],
    });

Load specific bundles in templates:

.. code-block:: jinja
    :caption: templates/admin.html

    {{ vite('resources/admin.ts') }}

.. code-block:: jinja
    :caption: templates/dashboard.html

    {{ vite('resources/dashboard.ts') }}

CSS Preprocessing
-----------------

Sass/SCSS Support
~~~~~~~~~~~~~~~~~

Install Sass:

.. code-block:: bash

    npm install -D sass

Use in components:

.. code-block:: text
    :caption: Component.vue

    <style lang="scss">
    $primary-color: #f50057;

    .button {
      background: $primary-color;

      &:hover {
        background: darken($primary-color, 10%);
      }
    }
    </style>

PostCSS Configuration
~~~~~~~~~~~~~~~~~~~~~

Create ``postcss.config.js``:

.. code-block:: javascript
    :caption: postcss.config.js

    export default {
      plugins: {
        'tailwindcss': {},
        'autoprefixer': {},
        'cssnano': {
          preset: 'default',
        },
      },
    };

TypeScript Configuration
------------------------

Path Aliases
~~~~~~~~~~~~

Configure path aliases for cleaner imports:

.. code-block:: json
    :caption: tsconfig.json

    {
      "compilerOptions": {
        "baseUrl": ".",
        "paths": {
          "@/*": ["./resources/*"],
          "@components/*": ["./resources/components/*"],
          "@utils/*": ["./resources/utils/*"]
        }
      }
    }

.. code-block:: typescript
    :caption: vite.config.ts

    import path from 'path';

    export default defineConfig({
      resolve: {
        alias: {
          '@': path.resolve(__dirname, './resources'),
          '@components': path.resolve(__dirname, './resources/components'),
          '@utils': path.resolve(__dirname, './resources/utils'),
        },
      },
    });

Use in code:

.. code-block:: typescript

    import Button from '@components/Button.vue';
    import { formatDate } from '@utils/date';

Strict Type Checking
~~~~~~~~~~~~~~~~~~~~

Enable strict mode for better type safety:

.. code-block:: json
    :caption: tsconfig.json

    {
      "compilerOptions": {
        "strict": true,
        "noUncheckedIndexedAccess": true,
        "noUnusedLocals": true,
        "noUnusedParameters": true,
        "noImplicitReturns": true
      }
    }

Development Tools
-----------------

Debugging
~~~~~~~~~

Enable source maps for debugging:

.. code-block:: typescript
    :caption: vite.config.ts

    export default defineConfig({
      build: {
        sourcemap: true,
      },
    });

Vue DevTools Integration
~~~~~~~~~~~~~~~~~~~~~~~~

For Vue applications, DevTools are automatically supported in development mode.

React DevTools Integration
~~~~~~~~~~~~~~~~~~~~~~~~~~

React DevTools work automatically with the React plugin.

Performance Monitoring
~~~~~~~~~~~~~~~~~~~~~~

Add performance monitoring:

.. code-block:: typescript
    :caption: resources/main.ts

    if (import.meta.env.DEV) {
      // Development performance monitoring
      const { startMeasure, endMeasure } = performance;

      startMeasure?.('app-init');
      // ... app initialization
      endMeasure?.('app-init');
    }

Troubleshooting
---------------

Port Conflicts
~~~~~~~~~~~~~~

If port 5173 is in use:

.. code-block:: typescript
    :caption: vite.config.ts

    export default defineConfig({
      server: {
        port: 5174,  // Use different port
        strictPort: true,  // Fail if port is in use
      },
    });

CORS Issues
~~~~~~~~~~~

Configure CORS for API requests:

.. code-block:: python
    :caption: app.py

    from litestar import Litestar
    from litestar.config.cors import CORSConfig

    cors_config = CORSConfig(
        allow_origins=["http://localhost:5173"],
        allow_methods=["GET", "POST", "PUT", "DELETE"],
    )

    app = Litestar(
        route_handlers=[...],
        cors_config=cors_config,
    )

Build Failures
~~~~~~~~~~~~~~

Clear cache and rebuild:

.. code-block:: bash

    # Clear Vite cache
    rm -rf node_modules/.vite

    # Clear build output
    rm -rf public

    # Rebuild
    npm run build

Slow Dev Server
~~~~~~~~~~~~~~~

Optimize dependencies pre-bundling:

.. code-block:: typescript
    :caption: vite.config.ts

    export default defineConfig({
      optimizeDeps: {
        include: ['react', 'react-dom'],  // Pre-bundle heavy dependencies
        exclude: ['your-local-package'],  // Don't pre-bundle local packages
      },
    });

Next Steps
----------

- Review :doc:`../reference/config` for complete API reference
- Check :doc:`../usage/modes` for deployment strategies
- Explore the `Vite documentation <https://vitejs.dev/>`_ for more advanced topics
