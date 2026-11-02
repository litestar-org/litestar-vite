# Runtime, Assets & Exceptions Reference

API reference for `ViteAssetLoader`, Jinja template helpers, `AppHandler`, `ViteProxyMiddleware`, Granian native static serving contracts, JavaScript runtime executors, and `litestar_vite.exceptions`.

---

## Asset Loader & Template Callables (`litestar_vite.loader`)

::: litestar_vite.loader.ViteAssetLoader
    options:
      heading_level: 4

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

## SPA Handler & Single-Port Dev Proxy (`litestar_vite.handler` & `litestar_vite.plugin`)

::: litestar_vite.handler.AppHandler
    options:
      heading_level: 4

::: litestar_vite.plugin.ViteProxyMiddleware
    options:
      heading_level: 4

---

## Static File Serving & Granian Native Placement

::: litestar_vite.plugin.StaticPlacement
    options:
      heading_level: 4

::: litestar_vite.plugin.StaticServerConfig
    options:
      heading_level: 4

::: litestar_vite.plugin.StaticServerMount
    options:
      heading_level: 4

::: litestar_vite.plugin.StaticFilesConfig
    options:
      heading_level: 4

---

## JavaScript Runtime Executors (`litestar_vite.executor`)

::: litestar_vite.executor.JSExecutor
    options:
      heading_level: 4

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

---

## Exceptions Hierarchy (`litestar_vite.exceptions`)

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
