==========================================================
Vite 7/8 Environment API & Direct Dev Asset Configuration
==========================================================

``litestar-vite`` requires Vite 7+. It uses Vite's ``RunnableDevEnvironment`` (``server.environments.ssr``) for development server-side rendering, ``build.rolldownOptions`` for bundler configuration, and direct Vite dev server URLs for asset and HMR delivery.

------------------------------------------------
Vite Configuration: Environments, Rolldown & WS
------------------------------------------------

1. **Environment API (``server.environments``)**:
   Vite provides isolated module graphs for ``client`` and ``ssr`` environments inside a single dev server instance. ``litestar-vite`` uses ``server.environments.ssr.runner`` to evaluate server-rendered components in development without running a separate SSR build.

2. **Rolldown Options (``build.rolldownOptions``)**:
   Vite 8 uses Rolldown for bundling. ``litestar-vite`` scaffolding templates configure output naming under ``build.rolldownOptions`` (falling back to ``build.rollupOptions`` on Vite 7 via the ``litestar-vite`` Vite plugin):

   .. docs-example: skip
   .. code-block:: ts

      // vite.config.ts
      export default defineConfig({
        build: {
          rolldownOptions: {
            output: {
              entryFileNames: "assets/[name]-[hash].js",
              chunkFileNames: "assets/[name]-[hash].js",
              assetFileNames: "assets/[name]-[hash][extname]",
            },
          },
        },
      });

3. **WebSocket Configuration (``server.ws``)**:
   Vite 8.1+ configures HMR WebSocket listeners under ``server.ws`` (``server.hmr`` on Vite 7 / 8.0, handled automatically by the plugin):

   .. docs-example: skip
   .. code-block:: ts

      server: {
        host: "0.0.0.0",
        port: Number(process.env.VITE_PORT || "5173"),
        cors: true,
        ws: {
          host: "localhost",
        },
      },

--------------------------
Direct Dev Asset Serving
--------------------------

By default in development mode (``dev_mode_direct_urls=True``), ``litestar-vite`` emits asset tags pointing directly to the Vite dev server URL (for example ``http://localhost:5173/@vite/client`` and ``http://localhost:5173/src/main.ts``) rather than proxying asset requests through the Litestar ASGI server:

.. mermaid::

   sequenceDiagram
       autonumber
       participant Browser as Browser
       participant Litestar as Litestar (Port 8000)
       participant Vite as Vite Dev Server (Port 5173)

       Browser->>Litestar: GET / (HTML Page Shell)
       Litestar->>Litestar: Resolve asset tags with direct Vite URLs
       Litestar-->>Browser: HTML with <script src="http://localhost:5173/src/main.ts">
       Browser->>Vite: GET http://localhost:5173/src/main.ts
       Vite-->>Browser: Transformed ES module
       Browser->>Vite: WebSocket HMR connection (ws://localhost:5173)
       Vite-->>Browser: HMR updates

The browser loads scripts, stylesheets, static assets, and HMR WebSocket connections directly from Vite, while Litestar serves HTML responses and API routes. The Vite plugin configures ``server.cors`` automatically so cross-origin module requests from the Litestar origin succeed.

If your environment requires single-origin serving behind a strict firewall or reverse proxy, set ``dev_mode_direct_urls=False`` on ``RuntimeConfig`` (or ``ViteConfig``) to enable the built-in AnyIO HTTP/WebSocket proxy middleware:

.. code-block:: python

   from pathlib import Path
   from litestar import Litestar
   from litestar_vite import PathConfig, ViteConfig, VitePlugin

   vite_config = ViteConfig(
       paths=PathConfig(
           root=Path(__file__).parent,
           resource_dir="resources",
           bundle_dir="public",
       ),
       dev_mode_direct_urls=True,
   )

   vite_plugin = VitePlugin(config=vite_config)
   app = Litestar(plugins=[vite_plugin])

---------------------
ModuleRunner Dev SSR
---------------------

In production, SSR components are imported from a built server bundle (such as ``ssr.js``). In development, ``litestar-vite`` uses Vite's ``createServerModuleRunner(server.environments.ssr)`` to evaluate SSR modules directly from Vite's transform pipeline:

1. When an SSR or fragment render request arrives, the worker imports the component through the SSR ``ModuleRunner``.
2. Vite transforms TypeScript, JSX, Vue SFCs, or Svelte modules on demand.
3. When a file changes, the Vite plugin invalidates the module and its importers in the SSR cache so subsequent renders use the updated code without rebuilding or restarting the worker.
