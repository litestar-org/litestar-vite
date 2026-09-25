====================================================================
Vite 6/7/8 Architecture, Environment API & Zero-Proxy Dev Workflow
====================================================================

The Vite ecosystem has progressed rapidly through major architectural milestones. Vite 6 introduced the **Environment API** to formalize multi-target runtimes (client, server, edge, worklet). Vite 7 and Vite 8 standardize on **Rolldown**—an ultra-fast, Rust-based bundler providing drop-in Rollup compatibility—and modernized WebSocket and network configurations.

Litestar Vite is engineered to leverage these cutting-edge capabilities natively, eliminating legacy reverse proxy layers, streamlining local development, and providing first-class development SSR via the ModuleRunner API.

-----------------------------------------------------------
Vite Evolution: Environments, Rolldown & Modern Networking
-----------------------------------------------------------

Understanding the transition across recent Vite major versions clarifies how Litestar Vite structures frontend compilation and runtime delivery:

1. **Vite 6 Environment API (``server.environments``)**:
   Historically, Vite treated the browser client as primary and server-side execution as a secondary concern with separate module graphs. Vite 6 introduced the Environment API, allowing multiple isolated execution environments (such as ``client``, ``ssr``, and custom worker targets) to coexist within a single Vite dev server instance, each with dedicated module resolution pipelines, transform plugins, and HMR lifecycles.

2. **Vite 7/8 & Rolldown Standardization**:
   Vite 7 and 8 transition the bundling engine toward Rolldown. To eliminate deprecation warnings and ensure forward compatibility, build options previously placed under Rollup hooks are configured via ``build.rolldownOptions``:

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

3. **Modern WebSocket Options (``server.ws``)**:
   Vite 6+ deprecates legacy HMR socket configurations in favor of explicit ``server.ws`` declarations:

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

---------------------------------
Zero-Proxy Direct Asset Serving
---------------------------------

In early versions of full-stack Python and Vite toolchains, the Python application server acted as a reverse proxy in local development: the browser requested an asset from ``http://localhost:8000/src/main.ts``, Python parsed the request, opened an HTTP client socket to Vite (``http://localhost:5173/src/main.ts``), streamed the transformed JavaScript through Python memory, and delivered it back to the browser.

This reverse proxy approach introduced several significant drawbacks:
- **Double-Hop Latency**: Every script and asset request incurred two TCP connections and Python ASGI middleware traversal.
- **CPU & Memory Pressure**: High numbers of concurrent HTTP requests for unbundled ES modules saturated Python async worker pools.
- **Proxy Translation Bugs**: WebSocket HMR frames, range requests, and chunked transfer encodings required intricate proxy translation logic.

Litestar Vite eliminates the reverse proxy double-hop using **Zero-Proxy Direct Asset Serving** via ``dev_mode_direct_urls=True``:

.. mermaid::

   sequenceDiagram
       autonumber
       participant Browser as Browser
       participant Litestar as Litestar (Port 8000)
       participant Vite as Vite Dev Server (Port 5173)

       Browser->>Litestar: GET / (HTML Page Shell)
       Litestar->>Litestar: Resolve asset tags with direct Vite URLs
       Litestar-->>Browser: HTML with <script src="http://localhost:5173/src/main.ts">
       Note over Browser, Vite: Direct Browser-to-Vite Connection (Zero-Proxy)
       Browser->>Vite: GET http://localhost:5173/src/main.ts
       Vite-->>Browser: Fast transformed ES module + sourcemaps
       Browser->>Vite: WebSocket HMR connection (ws://localhost:5173)
       Vite-->>Browser: Instant hot module replacement events

With direct asset URLs enabled, Litestar only generates the HTML page shell containing absolute URLs pointing directly to the Vite dev server origin. The browser communicates directly with Vite for all script loading, CSS injection, image assets, and WebSocket HMR events. Python handles only actual application API calls and server-rendered templates.

To enable direct URLs in your configuration:

.. docs-example: skip
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

---------------------------------
ModuleRunner Dev SSR
---------------------------------

In production, SSR components are pre-bundled into a standalone JavaScript entry point (e.g. ``ssr.js``). In development, however, developers expect instant Hot Module Replacement (HMR) without running a full production build every time a component file changes.

Vite 6's Environment API introduces ``ModuleRunner`` via ``createServerModuleRunner(server.environments.ssr)``. This API allows Node or Bun to execute modules directly from Vite's in-memory transformed module graph:

1. When a component render request arrives, the SSR worker loads the component using the environment module runner.
2. Vite compiles TypeScript, processes JSX/runes, and applies CSS transforms on-the-fly.
3. If an imported component or dependency is edited in an IDE, Vite invalidates only that node in the module graph, and the next SSR render reflects the changes instantly—with zero build step and zero process restarts.

This architecture enables seamless, instant-feedback server-side rendering for both Inertia.js and component fragments during local development.
