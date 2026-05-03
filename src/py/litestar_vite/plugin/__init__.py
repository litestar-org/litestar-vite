"""Vite Plugin for Litestar.

This module provides the VitePlugin class for integrating Vite with Litestar.
The plugin handles:

- Static file serving configuration
- Jinja2 template callable registration
- Vite dev server process management
- Async asset loader initialization
- Development proxies for Vite HTTP and HMR WebSockets (with hop-by-hop header filtering)

Example::

    from litestar import Litestar
    from litestar_vite import VitePlugin, ViteConfig

    app = Litestar(
        plugins=[VitePlugin(config=ViteConfig(dev_mode=True))],
    )
"""

import os
from contextlib import asynccontextmanager, contextmanager
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

import httpx
from litestar.exceptions import NotFoundException
from litestar.middleware import DefineMiddleware
from litestar.plugins import CLIPlugin, InitPluginProtocol
from litestar.static_files import create_static_files_router  # pyright: ignore[reportUnknownVariableType]

from litestar_vite.config import JINJA_INSTALLED, TRUE_VALUES, ExternalDevServer
from litestar_vite.loader import ViteAssetLoader
from litestar_vite.plugin._process import ViteProcess
from litestar_vite.plugin._proxy import (
    SSRProxyMiddleware,
    ViteProxyMiddleware,
    create_ssr_http_proxy_handler,
    create_ssr_proxy_controller,
    create_ssr_websocket_handler,
    create_ssr_ws_proxy_handler,
    create_vite_hmr_handler,
)
from litestar_vite.plugin._proxy_headers import ProxyHeadersMiddleware, TrustedHosts
from litestar_vite.plugin._static import StaticFilesConfig
from litestar_vite.plugin._utils import (
    create_proxy_client,
    get_litestar_route_prefixes,
    is_litestar_route,
    is_non_serving_assets_cli,
    log_fail,
    log_info,
    log_success,
    log_warn,
    pick_free_port,
    resolve_litestar_version,
    set_app_environment,
    set_environment,
    static_not_found_handler,
    vite_not_found_handler,
)
from litestar_vite.utils import read_hotfile_url

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator, Generator, Iterable

    from click import Group
    from litestar import Litestar
    from litestar.config.app import AppConfig
    from litestar.types import ControllerRouterHandler, ExceptionHandlersMap

    from litestar_vite.config import ViteConfig
    from litestar_vite.config._inertia import InertiaSSRConfig
    from litestar_vite.handler import AppHandler


def _user_has_root_http_handler(route_handlers: "Iterable[ControllerRouterHandler]") -> bool:
    """Return True if any handler in ``route_handlers`` registers an HTTP route at ``/``.

    Walks top-level entries (functions, Controllers, Routers). A match means the SSR
    proxy must omit the bare ``/`` from its HTTP path list to avoid Litestar raising
    ``Handler already registered for path '/'`` at app construction.
    """
    import inspect

    from litestar import Controller, Router
    from litestar.handlers.http_handlers import HTTPRouteHandler
    from litestar.routes import HTTPRoute

    def _is_root_path(prefix: str, path: str) -> bool:
        joined = (prefix.rstrip("/") + "/" + path.lstrip("/")).rstrip("/")
        return joined in {"", "/"}

    def _walk(item: Any, prefix: str = "") -> bool:
        if isinstance(item, HTTPRouteHandler):
            return any(_is_root_path(prefix, p) for p in item.paths)
        if isinstance(item, type) and issubclass(item, Controller):
            ctrl_path_attr = getattr(item, "path", "")
            ctrl_path = ctrl_path_attr if isinstance(ctrl_path_attr, str) else ""
            new_prefix = prefix.rstrip("/") + "/" + ctrl_path.lstrip("/")
            for _, member in inspect.getmembers(item):
                if isinstance(member, HTTPRouteHandler) and any(_is_root_path(new_prefix, p) for p in member.paths):
                    return True
            return False
        if isinstance(item, Router):
            # Router.routes is the resolved route list with full paths.
            full_root = (prefix.rstrip("/") or "/").rstrip("/") or "/"
            for route in item.routes:
                if isinstance(route, HTTPRoute):
                    full_path = (prefix.rstrip("/") + "/" + route.path.lstrip("/")).rstrip("/") or "/"
                    if full_path == full_root:
                        return True
            return False
        return False

    return any(_walk(item) for item in route_handlers or [])


class VitePlugin(InitPluginProtocol, CLIPlugin):
    """Vite plugin for Litestar.

    This plugin integrates Vite with Litestar, providing:

    - Static file serving configuration
    - Jinja2 template callables for asset tags
    - Vite dev server process management
    - Async asset loader initialization

    Example::

        from litestar import Litestar
        from litestar_vite import VitePlugin, ViteConfig

        app = Litestar(
            plugins=[
                VitePlugin(config=ViteConfig(dev_mode=True))
            ],
        )
    """

    __slots__ = (
        "_asset_loader",
        "_config",
        "_proxy_client",
        "_proxy_target",
        "_spa_handler",
        "_ssr_process",
        "_static_files_config",
        "_vite_process",
    )

    def __init__(
        self,
        config: "ViteConfig | None" = None,
        asset_loader: "ViteAssetLoader | None" = None,
        static_files_config: "StaticFilesConfig | None" = None,
    ) -> None:
        """Initialize the Vite plugin.

        Args:
            config: Vite configuration. Defaults to ViteConfig() if not provided.
            asset_loader: Optional pre-initialized asset loader.
            static_files_config: Optional configuration for static file serving.
        """
        from litestar_vite.config import ViteConfig

        if config is None:
            config = ViteConfig()
        self._config = config
        self._asset_loader = asset_loader
        self._vite_process: "ViteProcess | None" = None
        self._ssr_process: "ViteProcess | None" = None
        self._static_files_config: dict[str, Any] = static_files_config.__dict__ if static_files_config else {}
        self._proxy_target: "str | None" = None
        self._proxy_client: "httpx.AsyncClient | None" = None
        self._spa_handler: "AppHandler | None" = None

    def _get_vite_process(self) -> ViteProcess:
        """Get or create the Vite process manager lazily."""
        if self._vite_process is None:
            self._vite_process = ViteProcess(executor=self._config.executor)
        return self._vite_process

    def _get_ssr_process(self) -> ViteProcess:
        """Get or create the SSR process manager lazily.

        Returns a separate ViteProcess instance so SSR has its own signal-handler
        registration, atexit cleanup, and stop() lifecycle independent of Vite.
        """
        if self._ssr_process is None:
            self._ssr_process = ViteProcess(executor=self._config.executor)
        return self._ssr_process

    def _resolved_ssr_config(self) -> "InertiaSSRConfig | None":
        """Return the active InertiaSSRConfig when Inertia + SSR are enabled."""
        from litestar_vite.config._inertia import InertiaConfig

        inertia = self._config.inertia
        if not isinstance(inertia, InertiaConfig):
            return None
        return inertia.ssr_config

    def _run_ssr_health_check(self, ssr_config: "InertiaSSRConfig") -> None:
        """Poll the SSR url until it responds (or until timeout)."""
        import time
        from urllib.parse import urlparse

        deadline = time.monotonic() + ssr_config.health_check_timeout
        # Poll the origin (a GET on /render typically returns 405; any non-connection
        # error means the server is up).
        parsed = urlparse(ssr_config.url)
        origin = f"{parsed.scheme}://{parsed.netloc}"
        last_error: str = ""
        while time.monotonic() < deadline:
            try:
                response = httpx.get(origin, timeout=2.0)
                if response.status_code < 500:
                    log_success(f"SSR /render server ready at {origin}")
                    return
                last_error = f"HTTP {response.status_code}"
            except httpx.RequestError as exc:
                last_error = str(exc)
            time.sleep(0.25)
        log_warn(f"SSR /render server health check timed out at {origin} (last: {last_error})")

    @property
    def config(self) -> "ViteConfig":
        """Get the Vite configuration.

        Returns:
            The ViteConfig instance.
        """
        return self._config

    @property
    def asset_loader(self) -> "ViteAssetLoader":
        """Get the asset loader instance.

        Lazily initializes the loader if not already set.

        Returns:
            The ViteAssetLoader instance.
        """

        if self._asset_loader is None:
            self._asset_loader = ViteAssetLoader.initialize_loader(config=self._config)
        return self._asset_loader

    @property
    def spa_handler(self) -> "AppHandler | None":
        """Return the configured SPA handler when SPA mode is enabled.

        Returns:
            The AppHandler instance, or None when SPA mode is disabled/not configured.
        """
        return self._spa_handler

    @property
    def proxy_client(self) -> "httpx.AsyncClient | None":
        """Return the shared httpx.AsyncClient for proxy requests.

        The client is initialized during app lifespan (dev mode only) and provides
        connection pooling, TLS session reuse, and HTTP/2 multiplexing benefits.

        Returns:
            The shared AsyncClient instance, or None if not initialized or not in dev mode.
        """
        return self._proxy_client

    def _resolve_bundle_dir(self) -> Path:
        """Resolve the bundle directory to an absolute path.

        Returns:
            The absolute path to the bundle directory.
        """
        bundle_dir = Path(self._config.bundle_dir)
        if not bundle_dir.is_absolute():
            return self._config.root_dir / bundle_dir
        return bundle_dir

    def _resolve_hotfile_path(self) -> Path:
        """Resolve the path to the hotfile.

        Returns:
            The absolute path to the hotfile.
        """
        return self._resolve_bundle_dir() / self._config.hot_file

    def _write_hotfile(self, content: str) -> None:
        """Write content to the hotfile.

        Args:
            content: The content to write (usually the dev server URL).
        """
        hotfile_path = self._resolve_hotfile_path()
        hotfile_path.parent.mkdir(parents=True, exist_ok=True)
        hotfile_path.write_text(content, encoding="utf-8")

    def _resolve_dev_command(self) -> "list[str]":
        """Resolve the command to run for the dev server.

        Returns:
            The list of command arguments.
        """
        ext = self._config.runtime.external_dev_server
        if isinstance(ext, ExternalDevServer) and ext.enabled:
            command = ext.command or self._config.executor.start_command
            log_info(f"Starting external server: {' '.join(command)}")
            return command

        if self._config.hot_reload:
            log_info("Starting Vite server with HMR")
            return self._config.run_command

        log_info("Starting Vite watch build process")
        return self._config.build_watch_command

    def _ensure_proxy_target(self) -> None:
        """Prepare proxy target URL and port for proxy modes (vite, proxy, ssr).

        For all proxy modes in dev mode:
        - Auto-selects a free port if VITE_PORT is not explicitly set
        - Sets the port in runtime config for JS integrations to read

        For 'vite' mode specifically:
        - Forces loopback host unless VITE_ALLOW_REMOTE is set
        - Sets _proxy_target directly (JS writes hotfile when server starts)

        For 'proxy'/'ssr' modes:
        - Port is written to .litestar.json for SSR framework to read
        - SSR framework writes hotfile with actual URL when ready
        - Proxy discovers target from hotfile at request time
        """
        if not self._config.is_dev_mode:
            return

        if self._config.proxy_mode is None:
            return

        if os.getenv("VITE_PORT") is None and self._config.runtime.port == 5173:
            self._config.runtime.port = pick_free_port()

        if self._config.proxy_mode == "vite":
            if self._proxy_target is not None:
                return
            if os.getenv("VITE_ALLOW_REMOTE", "False") not in TRUE_VALUES:
                self._config.runtime.host = "127.0.0.1"
            self._proxy_target = f"{self._config.protocol}://{self._config.host}:{self._config.port}"

    def _configure_inertia(self, app_config: "AppConfig") -> "AppConfig":
        """Configure Inertia.js by registering an InertiaPlugin instance.

        This is called automatically when `inertia` config is provided to ViteConfig.
        Users can still use InertiaPlugin manually for more control.

        Args:
            app_config: The Litestar application configuration.

        Returns:
            The modified application configuration.
        """
        from litestar_vite.inertia.plugin import InertiaPlugin

        inertia_plugin = InertiaPlugin(config=self._config.inertia)  # type: ignore[arg-type]
        app_config = inertia_plugin.on_app_init(app_config)
        if inertia_plugin not in app_config.plugins:
            app_config.plugins.append(inertia_plugin)

        return app_config

    def _insert_dev_proxy_middleware(self, app_config: "AppConfig", middleware: "DefineMiddleware") -> None:
        """Insert a dev proxy middleware at the earliest safe position.

        Ordering guarantees:

        - Proxy headers middleware should run first when enabled, to ensure
          scheme/host/client are normalized before proxy routing decisions.
        - Vite proxy middleware should run before user middleware to avoid
          unnecessary auth/session overhead for pure Vite/static requests.
        """
        insert_at = 0
        for idx, existing in enumerate(app_config.middleware):
            if getattr(existing, "middleware", None) is ProxyHeadersMiddleware:
                insert_at = idx + 1
                break

        app_config.middleware.insert(insert_at, middleware)

    def on_cli_init(self, cli: "Group") -> None:
        """Register CLI commands.

        Args:
            cli: The Click command group to add commands to.
        """
        from litestar_vite.cli import vite_group

        cli.add_command(vite_group)

    def _configure_jinja_callables(self, app_config: "AppConfig") -> None:
        """Register Jinja2 template callables for Vite asset handling.

        Args:
            app_config: The Litestar application configuration.
        """
        from litestar.contrib.jinja import JinjaTemplateEngine

        from litestar_vite.loader import render_asset_tag, render_hmr_client, render_routes, render_static_asset

        template_config = app_config.template_config  # pyright: ignore[reportUnknownMemberType,reportUnknownVariableType]
        if template_config and isinstance(
            template_config.engine_instance,  # pyright: ignore[reportUnknownMemberType]
            JinjaTemplateEngine,
        ):
            engine = template_config.engine_instance  # pyright: ignore[reportUnknownMemberType]
            engine.register_template_callable(key="vite_hmr", template_callable=render_hmr_client)
            engine.register_template_callable(key="vite", template_callable=render_asset_tag)
            engine.register_template_callable(key="vite_static", template_callable=render_static_asset)
            engine.register_template_callable(key="vite_routes", template_callable=render_routes)

    def _wants_jinja_callables(self, app_config: "AppConfig") -> bool:
        """Decide whether to register Jinja ``vite_*`` callables for this app.

        The full gate requires three conditions, each of which is independently
        load-bearing: the configured mode must be ``template`` (canonical), Jinja2
        must be importable, and the user must have provided a ``TemplateConfig``
        backed by ``JinjaTemplateEngine``. Returning ``False`` here is harmless:
        callables are simply not registered and HTMX-without-Jinja, raw HTML, and
        non-Jinja template engine consumers continue to work.

        Args:
            app_config: The Litestar application configuration.

        Returns:
            True when ``vite_hmr`` / ``vite`` / ``vite_static`` / ``vite_routes`` should be registered.
        """
        if self._config.mode != "template" or not JINJA_INSTALLED:
            return False
        template_config = app_config.template_config  # pyright: ignore[reportUnknownMemberType,reportUnknownVariableType]
        if template_config is None:
            return False
        from litestar.contrib.jinja import JinjaTemplateEngine

        return isinstance(template_config.engine_instance, JinjaTemplateEngine)  # pyright: ignore[reportUnknownMemberType]

    def _configure_static_files(self, app_config: "AppConfig") -> None:
        """Configure static file serving for Vite assets.

        The static files router serves real files (JS, CSS, images). SPA fallback (serving
        index.html for client-side routes) is handled by the AppHandler.

        Args:
            app_config: The Litestar application configuration.
        """
        bundle_dir = self._resolve_bundle_dir()

        resource_dir = Path(self._config.resource_dir)
        if not resource_dir.is_absolute():
            resource_dir = self._config.root_dir / resource_dir

        static_dir = Path(self._config.static_dir)
        if not static_dir.is_absolute():
            static_dir = self._config.root_dir / static_dir

        static_dirs = [bundle_dir, resource_dir]
        if static_dir.exists() and static_dir != bundle_dir:
            static_dirs.append(static_dir)

        opt: dict[str, Any] = {}
        if self._config.exclude_static_from_auth:
            opt["exclude_from_auth"] = True
        user_opt = self._static_files_config.get("opt", {})
        if user_opt:
            opt = {**opt, **user_opt}

        base_config: dict[str, Any] = {
            "directories": (static_dirs if self._config.is_dev_mode else [bundle_dir]),
            "path": self._config.asset_url,
            "name": "vite",
            "html_mode": False,
            "include_in_schema": False,
            "opt": opt,
            "exception_handlers": {NotFoundException: static_not_found_handler},
        }
        user_config = {k: v for k, v in self._static_files_config.items() if k != "opt"}
        static_files_config: dict[str, Any] = {**base_config, **user_config}
        app_config.route_handlers.append(create_static_files_router(**static_files_config))

    def _configure_dev_proxy(self, app_config: "AppConfig") -> None:
        """Configure dev proxy middleware and handlers based on the canonical mode.

        Args:
            app_config: The Litestar application configuration.
        """
        hotfile_path = self._resolve_hotfile_path()

        if self._config.wants_html_proxy:
            self._configure_ssr_proxy(app_config, hotfile_path)
        else:
            self._configure_vite_proxy(app_config, hotfile_path)

    def _configure_vite_proxy(self, app_config: "AppConfig", hotfile_path: Path) -> None:
        """Configure Vite proxy mode (allow list).

        Args:
            app_config: The Litestar application configuration.
            hotfile_path: Path to the hotfile.
        """
        self._ensure_proxy_target()
        self._insert_dev_proxy_middleware(
            app_config,
            DefineMiddleware(
                ViteProxyMiddleware,
                hotfile_path=hotfile_path,
                asset_url=self._config.asset_url,
                resource_dir=self._config.resource_dir,
                bundle_dir=self._config.bundle_dir,
                root_dir=self._config.root_dir,
                http2=self._config.http2,
                plugin=self,
            ),
        )
        hmr_path = f"{self._config.asset_url.rstrip('/')}/vite-hmr"
        app_config.route_handlers.append(
            create_vite_hmr_handler(hotfile_path=hotfile_path, hmr_path=hmr_path, asset_url=self._config.asset_url)
        )

    def _configure_ssr_proxy(self, app_config: "AppConfig", hotfile_path: Path) -> None:
        """Configure SSR proxy mode for framework dev servers.

        Registers an HTTP catch-all route handler plus a WebSocket HMR handler at
        ``/`` and ``/{path:path}``. Litestar dispatches matched routes directly, so
        any path the user has not registered falls through to the framework's dev
        server. Litestar's per-route middleware never runs on unmatched paths, so a
        true route is required (see commit history: an earlier middleware-based
        approach hit 405 Method Not Allowed because the WS handler at ``/`` was
        matched first).

        Collision avoidance: when a user has already registered an HTTP handler at
        ``/``, the plugin omits ``/`` from the HTTP catch-all's path list (keeping
        ``/{path:path}``) so Litestar does not raise
        ``Handler already registered for path '/'`` at app construction.
        ``ViteProxyMiddleware`` is also registered for asset URLs since framework
        dev servers commonly ship Vite-bundled assets.

        Args:
            app_config: The Litestar application configuration.
            hotfile_path: Path to the hotfile.
        """
        self._ensure_proxy_target()
        external = self._config.external_dev_server
        static_target = external.target if external else None
        ssr_hotfile = hotfile_path if static_target is None else None

        user_owns_root = _user_has_root_http_handler(app_config.route_handlers)
        http_paths = ["/{path:path}"] if user_owns_root else ["/", "/{path:path}"]

        app_config.route_handlers.append(
            create_ssr_http_proxy_handler(
                target=static_target,
                hotfile_path=ssr_hotfile,
                http2=external.http2 if external else True,
                plugin=self,
                paths=http_paths,
            )
        )
        app_config.route_handlers.append(create_ssr_ws_proxy_handler(target=static_target, hotfile_path=ssr_hotfile))

        self._insert_dev_proxy_middleware(
            app_config,
            DefineMiddleware(
                ViteProxyMiddleware,
                hotfile_path=hotfile_path,
                asset_url=self._config.asset_url,
                resource_dir=self._config.resource_dir,
                bundle_dir=self._config.bundle_dir,
                root_dir=self._config.root_dir,
                http2=self._config.http2,
                plugin=self,
            ),
        )
        hmr_path = f"{self._config.asset_url.rstrip('/')}/vite-hmr"
        app_config.route_handlers.append(
            create_vite_hmr_handler(hotfile_path=hotfile_path, hmr_path=hmr_path, asset_url=self._config.asset_url)
        )

    def on_app_init(self, app_config: "AppConfig") -> "AppConfig":
        """Configure the Litestar application for Vite.

        This method wires up supporting configuration for dev/prod operation:

        - Adds types used by generated handlers to the signature namespace.
        - Ensures a consistent NotFound handler for asset/proxy lookups.
        - Registers optional Inertia and Jinja integrations.
        - Configures static file routing when enabled.
        - Configures dev proxy middleware based on proxy_mode.
        - Creates/initializes the SPA handler where applicable and registers lifespans.

        Args:
            app_config: The Litestar application configuration.

        Returns:
            The modified application configuration.
        """
        from litestar import Response
        from litestar.connection import Request as LitestarRequest

        app_config.signature_namespace["Response"] = Response
        app_config.signature_namespace["Request"] = LitestarRequest

        # Register proxy headers middleware FIRST if configured
        # This must run before other middleware to ensure correct scheme/client in scope
        if self._config.trusted_proxies is not None:
            from litestar_vite.plugin._proxy_headers import ProxyHeadersMiddleware

            app_config.middleware.insert(
                0,  # Insert at beginning for early processing
                DefineMiddleware(ProxyHeadersMiddleware, trusted_hosts=self._config.trusted_proxies),
            )

        handlers: ExceptionHandlersMap = cast("ExceptionHandlersMap", app_config.exception_handlers or {})  # pyright: ignore
        if NotFoundException not in handlers:
            handlers[NotFoundException] = vite_not_found_handler
            app_config.exception_handlers = handlers  # pyright: ignore[reportUnknownMemberType]

        if self._config.inertia is not None:
            app_config = self._configure_inertia(app_config)

        if self._wants_jinja_callables(app_config):
            self._configure_jinja_callables(app_config)

        skip_static = (
            self._config.wants_html_proxy
            and self._config.is_dev_mode
            and self._config.runtime.external_dev_server is not None
        )
        if self._config.set_static_folders and not skip_static:
            self._configure_static_files(app_config)

        if self._config.is_dev_mode and self._config.proxy_mode is not None and not is_non_serving_assets_cli():
            self._configure_dev_proxy(app_config)

        use_spa_handler = self._config.spa_handler and (
            self._config.registers_html_catchall or self._config.wants_html_proxy
        )
        use_spa_handler = use_spa_handler or (
            self._config.wants_html_proxy
            and not self._config.is_dev_mode
            and self._config.runtime.external_dev_server is not None
        )
        if use_spa_handler:
            from litestar_vite.handler import AppHandler

            self._spa_handler = AppHandler(self._config)
            app_config.route_handlers.append(self._spa_handler.create_route_handler())
        elif self._config.mode == "hybrid":
            # Hybrid mode prebuilds AppHandler so InertiaResponse._render_spa can reuse it.
            # Template + Inertia uses _render_template (Jinja-direct) and does not need this.
            from litestar_vite.handler import AppHandler

            self._spa_handler = AppHandler(self._config)

        app_config.lifespan.append(self.lifespan)  # pyright: ignore[reportUnknownMemberType]

        return app_config

    def _check_health(self) -> None:
        """Check if the Vite dev server is running and ready.

        Polls the dev server URL for up to 5 seconds.
        """
        import time

        url = f"{self._config.protocol}://{self._config.host}:{self._config.port}/__vite_ping"
        for _ in range(50):
            try:
                httpx.get(url, timeout=0.1)
            except httpx.HTTPError:
                time.sleep(0.1)
            else:
                log_success("Vite server responded to health check")
                return
        log_fail("Vite server health check failed")

    def _run_health_check(self) -> None:
        """Run the appropriate health check based on proxy mode."""
        match self._config.proxy_mode:
            case "proxy":
                self._check_ssr_health(self._resolve_hotfile_path())
            case _:
                self._check_health()

    def _check_ssr_health(self, hotfile_path: Path, timeout: float = 10.0) -> bool:
        """Wait for SSR framework to be ready via hotfile.

        Polls intelligently for the hotfile and validates HTTP connectivity.
        Exits early as soon as the server is confirmed ready.

        Args:
            hotfile_path: Path to the hotfile written by the SSR framework.
            timeout: Maximum time to wait in seconds (default 10s).

        Returns:
            True if SSR server is ready, False if timeout reached.
        """
        import time

        start = time.time()
        last_url = None

        while time.time() - start < timeout:
            if hotfile_path.exists():
                try:
                    url = read_hotfile_url(hotfile_path)
                    if url:
                        last_url = url
                        resp = httpx.get(url, timeout=0.5, follow_redirects=True)
                        if resp.status_code < 500:
                            log_success(f"SSR server ready at {url}")
                            return True
                except OSError:
                    pass
                except httpx.HTTPError:
                    pass

            time.sleep(0.1)

        if last_url:
            log_fail(f"SSR server at {last_url} did not respond within {timeout}s")
        else:
            log_fail(f"SSR hotfile not found at {hotfile_path} within {timeout}s")
        return False

    def _export_types_sync(self, app: "Litestar") -> None:
        """Export type metadata synchronously on startup.

        This exports OpenAPI schema, route metadata (JSON), typed routes (TypeScript),
        and Inertia pages metadata when type generation is enabled. The Vite plugin
        watches these files and triggers @hey-api/openapi-ts when they change.

        Uses the shared `export_integration_assets` function to guarantee
        byte-identical output between CLI and plugin.

        Args:
            app: The Litestar application instance.
        """
        from litestar_vite.codegen import export_integration_assets

        try:
            result = export_integration_assets(app, self._config)

            if result.exported_files:
                log_success(f"Types exported → {', '.join(result.exported_files)}")
        except (OSError, TypeError, ValueError, ImportError) as e:  # pragma: no cover
            log_warn(f"Type export failed: {e}")

    @contextmanager
    def server_lifespan(self, app: "Litestar") -> "Generator[None, None, None]":
        """Server-level lifespan context manager (runs ONCE per server, before workers).

        This is called by Litestar CLI before workers start. It handles:
        - Environment variable setup (with logging)
        - Vite dev server process start/stop (ONE instance for all workers)
        - Type export on startup

        Note: SPA handler and asset loader initialization happens in the per-worker
        `lifespan` method, which is auto-registered in `on_app_init`.

        Hotfile behavior: the hotfile is written before starting the dev server to ensure proxy
        middleware and SPA handlers can resolve a target URL immediately on first request.

        Args:
            app: The Litestar application instance.

        Yields:
            None
        """
        if self._config.is_dev_mode:
            self._ensure_proxy_target()

        if self._config.set_environment:
            set_environment(config=self._config)
            set_app_environment(app)
            log_info("Applied Vite environment variables")

        self._export_types_sync(app)

        ssr_config = self._resolved_ssr_config()
        ssr_should_start = (
            ssr_config is not None and ssr_config.command is not None and ssr_config.auto_start
        )
        ssr_process: ViteProcess | None = None

        if self._config.is_dev_mode and self._config.runtime.start_dev_server:
            ext = self._config.runtime.external_dev_server
            is_external = isinstance(ext, ExternalDevServer) and ext.enabled

            command_to_run = self._resolve_dev_command()
            if is_external and isinstance(ext, ExternalDevServer) and ext.target:
                self._write_hotfile(ext.target)
            elif not is_external:
                target_url = f"{self._config.protocol}://{self._config.host}:{self._config.port}"
                self._write_hotfile(target_url)

            vite_process: ViteProcess | None = None
            try:
                vite_process = self._get_vite_process()
                vite_process.start(command_to_run, self._config.root_dir)
                log_success("Vite process started")
                if self._config.health_check and not is_external:
                    self._run_health_check()
                if ssr_should_start and ssr_config is not None:
                    ssr_process = self._start_ssr_process(ssr_config)
                yield
            finally:
                self._stop_ssr_process(ssr_process)
                if vite_process is not None:
                    vite_process.stop()
                log_info("Vite process stopped.")
        elif ssr_should_start and ssr_config is not None:
            try:
                ssr_process = self._start_ssr_process(ssr_config)
                yield
            finally:
                self._stop_ssr_process(ssr_process)
        else:
            yield

    def _start_ssr_process(self, ssr_config: "InertiaSSRConfig") -> "ViteProcess":
        """Spawn the SSR /render Node process and run an optional health check."""
        if ssr_config.command is None:  # pragma: no cover - guarded by callers
            msg = "InertiaSSRConfig.command must be set to spawn the SSR process"
            raise ValueError(msg)
        process = self._get_ssr_process()
        cwd = ssr_config.cwd or self._config.root_dir
        process.start(ssr_config.command, cwd)
        log_success(f"SSR /render process started: {' '.join(ssr_config.command)}")
        if ssr_config.health_check:
            self._run_ssr_health_check(ssr_config)
        return process

    def _stop_ssr_process(self, ssr_process: "ViteProcess | None") -> None:
        """Stop the SSR process if one was started."""
        if ssr_process is not None:
            ssr_process.stop()
            log_info("SSR /render process stopped.")

    @asynccontextmanager
    async def lifespan(self, app: "Litestar") -> "AsyncGenerator[None, None]":
        """Worker-level lifespan context manager (runs per worker process).

        This is auto-registered in `on_app_init` and handles per-worker initialization:
        - Environment variable setup (silently - each worker needs process-local env vars)
        - Shared proxy client initialization (dev mode only, for ViteProxyMiddleware/SSRProxyController)
        - Asset loader initialization
        - SPA handler initialization
        - Route metadata injection

        Note: The Vite dev server process is started in `server_lifespan`, which
        runs ONCE per server before workers start.

        Args:
            app: The Litestar application instance.

        Yields:
            None
        """
        from litestar_vite.loader import ViteAssetLoader

        if self._config.set_environment:
            set_environment(config=self._config)
            set_app_environment(app)

        # Initialize shared proxy client for ViteProxyMiddleware/SSRProxyController
        # Uses connection pooling for better performance (HTTP/2 multiplexing, TLS reuse)
        if self._config.is_dev_mode and self._config.proxy_mode is not None:
            self._proxy_client = create_proxy_client(http2=self._config.http2)

        if self._asset_loader is None:
            self._asset_loader = ViteAssetLoader(config=self._config)
        await self._asset_loader.initialize()

        if self._spa_handler is not None and not self._spa_handler.is_initialized:
            self._spa_handler.initialize_sync(vite_url=self._proxy_target)
            log_success("SPA handler initialized")

        is_ssr_mode = self._config.wants_html_proxy
        if not self._config.is_dev_mode and not self._config.has_built_assets() and not is_ssr_mode:
            log_warn(
                "Vite dev server is disabled (dev_mode=False) but no index.html was found. "
                "Run your front-end build or set VITE_DEV_MODE=1 to enable HMR."
            )

        try:
            yield
        finally:
            if self._proxy_client is not None:
                await self._proxy_client.aclose()
                self._proxy_client = None
            if self._spa_handler is not None:
                await self._spa_handler.shutdown_async()


__all__ = (
    "ProxyHeadersMiddleware",
    "SSRProxyMiddleware",
    "StaticFilesConfig",
    "TrustedHosts",
    "VitePlugin",
    "ViteProcess",
    "ViteProxyMiddleware",
    "create_ssr_proxy_controller",
    "create_ssr_websocket_handler",
    "create_vite_hmr_handler",
    "get_litestar_route_prefixes",
    "is_litestar_route",
    "resolve_litestar_version",
    "set_app_environment",
    "set_environment",
)
