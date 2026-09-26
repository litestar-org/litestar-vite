==========================================================
Vite 7/8 Environment API & Dev Proxy Architecture
==========================================================

``litestar-vite`` requires Vite 7+. It uses Vite's ``RunnableDevEnvironment`` (``server.environments.ssr``) for development server-side rendering, ``build.rolldownOptions`` for bundler configuration, and a zero-``httpx`` AnyIO byte-streaming reverse proxy for single-port asset and HMR delivery.

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

------------------------------------
Single-Port AnyIO Dev Asset Proxying
------------------------------------

In development mode (``dev_mode=True``), ``litestar-vite`` serves your entire application on a single ASGI port (for example ``http://localhost:8000``). Asset requests under ``asset_url`` (such as ``/static/@vite/client`` and ``/static/src/main.ts``) and HMR WebSocket connections (``/static/vite-hmr``) are streamed from the Vite dev server using AnyIO TCP sockets without external HTTP client dependencies:

.. mermaid::

   sequenceDiagram
       autonumber
       participant Browser as Browser
       participant Litestar as Litestar (Port 8000)
       participant Vite as Vite Dev Server (Port 5173)

       Browser->>Litestar: GET / (HTML Page Shell)
       Litestar-->>Browser: HTML with <script src="/static/src/main.ts">
       Browser->>Litestar: GET /static/src/main.ts
       Litestar->>Vite: AnyIO TCP stream /static/src/main.ts
       Vite-->>Litestar: Transformed ES module
       Litestar-->>Browser: Streamed ES module
       Browser->>Litestar: WebSocket HMR (/static/vite-hmr)
       Litestar->>Vite: WebSocket HMR tunnel
       Vite-->>Browser: HMR updates

.. code-block:: python

   from pathlib import Path
   from litestar import Litestar
   from litestar_vite import PathConfig, ViteConfig, VitePlugin

   vite_config = ViteConfig(
       dev_mode=True,
       paths=PathConfig(
           root=Path(__file__).parent,
           resource_dir="resources",
           bundle_dir="public",
       ),
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
