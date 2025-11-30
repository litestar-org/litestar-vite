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
from litestar.cli._utils import console  # pyright: ignore[reportPrivateImportUsage]
from litestar.enums import ScopeType
from litestar.exceptions import WebSocketDisconnect
from litestar.middleware import AbstractMiddleware, DefineMiddleware
from litestar.plugins import CLIPlugin, InitPluginProtocol
from litestar.static_files import create_static_files_router  # pyright: ignore[reportUnknownVariableType]
from websockets.typing import Subprotocol

from litestar_vite.config import JINJA_INSTALLED, TRUE_VALUES, TypeGenConfig, ViteConfig
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
    path = Path(root) / ".litestar-vite.json"
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
    litestar_version = _resolve_litestar_version()
    asset_url = asset_url_override or config.asset_url
    base_url = config.base_url or asset_url
    if asset_url:
        os.environ.setdefault("ASSET_URL", asset_url)
    if base_url:
        os.environ.setdefault("VITE_BASE_URL", base_url)
    os.environ.setdefault("VITE_ALLOW_REMOTE", str(True))

    backend_host = os.environ.get("LITESTAR_HOST") or "127.0.0.1"
    if backend_host == "127.0.0":
        backend_host = "127.0.0.1"
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

    os.environ.setdefault("LITESTAR_VERSION", litestar_version)
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
        self._cached_target: "str | None" = None
        self.asset_prefix = _normalize_prefix(asset_url) if asset_url else "/"
        self.http2 = http2
        self._proxy_path_prefixes = _normalize_proxy_prefixes(
            base_prefixes=_PROXY_PATH_PREFIXES,
            asset_url=asset_url,
            resource_dir=resource_dir,
            bundle_dir=bundle_dir,
            root_dir=root_dir,
        )

    def _get_target_base_url(self) -> "str | None":
        """Read the Vite server URL from the hotfile.

        Caches the result to avoid reading the file on every request.
        The cache is invalidated if the hotfile is modified.
        """
        try:
            url = self.hotfile_path.read_text().strip()
            if url != self._cached_target:
                self._cached_target = url
                if _is_proxy_debug():
                    console.print(f"[dim][vite-proxy] Target: {url}[/]")
            return url.rstrip("/")
        except FileNotFoundError:
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
        self.http2 = http2
        self._litestar_app = litestar_app
        self._excluded_prefixes: tuple[str, ...] | None = None

    def _get_target(self) -> str | None:
        """Get the proxy target URL.

        Returns static target if configured, otherwise reads from hotfile.
        Caches the hotfile result to avoid reading on every request.

        Returns:
            The target URL or None if unavailable.
        """
        if self._static_target:
            return self._static_target

        if self._hotfile_path:
            try:
                url = self._hotfile_path.read_text().strip()
                if url != self._cached_target:
                    self._cached_target = url
                    if _is_proxy_debug():
                        console.print(f"[dim][proxy] Dynamic target: {url}[/]")
                return url.rstrip("/")
            except FileNotFoundError:
                return None

        return None

    def _get_excluded_prefixes(self, scope: "Scope") -> tuple[str, ...]:
        """Build list of path prefixes to exclude from proxying.

        Automatically excludes:
        - All registered Litestar routes
        - Static file mounts
        - OpenAPI/schema paths
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
        """Determine if the request should be proxied to the external server."""
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
            if k.lower() not in (b"host", b"connection", b"keep-alive")
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

    Returns None if the hotfile doesn't exist (Vite not running).

    Note: Vite's HMR WebSocket listens at {base}{hmr.path}, so we preserve
    the full path including the asset prefix (e.g., /static/vite-hmr).
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
    """Extract WebSocket subprotocols from the request headers."""
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


def create_vite_hmr_handler(  # noqa: C901
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
    with proper thread safety and graceful shutdown.
    """

    _atexit_registered: bool = False

    def __init__(self, executor: "JSExecutor") -> None:
        """Initialize the Vite process manager.

        Args:
            executor: The JavaScript executor to use for running Vite.
        """
        self.process: "subprocess.Popen[bytes] | None" = None
        self._lock = threading.Lock()
        self._executor = executor
        if not ViteProcess._atexit_registered:
            import atexit

            atexit.register(self._atexit_stop)
            ViteProcess._atexit_registered = True

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
        "_spa_handler",
        "_static_files_config",
        "_use_server_lifespan",
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
        self._use_server_lifespan = True
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
        """Prepare proxy target URL and hotfile for vite proxy mode."""
        # Skip if already set, not in vite mode, or not in dev mode
        if self._proxy_target is not None:
            return
        if self._config.proxy_mode != "vite":
            return
        if not self._config.is_dev_mode:
            return

        # Force loopback for internal dev server unless explicitly overridden
        if os.getenv("VITE_ALLOW_REMOTE", "False") not in TRUE_VALUES:
            self._config.runtime.host = "127.0.0.1"

        # If VITE_PORT not explicitly set, pick a free one for the internal server
        if os.getenv("VITE_PORT") is None:
            self._config.runtime.port = _pick_free_port()

        self._proxy_target = f"{self._config.protocol}://{self._config.host}:{self._config.port}"
        # Note: We don't write the hotfile here anymore.
        # The TypeScript Vite plugin writes it when the dev server starts.
        # This ensures the hotfile contains the actual Vite server URL.

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

        # Add dev proxy middleware based on proxy_mode
        if self._config.is_dev_mode and self._config.proxy_mode is not None:
            proxy_mode = self._config.proxy_mode

            # Resolve bundle_dir relative to root_dir to handle --app-dir scenarios
            bundle_dir = self._config.bundle_dir
            if not bundle_dir.is_absolute():
                bundle_dir = self._config.root_dir / bundle_dir
            hotfile_path = bundle_dir / self._config.hot_file

            if proxy_mode == "vite":
                # Vite proxy mode (whitelist): proxy only Vite assets, HMR via WebSocket
                self._ensure_proxy_target()
                # Add middleware for HTTP proxy requests
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
                # Add WebSocket route handler for HMR
                # Vite HMR uses WebSocket at {asset_url}/vite-hmr
                hmr_path = f"{self._config.asset_url.rstrip('/')}/vite-hmr"
                app_config.route_handlers.append(
                    create_vite_hmr_handler(
                        hotfile_path=hotfile_path,
                        hmr_path=hmr_path,
                        asset_url=self._config.asset_url,
                    )
                )
                console.print(f"[dim]Vite proxy enabled (whitelist) at {hmr_path}[/]")

            elif proxy_mode == "proxy":
                # Proxy mode (blacklist): proxy everything except Litestar routes
                # Used for SSR frameworks (Astro, Nuxt, SvelteKit) and external servers (Angular CLI)
                external = self._config.external_dev_server

                # Determine target source: static URL or hotfile (dynamic)
                static_target = external.target if external else None

                app_config.middleware.append(
                    DefineMiddleware(
                        ExternalDevServerProxyMiddleware,
                        target=static_target,
                        hotfile_path=hotfile_path if static_target is None else None,
                        http2=external.http2 if external else True,
                    )
                )

                # Add HMR WebSocket handler for SSR frameworks using Vite
                hmr_path = f"{self._config.asset_url.rstrip('/')}/vite-hmr"
                app_config.route_handlers.append(
                    create_vite_hmr_handler(
                        hotfile_path=hotfile_path,
                        hmr_path=hmr_path,
                        asset_url=self._config.asset_url,
                    )
                )

                if static_target:
                    console.print(f"[dim]Proxy enabled (blacklist) → {static_target}[/]")
                else:
                    console.print("[dim]Proxy enabled (blacklist, dynamic target via hotfile)[/]")

        # Add SPA catch-all route handler if in SPA mode
        if self._config.mode == "spa" and self._config.spa_handler:
            from litestar_vite.spa import ViteSPAHandler

            self._spa_handler = ViteSPAHandler(self._config)
            # Add the catch-all route - it should be last to avoid conflicts with API routes
            app_config.route_handlers.append(self._spa_handler.create_route_handler())

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

            _log_info("Exporting type metadata for Vite...")

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

            _log_success(
                f"Types exported → {self._config.types.routes_path}"
                + (f" (openapi: {self._config.types.openapi_path})" if has_openapi else " (openapi skipped)")
            )
        except (OSError, TypeError, ValueError, ImportError) as e:  # pragma: no cover
            _log_warn(f"Type export failed: {e}")

    def _inject_routes_to_spa_handler(self, app: "Litestar") -> None:
        """Extract route metadata and inject it into the SPA handler.

        This method is called during lifespan startup when SPA route injection
        is enabled. It uses generate_routes_json() to extract routes and passes
        them to the SPA handler for HTML injection.

        Args:
            app: The Litestar application instance.
        """
        spa_config = self._config.spa_config
        if self._spa_handler is None or spa_config is None:
            return

        if not spa_config.inject_routes:
            return

        try:
            from litestar_vite.codegen import generate_routes_json

            # Extract routes with filtering
            routes_data = generate_routes_json(
                app,
                only=spa_config.routes_include,
                exclude=spa_config.routes_exclude,
                include_components=True,
            )
            # Filter out schema routes and HEAD/OPTIONS-only routes to keep SPA metadata lean
            routes = routes_data.get("routes", {})
            filtered_routes: dict[str, Any] = {}
            for name, route in routes.items():
                uri = route.get("uri", "")
                methods: list[str] = route.get("methods", [])

                # Skip schema-related routes
                if uri.startswith("/schema"):
                    continue

                # Skip routes that only expose HEAD/OPTIONS
                method_set = {m.upper() for m in methods}
                if method_set and method_set.issubset({"HEAD", "OPTIONS"}):
                    continue

                filtered_routes[name] = route

            routes_data["routes"] = filtered_routes

            self._spa_handler.set_routes_metadata(routes_data)
            _log_success(f"Injected {len(filtered_routes)} routes into SPA handler")
        except (ImportError, TypeError, ValueError, AttributeError) as e:
            _log_warn(f"Route injection failed: {e}")

    @contextmanager
    def server_lifespan(self, app: "Litestar") -> "Iterator[None]":
        """Synchronous context manager for Vite server lifecycle.

        Manages the Vite dev server process during the application lifespan.

        Args:
            app: The Litestar application instance.

        Yields:
            None
        """
        import asyncio

        # Ensure proxy target is set BEFORE environment variables (port selection)
        if self._use_server_lifespan and self._config.is_dev_mode:
            self._ensure_proxy_target()

        if self._config.set_environment:
            set_environment(config=self._config)
            set_app_environment(app)
            _log_info("Applied Vite environment variables")

        # Add HEAD→GET middleware for OpenAPI JSON so health checks and tooling work
        # Initialize SPA handler if enabled
        if self._spa_handler is not None:
            asyncio.get_event_loop().run_until_complete(self._spa_handler.initialize())
            _log_success("SPA handler initialized")

        if not self._config.is_dev_mode and not self._config.has_built_assets():
            _log_warn(
                "Vite dev server is disabled (dev_mode=False) but no index.html was found. "
                "Run your front-end build or set VITE_DEV_MODE=1 to enable HMR."
            )

        # Inject route metadata into SPA handler (if configured)
        self._inject_routes_to_spa_handler(app)

        # Export types on startup (when enabled)
        self._export_types_sync(app)

        if self._use_server_lifespan and self._config.is_dev_mode and self._config.runtime.start_dev_server:
            if not app.debug:
                _log_warn("Vite dev mode is enabled in production!")

            command_to_run = self._config.run_command if self._config.hot_reload else self._config.build_watch_command

            if self._config.hot_reload:
                _log_info("Starting Vite dev server (HMR enabled)")
            else:
                _log_info("Starting Vite watch build process")

            if self._proxy_target:
                _log_info(f"Vite proxy target: {self._proxy_target}")

            try:
                self._vite_process.start(command_to_run, self._config.root_dir)
                _log_success("Vite process started")
                if self._config.health_check:
                    self._check_health()
                yield
            finally:
                self._vite_process.stop()
                _log_info("Vite process stopped.")
                # Shutdown SPA handler
                if self._spa_handler is not None:
                    asyncio.get_event_loop().run_until_complete(self._spa_handler.shutdown())
        else:
            try:
                yield
            finally:
                # Shutdown SPA handler
                if self._spa_handler is not None:
                    asyncio.get_event_loop().run_until_complete(self._spa_handler.shutdown())

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
            set_app_environment(app)
            _log_info("Applied Vite environment variables")

        # Initialize asset loader asynchronously
        if self._asset_loader is None:
            self._asset_loader = ViteAssetLoader(config=self._config)
        await self._asset_loader.initialize()

        # Initialize SPA handler if enabled
        if self._spa_handler is not None:
            await self._spa_handler.initialize()
            _log_success("SPA handler initialized")

        if not self._config.is_dev_mode and not self._config.has_built_assets():
            _log_warn(
                "Vite dev server is disabled (dev_mode=False) but no index.html was found. "
                "Run your front-end build or set VITE_DEV_MODE=1 to enable HMR."
            )

        # Inject route metadata into SPA handler (if configured)
        self._inject_routes_to_spa_handler(app)

        # Export types on startup (when enabled)
        self._export_types_sync(app)

        if self._use_server_lifespan and self._config.is_dev_mode and self._config.runtime.start_dev_server:
            self._ensure_proxy_target()
            if self._config.set_environment:
                set_environment(config=self._config)
            if not app.debug:
                _log_warn("Vite dev mode is enabled in production!")

            command_to_run = self._config.run_command if self._config.hot_reload else self._config.build_watch_command

            if self._config.hot_reload:
                _log_info("Starting Vite dev server (HMR enabled)")
            else:
                _log_info("Starting Vite watch build process")

            try:
                self._vite_process.start(command_to_run, self._config.root_dir)
                _log_success("Vite process started")
                if self._config.health_check:
                    self._check_health()
                yield
            finally:
                self._vite_process.stop()
                _log_info("Vite process stopped.")
                # Shutdown SPA handler
                if self._spa_handler is not None:
                    await self._spa_handler.shutdown()
        else:
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
