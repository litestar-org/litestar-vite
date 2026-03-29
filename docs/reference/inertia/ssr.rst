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

Typical file layout:

- Browser entry: ``resources/main.tsx`` or ``resources/main.ts``
- Node SSR entry: ``resources/ssr.tsx`` or ``resources/ssr.ts``

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
