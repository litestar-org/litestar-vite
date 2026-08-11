======
Loader
======

.. automodule:: litestar_vite.loader
    :members:
    :show-inheritance:
    :inherited-members:

Secondary HTML entries
----------------------

``ViteAssetLoader.resolve_html_entry()`` resolves a nested Vite HTML entry without relying on
Vite's SPA fallback. Pass the source entry separately from the production artifact:

.. code-block:: python

   html = await plugin.asset_loader.resolve_html_entry(
       "pages/offline.html",
       production_path="public/offline.html",
       absolute_dev_asset_urls=True,
   )

Relative ``production_path`` values are resolved beneath ``ViteConfig.root_dir``. In production,
or when the hot file is missing, empty, unreadable, or malformed, the production file is returned
unchanged. When the current hot file contains an HTTP or HTTPS target, the loader asks that Vite
server to read and transform the exact entry. Connection failures and non-success responses raise
``HTMLEntryResolutionError`` and do not fall back to a stale production artifact.

``resolve_html_entry_sync()`` provides the same source selection and validation for synchronous
callers. It performs blocking filesystem and network I/O, so do not call it on an async event-loop
thread. Both methods create a bounded one-shot HTTP client outside plugin lifespan; the async method
reuses the plugin's lifespan-managed client when available.

Set ``absolute_dev_asset_urls=True`` when the returned document will be displayed outside the normal
Litestar origin, including a document opened through a ``file://`` URL. Only Vite module scripts,
stylesheet and module-preload links, HMR paths, and React refresh imports are made absolute. Forms,
images, anchors, unrelated links, and URLs that are already absolute are preserved. The browser-facing
origin comes from ``.litestar.json.appUrl`` when available and otherwise from the hot file.

The Python ``litestar-vite`` package and npm ``litestar-vite-plugin`` package must use matching minor
versions because the exact-entry request is a paired server contract. Version 0.30.x requires 0.30.x
on both sides.
