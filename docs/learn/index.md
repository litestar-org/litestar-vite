# Core Concepts

`litestar-vite` is built around a small set of explicit mental models that govern how Python and Vite communicate during development, build time, and production execution.

---

## Core Mental Models

<div class="grid cards" markdown>

-   :material-tune-variant: **Operating Modes (`spa`, `hybrid`, `template`, `framework`)**

    ---

    Understand how `ViteConfig(mode=...)` determines who owns the HTML shell, client routing, asset injection, and data transport.

    [:octicons-arrow-right-24: Operating Modes](operating-modes.md)

-   :material-cog-outline: **Configuration & `.litestar.json` Bridge**

    ---

    Configure `ViteConfig` and its five focused sub-configs (`PathConfig`, `RuntimeConfig`, `InertiaConfig`, `TypeGenConfig`, `DeployConfig`) while `.litestar.json` keeps Vite in sync.

    [:octicons-arrow-right-24: Configuration Guide](configuration.md)

-   :material-database-export-outline: **Static Props (`virtual:litestar-static-props`)**

    ---

    Expose typed build-time constants, feature flags, and environment metadata from Python to your Vite bundle with zero HTTP round-trips.

    [:octicons-arrow-right-24: Static Props](static-props.md)

-   :material-puzzle-outline: **Islands Architecture & HTMX Fragments**

    ---

    Combine server-rendered Jinja2 HTML and HTMX partial swaps with `<litestar-island>` partial hydration and `ComponentResponse` server fragments.

    [:octicons-arrow-right-24: Islands & HTMX](islands-and-htmx.md)

-   :material-server-network: **Server-Side Rendering (Dev vs. Prod IPC)**

    ---

    How `TCPStreamIPCTransport` (Vite 7+ `RunnableDevEnvironment` in dev) and `StdioIPCTransport` (persistent NDJSON worker in prod) render Inertia pages and UI islands with `SSRCircuitBreaker` fallback.

    [:octicons-arrow-right-24: SSR & IPC Lifecycle](ssr.md)

-   :material-rocket-launch-outline: **Production Builds, Granian Native Static & CDN**

    ---

    Serve immutable fingerprinted bundles with `ViteAssetLoader`, offload static files to Granian's Rust HTTP server (`StaticPlacement.NATIVE`), or push to S3/GCS/R2 via `litestar assets deploy`.

    [:octicons-arrow-right-24: Production & Deploy](production-and-deploy.md)

</div>

---

## Diagnostics & Troubleshooting

When paths, ports, or generated types drift out of sync, run `litestar assets doctor` to run 9 automated health checks across `ViteConfig`, `.litestar.json`, `vite.config.ts`, and `package.json`:

- [**Doctor CLI & Troubleshooting Guide**](doctor-and-troubleshooting.md)
