===============
Operation Modes
===============

Litestar Vite supports multiple operation modes to suit different architectural needs.

SPA Mode (Default)
------------------

The Single Page Application (SPA) mode is designed for modern frontend frameworks like React, Vue, and Svelte.

**Key Features:**

- Serves a standard ``index.html`` entry point.
- No Jinja2 template engine required.
- Automatic injection of configuration and data into HTML.
- Proxies requests to Vite dev server in development.
- Registers a catch-all ``vite_spa`` route for you (no manual ``/`` handler needed) when ``spa_handler`` is enabled.

**Configuration:**

.. code-block:: python

    VitePlugin(
        config=ViteConfig(
            mode="spa",
            dev_mode=True,
        )
    )

Template Mode
-------------

The Template mode is for traditional server-side rendered applications using Jinja2 templates.

**Key Features:**

- Uses Jinja2 to render HTML.
- Provides ``{{ vite() }}`` and ``{{ vite_hmr() }}`` helpers.
- Full control over HTML structure.

**Configuration:**

.. code-block:: python

    VitePlugin(
        config=ViteConfig(
            mode="template",
            dev_mode=True,
        )
    )

HTMX Mode
---------

The HTMX mode is a specialized template mode optimized for HTMX applications.

**Key Features:**

- Includes HTMX-specific template helpers.
- Optimized for partial rendering.

**Configuration:**

.. code-block:: python

    VitePlugin(
        config=ViteConfig(
            mode="htmx",
            dev_mode=True,
        )
    )

Hybrid Mode (Inertia.js)
------------------------

The Hybrid mode is designed for Inertia.js applications that combine server-side routing with client-side rendering.

**Alias:** ``inertia`` mode is an alias for ``hybrid``

**Key Features:**

- Combines server-side routing with SPA-like client-side transitions.
- Inertia.js protocol support (partial reloads, shared data, etc.).
- Can use either Jinja2 templates or SPA mode (HTML transformation).

**Configuration:**

.. code-block:: python

    from litestar_vite import ViteConfig, VitePlugin
    from litestar_vite.inertia import InertiaConfig

    VitePlugin(
        config=ViteConfig(
            mode="hybrid",  # Or "inertia" (alias)
            dev_mode=True,
            inertia=InertiaConfig(),
        )
    )

SSR Mode
--------

The Server-Side Rendering (SSR) mode is for meta-frameworks like Nuxt, SvelteKit, or Astro that render on the server.

**Alias:** ``ssg`` mode is an alias for ``ssr`` (legacy compatibility)

**Key Features:**

- Server-side rendering with hydration.
- Proxy mode set to ``"proxy"`` (blacklist) by default.
- SSR bundle management.

**Configuration:**

.. code-block:: python

    VitePlugin(
        config=ViteConfig(
            mode="ssr",  # Or "ssg" (alias)
            dev_mode=True,
            runtime=RuntimeConfig(
                ssr_enabled=True,
                proxy_mode="proxy",
            ),
        )
    )

External Mode
-------------

The External mode is for non-Vite frameworks (Angular CLI, Create React App, etc.) with their own build system.

**Key Features:**

- Auto-serves ``bundle_dir`` in production.
- No Vite manifest dependency.
- External dev server configuration support.

**Configuration:**

.. code-block:: python

    from litestar_vite import ViteConfig, VitePlugin, RuntimeConfig
    from litestar_vite.config import ExternalDevServer

    VitePlugin(
        config=ViteConfig(
            mode="external",
            dev_mode=True,
            runtime=RuntimeConfig(
                external_dev_server=ExternalDevServer(
                    target="http://localhost:4200",
                    command=["ng", "serve"],
                    build_command=["ng", "build"],
                ),
            ),
        )
    )

Mode Aliases
------------

For backward compatibility and semantic clarity, some modes have aliases:

.. list-table::
   :widths: 25 25 50
   :header-rows: 1

   * - Primary Mode
     - Alias
     - Notes
   * - ``hybrid``
     - ``inertia``
     - Both refer to Inertia.js integration
   * - ``ssr``
     - ``ssg``
     - Legacy name for SSR mode (Static Site Generation)
