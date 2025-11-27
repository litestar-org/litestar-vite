===============
Operation Modes
===============

Litestar Vite v2 supports multiple operation modes to suit different architectural needs.

SPA Mode (Default)
------------------

The Single Page Application (SPA) mode is designed for modern frontend frameworks like React, Vue, and Svelte.

**Key Features:**

- Serves a standard ``index.html`` entry point.
- No Jinja2 template engine required.
- Automatic injection of configuration and data into HTML.
- Proxies requests to Vite dev server in development.

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
