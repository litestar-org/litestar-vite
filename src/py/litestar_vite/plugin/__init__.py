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
from litestar_vite.plugin._proxy import ViteProxyMiddleware, create_ssr_proxy_controller, create_vite_hmr_handler
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
    from collections.abc import AsyncIterator, Iterator

    from click import Group
    from litestar import Litestar
    from litestar.config.app import AppConfig
    from litestar.types import ExceptionHandlersMap

    from litestar_vite.config import ViteConfig
    from litestar_vite.handler import AppHandler


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
        self._vite_process = ViteProcess(executor=config.executor)
        self._static_files_config: dict[str, Any] = static_files_config.__dict__ if static_files_config else {}
        self._proxy_target: "str | None" = None
        self._proxy_client: "httpx.AsyncClient | None" = None
        self._spa_handler: "AppHandler | None" = None

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
        app_config.plugins.append(inertia_plugin)

        return app_config

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
        """Configure dev proxy middleware and handlers based on proxy_mode.

        Args:
            app_config: The Litestar application configuration.
        """
        proxy_mode = self._config.proxy_mode
        hotfile_path = self._resolve_hotfile_path()

        if proxy_mode == "vite":
            self._configure_vite_proxy(app_config, hotfile_path)
        elif proxy_mode == "proxy":
            self._configure_ssr_proxy(app_config, hotfile_path)

    def _configure_vite_proxy(self, app_config: "AppConfig", hotfile_path: Path) -> None:
        """Configure Vite proxy mode (allow list).

        Args:
            app_config: The Litestar application configuration.
            hotfile_path: Path to the hotfile.
        """
        self._ensure_proxy_target()
        app_config.middleware.append(
            DefineMiddleware(
                ViteProxyMiddleware,
                hotfile_path=hotfile_path,
                asset_url=self._config.asset_url,
                resource_dir=self._config.resource_dir,
                bundle_dir=self._config.bundle_dir,
                root_dir=self._config.root_dir,
                http2=self._config.http2,
                plugin=self,
            )
        )
        hmr_path = f"{self._config.asset_url.rstrip('/')}/vite-hmr"
        app_config.route_handlers.append(
            create_vite_hmr_handler(hotfile_path=hotfile_path, hmr_path=hmr_path, asset_url=self._config.asset_url)
        )

    def _configure_ssr_proxy(self, app_config: "AppConfig", hotfile_path: Path) -> None:
        """Configure SSR proxy mode (deny list).

        Args:
            app_config: The Litestar application configuration.
            hotfile_path: Path to the hotfile.
        """
        self._ensure_proxy_target()
        external = self._config.external_dev_server
        static_target = external.target if external else None

        app_config.route_handlers.append(
            create_ssr_proxy_controller(
                target=static_target,
                hotfile_path=hotfile_path if static_target is None else None,
                http2=external.http2 if external else True,
                plugin=self,
            )
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

        if JINJA_INSTALLED and self._config.mode in {"template", "htmx"}:
            self._configure_jinja_callables(app_config)

        skip_static = self._config.mode == "external" and self._config.is_dev_mode
        if self._config.set_static_folders and not skip_static:
            self._configure_static_files(app_config)

        if self._config.is_dev_mode and self._config.proxy_mode is not None and not is_non_serving_assets_cli():
            self._configure_dev_proxy(app_config)

        use_spa_handler = self._config.spa_handler and self._config.mode in {"spa", "framework"}
        use_spa_handler = use_spa_handler or (self._config.mode == "external" and not self._config.is_dev_mode)
        if use_spa_handler:
            from litestar_vite.handler import AppHandler

            self._spa_handler = AppHandler(self._config)
            app_config.route_handlers.append(self._spa_handler.create_route_handler())
        elif self._config.mode == "hybrid":
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
    def server_lifespan(self, app: "Litestar") -> "Iterator[None]":
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

        if self._config.is_dev_mode and self._config.runtime.start_dev_server:
            ext = self._config.runtime.external_dev_server
            is_external = isinstance(ext, ExternalDevServer) and ext.enabled

            command_to_run = self._resolve_dev_command()
            if is_external and isinstance(ext, ExternalDevServer) and ext.target:
                self._write_hotfile(ext.target)
            elif not is_external:
                target_url = f"{self._config.protocol}://{self._config.host}:{self._config.port}"
                self._write_hotfile(target_url)

            try:
                self._vite_process.start(command_to_run, self._config.root_dir)
                log_success("Vite process started")
                if self._config.health_check and not is_external:
                    self._run_health_check()
                yield
            finally:
                self._vite_process.stop()
                log_info("Vite process stopped.")
        else:
            yield

    @asynccontextmanager
    async def lifespan(self, app: "Litestar") -> "AsyncIterator[None]":
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

        is_ssr_mode = self._config.mode == "framework" or self._config.proxy_mode == "proxy"
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
    "StaticFilesConfig",
    "TrustedHosts",
    "VitePlugin",
    "ViteProcess",
    "ViteProxyMiddleware",
    "create_ssr_proxy_controller",
    "create_vite_hmr_handler",
    "get_litestar_route_prefixes",
    "is_litestar_route",
    "resolve_litestar_version",
    "set_app_environment",
    "set_environment",
)
