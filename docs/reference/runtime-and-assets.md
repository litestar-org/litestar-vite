# Runtime, Assets & Exceptions Reference

API reference for `ViteAssetLoader`, Jinja template helpers, `AppHandler`, `ViteProxyMiddleware`, Granian native static serving contracts, JavaScript runtime executors, and `litestar_vite.exceptions`.

---

## Asset Loader & Template Callables

::: litestar_vite.loader.ViteAssetLoader

::: litestar_vite.loader.render_hmr_client
    options:
      heading_level: 4

::: litestar_vite.loader.render_asset_tag
    options:
      heading_level: 4

::: litestar_vite.loader.render_static_asset
    options:
      heading_level: 4

::: litestar_vite.loader.render_routes
    options:
      heading_level: 4

---

## SPA Handler & Single-Port Dev Proxy

::: litestar_vite.handler.AppHandler

::: litestar_vite.plugin.ViteProxyMiddleware

---

## Static File Serving & Granian Native Placement

::: litestar_vite.plugin.StaticPlacement

::: litestar_vite.plugin.StaticServerConfig

::: litestar_vite.plugin.StaticServerMount
    options:
      heading_level: 4

::: litestar_vite.plugin.StaticFilesConfig
    options:
      heading_level: 4

---

## JavaScript Runtime Executors

::: litestar_vite.executor.JSExecutor

::: litestar_vite.executor.NodeExecutor
    options:
      heading_level: 4

::: litestar_vite.executor.BunExecutor
    options:
      heading_level: 4

::: litestar_vite.executor.DenoExecutor
    options:
      heading_level: 4

::: litestar_vite.executor.PnpmExecutor
    options:
      heading_level: 4

::: litestar_vite.executor.YarnExecutor
    options:
      heading_level: 4

::: litestar_vite.executor.NodeenvExecutor
    options:
      heading_level: 4

::: litestar_vite.executor.resolve_ssr_command
    options:
      heading_level: 4

---

## Exceptions Hierarchy

::: litestar_vite.exceptions.LitestarViteError
    options:
      heading_level: 4

::: litestar_vite.exceptions.ManifestNotFoundError
    options:
      heading_level: 4

::: litestar_vite.exceptions.AssetNotFoundError
    options:
      heading_level: 4

::: litestar_vite.exceptions.HTMLEntryResolutionError
    options:
      heading_level: 4

::: litestar_vite.exceptions.MissingDependencyError
    options:
      heading_level: 4

::: litestar_vite.exceptions.ViteExecutableNotFoundError
    options:
      heading_level: 4

::: litestar_vite.exceptions.ViteExecutionError
    options:
      heading_level: 4

::: litestar_vite.exceptions.ViteProcessError
    options:
      heading_level: 4

---

## HTML Transform Helpers

::: litestar_vite.html_transform.inject_head_html
    options:
      heading_level: 4

::: litestar_vite.html_transform.inject_head_script
    options:
      heading_level: 4

::: litestar_vite.html_transform.inject_inertia_ssr_tags
    options:
      heading_level: 4

::: litestar_vite.html_transform.inject_page_script
    options:
      heading_level: 4

::: litestar_vite.html_transform.inject_vite_dev_scripts
    options:
      heading_level: 4

::: litestar_vite.html_transform.replace_element_outer_html
    options:
      heading_level: 4

::: litestar_vite.html_transform.set_data_attribute
    options:
      heading_level: 4

::: litestar_vite.html_transform.transform_asset_urls
    options:
      heading_level: 4
