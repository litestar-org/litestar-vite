================
Inertia SSR (JS)
================

Server-side rendering settings for Inertia.js responses (Node SSR server).

``InertiaConfig(ssr=True)`` enables a separate Node SSR server for initial HTML responses.
Litestar sends the full Inertia page object to that server, then injects the rendered
head tags and body markup back into the HTML response.

This SSR path is distinct from framework proxy mode:

- Inertia SSR: ``InertiaConfig(ssr=True)``
- Meta-framework proxy mode: ``ViteConfig(mode="framework")`` or alias ``mode="ssr"``

In development mode, Litestar sends the page object to the running Vite dev server's
``/__litestar_ssr__`` endpoint, which evaluates your SSR entrypoint via Vite's
``RunnableDevEnvironment.runner``. In production mode, Litestar spawns the built SSR bundle over
``StdioIPCTransport`` and uses the returned ``head`` and ``body`` fields when building the
initial HTML response.

Typical file layout:

- Browser entry: ``resources/main.tsx`` or ``resources/main.ts``
- Node SSR entry: ``resources/ssr.tsx`` or ``resources/ssr.ts``

Process management
------------------

``InertiaSSRConfig.command`` configures the production ``stdio`` worker command started during Litestar lifespan:

.. code-block:: python

   from litestar_vite import InertiaConfig, InertiaSSRConfig

   InertiaConfig(
       ssr=InertiaSSRConfig(
           command=["node", "bootstrap/ssr/ssr.js"],
           timeout=2.0,
           fallback_to_client=True,
       )
   )

When ``dev_mode=False``, ``litestar-vite`` spawns the configured ``command`` on application startup and closes its ``stdin`` pipe on shutdown. When ``fallback_to_client=True`` (the default), SSR errors or circuit breaker trips fall back gracefully to the client-side SPA shell.

Plugin boundary
---------------

Generated Litestar scaffolds do not install ``@inertiajs/vite`` by default. The default frontend
bridge remains ``litestar-vite-plugin`` because it owns Litestar-specific behavior:

- writing and reading the ``.litestar.json`` bridge contract;
- dev/prod asset resolution and proxy integration;
- route and schema type generation;
- CSRF helper wiring for generated Inertia entries;
- the ``resolvePageComponent()`` wrapper used by the templates.

The upstream ``@inertiajs/vite`` plugin may be useful if an application wants to experiment with
its page shorthand or Laravel-centered SSR automation, but it must not replace the
``litestar-vite-plugin`` bridge/proxy/typegen responsibilities. If both plugins are combined,
keep ``litestar-vite-plugin`` as the bridge owner and treat ``@inertiajs/vite`` as application
owned integration code.

When you use the default script-element bootstrap transport:

- Inertia v3 clients use the script-element bootstrap by default, so no extra client
  ``defaults`` block is required.
- Inertia v2 clients must keep ``defaults.future.useScriptElementForInitialPage`` in the browser
  entry so hydration reads the initial page payload correctly instead of expecting the default
  ``data-page`` attribute.
- Inertia v2 SSR entries should mirror the same option because Inertia applies the same defaults
  during server rendering.
- Set ``use_script_element=False`` if you need to keep the legacy ``data-page`` attribute bootstrap.

.. note::
   This guidance is intentionally version-scoped. Inertia v2 still uses the ``future`` namespace
   for script-element bootstrap, while Inertia v3 removes that extra client configuration.

Selector behavior follows ``SPAConfig.app_selector``. If you render into ``#root`` instead of
``#app``, keep the browser template, SSR output, and app selector aligned so Litestar can replace
the correct wrapper element during the initial SSR response.

.. autoclass:: litestar_vite.config.InertiaSSRConfig
    :members:
    :show-inheritance:
