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

The SSR server is a Node ``/render`` endpoint. Litestar posts the page object to
``InertiaSSRConfig.url`` and uses the returned ``head`` and ``body`` fields when building the
initial HTML response. This request is required when SSR is enabled; failures to contact the
configured endpoint are errors, not a silent fallback to client-side rendering.

Typical file layout:

- Browser entry: ``resources/main.tsx`` or ``resources/main.ts``
- Node SSR entry: ``resources/ssr.tsx`` or ``resources/ssr.ts``

Process management
------------------

``InertiaSSRConfig.command`` can start the Node ``/render`` server during Litestar lifespan:

.. code-block:: python

   from litestar_vite import InertiaConfig, InertiaSSRConfig

   InertiaConfig(
       ssr=InertiaSSRConfig(
           command=["npm", "run", "start:ssr"],
           auto_start=True,
           health_check=True,
       )
   )

When ``command`` is set and ``auto_start`` is true, litestar-vite starts the process on
application startup and stops it on shutdown. Set ``auto_start=False`` when another process
manager owns the SSR server. With ``health_check=True``, startup polls the configured SSR URL up
to ``health_check_timeout`` seconds and logs a warning if the endpoint does not become reachable.

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
