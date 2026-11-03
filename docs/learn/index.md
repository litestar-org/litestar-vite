# Core Concepts

Litestar Vite is built around a small set of explicit mental models that govern how Python and Vite communicate during development, build time, and production execution.

---

## Core Mental Models

<div class="grid cards" markdown>

-   **Operating Modes (`spa`, `hybrid`, `template`, `framework`)**

    ---

    Understand how `ViteConfig(mode=...)` determines who owns the HTML shell, client routing, asset injection, and data transport.

    [→ Operating Modes](operating-modes.md)

-   **Configuration & `.litestar.json` Bridge**

    ---

    Configure `ViteConfig` and its five focused sub-configs (`PathConfig`, `RuntimeConfig`, `InertiaConfig`, `TypeGenConfig`, `DeployConfig`) while `.litestar.json` keeps Vite in sync.

    [→ Configuration Guide](configuration.md)

-   **Development Workflow & Single-Port Proxy**

    ---

    How `ViteProxyMiddleware` streams Vite modules and `/vite-hmr` WebSocket upgrades through Litestar on a single port, plus `mode="external"` for non-Vite dev servers.

    [→ Development & Proxy](development-and-proxy.md)

-   **Static Props (`virtual:litestar-static-props`)**

    ---

    Expose typed build-time constants, feature flags, and environment metadata from Python to your Vite bundle with zero HTTP round-trips.

    [→ Static Props](static-props.md)

-   **Islands Architecture & HTMX Fragments**

    ---

    Combine server-rendered Jinja2 HTML and HTMX partial swaps with `<litestar-island>` partial hydration and `ComponentResponse` server fragments.

    [→ Islands & HTMX](islands-and-htmx.md)

-   **Server-Side Rendering (Dev vs. Prod IPC)**

    ---

    How `TCPStreamIPCTransport` (Vite 7+ `RunnableDevEnvironment` in dev) and `StdioIPCTransport` (persistent NDJSON worker in prod) render Inertia pages and UI islands with `SSRCircuitBreaker` fallback.

    [→ SSR & IPC Lifecycle](ssr.md)

-   **Production Builds, Granian Native Static & CDN**

    ---

    Serve immutable fingerprinted bundles with `ViteAssetLoader`, offload static files to Granian's Rust HTTP server (`StaticPlacement.NATIVE`), or push to S3/GCS/R2 via `litestar assets deploy`.

    [→ Production & Deploy](production-and-deploy.md)

-   **Diagnostics & v0.32 Migration**

    ---

    Run 9 automated health checks with `litestar assets doctor`, or upgrade from `0.30.x` / `0.31.x` to v0.32.

    [→ Doctor & Troubleshooting](doctor-and-troubleshooting.md) · [v0.32 Migration Guide](migration-0-32.md)

</div>

---

## Diagnostics & Troubleshooting

When paths, ports, or generated types drift out of sync, run `litestar assets doctor` to run 9 automated health checks across `ViteConfig`, `.litestar.json`, `vite.config.ts`, and `package.json`:

- [**Doctor CLI & Troubleshooting Guide**](doctor-and-troubleshooting.md)
