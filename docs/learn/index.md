# Core Concepts

Litestar Vite coordinates how your Python ASGI backend and Vite frontend communicate across local development, static asset builds, server-side rendering, and production deployment.

---

## Architecture & Guides

<div class="grid cards" markdown>

-   :lucide-layers: **Operating Modes**

    ---

    Understand how SPA, Inertia hybrid, Jinja template, and meta-framework modes determine HTML shell ownership, routing, asset injection, and data transport.

    [→ Operating Modes](operating-modes.md)

-   :lucide-sliders-horizontal: **Configuration & Bridge**

    ---

    Configure paths, runtime execution, Inertia options, type generation, and cloud deployment in Python while keeping Vite automatically synchronized.

    [→ Configuration Guide](configuration.md)

-   :lucide-network: **Development Server & Proxy**

    ---

    Stream Vite modules and HMR WebSocket upgrades through Litestar on a single port, or proxy external frontend dev servers without CORS overhead.

    [→ Development & Proxy](development-and-proxy.md)

-   :lucide-database: **Static Props**

    ---

    Expose typed build-time constants, feature flags, and environment metadata from Python directly to your frontend bundle with zero HTTP round-trips.

    [→ Static Props](static-props.md)

-   :lucide-puzzle: **Islands & HTMX Fragments**

    ---

    Combine server-rendered Jinja2 HTML and HTMX partial swaps with interactive island hydration and server-rendered UI component fragments.

    [→ Islands & HTMX](islands-and-htmx.md)

-   :lucide-server: **Server-Side Rendering**

    ---

    Render Inertia pages and UI islands on the server using Vite's dev runner during development and a persistent worker pool or QuickJS runtime in production.

    [→ SSR & IPC Lifecycle](ssr.md)

-   :lucide-package-check: **Production & Deployment**

    ---

    Serve immutable fingerprinted bundles from the Vite manifest, offload static files to Granian's Rust HTTP server, or deploy assets to S3, GCS, or R2.

    [→ Production & Deploy](production-and-deploy.md)

-   :lucide-stethoscope: **Diagnostics & Upgrades**

    ---

    Run automated health checks across your Python and Vite configuration with the doctor CLI, or follow step-by-step release migration guides.

    [→ Doctor & Troubleshooting](doctor-and-troubleshooting.md) · [v0.33 Migration](migration-0-33.md) · [v0.32 Migration](migration-0-32.md)

</div>

---

## Diagnostics & Troubleshooting

When paths, ports, or generated types drift out of sync, use the built-in doctor CLI to run automated health checks across your Python configuration, Vite config, and frontend package metadata:

- [**Doctor CLI & Troubleshooting Guide**](doctor-and-troubleshooting.md)
