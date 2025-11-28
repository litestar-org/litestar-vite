"""Vite Plugin for Litestar.

This module provides the VitePlugin class for integrating Vite with Litestar.
The plugin handles:

- Static file serving configuration
- Jinja2 template callable registration
- Vite dev server process management
- Async asset loader initialization

Example::

    from litestar import Litestar
    from litestar_vite import VitePlugin, ViteConfig

    app = Litestar(
        plugins=[VitePlugin(config=ViteConfig(dev_mode=True))],
    )
"""

import importlib.metadata
import os
import signal
import subprocess
import threading
from contextlib import asynccontextmanager, contextmanager, suppress
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any, Optional, Union, cast

import anyio
import httpx  # used in proxy middleware health and HTTP forwarding
import websockets  # used in proxy middleware WS forwarding
from rich import print as rich_print
from litestar.cli._utils import console  # pyright: ignore[reportPrivateImportUsage]
from litestar.middleware import DefineMiddleware
from litestar.plugins import CLIPlugin, InitPluginProtocol
from litestar.static_files import create_static_files_router  # pyright: ignore[reportUnknownVariableType]

from litestar_vite.config import JINJA_INSTALLED, TRUE_VALUES
from litestar_vite.exceptions import ViteProcessError

if TYPE_CHECKING:
    from collections.abc import AsyncIterator, Iterator, Sequence

    from click import Group
    from litestar import Litestar
    from litestar.config.app import AppConfig
    from litestar.datastructures import CacheControlHeader
    from litestar.openapi.spec import SecurityRequirement
    from litestar.types import (
        AfterRequestHookHandler,  # pyright: ignore[reportUnknownVariableType]
        AfterResponseHookHandler,  # pyright: ignore[reportUnknownVariableType]
        ASGIApp,
        BeforeRequestHookHandler,  # pyright: ignore[reportUnknownVariableType]
        ExceptionHandlersMap,
        Guard,  # pyright: ignore[reportUnknownVariableType]
        Middleware,
        Receive,
        Scope,
        Send,
    )

    from litestar_vite.config import ViteConfig
    from litestar_vite.executor import JSExecutor
    from litestar_vite.loader import ViteAssetLoader


def set_environment(config: "ViteConfig") -> None:
    """Configure environment variables for Vite integration.

    Sets environment variables that can be used by both the Python backend
    and the Vite frontend during development.

    Args:
        config: The Vite configuration.
    """
    litestar_version = _resolve_litestar_version()
    os.environ.setdefault("ASSET_URL", config.asset_url)
    os.environ.setdefault("VITE_ALLOW_REMOTE", str(True))
    os.environ.setdefault("VITE_PORT", str(config.port))
    os.environ.setdefault("VITE_HOST", config.host)
    os.environ.setdefault("VITE_PROTOCOL", config.protocol)
    os.environ.setdefault("VITE_PROXY_MODE", config.proxy_mode)
    os.environ.setdefault("LITESTAR_VERSION", litestar_version)
    os.environ.setdefault("LITESTAR_VITE_RUNTIME", config.runtime.executor or "node")
    os.environ.setdefault("LITESTAR_VITE_INSTALL_CMD", " ".join(config.install_command))
    os.environ.setdefault("APP_URL", f"http://localhost:{os.environ.get('LITESTAR_PORT', '8000')}")
    if config.is_dev_mode:
        os.environ.setdefault("VITE_DEV_MODE", str(config.is_dev_mode))


def _resolve_litestar_version() -> str:
    """Safely resolve the installed Litestar version as a string."""

    try:
        return importlib.metadata.version("litestar")
    except importlib.metadata.PackageNotFoundError:
        # Fallback to runtime constant if available
        try:
            from litestar import __version__

            return getattr(__version__, "formatted", lambda: str(__version__))()
        except (AttributeError, TypeError):  # pragma: no cover - extremely rare fallback
            return "unknown"


def _pick_free_port() -> int:
    import socket

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


_PROXY_PATH_PREFIXES: tuple[str, ...] = (
    "/@vite",
    "/@id/",
    "/@fs/",
    "/@react-refresh",
    "/@vite/client",
    "/@vite/env",
    "/vite-hmr",
    "/node_modules/.vite/",
    "/@analogjs/",
    "/src/",
)

_PATHS_REQUIRE_BASE_PREFIX: tuple[str, ...] = (
    "/@vite",
    "/@id/",
    "/@fs/",
    "/@react-refresh",
    "/@vite/client",
    "/@vite/env",
    "/vite-hmr",
    "/node_modules/.vite/",
    "/@analogjs/",
    "/src/",
)


def _normalize_prefix(prefix: str) -> str:
    if not prefix.startswith("/"):
        prefix = f"/{prefix}"
    if not prefix.endswith("/"):
        prefix = f"{prefix}/"
    return prefix


class ViteProxyMiddleware:
    """ASGI middleware to proxy Vite dev traffic (HTTP + WS) to internal Vite server."""

    def __init__(
        self,
        app: "ASGIApp",
        target_base_url: str,
        asset_url: Optional[str] = None,
        resource_dir: Optional[Path] = None,
        bundle_dir: Optional[Path] = None,
        root_dir: Optional[Path] = None,
    ) -> None:
        self.app = app
        self.target_base_url = target_base_url.rstrip("/")
        self.asset_prefix = _normalize_prefix(asset_url) if asset_url else "/"
        self._proxy_path_prefixes = _normalize_proxy_prefixes(
            base_prefixes=_PROXY_PATH_PREFIXES,
            asset_url=asset_url,
            resource_dir=resource_dir,
            bundle_dir=bundle_dir,
            root_dir=root_dir,
        )

    async def __call__(self, scope: "Scope", receive: "Receive", send: "Send") -> None:
        scope_dict = cast("dict[str, Any]", scope)
        path = scope_dict.get("path", "")
        should = self._should_proxy(path)
        rich_print(f"[vite-proxy] path={path!s} should_proxy={should}")
        if scope["type"] == "http" and should:
            await self._proxy_http(scope_dict, receive, send)
            return
        if scope["type"] == "websocket" and should:
            await self._proxy_ws(scope_dict, receive, send)
            return
        await self.app(scope, receive, send)

    def _should_proxy(self, path: str) -> bool:
        # Litestar may hand us percent-encoded paths (e.g. /%40vite/client).
        try:
            from urllib.parse import unquote
        except Exception:  # pragma: no cover - extremely small surface
            return path.startswith(self._proxy_path_prefixes)

        decoded = unquote(path)
        return decoded.startswith(self._proxy_path_prefixes) or path.startswith(self._proxy_path_prefixes)

    async def _proxy_http(self, scope: dict[str, Any], receive: Any, send: Any) -> None:
        method = scope.get("method", "GET")
        raw_path = scope.get("raw_path", b"").decode()
        query_string = scope.get("query_string", b"").decode()
        proxied_path = raw_path
        if self.asset_prefix != "/" and not raw_path.startswith(self.asset_prefix):
            proxied_path = f"{self.asset_prefix.rstrip('/')}{raw_path}"

        url = f"{self.target_base_url}{proxied_path}"
        if query_string:
            url = f"{url}?{query_string}"

        headers = [(k.decode(), v.decode()) for k, v in scope.get("headers", [])]
        body = b""
        more_body = True
        while more_body:
            event = await receive()
            if event["type"] != "http.request":
                continue
            body += event.get("body", b"")
            more_body = event.get("more_body", False)

        async with httpx.AsyncClient() as client:
            try:
                upstream_resp = await client.request(method, url, headers=headers, content=body, timeout=10.0)
            except httpx.HTTPError as exc:  # pragma: no cover - network failure path
                await send({
                    "type": "http.response.start",
                    "status": 502,
                    "headers": [(b"content-type", b"text/plain")],
                })
                await send({"type": "http.response.body", "body": str(exc).encode()})
                return

        response_headers = [(k.encode(), v.encode()) for k, v in upstream_resp.headers.items()]
        await send({
            "type": "http.response.start",
            "status": upstream_resp.status_code,
            "headers": response_headers,
        })
        await send({"type": "http.response.body", "body": upstream_resp.content})

    async def _proxy_ws(self, scope: dict[str, Any], receive: Any, send: Any) -> None:
        raw_path = scope.get("raw_path", b"").decode()
        query_string = scope.get("query_string", b"").decode()
        proxied_path = raw_path
        if self.asset_prefix != "/" and not raw_path.startswith(self.asset_prefix):
            proxied_path = f"{self.asset_prefix.rstrip('/')}{raw_path}"

        target = f"{self.target_base_url.replace('http', 'ws')}{proxied_path}"
        if query_string:
            target = f"{target}?{query_string}"

        headers = [(k.decode(), v.decode()) for k, v in scope.get("headers", [])]
        await send({"type": "websocket.accept"})

        async with websockets.connect(target, extra_headers=headers) as upstream:

            async def client_to_upstream() -> None:
                while True:
                    message = await receive()
                    if message["type"] == "websocket.receive":
                        if "text" in message and message["text"] is not None:
                            await upstream.send(message["text"])
                        if "bytes" in message and message["bytes"] is not None:
                            await upstream.send(message["bytes"])
                    elif message["type"] == "websocket.disconnect":
                        await upstream.close()
                        break

            async def upstream_to_client() -> None:
                async for msg in upstream:
                    if isinstance(msg, str):
                        await send({"type": "websocket.send", "text": msg})
                    else:
                        await send({"type": "websocket.send", "bytes": msg})
                await send({"type": "websocket.close", "code": 1000})

            async with anyio.create_task_group() as tg:
                tg.start_soon(client_to_upstream)
                tg.start_soon(upstream_to_client)


@dataclass
class StaticFilesConfig:
    """Configuration for static file serving.

    This configuration is passed to Litestar's static files router.
    """

    after_request: "Optional[AfterRequestHookHandler]" = None
    after_response: "Optional[AfterResponseHookHandler]" = None
    before_request: "Optional[BeforeRequestHookHandler]" = None
    cache_control: "Optional[CacheControlHeader]" = None
    exception_handlers: "Optional[ExceptionHandlersMap]" = None
    guards: "Optional[list[Guard]]" = None
    middleware: "Optional[Sequence[Middleware]]" = None
    opt: "Optional[dict[str, Any]]" = None
    security: "Optional[Sequence[SecurityRequirement]]" = None
    tags: "Optional[Sequence[str]]" = None


class ViteProcess:
    """Manages the Vite development server process.

    This class handles starting and stopping the Vite dev server process,
    with proper thread safety and graceful shutdown.
    """

    _atexit_registered: bool = False

    def __init__(self, executor: "JSExecutor") -> None:
        """Initialize the Vite process manager.

        Args:
            executor: The JavaScript executor to use for running Vite.
        """
        self.process: "Optional[subprocess.Popen[bytes]]" = None
        self._lock = threading.Lock()
        self._executor = executor
        if not ViteProcess._atexit_registered:
            import atexit

            atexit.register(self._atexit_stop)
            ViteProcess._atexit_registered = True

    def start(self, command: list[str], cwd: "Optional[Union[Path, str]]") -> None:
        """Start the Vite process.

        Args:
            command: The command to run (e.g., ["npm", "run", "dev"]).
            cwd: The working directory for the process.

        Raises:
            ViteProcessError: If the process fails to start.
        """
        if cwd is not None and isinstance(cwd, str):
            cwd = Path(cwd)

        try:
            with self._lock:
                if self.process and self.process.poll() is None:
                    return

                if cwd:
                    self.process = self._executor.run(command, cwd)
                    # If the process exited immediately, surface stdout/stderr for debugging
                    if self.process and self.process.poll() is not None:
                        stdout, stderr = self.process.communicate()
                        out_str = stdout.decode(errors="ignore") if stdout else ""
                        err_str = stderr.decode(errors="ignore") if stderr else ""
                        console.print(
                            "[red]Vite process exited immediately.[/]\n"
                            f"[red]Command:[/] {' '.join(command)}\n"
                            f"[red]Exit code:[/] {self.process.returncode}\n"
                            f"[red]Stdout:[/]\n{out_str or '<empty>'}\n"
                            f"[red]Stderr:[/]\n{err_str or '<empty>'}"
                        )
                        msg = f"Vite process failed to start (exit {self.process.returncode})"
                        raise ViteProcessError(msg)
        except Exception as e:
            console.print(f"[red]Failed to start Vite process: {e!s}[/]")
            msg = f"Failed to start Vite process: {e!s}"
            raise ViteProcessError(msg) from e

    def stop(self, timeout: float = 5.0) -> None:
        """Stop the Vite process.

        Args:
            timeout: Seconds to wait for graceful shutdown before killing.

        Raises:
            ViteProcessError: If the process fails to stop.
        """
        try:
            with self._lock:
                if self.process and self.process.poll() is None:
                    # Send SIGTERM for graceful shutdown
                    if hasattr(signal, "SIGTERM"):
                        self.process.terminate()
                    try:
                        self.process.wait(timeout=timeout)
                    except subprocess.TimeoutExpired:
                        # Force kill if still alive
                        if hasattr(signal, "SIGKILL"):
                            self.process.kill()
                        self.process.wait(timeout=1.0)
        except Exception as e:
            console.print(f"[red]Failed to stop Vite process: {e!s}[/]")
            msg = f"Failed to stop Vite process: {e!s}"
            raise ViteProcessError(msg) from e

    def _atexit_stop(self) -> None:
        """Best-effort stop on interpreter exit."""
        with suppress(Exception):
            self.stop()


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
        "_proxy_target",
        "_static_files_config",
        "_use_server_lifespan",
        "_vite_process",
    )

    def __init__(
        self,
        config: "Optional[ViteConfig]" = None,
        asset_loader: "Optional[ViteAssetLoader]" = None,
        static_files_config: "Optional[StaticFilesConfig]" = None,
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
        self._use_server_lifespan = True
        self._proxy_target: "Optional[str]" = None

    @property
    def config(self) -> "ViteConfig":
        """Get the Vite configuration."""
        return self._config

    @property
    def asset_loader(self) -> "ViteAssetLoader":
        """Get the asset loader instance.

        Lazily initializes the loader if not already set.
        """
        from litestar_vite.loader import ViteAssetLoader

        if self._asset_loader is None:
            self._asset_loader = ViteAssetLoader.initialize_loader(config=self._config)
        return self._asset_loader

    def _ensure_proxy_target(self) -> None:
        """Prepare proxy target URL and hotfile for proxy mode."""
        if self._proxy_target is not None or self._config.proxy_mode != "proxy" or not self._config.is_dev_mode:
            return

        # Force loopback for internal dev server unless explicitly overridden
        if os.getenv("VITE_ALLOW_REMOTE", "False") not in TRUE_VALUES:
            self._config.runtime.host = "127.0.0.1"

        # If VITE_PORT not explicitly set, pick a free one for the internal server
        if os.getenv("VITE_PORT") is None:
            self._config.runtime.port = _pick_free_port()

        self._proxy_target = f"{self._config.protocol}://{self._config.host}:{self._config.port}"

        # Write hotfile for JS plugin consumption
        hotfile_path = self._config.bundle_dir / self._config.hot_file
        hotfile_path.parent.mkdir(parents=True, exist_ok=True)
        hotfile_path.write_text(self._proxy_target)

    def on_cli_init(self, cli: "Group") -> None:
        """Register CLI commands.

        Args:
            cli: The Click command group to add commands to.
        """
        from litestar_vite.cli import vite_group

        cli.add_command(vite_group)

    def on_app_init(self, app_config: "AppConfig") -> "AppConfig":
        """Configure the Litestar application for Vite.

        This method:
        - Registers Jinja2 template callables (if Jinja2 is installed and template mode)
        - Configures static file serving
        - Sets up SPA handler if in SPA mode
        - Sets up the server lifespan hook if enabled

        Args:
            app_config: The Litestar application configuration.

        Returns:
            The modified application configuration.
        """
        from litestar_vite.loader import (
            render_asset_tag,
            render_hmr_client,
            render_partial_asset_tag,
            render_static_asset,
        )

        # Register Jinja2 template callables if Jinja2 is installed and in template mode
        if JINJA_INSTALLED and self._config.mode in {"template", "htmx"}:
            from litestar.contrib.jinja import JinjaTemplateEngine

            template_config = app_config.template_config  # pyright: ignore[reportUnknownMemberType,reportUnknownVariableType]
            if template_config and isinstance(
                template_config.engine_instance,  # pyright: ignore[reportUnknownMemberType]
                JinjaTemplateEngine,
            ):
                engine = template_config.engine_instance  # pyright: ignore[reportUnknownMemberType]
                engine.register_template_callable(
                    key="vite_hmr",
                    template_callable=render_hmr_client,
                )
                engine.register_template_callable(
                    key="vite",
                    template_callable=render_asset_tag,
                )
                engine.register_template_callable(
                    key="vite_static",
                    template_callable=render_static_asset,
                )
                engine.register_template_callable(
                    key="vite_partial",
                    template_callable=render_partial_asset_tag,
                )

        # Configure static file serving
        if self._config.set_static_folders:
            static_dirs = [
                Path(self._config.bundle_dir),
                Path(self._config.resource_dir),
            ]
            if Path(self._config.public_dir).exists() and self._config.public_dir != self._config.bundle_dir:
                static_dirs.append(Path(self._config.public_dir))

            base_config = {
                "directories": (static_dirs if self._config.is_dev_mode else [Path(self._config.bundle_dir)]),
                "path": self._config.asset_url,
                "name": "vite",
                "html_mode": False,
                "include_in_schema": False,
                "opt": {"exclude_from_auth": True},
            }
            static_files_config: dict[str, Any] = {**base_config, **self._static_files_config}
            app_config.route_handlers.append(create_static_files_router(**static_files_config))

        # Add dev proxy middleware for single-port mode
        if self._config.is_dev_mode and self._config.proxy_mode == "proxy":
            self._ensure_proxy_target()
            app_config.middleware.append(
                DefineMiddleware(
                    ViteProxyMiddleware,
                    target_base_url=self._proxy_target or "",
                    asset_url=self._config.asset_url,
                    resource_dir=self._config.resource_dir,
                    bundle_dir=self._config.bundle_dir,
                    root_dir=self._config.root_dir,
                )
            )

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
                return
        console.print("[red]Vite server health check failed[/]")

    def _export_types_sync(self, app: "Litestar") -> None:
        """Export type metadata synchronously on startup.

        This exports OpenAPI schema and route metadata when type generation
        is enabled. The Vite plugin watches these files and triggers
        @hey-api/openapi-ts when they change.

        Args:
            app: The Litestar application instance.
        """
        from litestar_vite.config import TypeGenConfig

        if not isinstance(self._config.types, TypeGenConfig) or not self._config.types.enabled:
            return

        try:
            import msgspec
            from litestar.serialization import encode_json, get_serializer

            from litestar_vite.codegen import generate_routes_json

            console.print("[dim]Exporting type metadata for Vite...[/]")

            # Check if OpenAPI is configured by looking at the plugins registry
            # (accessing openapi_schema property directly raises when not configured)
            from litestar._openapi.plugin import OpenAPIPlugin

            openapi_plugin = next((p for p in app.plugins._plugins if isinstance(p, OpenAPIPlugin)), None)  # pyright: ignore[reportPrivateUsage]
            has_openapi = openapi_plugin is not None and openapi_plugin._openapi_config is not None  # pyright: ignore[reportPrivateUsage]
            if has_openapi:
                try:
                    serializer = get_serializer(
                        app.type_encoders if isinstance(getattr(app, "type_encoders", None), dict) else None
                    )
                    schema_dict = app.openapi_schema.to_schema()
                    schema_content = msgspec.json.format(
                        encode_json(schema_dict, serializer=serializer),
                        indent=2,
                    )
                    self._config.types.openapi_path.parent.mkdir(parents=True, exist_ok=True)
                    self._config.types.openapi_path.write_bytes(schema_content)
                except (TypeError, ValueError, OSError, AttributeError) as exc:  # pragma: no cover
                    console.print(f"[yellow]! OpenAPI export skipped: {exc}[/]")
            else:
                console.print("[yellow]! OpenAPI schema not available; skipping openapi.json export[/]")

            # Export routes
            routes_data = generate_routes_json(app, include_components=True)
            routes_data["litestar_version"] = _resolve_litestar_version()
            routes_content = msgspec.json.format(
                msgspec.json.encode(routes_data),
                indent=2,
            )
            self._config.types.routes_path.parent.mkdir(parents=True, exist_ok=True)
            self._config.types.routes_path.write_bytes(routes_content)

            console.print(
                f"[green]✓ Types exported to {self._config.types.routes_path}[/]"
                + (f" (openapi: {self._config.types.openapi_path})" if has_openapi else " (openapi skipped)")
            )
        except (OSError, TypeError, ValueError, ImportError) as e:  # pragma: no cover
            console.print(f"[yellow]! Type export failed: {e}[/]")

    @contextmanager
    def server_lifespan(self, app: "Litestar") -> "Iterator[None]":
        """Synchronous context manager for Vite server lifecycle.

        Manages the Vite dev server process during the application lifespan.

        Args:
            app: The Litestar application instance.

        Yields:
            None
        """
        if self._config.set_environment:
            set_environment(config=self._config)

        # Export types on startup (when enabled)
        self._export_types_sync(app)

        if self._use_server_lifespan and self._config.is_dev_mode:
            self._ensure_proxy_target()
            if not app.debug:
                console.print("[yellow]WARNING: Vite dev mode is enabled in production![/]")

            command_to_run = self._config.run_command if self._config.hot_reload else self._config.build_watch_command

            if self._config.hot_reload:
                console.rule("[yellow]Starting Vite process with HMR Enabled[/]", align="left")
            else:
                console.rule("[yellow]Starting Vite watch and build process[/]", align="left")

            if self._proxy_target:
                console.print(f"[dim]Vite proxy target: {self._proxy_target}[/]")

            try:
                self._vite_process.start(command_to_run, self._config.root_dir)
                if self._config.health_check:
                    self._check_health()
                yield
            finally:
                self._vite_process.stop()
                console.print("[yellow]Vite process stopped.[/]")
        else:
            yield

    @asynccontextmanager
    async def async_server_lifespan(self, app: "Litestar") -> "AsyncIterator[None]":
        """Async context manager for Vite server lifecycle.

        This is the preferred lifespan manager for async applications.
        It initializes the asset loader asynchronously for non-blocking I/O.

        Args:
            app: The Litestar application instance.

        Yields:
            None
        """
        from litestar_vite.loader import ViteAssetLoader

        if self._config.set_environment:
            set_environment(config=self._config)

        # Initialize asset loader asynchronously
        if self._asset_loader is None:
            self._asset_loader = ViteAssetLoader(config=self._config)
        await self._asset_loader.initialize()

        # Export types on startup (when enabled)
        self._export_types_sync(app)

        if self._use_server_lifespan and self._config.is_dev_mode:
            self._ensure_proxy_target()
            if self._config.set_environment:
                set_environment(config=self._config)
            if not app.debug:
                console.print("[yellow]WARNING: Vite dev mode is enabled in production![/]")

            command_to_run = self._config.run_command if self._config.hot_reload else self._config.build_watch_command

            if self._config.hot_reload:
                console.rule("[yellow]Starting Vite process with HMR Enabled[/]", align="left")
            else:
                console.rule("[yellow]Starting Vite watch and build process[/]", align="left")

            try:
                self._vite_process.start(command_to_run, self._config.root_dir)
                if self._config.health_check:
                    self._check_health()
                yield
            finally:
                self._vite_process.stop()
                console.print("[yellow]Vite process stopped.[/]")
        else:
            yield


def _normalize_proxy_prefixes(
    base_prefixes: tuple[str, ...],
    asset_url: "Optional[str]" = None,
    resource_dir: "Optional[Path]" = None,
    bundle_dir: "Optional[Path]" = None,
    root_dir: "Optional[Path]" = None,
) -> tuple[str, ...]:

    def _normalize_prefix(prefix: str) -> str:
        if not prefix.startswith("/"):
            prefix = f"/{prefix}"
        if not prefix.endswith("/"):
            prefix = f"{prefix}/"
        return prefix

    prefixes: list[str] = list(base_prefixes)

    if asset_url:
        prefixes.append(_normalize_prefix(asset_url))

    def _add_path(path: Union[Path, str, None]) -> None:
        if path is None:
            return
        p = Path(path)
        if root_dir and p.is_absolute():
            with suppress(ValueError):
                p = p.relative_to(root_dir)
        prefixes.append(_normalize_prefix(str(p).replace("\\", "/")))

    _add_path(resource_dir)
    _add_path(bundle_dir)

    # Remove duplicates while preserving order
    seen: set[str] = set()
    unique = []
    for p in prefixes:
        if p not in seen:
            unique.append(p)
            seen.add(p)
    return tuple(unique)
