# PRD: Fix WebSocket HMR Proxying for Nuxt 4 & SSR Frameworks

## Problem Description
Users running Nuxt 4 (and potentially other SSR frameworks like Astro/SvelteKit) behind the Litestar proxy experience broken Hot Module Replacement (HMR) and WebSocket errors.

**Symptoms:**
1.  WebSocket 404 errors on `/_nuxt` (or similar HMR paths).
2.  Page refresh loops.
3.  `html.replace` errors in the browser console.

**Root Cause:**
*   Nuxt (via Nitro) runs the HTTP server on one port (e.g., 44433).
*   Vite (embedded in Nuxt) runs the HMR WebSocket server on a *separate, random* port (e.g., 24678) because it's configured with `hmr: { port: 0 }`.
*   Litestar's `SSRProxyController` proxies **all** traffic (HTTP and WS) to the HTTP server URL found in the `hot` file (e.g., `http://localhost:44433`).
*   Consequently, HMR WebSocket connections sent to the HTTP port are rejected (404), as the HTTP server doesn't handle them.

## Goals
1.  Ensure HMR works seamlessly when accessing the app via the Litestar port (e.g., 8000).
2.  Maintain "identical" behavior whether accessing via Litestar port or Vite/Nuxt port.
3.  Support the separate HMR port architecture used by Nuxt/Vite.

## Proposed Solution

### 1. Frontend (JS) Updates
Modify the Nuxt integration (and potentially others) to explicitly manage the HMR port and expose it to the backend.

*   **File:** `src/js/src/nuxt.ts`
*   **Changes:**
    *   Determine a free port for HMR (distinct from the HTTP port).
    *   Configure Vite's `server.hmr` to use this specific port.
    *   Write this HMR URL (e.g., `http://localhost:{hmrPort}`) to a new "hotfile" specifically for HMR (e.g., `hot.hmr`), located alongside the existing `hot` file.

### 2. Backend (Python) Updates
Update the Litestar Vite plugin to recognize the separate HMR target.

*   **File:** `src/py/litestar_vite/plugin.py`
*   **Changes:**
    *   Update `create_ssr_proxy_controller` to look for the `hot.hmr` file.
    *   Modify `SSRProxyController.ws_proxy`:
        *   Check if an HMR target is available (from `hot.hmr`).
        *   If available, use the HMR target for WebSocket connections.
        *   *Refinement:* If possible, distinguish HMR traffic (e.g., via `sec-websocket-protocol: vite-hmr`) to only route HMR traffic to the HMR port, while keeping standard WebSockets on the main HTTP port (if Nuxt supports app-level WS). For now, routing all WS to HMR port in SSR mode might be safer if Nuxt doesn't support app-level WS on the Nitro port easily, but verifying the protocol is the robust path.

## Implementation Details

### JS Side (`src/js/src/nuxt.ts`)
*   Import logic to find a free port (or rely on `0` but we need to *know* what it picked). Since getting the port back from Vite in the config hook is tricky before the server starts, it's better to pick one explicitly.
*   Use `getPort()` (or similar simple logic) to find an available port.
*   Update `createProxyPlugin` config:
    ```typescript
    hmr: {
      port: hmrPort,
      host: "localhost",
    },
    ```
*   Write the `hot.hmr` file.

### Python Side (`src/py/litestar_vite/plugin.py`)
*   In `SSRProxyController`:
    *   Add `_get_hmr_target_url` helper.
    *   In `ws_proxy`:
        ```python
        hmr_target = get_hmr_target_url()
        target = hmr_target if hmr_target else http_target
        # ... proceed to proxy
        ```

## Verification Plan
1.  Start a Litestar app with Nuxt integration.
2.  Verify `hot` file contains HTTP port.
3.  Verify `hot.hmr` file contains HMR port.
4.  Access app at `http://localhost:8000`.
5.  Verify page loads (HTTP proxy).
6.  Verify WebSocket connects (HMR proxy).
7.  Modify a Vue file and verify Hot Module Replacement occurs without page reload.
