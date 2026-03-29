=============
Upgrade Guide
=============

Move existing Litestar-Vite Inertia apps from Inertia v2 to Inertia v3 without losing compatibility for projects that stay on v2.

.. seealso::
   Official Inertia.js docs: `Upgrade Guide <https://inertiajs.com/docs/v3/getting-started/upgrade-guide>`_

Version Support
---------------

litestar-vite supports Inertia v2 and v3.

- Generated templates and examples now target Inertia v3.
- Existing Inertia v2 projects remain supported.
- The main version-specific difference in this repository is script-element bootstrap configuration.

What Changes In This Repository
-------------------------------

litestar-vite now defaults Inertia apps to script-element bootstrap:

- Inertia v3 clients use the script-element bootstrap by default.
- Inertia v2 clients must still enable ``defaults.future.useScriptElementForInitialPage`` in ``createInertiaApp(...)``.
- If ``InertiaConfig(ssr=True)`` is enabled, Inertia v2 SSR entries must mirror that same setting.

The generated ``page-props.ts`` contract now also matches runtime behavior for non-mapping handler returns by nesting those payloads under ``content``.

Upgrade Steps
-------------

1. Bump your frontend adapter package to Inertia v3.

   - React: ``@inertiajs/react@3``
   - Vue: ``@inertiajs/vue3@3``
   - Svelte: ``@inertiajs/svelte@3``

2. Remove explicit ``use_script_element=True`` if you previously added it just to enable the default transport.

3. Remove the Inertia v2-only client opt-in:

   .. code-block:: typescript

      defaults: {
        future: {
          useScriptElementForInitialPage: true,
        },
      }

   In Inertia v3, that transport is already the default.

4. If you use an SSR entry (``resources/ssr.tsx`` / ``resources/ssr.ts``), remove the same
   ``defaults.future.useScriptElementForInitialPage`` block there too.

5. Reinstall dependencies and regenerate package lockfiles so the adapter upgrade is reflected in committed manifests.

Framework Notes
---------------

- React projects in this repository already use React 19, which matches Inertia v3 requirements.
- Vue projects in this repository already use Vue 3 and only need the adapter bump.
- Svelte Inertia scaffolds in this repository already use Svelte 5, which matches Inertia v3 support.

Staying On Inertia v2
---------------------

If you are not ready to upgrade yet, keep your current Inertia v2 adapter package and retain the
``defaults.future.useScriptElementForInitialPage`` client configuration while using the default
script-element transport, or set ``InertiaConfig(use_script_element=False)`` to stay on the legacy
``data-page`` bootstrap.
