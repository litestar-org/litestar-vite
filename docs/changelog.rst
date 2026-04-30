=========
Changelog
=========

All commits to this project will be documented in this file.

Litestar Vite Changelog
^^^^^^^^^^^^^^^^^^^^^^^

Unreleased
----------

- Fixed metadata loss for Inertia deferred props (#236). Metadata is now correctly extracted before props are filtered for initial/partial responses.
- Fixed Inertia partial reload behavior where non-requested properties were incorrectly included in responses.
- Fixed cross-loop failure for Inertia async prop callbacks (#244). Async callbacks passed to ``optional()``/``defer()``/``lazy()``/``once()`` are now pre-resolved on the request event loop, so callbacks that touch request-scoped async resources (asyncpg/aiosqlite/sqlspec sessions) no longer fail with ``InterfaceError`` or cross-loop errors. SSR HTTP fetches were also moved to the request loop in the same async pre-pass.
- Fixed Inertia page subtree remount on every navigation/partial-reload caused by ``resolvePageComponent`` allocating a fresh wrapper closure on each call. ``wrapComponent`` now memoizes its result by source-module reference (``WeakMap``), so the resolved component identity is stable across Inertia's repeated ``resolveComponent`` calls. React/Vue no longer unmount the page tree on partial reloads, preserving local component state and avoiding redundant effect re-runs.
- **Breaking** (Inertia internals): Removed ``inertia_plugin.portal`` and the ``BlockingPortal`` lifespan attached to ``InertiaPlugin``. Removed the ``portal=`` parameter from ``StaticProp.render()``/``DeferredProp.render()``/``OnceProp.render()``/``OptionalProp.render()``/``AlwaysProp.render()``. Removed the ``litestar_vite.inertia._async_mixin`` module (``AsyncRenderMixin`` is no longer needed). Calling ``render()`` directly on a prop with an unresolved async callback now raises ``RuntimeError``; async callbacks are pre-resolved by ``InertiaResponse`` during ASGI dispatch.
- Updated documentation build to include ``llms.txt`` and ``llms-full.txt`` at the site root for better LLM discovery (#240).
- Isolated TanStack Router generated assets into ``src/generated/`` in example and scaffolding templates.
- Default ``resource_dir`` set to ``src`` for non-Inertia templates; Inertia stays on ``resources/``.
- CLI/docs now reference `litestar assets` consistently and document `--frontend-dir`.
