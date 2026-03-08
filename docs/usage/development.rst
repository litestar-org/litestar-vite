====================
Development Workflow
====================

Run Litestar as the public entry point in development while Vite handles assets, refresh, and HMR behind it.

.. grid:: 1
   :gutter: 2

   .. grid-item-card:: :octicon:`zap` Integrated HMR
      :class-card: demo-frame

      .. image:: /_static/demos/hmr.gif
         :alt: HMR demo
         :align: center
         :width: 100%

      Keep one public app URL while Litestar proxies Vite assets and WebSocket traffic in development.

Development Server
------------------

When `use_server_lifespan` is set to `True` (default when `dev_mode=True`), the Litestar CLI automatically manages the Vite development server.

.. code-block:: bash

    litestar run

Proxy vs Direct Modes
---------------------

- **Proxy (default):** Litestar proxies Vite HTTP + WS/HMR through the ASGI port. Vite binds to loopback with an auto-picked port if `VITE_PORT` is unset, writes `public/hot` with its URL, and the JS plugin reads it. Paths like `/@vite/client`, `/@fs/`, `/node_modules/.vite/`, `/src/`, and `/__vite_ping` are forwarded, including WebSockets.
- **Direct:** classic two-port setup; Vite is exposed on `VITE_HOST:VITE_PORT` and Litestar does not proxy it.

Switch with `VITE_PROXY_MODE=proxy|direct` (or `ViteConfig.runtime.proxy_mode`).

Origin Behavior in Development
------------------------------

- In proxy mode, the JS plugin leaves Vite `server.origin` unset by default. This keeps CSS-imported assets, including `node_modules` fonts, as `/static/...` paths on the Litestar origin so proxy middleware can intercept them.
- If your workflow depends on absolute asset URLs to the Vite dev server, set `server.origin` explicitly in `vite.config.ts` or run direct mode.
- Migration note: setups that previously depended on implicit absolute `http://localhost:<vite-port>/...` CSS asset URLs must now opt in via explicit `server.origin`.

Dev URL Derivation
------------------

- `server.origin` (explicit) wins and is written as-is.
- Otherwise host precedence is: `server.hmr.host` -> `server.host` -> remote-mode loopback fallback (`127.0.0.1` / `[::1]`) -> bound server address.
- Port precedence is: `server.hmr.clientPort` -> Vite listening port.
- Protocol precedence is: `server.hmr.protocol` (`wss` => `https`) -> Vite HTTPS setting.

Manual Vite Workflow
--------------------

If you prefer to manage the Vite server manually, keep `dev_mode=True` but start Vite yourself:

.. code-block:: bash
   :caption: Terminal 1: Start Vite Dev Server via the Litestar CLI

    litestar assets serve

.. code-block:: bash
   :caption: Terminal 2: Run Litestar App

    litestar run

See Also
--------

- :doc:`/usage/vite` - Installation, bridge file, and configuration
- :doc:`/usage/production` - Production builds and deploy flow
- :doc:`/usage/modes` - Runtime mode selection
