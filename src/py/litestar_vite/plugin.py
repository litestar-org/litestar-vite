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
import json
import logging
import os
import signal
import subprocess
import sys
import threading
from contextlib import asynccontextmanager, contextmanager, suppress
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

import anyio
import httpx  # used in proxy middleware health and HTTP forwarding
import websockets  # used in proxy middleware WS forwarding
from litestar import Response
from litestar.cli._utils import console  # pyright: ignore[reportPrivateImportUsage]
from litestar.connection import Request
from litestar.enums import ScopeType
from litestar.exceptions import NotFoundException, WebSocketDisconnect
from litestar.middleware import AbstractMiddleware, DefineMiddleware
from litestar.plugins import CLIPlugin, InitPluginProtocol
from litestar.static_files import create_static_files_router  # pyright: ignore[reportUnknownVariableType]
from websockets.typing import Subprotocol

from litestar_vite.config import JINJA_INSTALLED, TRUE_VALUES, ExternalDevServer, TypeGenConfig, ViteConfig
from litestar_vite.exceptions import ViteProcessError

if TYPE_CHECKING:
    from collections.abc import AsyncIterator, Callable, Iterator, Sequence

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
    from websockets.typing import Subprotocol

    from litestar_vite.executor import JSExecutor
    from litestar_vite.loader import ViteAssetLoader
    from litestar_vite.spa import ViteSPAHandler


# Disconnect exceptions that should be silently ignored during WebSocket shutdown
_DISCONNECT_EXCEPTIONS = (WebSocketDisconnect, anyio.ClosedResourceError, websockets.ConnectionClosed)
_TICK = "[bold green]✓[/]"
_INFO = "[cyan]•[/]"
_WARN = "[yellow]![/]"
_FAIL = "[red]x[/]"


def _fmt_path(path: Path) -> str:
    """Return a path relative to CWD when possible to keep logs short."""
    try:
        return str(path.relative_to(Path.cwd()))
    except ValueError:
        return str(path)


# Cache debug flag check to avoid repeated os.environ lookups
_vite_proxy_debug: bool | None = None


def _is_proxy_debug() -> bool:
    """Check if VITE_PROXY_DEBUG is enabled (cached).

    Returns:
        True if VITE_PROXY_DEBUG is set to a truthy value, else False.
    """
    global _vite_proxy_debug  # noqa: PLW0603
    if _vite_proxy_debug is None:
        _vite_proxy_debug = os.environ.get("VITE_PROXY_DEBUG", "").lower() in {"1", "true", "yes"}
    return _vite_proxy_debug


def _configure_proxy_logging() -> None:
    """Suppress verbose proxy-related logging unless debug is enabled.

    Suppresses INFO-level logs from:
    - httpx: logs every HTTP request
    - websockets: logs connection events
    - uvicorn.protocols.websockets: logs "connection open/closed"

    Only show these logs when VITE_PROXY_DEBUG is enabled.
    """

    if not _is_proxy_debug():
        for logger_name in ("httpx", "websockets", "uvicorn.protocols.websockets"):
            logging.getLogger(logger_name).setLevel(logging.WARNING)


# Configure proxy logging on module load
_configure_proxy_logging()


def _infer_port_from_argv() -> str | None:
    """Best-effort extraction of `--port/-p` from process argv.

    Returns:
        The port as a string if found, else None.
    """

    argv = sys.argv[1:]
    for i, arg in enumerate(argv):
        if arg in {"-p", "--port"} and i + 1 < len(argv) and argv[i + 1].isdigit():
            return argv[i + 1]
        if arg.startswith("--port="):
            _, _, value = arg.partition("=")
            if value.isdigit():
                return value
    return None


def _is_non_serving_assets_cli() -> bool:
    """Return True when running CLI assets commands that don't start a server.

    This suppresses dev-proxy setup/logging for commands like `assets build`
    where only a Vite build is performed and no proxy should be initialized.
    """

    argv_str = " ".join(sys.argv)
    non_serving_commands = (
        " assets build",
        " assets install",
        " assets deploy",
        " assets doctor",
        " assets generate-types",
        " assets export-routes",
        " assets status",
        " assets init",
    )
    return any(cmd in argv_str for cmd in non_serving_commands)


def _log_success(message: str) -> None:
    """Print a success message with consistent styling."""

    console.print(f"{_TICK} {message}")


def _log_info(message: str) -> None:
    """Print an informational message with consistent styling."""

    console.print(f"{_INFO} {message}")


def _log_warn(message: str) -> None:
    """Print a warning message with consistent styling."""

    console.print(f"{_WARN} {message}")


def _log_fail(message: str) -> None:
    """Print an error message with consistent styling."""

    console.print(f"{_FAIL} {message}")


def _write_runtime_config_file(config: ViteConfig) -> str:
    """Write a JSON handoff file for the Vite plugin and return its path.

    Returns:
        The path to the written config file.

    """

    root = config.root_dir or Path.cwd()
    path = Path(root) / ".litestar.json"
    types = config.types if isinstance(config.types, TypeGenConfig) else None
    deploy = config.deploy_config
    resource_dir = config.resource_dir
    resource_dir_value = str(resource_dir) if resource_dir != Path("src") else None
    bundle_dir_value = str(config.bundle_dir)
    ssr_out_dir_value = str(config.ssr_output_dir) if config.ssr_output_dir else None
    if resource_dir_value is None:
        # Keep JS defaults (resources/bootstrap/ssr)
        ssr_out_dir_value = None

    # Extract external dev server info
    external = config.external_dev_server
    external_target = external.target if external else None
    external_http2 = external.http2 if external else False

    litestar_version = os.environ.get("LITESTAR_VERSION") or _resolve_litestar_version()

    payload = {
        "assetUrl": config.asset_url,
        "baseUrl": config.base_url,
        "bundleDir": bundle_dir_value,
        "hotFile": config.hot_file,
        "resourceDir": resource_dir_value,
        "publicDir": str(config.public_dir),
        "manifest": config.manifest_name,
        "mode": config.mode,
        # Dev server fields
        "proxyMode": config.proxy_mode,
        "port": config.port,
        "host": config.host,
        "externalTarget": external_target,
        "externalHttp2": external_http2,
        # SSR fields
        "ssrEnabled": config.ssr_enabled,
        "ssrOutDir": ssr_out_dir_value,
        "types": {
            "enabled": types.enabled,
            "output": str(types.output),
            "openapiPath": str(types.openapi_path),
            "routesPath": str(types.routes_path),
            "generateZod": types.generate_zod,
            "generateSdk": types.generate_sdk,
        }
        if types
        else None,
        "deploy": {
            "storageBackend": deploy.storage_backend if deploy else None,
            "deleteOrphaned": deploy.delete_orphaned if deploy else None,
            "includeManifest": deploy.include_manifest if deploy else None,
            "contentTypes": deploy.content_types if deploy else None,
        },
        # Executor for package commands (npx, bunx, etc.)
        "executor": config.runtime.executor,
        "litestarVersion": litestar_version,
    }

    path.write_text(json.dumps(payload, indent=2))
    return str(path)


def set_environment(config: ViteConfig, asset_url_override: str | None = None) -> None:
    """Configure environment variables for Vite integration.

    Sets environment variables that can be used by both the Python backend
    and the Vite frontend during development.

    Args:
        config: The Vite configuration.
        asset_url_override: Optional asset URL to force (e.g., CDN base during build).
    """
    litestar_version = os.environ.get("LITESTAR_VERSION") or _resolve_litestar_version()
    asset_url = asset_url_override or config.asset_url
    base_url = config.base_url or asset_url
    if asset_url:
        os.environ.setdefault("ASSET_URL", asset_url)
    if base_url:
        os.environ.setdefault("VITE_BASE_URL", base_url)
    os.environ.setdefault("VITE_ALLOW_REMOTE", str(True))

    backend_host = os.environ.get("LITESTAR_HOST") or "127.0.0.1"
    backend_port = os.environ.get("LITESTAR_PORT") or os.environ.get("PORT") or _infer_port_from_argv() or "8000"
    os.environ["LITESTAR_HOST"] = backend_host
    os.environ["LITESTAR_PORT"] = str(backend_port)
    os.environ.setdefault("APP_URL", f"http://{backend_host}:{backend_port}")

    # VITE_ env for the JS side
    os.environ.setdefault("VITE_PROTOCOL", config.protocol)
    if config.proxy_mode is not None:
        os.environ.setdefault("VITE_PROXY_MODE", config.proxy_mode)

    # If the Python side already picked a host/port (e.g., proxy mode with an auto-free port),
    # surface them to the Vite process unless the user explicitly set them.
    os.environ.setdefault("VITE_HOST", config.host)
    os.environ.setdefault("VITE_PORT", str(config.port))
    # Set framework-specific host/port env vars for SSR frameworks
    # Nuxt/Nitro priority: NUXT_HOST > NITRO_HOST > HOST, NUXT_PORT > NITRO_PORT > PORT
    os.environ.setdefault("NUXT_HOST", config.host)
    os.environ.setdefault("NUXT_PORT", str(config.port))
    os.environ.setdefault("NITRO_HOST", config.host)
    os.environ.setdefault("NITRO_PORT", str(config.port))
    # Generic HOST/PORT fallback (Nitro, Astro, etc.)
    os.environ.setdefault("HOST", config.host)
    os.environ.setdefault("PORT", str(config.port))

    os.environ["LITESTAR_VERSION"] = litestar_version
    os.environ.setdefault("LITESTAR_VITE_RUNTIME", config.runtime.executor or "node")
    os.environ.setdefault("LITESTAR_VITE_INSTALL_CMD", " ".join(config.install_command))

    if config.is_dev_mode:
        os.environ.setdefault("VITE_DEV_MODE", str(config.is_dev_mode))

    config_path = _write_runtime_config_file(config)
    os.environ["LITESTAR_VITE_CONFIG_PATH"] = config_path


def set_app_environment(app: "Litestar") -> None:
    """Set environment variables derived from the Litestar app instance.

    This is called after set_environment() once the app is available,
    to export app-specific configuration like OpenAPI paths.

    Args:
        app: The Litestar application instance.
    """
    # Export OpenAPI schema path for Vite plugin health checks
    openapi_config = app.openapi_config
    if openapi_config is not None:
        path = getattr(openapi_config, "path", None)
        if isinstance(path, str) and path:
            # The path attribute contains the schema endpoint path (default: "/schema")
            os.environ.setdefault("LITESTAR_OPENAPI_PATH", path)


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
    "/__vite_ping",
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


class ViteProxyMiddleware(AbstractMiddleware):
    """ASGI middleware to proxy Vite dev HTTP traffic to internal Vite server.

    HTTP requests use httpx.AsyncClient with optional HTTP/2 support for better
    connection multiplexing. WebSocket traffic (used by Vite HMR) is handled by
    a dedicated WebSocket route handler created by create_vite_hmr_handler().

    The middleware reads the Vite server URL from the hotfile dynamically,
    ensuring it always connects to the correct Vite server even if the port changes.
    """

    # Only handle HTTP requests - WebSocket HMR is handled by a dedicated route handler
    scopes = {ScopeType.HTTP}

    def __init__(
        self,
        app: "ASGIApp",
        hotfile_path: Path,
        asset_url: "str | None" = None,
        resource_dir: "Path | None" = None,
        bundle_dir: "Path | None" = None,
        root_dir: "Path | None" = None,
        http2: bool = True,
    ) -> None:
        super().__init__(app)
        self.hotfile_path = hotfile_path
        self._cached_target: str | None = None
        self._cache_initialized = False
        self.asset_prefix = _normalize_prefix(asset_url) if asset_url else "/"
        self.http2 = http2
        self._proxy_path_prefixes = _normalize_proxy_prefixes(
            base_prefixes=_PROXY_PATH_PREFIXES,
            asset_url=asset_url,
            resource_dir=resource_dir,
            bundle_dir=bundle_dir,
            root_dir=root_dir,
        )

    def _get_target_base_url(self) -> str | None:
        """Read the Vite server URL from the hotfile with permanent caching.

        The hotfile is read once and cached for the lifetime of the server.
        Server restart refreshes the cache automatically.

        Returns:
            The Vite server URL or None if unavailable.
        """
        if self._cache_initialized:
            return self._cached_target.rstrip("/") if self._cached_target else None

        try:
            url = self.hotfile_path.read_text().strip()
            self._cached_target = url
            self._cache_initialized = True
            if _is_proxy_debug():
                console.print(f"[dim][vite-proxy] Target: {url}[/]")
            return url.rstrip("/")
        except FileNotFoundError:
            self._cached_target = None
            self._cache_initialized = True
            return None

    async def __call__(self, scope: "Scope", receive: "Receive", send: "Send") -> None:
        scope_dict = cast("dict[str, Any]", scope)
        path = scope_dict.get("path", "")
        should = self._should_proxy(path)
        if _is_proxy_debug():
            console.print(f"[dim][vite-proxy] {path} → proxy={should}[/]")
        if should:
            await self._proxy_http(scope_dict, receive, send)
            return
        await self.app(scope, receive, send)

    def _should_proxy(self, path: str) -> bool:
        # Litestar may hand us percent-encoded paths (e.g. /%40vite/client).
        try:
            from urllib.parse import unquote
        except ImportError:  # pragma: no cover - extremely small surface
            return path.startswith(self._proxy_path_prefixes)

        decoded = unquote(path)
        return decoded.startswith(self._proxy_path_prefixes) or path.startswith(self._proxy_path_prefixes)

    async def _proxy_http(self, scope: dict[str, Any], receive: Any, send: Any) -> None:
        target_base_url = self._get_target_base_url()
        if target_base_url is None:
            # Hotfile not found - Vite server not running
            await send(
                {
                    "type": "http.response.start",
                    "status": 503,
                    "headers": [(b"content-type", b"text/plain")],
                }
            )
            await send({"type": "http.response.body", "body": b"Vite dev server not running"})
            return

        method = scope.get("method", "GET")
        raw_path = scope.get("raw_path", b"").decode()
        query_string = scope.get("query_string", b"").decode()
        proxied_path = raw_path
        if self.asset_prefix != "/" and not raw_path.startswith(self.asset_prefix):
            proxied_path = f"{self.asset_prefix.rstrip('/')}{raw_path}"

        url = f"{target_base_url}{proxied_path}"
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

        # Use HTTP/2 when enabled for better connection multiplexing
        # Note: httpx handles the protocol negotiation automatically
        # HTTP/2 requires the h2 package - gracefully fallback if not installed
        http2_enabled = self.http2
        if http2_enabled:
            try:
                import h2  # noqa: F401  # pyright: ignore[reportMissingImports,reportUnusedImport]
            except ImportError:
                http2_enabled = False

        async with httpx.AsyncClient(http2=http2_enabled) as client:
            try:
                upstream_resp = await client.request(method, url, headers=headers, content=body, timeout=10.0)
            except httpx.HTTPError as exc:  # pragma: no cover - network failure path
                await send(
                    {
                        "type": "http.response.start",
                        "status": 502,
                        "headers": [(b"content-type", b"text/plain")],
                    }
                )
                await send({"type": "http.response.body", "body": str(exc).encode()})
                return

        response_headers = [(k.encode(), v.encode()) for k, v in upstream_resp.headers.items()]
        await send(
            {
                "type": "http.response.start",
                "status": upstream_resp.status_code,
                "headers": response_headers,
            }
        )
        await send({"type": "http.response.body", "body": upstream_resp.content})


class ExternalDevServerProxyMiddleware(AbstractMiddleware):
    """ASGI middleware to proxy requests to an external dev server (blacklist mode).

    This middleware proxies all requests that don't match Litestar-registered routes
    to the target dev server. It supports two modes:

    1. **Static target**: Provide a fixed URL (e.g., "http://localhost:4200" for Angular CLI)
    2. **Dynamic target**: Leave target as None and provide hotfile_path - the proxy reads
       the target URL from the Vite hotfile (for SSR frameworks like Astro, Nuxt, SvelteKit)

    Unlike ViteProxyMiddleware (whitelist), this middleware:
    - Uses blacklist approach: proxies everything EXCEPT Litestar routes
    - Supports both static and dynamic target URLs
    - Auto-excludes Litestar routes, static mounts, and schema paths
    """

    scopes = {ScopeType.HTTP}

    def __init__(
        self,
        app: "ASGIApp",
        target: "str | None" = None,
        hotfile_path: "Path | None" = None,
        http2: bool = False,
        litestar_app: "Litestar | None" = None,
    ) -> None:
        """Initialize the external dev server proxy middleware.

        Args:
            app: The ASGI application to wrap.
            target: Static target URL to proxy to (e.g., "http://localhost:4200").
                If None, uses hotfile_path for dynamic target discovery.
            hotfile_path: Path to the Vite hotfile for dynamic target discovery.
                Used when target is None (SSR frameworks with dynamic ports).
            http2: Enable HTTP/2 for proxy connections.
            litestar_app: Optional Litestar app instance for route exclusion.
        """
        super().__init__(app)
        self._static_target = target.rstrip("/") if target else None
        self._hotfile_path = hotfile_path
        self._cached_target: str | None = None
        self._cache_initialized = False
        self.http2 = http2
        self._litestar_app = litestar_app
        self._excluded_prefixes: tuple[str, ...] | None = None

    def _get_target(self) -> str | None:
        """Get the proxy target URL with permanent caching.

        Returns static target if configured, otherwise reads from hotfile.
        The hotfile is read once and cached for the lifetime of the server.

        Returns:
            The target URL or None if unavailable.
        """
        if self._static_target:
            return self._static_target

        if self._hotfile_path:
            if self._cache_initialized:
                return self._cached_target.rstrip("/") if self._cached_target else None

            try:
                url = self._hotfile_path.read_text().strip()
                self._cached_target = url
                self._cache_initialized = True
                if _is_proxy_debug():
                    console.print(f"[dim][proxy] Dynamic target: {url}[/]")
                return url.rstrip("/")
            except FileNotFoundError:
                self._cached_target = None
                self._cache_initialized = True
                return None

        return None

    def _get_excluded_prefixes(self, scope: "Scope") -> tuple[str, ...]:
        """Build list of path prefixes to exclude from proxying.

        Automatically excludes:
        - All registered Litestar routes
        - Static file mounts
        - OpenAPI/schema paths

        Returns:
            A tuple of excluded path prefixes.
        """
        if self._excluded_prefixes is not None:
            return self._excluded_prefixes

        prefixes: list[str] = []

        # Get Litestar app from scope if not provided during init
        app: "Litestar | None" = self._litestar_app or scope.get("app")  # pyright: ignore[reportUnknownMemberType]
        if app:
            # Exclude all registered route paths
            for route in getattr(app, "routes", []):
                path = getattr(route, "path", None)
                if path:
                    # Normalize path to prefix
                    prefix = path.rstrip("/")
                    if prefix:
                        prefixes.append(prefix)

            # Exclude OpenAPI schema path
            openapi_config = getattr(app, "openapi_config", None)
            if openapi_config is not None:
                schema_path = getattr(openapi_config, "path", "/schema")
                if schema_path:
                    prefixes.append(schema_path.rstrip("/"))

        # Always exclude common API prefixes
        prefixes.extend(["/api", "/schema", "/docs"])

        # Remove duplicates and sort by length (longest first for proper matching)
        unique_prefixes = sorted(set(prefixes), key=len, reverse=True)
        self._excluded_prefixes = tuple(unique_prefixes)

        if _is_proxy_debug():
            console.print(f"[dim][external-proxy] Excluded prefixes: {self._excluded_prefixes}[/]")

        return self._excluded_prefixes

    def _should_proxy(self, path: str, scope: "Scope") -> bool:
        """Determine if the request should be proxied to the external server.

        Returns:
            True if the request should be proxied, else False.
        """
        excluded = self._get_excluded_prefixes(scope)

        # Check if path matches any excluded prefix
        return all(not (path == prefix or path.startswith(f"{prefix}/")) for prefix in excluded)

    async def __call__(self, scope: "Scope", receive: "Receive", send: "Send") -> None:
        scope_dict = cast("dict[str, Any]", scope)
        path = scope_dict.get("path", "")

        should = self._should_proxy(path, scope)
        if _is_proxy_debug():
            console.print(f"[dim][external-proxy] {path} → proxy={should}[/]")

        if should:
            await self._proxy_request(scope_dict, receive, send)
            return

        await self.app(scope, receive, send)

    async def _proxy_request(self, scope: dict[str, Any], receive: Any, send: Any) -> None:
        """Proxy the HTTP request to the external dev server."""
        target = self._get_target()
        if target is None:
            # No target available - dev server not running
            await send(
                {
                    "type": "http.response.start",
                    "status": 503,
                    "headers": [(b"content-type", b"text/plain")],
                }
            )
            await send({"type": "http.response.body", "body": b"Dev server not running"})
            return

        method = scope.get("method", "GET")
        raw_path = scope.get("raw_path", b"").decode()
        query_string = scope.get("query_string", b"").decode()

        url = f"{target}{raw_path}"
        if query_string:
            url = f"{url}?{query_string}"

        # Build headers, filtering out hop-by-hop headers
        headers = [
            (k.decode(), v.decode())
            for k, v in scope.get("headers", [])
            if k.lower() not in {b"host", b"connection", b"keep-alive"}
        ]

        # Read request body
        body = b""
        more_body = True
        while more_body:
            event = await receive()
            if event["type"] != "http.request":
                continue
            body += event.get("body", b"")
            more_body = event.get("more_body", False)

        # Check for HTTP/2 support
        http2_enabled = self.http2
        if http2_enabled:
            try:
                import h2  # noqa: F401  # pyright: ignore[reportMissingImports,reportUnusedImport]
            except ImportError:
                http2_enabled = False

        async with httpx.AsyncClient(http2=http2_enabled, timeout=30.0) as client:
            try:
                upstream_resp = await client.request(method, url, headers=headers, content=body)
            except httpx.ConnectError:
                await send(
                    {
                        "type": "http.response.start",
                        "status": 503,
                        "headers": [(b"content-type", b"text/plain")],
                    }
                )
                await send(
                    {
                        "type": "http.response.body",
                        "body": f"Dev server not running at {target}".encode(),
                    }
                )
                return
            except httpx.HTTPError as exc:
                await send(
                    {
                        "type": "http.response.start",
                        "status": 502,
                        "headers": [(b"content-type", b"text/plain")],
                    }
                )
                await send({"type": "http.response.body", "body": str(exc).encode()})
                return

        response_headers = [(k.encode(), v.encode()) for k, v in upstream_resp.headers.items()]
        await send(
            {
                "type": "http.response.start",
                "status": upstream_resp.status_code,
                "headers": response_headers,
            }
        )
        await send({"type": "http.response.body", "body": upstream_resp.content})


def _build_hmr_target_url(
    hotfile_path: Path,
    scope: dict[str, Any],
    hmr_path: str,
    asset_url: str,
) -> "str | None":
    """Build the target WebSocket URL for Vite HMR proxy.

    Note: Vite's HMR WebSocket listens at {base}{hmr.path}, so we preserve
    the full path including the asset prefix (e.g., /static/vite-hmr).

    Returns:
        The target WebSocket URL or None if the hotfile is not found.
    """
    try:
        vite_url = hotfile_path.read_text(encoding="utf-8").strip()
    except FileNotFoundError:
        return None

    ws_url = vite_url.replace("http://", "ws://").replace("https://", "wss://")
    # Use the original path as-is - Vite expects the full path including base
    original_path = scope.get("path", hmr_path)
    query_string = scope.get("query_string", b"").decode()

    target = f"{ws_url}{original_path}"
    if query_string:
        target = f"{target}?{query_string}"

    if _is_proxy_debug():
        console.print(f"[dim][vite-hmr] Connecting: {target}[/]")

    return target


def _extract_forward_headers(scope: dict[str, Any]) -> list[tuple[str, str]]:
    """Extract headers to forward, excluding WebSocket handshake headers.

    Note: We exclude protocol-specific headers that websockets library handles itself.
    The sec-websocket-protocol header is also excluded since we handle subprotocols separately.

    Returns:
        A list of (header_name, header_value) tuples.
    """
    skip_headers = (
        b"host",
        b"upgrade",
        b"connection",
        b"sec-websocket-key",
        b"sec-websocket-version",
        b"sec-websocket-protocol",
        b"sec-websocket-extensions",
    )
    return [(k.decode(), v.decode()) for k, v in scope.get("headers", []) if k.lower() not in skip_headers]


def _extract_subprotocols(scope: dict[str, Any]) -> list[str]:
    """Extract WebSocket subprotocols from the request headers.

    Returns:
        A list of subprotocol strings.
    """
    for key, value in scope.get("headers", []):
        if key.lower() == b"sec-websocket-protocol":
            # Subprotocols are comma-separated
            return [p.strip() for p in value.decode().split(",")]
    return []


async def _run_websocket_proxy(
    socket: Any,
    upstream: Any,
) -> None:
    """Run bidirectional WebSocket proxy between client and upstream.

    Args:
        socket: The client WebSocket connection (Litestar WebSocket).
        upstream: The upstream WebSocket connection (websockets client).
    """

    async def client_to_upstream() -> None:
        """Forward messages from browser to Vite."""
        try:
            while True:
                data = await socket.receive_text()
                await upstream.send(data)
        except (WebSocketDisconnect, anyio.ClosedResourceError, websockets.ConnectionClosed):
            pass
        finally:
            with suppress(websockets.ConnectionClosed):
                await upstream.close()

    async def upstream_to_client() -> None:
        """Forward messages from Vite to browser."""
        try:
            async for msg in upstream:
                if isinstance(msg, str):
                    await socket.send_text(msg)
                else:
                    await socket.send_bytes(msg)
        except (WebSocketDisconnect, anyio.ClosedResourceError, websockets.ConnectionClosed):
            pass
        finally:
            with suppress(anyio.ClosedResourceError, WebSocketDisconnect):
                await socket.close()

    async with anyio.create_task_group() as tg:
        tg.start_soon(client_to_upstream)
        tg.start_soon(upstream_to_client)


def create_vite_hmr_handler(
    hotfile_path: Path,
    hmr_path: str = "/static/vite-hmr",
    asset_url: str = "/static/",
) -> Any:
    """Create a WebSocket route handler for Vite HMR proxy.

    This handler proxies WebSocket connections from the browser to the Vite
    dev server for Hot Module Replacement (HMR) functionality.

    Args:
        hotfile_path: Path to the hotfile written by the Vite plugin.
        hmr_path: The path to register the WebSocket handler at.
        asset_url: The asset URL prefix to strip when connecting to Vite.

    Returns:
        A WebsocketRouteHandler that proxies HMR connections.
    """
    from litestar import WebSocket, websocket

    @websocket(path=hmr_path, opt={"exclude_from_auth": True})
    async def vite_hmr_proxy(socket: "WebSocket[Any, Any, Any]") -> None:
        """Proxy WebSocket messages between browser and Vite dev server."""
        scope_dict = dict(socket.scope)
        target = _build_hmr_target_url(hotfile_path, scope_dict, hmr_path, asset_url)
        if target is None:
            console.print("[yellow][vite-hmr] Vite dev server not running[/]")
            await socket.close(code=1011, reason="Vite dev server not running")
            return

        headers = _extract_forward_headers(scope_dict)
        subprotocols = _extract_subprotocols(scope_dict)
        typed_subprotocols: list[Subprotocol] = [cast("Subprotocol", p) for p in subprotocols]
        await socket.accept(subprotocols=typed_subprotocols[0] if typed_subprotocols else None)

        try:
            async with websockets.connect(
                target,
                additional_headers=headers,
                open_timeout=10,
                subprotocols=typed_subprotocols or None,
            ) as upstream:
                if _is_proxy_debug():
                    console.print("[dim][vite-hmr] ✓ Connected[/]")
                await _run_websocket_proxy(socket, upstream)
        except TimeoutError:
            if _is_proxy_debug():
                console.print("[yellow][vite-hmr] Connection timeout[/]")
            with suppress(anyio.ClosedResourceError, WebSocketDisconnect):
                await socket.close(code=1011, reason="Vite HMR connection timeout")
        except OSError as exc:
            if _is_proxy_debug():
                console.print(f"[yellow][vite-hmr] Connection failed: {exc}[/]")
            with suppress(anyio.ClosedResourceError, WebSocketDisconnect):
                await socket.close(code=1011, reason="Vite HMR connection failed")
        except WebSocketDisconnect:
            pass  # Normal client disconnect
        except BaseException as exc:
            if hasattr(exc, "exceptions"):
                non_disconnect = [
                    err for err in getattr(exc, "exceptions", []) if not isinstance(err, _DISCONNECT_EXCEPTIONS)
                ]
                if non_disconnect:
                    raise
            elif not isinstance(exc, _DISCONNECT_EXCEPTIONS):
                raise

    return vite_hmr_proxy


def _check_http2_support(enable: bool) -> bool:
    """Check if HTTP/2 support is available.

    Returns:
        True if HTTP/2 is enabled and the h2 package is installed, else False.
    """
    if not enable:
        return False
    try:
        import h2  # noqa: F401  # pyright: ignore[reportMissingImports,reportUnusedImport]
    except ImportError:
        return False
    else:
        return True


def _build_proxy_url(target_url: str, path: str, query: str) -> str:
    """Build the full proxy URL from target, path, and query string.

    Returns:
        The full URL as a string.
    """
    url = f"{target_url}{path}"
    return f"{url}?{query}" if query else url


def _create_target_url_getter(
    target: "str | None", hotfile_path: "Path | None", cached_target: list["str | None"]
) -> "Callable[[], str | None]":
    """Create a function that returns the current target URL with permanent caching.

    The hotfile is read once and cached for the lifetime of the server.
    Server restart refreshes the cache automatically.

    Returns:
        A callable that returns the target URL or None if unavailable.
    """
    cache_initialized: list[bool] = [False]

    def _get_target_url() -> str | None:
        if target is not None:
            return target.rstrip("/")
        if hotfile_path is None:
            return None

        if cache_initialized[0]:
            return cached_target[0].rstrip("/") if cached_target[0] else None

        try:
            url = hotfile_path.read_text().strip()
            cached_target[0] = url
            cache_initialized[0] = True
            if _is_proxy_debug():
                console.print(f"[dim][ssr-proxy] Dynamic target: {url}[/]")
            return url.rstrip("/")
        except FileNotFoundError:
            cached_target[0] = None
            cache_initialized[0] = True
            return None

    return _get_target_url


def _create_hmr_target_getter(
    hotfile_path: "Path | None",
    cached_hmr_target: list["str | None"],
) -> "Callable[[], str | None]":
    """Create a function that returns the HMR target URL from hotfile with permanent caching.

    The hotfile is read once and cached for the lifetime of the server.
    Server restart refreshes the cache automatically.

    Returns:
        A callable that returns the HMR target URL or None if unavailable.
    """
    cache_initialized: list[bool] = [False]

    def _get_hmr_target_url() -> str | None:
        if hotfile_path is None:
            return None

        if cache_initialized[0]:
            return cached_hmr_target[0].rstrip("/") if cached_hmr_target[0] else None

        # JS writes to `${config.hotFile}.hmr`
        hmr_path = Path(f"{hotfile_path}.hmr")
        try:
            url = hmr_path.read_text(encoding="utf-8").strip()
            cached_hmr_target[0] = url
            cache_initialized[0] = True
            if _is_proxy_debug():
                console.print(f"[dim][ssr-proxy] HMR target: {url}[/]")
            return url.rstrip("/")
        except FileNotFoundError:
            cached_hmr_target[0] = None
            cache_initialized[0] = True
            return None

    return _get_hmr_target_url


async def _handle_ssr_websocket_proxy(
    socket: Any,
    ws_url: str,
    headers: list[tuple[str, str]],
    typed_subprotocols: "list[Subprotocol]",
) -> None:
    """Handle the WebSocket proxy connection to SSR framework.

    Args:
        socket: The client WebSocket connection.
        ws_url: The upstream WebSocket URL.
        headers: Headers to forward.
        typed_subprotocols: WebSocket subprotocols.
    """
    try:
        async with websockets.connect(
            ws_url, additional_headers=headers, open_timeout=10, subprotocols=typed_subprotocols or None
        ) as upstream:
            if _is_proxy_debug():
                console.print("[dim][ssr-proxy-ws] ✓ Connected[/]")
            await _run_websocket_proxy(socket, upstream)
    except TimeoutError:
        if _is_proxy_debug():
            console.print("[yellow][ssr-proxy-ws] Connection timeout[/]")
        with suppress(anyio.ClosedResourceError, WebSocketDisconnect):
            await socket.close(code=1011, reason="SSR HMR connection timeout")
    except OSError as exc:
        if _is_proxy_debug():
            console.print(f"[yellow][ssr-proxy-ws] Connection failed: {exc}[/]")
        with suppress(anyio.ClosedResourceError, WebSocketDisconnect):
            await socket.close(code=1011, reason="SSR HMR connection failed")
    except (WebSocketDisconnect, websockets.ConnectionClosed, anyio.ClosedResourceError):
        pass  # Normal disconnect/close


def create_ssr_proxy_controller(
    target: "str | None" = None,
    hotfile_path: "Path | None" = None,
    http2: bool = True,
) -> type:
    """Create a Controller that proxies to an SSR framework dev server.

    This controller is used for SSR frameworks (Astro, Nuxt, SvelteKit) where all
    non-API requests should be proxied to the framework's dev server for rendering.

    Args:
        target: Static target URL to proxy to. If None, uses hotfile for dynamic discovery.
        hotfile_path: Path to the hotfile for dynamic target discovery.
        http2: Enable HTTP/2 for proxy connections.

    Returns:
        A Litestar Controller class with HTTP and WebSocket handlers for SSR proxy.
    """
    from litestar import Controller, HttpMethod, Response, WebSocket, route, websocket

    cached_target: list[str | None] = [target]
    get_target_url = _create_target_url_getter(target, hotfile_path, cached_target)
    get_hmr_target_url = _create_hmr_target_getter(hotfile_path, [None])

    class SSRProxyController(Controller):
        """Controller that proxies requests to an SSR framework dev server."""

        include_in_schema = False
        opt = {"exclude_from_auth": True}

        @route(
            path=["/", "/{path:path}"],
            http_method=[
                HttpMethod.GET,
                HttpMethod.POST,
                HttpMethod.PUT,
                HttpMethod.PATCH,
                HttpMethod.DELETE,
                HttpMethod.HEAD,
                HttpMethod.OPTIONS,
            ],
            name="ssr_proxy",
        )
        async def http_proxy(self, request: "Request[Any, Any, Any]") -> "Response[bytes]":
            """Proxy all HTTP requests to the SSR framework dev server.

            Returns:
                A Response with the proxied content from the SSR server.
            """
            target_url = get_target_url()
            if target_url is None:
                return Response(content=b"SSR dev server not running", status_code=503, media_type="text/plain")

            req_path: str = request.url.path
            url = _build_proxy_url(target_url, req_path, request.url.query or "")

            if _is_proxy_debug():
                console.print(f"[dim][ssr-proxy] {request.method} {req_path} → {url}[/]")

            headers_to_forward = [
                (k, v) for k, v in request.headers.items() if k.lower() not in {"host", "connection", "keep-alive"}
            ]
            body = await request.body()
            http2_enabled = _check_http2_support(http2)

            async with httpx.AsyncClient(http2=http2_enabled, timeout=30.0) as client:
                try:
                    upstream_resp = await client.request(
                        request.method, url, headers=headers_to_forward, content=body, follow_redirects=False
                    )
                except httpx.ConnectError:
                    return Response(
                        content=f"SSR dev server not running at {target_url}".encode(),
                        status_code=503,
                        media_type="text/plain",
                    )
                except httpx.HTTPError as exc:
                    return Response(content=str(exc).encode(), status_code=502, media_type="text/plain")

            return Response(
                content=upstream_resp.content,
                status_code=upstream_resp.status_code,
                headers=dict(upstream_resp.headers.items()),
                media_type=upstream_resp.headers.get("content-type"),
            )

        @websocket(path=["/", "/{path:path}"], name="ssr_proxy_ws")
        async def ws_proxy(self, socket: "WebSocket[Any, Any, Any]") -> None:
            """Proxy WebSocket connections to the SSR framework dev server (for HMR)."""
            target_url = get_hmr_target_url() or get_target_url()

            if target_url is None:
                await socket.close(code=1011, reason="SSR dev server not running")
                return

            ws_target = target_url.replace("http://", "ws://").replace("https://", "wss://")
            scope_dict = dict(socket.scope)
            ws_path = str(scope_dict.get("path", "/"))
            query_bytes = cast("bytes", scope_dict.get("query_string", b""))
            ws_url = _build_proxy_url(ws_target, ws_path, query_bytes.decode("utf-8") if query_bytes else "")

            if _is_proxy_debug():
                console.print(f"[dim][ssr-proxy-ws] {ws_path} → {ws_url}[/]")

            headers = _extract_forward_headers(scope_dict)
            subprotocols = _extract_subprotocols(scope_dict)
            typed_subprotocols: list[Subprotocol] = [cast("Subprotocol", p) for p in subprotocols]

            await socket.accept(subprotocols=typed_subprotocols[0] if typed_subprotocols else None)
            await _handle_ssr_websocket_proxy(socket, ws_url, headers, typed_subprotocols)

    return SSRProxyController


@dataclass
class StaticFilesConfig:
    """Configuration for static file serving.

    This configuration is passed to Litestar's static files router.
    """

    after_request: "AfterRequestHookHandler | None" = None
    after_response: "AfterResponseHookHandler | None" = None
    before_request: "BeforeRequestHookHandler | None" = None
    cache_control: "CacheControlHeader | None" = None
    exception_handlers: "ExceptionHandlersMap | None" = None
    guards: "list[Guard] | None" = None
    middleware: "Sequence[Middleware] | None" = None
    opt: "dict[str, Any] | None" = None
    security: "Sequence[SecurityRequirement] | None" = None
    tags: "Sequence[str] | None" = None


class ViteProcess:
    """Manages the Vite development server process.

    This class handles starting and stopping the Vite dev server process,
    with proper thread safety and graceful shutdown. It registers signal
    handlers for SIGTERM and SIGINT to ensure child processes are terminated
    even if Python is killed externally.
    """

    _instances: "list[ViteProcess]" = []
    _signals_registered: bool = False
    _original_handlers: "dict[int, Any]" = {}

    def __init__(self, executor: "JSExecutor") -> None:
        """Initialize the Vite process manager.

        Args:
            executor: The JavaScript executor to use for running Vite.
        """
        self.process: "subprocess.Popen[Any] | None" = None
        self._lock = threading.Lock()
        self._executor = executor

        # Track this instance for signal handler cleanup
        ViteProcess._instances.append(self)

        # Register signal handlers once (class-level)
        if not ViteProcess._signals_registered:
            self._register_signal_handlers()
            ViteProcess._signals_registered = True

            # Also register atexit as fallback
            import atexit

            atexit.register(ViteProcess._cleanup_all_instances)

    @classmethod
    def _register_signal_handlers(cls) -> None:
        """Register signal handlers for graceful shutdown on SIGTERM/SIGINT."""
        for sig in (signal.SIGTERM, signal.SIGINT):
            try:
                original = signal.signal(sig, cls._signal_handler)
                cls._original_handlers[sig] = original
            except (OSError, ValueError):
                # Signal registration can fail in certain environments
                pass

    @classmethod
    def _signal_handler(cls, signum: int, frame: Any) -> None:
        """Handle termination signals by stopping all Vite processes first."""
        # Stop all tracked ViteProcess instances
        cls._cleanup_all_instances()

        # Chain to the original handler
        original = cls._original_handlers.get(signum, signal.SIG_DFL)
        if callable(original) and original not in {signal.SIG_IGN, signal.SIG_DFL}:
            original(signum, frame)
        elif original == signal.SIG_DFL:
            # Restore default and re-raise
            signal.signal(signum, signal.SIG_DFL)
            os.kill(os.getpid(), signum)

    @classmethod
    def _cleanup_all_instances(cls) -> None:
        """Stop all tracked ViteProcess instances."""
        for instance in cls._instances:
            with suppress(Exception):
                instance.stop()

    def start(self, command: list[str], cwd: "Path | str | None") -> None:
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
                            f"[red]Stderr:[/]\n{err_str or '<empty>'}\n"
                            "[yellow]Hint: Run `litestar assets doctor` to diagnose configuration issues.[/]"
                        )
                        msg = f"Vite process failed to start (exit {self.process.returncode})"
                        raise ViteProcessError(  # noqa: TRY301
                            msg,
                            command=command,
                            exit_code=self.process.returncode,
                            stderr=err_str,
                            stdout=out_str,
                        )
        except Exception as e:
            if isinstance(e, ViteProcessError):
                raise
            console.print(f"[red]Failed to start Vite process: {e!s}[/]")
            msg = f"Failed to start Vite process: {e!s}"
            raise ViteProcessError(msg) from e

    def stop(self, timeout: float = 5.0) -> None:
        """Stop the Vite process and all its child processes.

        Uses process groups to ensure child processes (node, astro, nuxt, vite, etc.)
        are terminated along with the parent npm/npx process.

        Args:
            timeout: Seconds to wait for graceful shutdown before killing.

        Raises:
            ViteProcessError: If the process fails to stop.
        """
        try:
            with self._lock:
                self._terminate_process_group(timeout)
        except Exception as e:
            console.print(f"[red]Failed to stop Vite process: {e!s}[/]")
            msg = f"Failed to stop Vite process: {e!s}"
            raise ViteProcessError(msg) from e

    def _terminate_process_group(self, timeout: float) -> None:
        """Terminate the process group, waiting and killing if needed."""
        if not self.process or self.process.poll() is not None:
            return
        # On Unix, kill the entire process group to ensure all children die.
        # The process was started with start_new_session=True so the pid IS the pgid.
        pid = self.process.pid
        # isinstance check needed for tests where pid may be a Mock object
        if hasattr(os, "killpg") and hasattr(signal, "SIGTERM") and isinstance(pid, int):  # pyright: ignore[reportUnnecessaryIsInstance]
            with suppress(ProcessLookupError):
                os.killpg(pid, signal.SIGTERM)
        elif hasattr(signal, "SIGTERM"):
            self.process.terminate()
        try:
            self.process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            self._force_kill_process_group()
            self.process.wait(timeout=1.0)
        finally:
            # Clear reference so atexit cleanup doesn't try to stop again
            self.process = None

    def _force_kill_process_group(self) -> None:
        """Force kill the process group if still alive."""
        if not self.process:
            return
        pid = self.process.pid
        # isinstance check needed for tests where pid may be a Mock object
        if hasattr(os, "killpg") and hasattr(signal, "SIGKILL") and isinstance(pid, int):  # pyright: ignore[reportUnnecessaryIsInstance]
            with suppress(ProcessLookupError):
                os.killpg(pid, signal.SIGKILL)
        elif hasattr(signal, "SIGKILL"):
            self.process.kill()

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
        self._spa_handler: "ViteSPAHandler | None" = None

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
        # Skip if not in dev mode
        if not self._config.is_dev_mode:
            return

        # Skip if proxy disabled
        if self._config.proxy_mode is None:
            return

        # For all proxy modes, pick a free port if not explicitly set
        # This ensures JS integrations know what port to use
        # Only pick a port if:
        # 1. VITE_PORT env var is not already set, AND
        # 2. We haven't already picked a port (check if port != default 5173)
        if os.getenv("VITE_PORT") is None and self._config.runtime.port == 5173:
            self._config.runtime.port = _pick_free_port()

        # For 'vite' mode, set proxy target directly (internal Vite server)
        if self._config.proxy_mode == "vite":
            # Skip if proxy target already set
            if self._proxy_target is not None:
                return
            # Force loopback for internal dev server unless explicitly overridden
            if os.getenv("VITE_ALLOW_REMOTE", "False") not in TRUE_VALUES:
                self._config.runtime.host = "127.0.0.1"
            self._proxy_target = f"{self._config.protocol}://{self._config.host}:{self._config.port}"
        # For 'proxy'/'ssr' modes, target is discovered from hotfile at request time
        # The SSR framework (Nuxt/Astro/SvelteKit) writes the hotfile when ready

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

        # Create and register InertiaPlugin - it handles all the configuration
        # in its own on_app_init method
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

        from litestar_vite.loader import (
            render_asset_tag,
            render_hmr_client,
            render_partial_asset_tag,
            render_static_asset,
        )

        template_config = app_config.template_config  # pyright: ignore[reportUnknownMemberType,reportUnknownVariableType]
        if template_config and isinstance(
            template_config.engine_instance,  # pyright: ignore[reportUnknownMemberType]
            JinjaTemplateEngine,
        ):
            engine = template_config.engine_instance  # pyright: ignore[reportUnknownMemberType]
            engine.register_template_callable(key="vite_hmr", template_callable=render_hmr_client)
            engine.register_template_callable(key="vite", template_callable=render_asset_tag)
            engine.register_template_callable(key="vite_static", template_callable=render_static_asset)
            engine.register_template_callable(key="vite_partial", template_callable=render_partial_asset_tag)

    def _configure_static_files(self, app_config: "AppConfig") -> None:
        """Configure static file serving for Vite assets.

        Args:
            app_config: The Litestar application configuration.
        """
        bundle_dir = Path(self._config.bundle_dir)
        if not bundle_dir.is_absolute():
            bundle_dir = self._config.root_dir / bundle_dir

        resource_dir = Path(self._config.resource_dir)
        if not resource_dir.is_absolute():
            resource_dir = self._config.root_dir / resource_dir

        public_dir = Path(self._config.public_dir)
        if not public_dir.is_absolute():
            public_dir = self._config.root_dir / public_dir

        static_dirs = [bundle_dir, resource_dir]
        if public_dir.exists() and public_dir != bundle_dir:
            static_dirs.append(public_dir)

        def _static_not_found_handler(
            _request: Request[Any, Any, Any], _exc: NotFoundException
        ) -> Response[bytes]:  # pragma: no cover - trivial
            return Response(status_code=404, content=b"")

        base_config = {
            "directories": (static_dirs if self._config.is_dev_mode else [bundle_dir]),
            "path": self._config.asset_url,
            "name": "vite",
            "html_mode": False,
            "include_in_schema": False,
            "opt": {"exclude_from_auth": True},
            "exception_handlers": {NotFoundException: _static_not_found_handler},
        }
        static_files_config: dict[str, Any] = {**base_config, **self._static_files_config}
        app_config.route_handlers.append(create_static_files_router(**static_files_config))

    def _configure_dev_proxy(self, app_config: "AppConfig") -> None:
        """Configure dev proxy middleware and handlers based on proxy_mode.

        Args:
            app_config: The Litestar application configuration.
        """
        proxy_mode = self._config.proxy_mode
        bundle_dir = self._config.bundle_dir
        if not bundle_dir.is_absolute():
            bundle_dir = self._config.root_dir / bundle_dir
        hotfile_path = bundle_dir / self._config.hot_file

        if proxy_mode == "vite":
            self._configure_vite_proxy(app_config, hotfile_path)
        elif proxy_mode == "proxy":
            self._configure_ssr_proxy(app_config, hotfile_path)

    def _configure_vite_proxy(self, app_config: "AppConfig", hotfile_path: Path) -> None:
        """Configure Vite proxy mode (whitelist).

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
            )
        )
        hmr_path = f"{self._config.asset_url.rstrip('/')}/vite-hmr"
        app_config.route_handlers.append(
            create_vite_hmr_handler(hotfile_path=hotfile_path, hmr_path=hmr_path, asset_url=self._config.asset_url)
        )
        console.print(f"[dim]Vite proxy enabled (whitelist) at {hmr_path}[/]")

    def _configure_ssr_proxy(self, app_config: "AppConfig", hotfile_path: Path) -> None:
        """Configure SSR proxy mode (blacklist).

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
            )
        )
        hmr_path = f"{self._config.asset_url.rstrip('/')}/vite-hmr"
        app_config.route_handlers.append(
            create_vite_hmr_handler(hotfile_path=hotfile_path, hmr_path=hmr_path, asset_url=self._config.asset_url)
        )
        if static_target:
            console.print(f"[dim]Proxy enabled (blacklist) → {static_target}[/]")
        else:
            console.print("[dim]Proxy enabled (blacklist, dynamic target via hotfile)[/]")

    def on_app_init(self, app_config: "AppConfig") -> "AppConfig":
        """Configure the Litestar application for Vite.

        Args:
            app_config: The Litestar application configuration.

        Returns:
            The modified application configuration.
        """
        from litestar import Response
        from litestar.connection import Request as LitestarRequest

        # Add Response and Request to signature namespace for SSR proxy handler type hints
        app_config.signature_namespace["Response"] = Response
        app_config.signature_namespace["Request"] = LitestarRequest

        # Provide a consistent 404 response for missing static assets / routes (e.g., Vite HMR/static lookups)
        handlers: ExceptionHandlersMap = cast("ExceptionHandlersMap", app_config.exception_handlers or {})  # pyright: ignore
        if NotFoundException not in handlers:

            def _vite_not_found_handler(
                request: LitestarRequest[Any, Any, Any], exc: NotFoundException
            ) -> Response[Any]:
                # Check if this is an Inertia request by looking for X-Inertia header
                # Inertia requests should be handled by the Inertia exception handler
                # which supports redirect_404 configuration
                is_inertia_request = request.headers.get("x-inertia", "").lower() == "true"
                if is_inertia_request:
                    from litestar_vite.inertia.exception_handler import exception_to_http_response

                    return exception_to_http_response(request, exc)
                return Response(status_code=404, content=b"")

            handlers[NotFoundException] = _vite_not_found_handler
            app_config.exception_handlers = handlers  # pyright: ignore[reportUnknownMemberType]

        # Auto-register Inertia if config is provided
        if self._config.inertia is not None:
            app_config = self._configure_inertia(app_config)

        # Register Jinja2 template callables if applicable
        if JINJA_INSTALLED and self._config.mode in {"template", "htmx"}:
            self._configure_jinja_callables(app_config)

        # Configure static file serving
        if self._config.set_static_folders:
            self._configure_static_files(app_config)

        # Add dev proxy middleware based on proxy_mode (skip non-serving CLI commands)
        if self._config.is_dev_mode and self._config.proxy_mode is not None and not _is_non_serving_assets_cli():
            self._configure_dev_proxy(app_config)

        # Add SPA catch-all route handler if spa_handler is enabled
        # This applies to mode="spa", mode="ssr" (with built assets), and when spa_handler=True explicitly
        if self._config.spa_handler and self._config.mode in {"spa", "ssr"}:
            from litestar_vite.spa import ViteSPAHandler

            self._spa_handler = ViteSPAHandler(self._config)
            app_config.route_handlers.append(self._spa_handler.create_route_handler())
        elif self._config.mode == "hybrid":
            from litestar_vite.spa import ViteSPAHandler

            self._spa_handler = ViteSPAHandler(self._config)

        # Auto-register per-worker lifespan for SPA handler init, asset loader, env setup
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
                _log_success("Vite dev server responded to health check")
                return
        _log_fail("Vite server health check failed")

    def _run_health_check(self) -> None:
        """Run the appropriate health check based on proxy mode."""
        if self._config.proxy_mode == "proxy":
            # SSR framework health check via hotfile
            bundle_dir = self._config.bundle_dir
            if not bundle_dir.is_absolute():
                bundle_dir = self._config.root_dir / bundle_dir
            hotfile_path = bundle_dir / self._config.hot_file
            self._check_ssr_health(hotfile_path)
        else:
            # Standard Vite dev server health check
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
                    url = hotfile_path.read_text(encoding="utf-8").strip()
                    if url:
                        last_url = url
                        # Try a quick HTTP request to verify server is actually up
                        resp = httpx.get(url, timeout=0.5, follow_redirects=True)
                        # Any non-5xx response means server is up (even 404 is fine)
                        if resp.status_code < 500:
                            _log_success(f"SSR server ready at {url}")
                            return True
                except OSError:
                    pass  # Hotfile read error, keep polling
                except httpx.HTTPError:
                    pass  # Server not ready yet, keep polling

            time.sleep(0.1)  # Poll every 100ms

        if last_url:
            _log_fail(f"SSR server at {last_url} did not respond within {timeout}s")
        else:
            _log_fail(f"SSR hotfile not found at {hotfile_path} within {timeout}s")
        return False

    def _export_types_sync(self, app: "Litestar") -> None:
        """Export type metadata synchronously on startup.

        This exports OpenAPI schema, route metadata (JSON), and typed routes (TypeScript)
        when type generation is enabled. The Vite plugin watches these files and triggers
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

            from litestar_vite.codegen import generate_routes_json, generate_routes_ts

            _log_info("Exporting type metadata for Vite...")

            # Check if OpenAPI is configured by looking at the plugins registry
            # (accessing openapi_schema property directly raises when not configured)
            from litestar._openapi.plugin import OpenAPIPlugin

            openapi_plugin = next((p for p in app.plugins._plugins if isinstance(p, OpenAPIPlugin)), None)  # pyright: ignore[reportPrivateUsage]
            has_openapi = openapi_plugin is not None and openapi_plugin._openapi_config is not None  # pyright: ignore[reportPrivateUsage]
            openapi_schema: "dict[str, Any] | None" = None

            if has_openapi:
                try:
                    serializer = get_serializer(
                        app.type_encoders if isinstance(getattr(app, "type_encoders", None), dict) else None
                    )
                    schema_dict = app.openapi_schema.to_schema()
                    openapi_schema = schema_dict
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

            # Export routes JSON
            routes_data = generate_routes_json(app, include_components=True, openapi_schema=openapi_schema)
            routes_data["litestar_version"] = _resolve_litestar_version()
            routes_content = msgspec.json.format(
                msgspec.json.encode(routes_data),
                indent=2,
            )
            self._config.types.routes_path.parent.mkdir(parents=True, exist_ok=True)
            self._config.types.routes_path.write_bytes(routes_content)

            # Export typed routes TypeScript file
            routes_ts_exported = False
            if self._config.types.generate_routes and self._config.types.routes_ts_path is not None:
                try:
                    routes_ts_content = generate_routes_ts(app, openapi_schema=openapi_schema)
                    self._config.types.routes_ts_path.parent.mkdir(parents=True, exist_ok=True)
                    self._config.types.routes_ts_path.write_text(routes_ts_content, encoding="utf-8")
                    routes_ts_exported = True
                except (TypeError, ValueError, OSError) as exc:  # pragma: no cover
                    console.print(f"[yellow]! routes.ts export skipped: {exc}[/]")

            # Log success
            exported_files = [_fmt_path(self._config.types.routes_path)]
            if has_openapi:
                exported_files.append(f"openapi: {_fmt_path(self._config.types.openapi_path)}")
            if routes_ts_exported and self._config.types.routes_ts_path is not None:
                exported_files.append(f"routes.ts: {_fmt_path(self._config.types.routes_ts_path)}")
            _log_success(f"Types exported → {', '.join(exported_files)}")
        except (OSError, TypeError, ValueError, ImportError) as e:  # pragma: no cover
            _log_warn(f"Type export failed: {e}")

    @contextmanager
    def server_lifespan(self, app: "Litestar") -> "Iterator[None]":
        """Server-level lifespan context manager (runs ONCE per server, before workers).

        This is called by Litestar CLI before workers start. It handles:
        - Environment variable setup (with logging)
        - Vite dev server process start/stop (ONE instance for all workers)
        - Type export on startup

        Note: SPA handler and asset loader initialization happens in the per-worker
        `lifespan` method, which is auto-registered in `on_app_init`.

        Args:
            app: The Litestar application instance.

        Yields:
            None
        """
        # Ensure proxy target is set BEFORE environment variables (port selection)
        if self._config.is_dev_mode:
            self._ensure_proxy_target()

        if self._config.set_environment:
            set_environment(config=self._config)
            set_app_environment(app)
            _log_info("Applied Vite environment variables")

        # Export types on startup (when enabled)
        self._export_types_sync(app)

        if self._config.is_dev_mode and self._config.runtime.start_dev_server:
            if not app.debug:
                _log_warn("Vite dev mode is enabled in production!")

            # Determine command to run
            ext = self._config.runtime.external_dev_server
            if isinstance(ext, ExternalDevServer) and ext.enabled:
                # External dev server (Angular CLI, Next.js, etc.)
                command_to_run = ext.command or self._config.executor.start_command
                _log_info(f"Starting external dev server: {' '.join(command_to_run)}")
            elif self._config.hot_reload:
                command_to_run = self._config.run_command
                _log_info("Starting Vite dev server (HMR enabled)")
            else:
                command_to_run = self._config.build_watch_command
                _log_info("Starting Vite watch build process")

            if self._proxy_target:
                _log_info(f"Vite proxy target: {self._proxy_target}")

            try:
                self._vite_process.start(command_to_run, self._config.root_dir)
                _log_success("Dev server process started")
                if self._config.health_check and not (isinstance(ext, ExternalDevServer) and ext.enabled):
                    # Only run Vite-specific health check for non-external servers
                    self._run_health_check()
                yield
            finally:
                self._vite_process.stop()
                _log_info("Dev server process stopped.")
        else:
            yield

    @asynccontextmanager
    async def lifespan(self, app: "Litestar") -> "AsyncIterator[None]":
        """Worker-level lifespan context manager (runs per worker process).

        This is auto-registered in `on_app_init` and handles per-worker initialization:
        - Environment variable setup (silently - each worker needs process-local env vars)
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

        # Set environment variables for this worker (no logging - server_lifespan logs once)
        # Environment variables are process-local, so each worker needs them
        if self._config.set_environment:
            set_environment(config=self._config)
            set_app_environment(app)

        # Initialize asset loader asynchronously
        if self._asset_loader is None:
            self._asset_loader = ViteAssetLoader(config=self._config)
        await self._asset_loader.initialize()

        # Initialize SPA handler if enabled (check is_initialized to avoid double-init)
        if self._spa_handler is not None and not self._spa_handler.is_initialized:
            # Pass the proxy target URL to avoid stale hotfile issues
            # The VitePlugin knows the correct URL because it selects the port
            await self._spa_handler.initialize(vite_url=self._proxy_target)
            _log_success("SPA handler initialized")

        # Warn if no built assets in production (skip for SSR mode since Node serves frontend)
        # Check both mode='ssr' and proxy_mode in case user is using proxy mode directly
        is_ssr_mode = self._config.mode == "ssr" or self._config.proxy_mode in {"proxy", "ssr"}
        if not self._config.is_dev_mode and not self._config.has_built_assets() and not is_ssr_mode:
            _log_warn(
                "Vite dev server is disabled (dev_mode=False) but no index.html was found. "
                "Run your front-end build or set VITE_DEV_MODE=1 to enable HMR."
            )

        try:
            yield
        finally:
            # Shutdown SPA handler
            if self._spa_handler is not None:
                await self._spa_handler.shutdown()


def _normalize_proxy_prefixes(
    base_prefixes: tuple[str, ...],
    asset_url: "str | None" = None,
    resource_dir: "Path | None" = None,
    bundle_dir: "Path | None" = None,
    root_dir: "Path | None" = None,
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

    def _add_path(path: Path | str | None) -> None:
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
    unique: list[str] = []
    for p in prefixes:
        if p not in seen:
            unique.append(p)
            seen.add(p)
    return tuple(unique)
