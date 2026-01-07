"""Utilities for logging, environment setup, and route detection."""

__all__ = (
    "configure_proxy_logging",
    "console",
    "create_proxy_client",
    "get_litestar_route_prefixes",
    "infer_port_from_argv",
    "is_litestar_route",
    "is_non_serving_assets_cli",
    "is_proxy_debug",
    "log_fail",
    "log_info",
    "log_success",
    "log_warn",
    "normalize_prefix",
    "pick_free_port",
    "resolve_litestar_version",
    "set_app_environment",
    "set_environment",
    "static_not_found_handler",
    "vite_not_found_handler",
    "write_runtime_config_file",
)

import importlib.metadata
import logging
import os
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any, Protocol, cast, overload

from litestar.cli._utils import console  # pyright: ignore[reportPrivateImportUsage]

from litestar_vite.codegen import write_if_changed as _write_if_changed
from litestar_vite.config import InertiaConfig, TypeGenConfig

if TYPE_CHECKING:
    import httpx
    from litestar import Litestar, Response
    from litestar.connection import Request
    from litestar.exceptions import NotFoundException

    from litestar_vite.config import ViteConfig

_TICK = "[bold green]✓[/]"
_INFO = "[cyan]•[/]"
_WARN = "[yellow]![/]"
_FAIL = "[red]x[/]"


_vite_proxy_debug: bool | None = None


def is_proxy_debug() -> bool:
    """Check if VITE_PROXY_DEBUG is enabled (cached).

    Returns:
        True if VITE_PROXY_DEBUG is set to a truthy value, else False.
    """
    global _vite_proxy_debug  # noqa: PLW0603
    if _vite_proxy_debug is None:
        _vite_proxy_debug = os.environ.get("VITE_PROXY_DEBUG", "").lower() in {"1", "true", "yes"}
    return _vite_proxy_debug


def configure_proxy_logging() -> None:
    """Suppress verbose proxy-related logging unless debug is enabled.

    Suppresses INFO-level logs from:
    - httpx: logs every HTTP request
    - websockets: logs connection events
    - uvicorn.protocols.websockets: logs "connection open/closed"

    Only show these logs when VITE_PROXY_DEBUG is enabled.
    """

    if not is_proxy_debug():
        for logger_name in ("httpx", "websockets", "uvicorn.protocols.websockets"):
            logging.getLogger(logger_name).setLevel(logging.WARNING)


configure_proxy_logging()


# Cache HTTP/2 availability check result
_h2_available: bool | None = None


def _check_h2_available() -> bool:
    """Check if the h2 package is installed for HTTP/2 support.

    Returns:
        True if h2 is installed, False otherwise.
    """
    global _h2_available  # noqa: PLW0603
    if _h2_available is None:
        try:
            import h2  # noqa: F401  # pyright: ignore[reportMissingImports,reportUnusedImport]

            _h2_available = True
        except ImportError:
            _h2_available = False
    return _h2_available


def create_proxy_client(
    http2: bool = True,
    timeout: float = 30.0,
    max_keepalive: int = 20,
    max_connections: int = 40,
    keepalive_expiry: float = 60.0,
) -> "httpx.AsyncClient":
    """Create an httpx.AsyncClient with connection pooling for proxy use.

    This factory function creates a shared HTTP client with optimized settings
    for proxying requests to Vite dev servers or SSR frameworks. The client
    uses connection pooling for better performance.

    Args:
        http2: Enable HTTP/2 support (requires h2 package).
        timeout: Request timeout in seconds.
        max_keepalive: Maximum number of keep-alive connections per host.
        max_connections: Maximum total concurrent connections.
        keepalive_expiry: Idle timeout before closing keep-alive connections.

    Returns:
        A configured httpx.AsyncClient with connection pooling.
    """
    import httpx

    http2_enabled = http2 and _check_h2_available()
    limits = httpx.Limits(
        max_keepalive_connections=max_keepalive, max_connections=max_connections, keepalive_expiry=keepalive_expiry
    )
    return httpx.AsyncClient(limits=limits, timeout=httpx.Timeout(timeout), http2=http2_enabled)


def infer_port_from_argv() -> str | None:
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


def is_non_serving_assets_cli() -> bool:
    """Return True when running CLI assets commands that don't start a server.

    This suppresses dev-proxy setup/logging for commands like `assets build`
    where only a Vite build is performed and no proxy should be initialized.

    Returns:
        True when the current process is running a non-serving `litestar assets ...` command, otherwise False.
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


def log_success(message: str) -> None:
    """Print a success message with consistent styling."""

    console.print(f"{_TICK} {message}")


def log_info(message: str) -> None:
    """Print an informational message with consistent styling."""

    console.print(f"{_INFO} {message}")


def log_warn(message: str) -> None:
    """Print a warning message with consistent styling."""

    console.print(f"{_WARN} {message}")


def log_fail(message: str) -> None:
    """Print an error message with consistent styling."""

    console.print(f"{_FAIL} {message}")


def _path_for_bridge(path: Path, root_dir: Path) -> str:
    """Convert a path to a relative string for the JS bridge config.

    The JavaScript plugin expects relative paths without leading slashes.
    This function converts absolute paths to relative paths (relative to root_dir)
    when possible.

    Args:
        path: The path to convert.
        root_dir: The project root directory.

    Returns:
        A relative path string suitable for .litestar.json.
        If the path cannot be made relative (outside root_dir), returns
        a relative path using os.path.relpath (e.g., "../external").
    """
    if not path.is_absolute():
        # Already relative, return as-is without any leading slash
        return str(path).lstrip("/")

    # Resolve both paths to handle symlinks consistently
    resolved_path = path.resolve()
    resolved_root = root_dir.resolve()
    try:
        relative = resolved_path.relative_to(resolved_root)
        return str(relative)
    except ValueError:
        # Path is outside root_dir - cannot make relative via relative_to
        # Use os.path.relpath as fallback which handles "../" paths
        return os.path.relpath(resolved_path, resolved_root)


@overload
def write_runtime_config_file(config: "ViteConfig", *, asset_url_override: str | None = None) -> str: ...


@overload
def write_runtime_config_file(
    config: "ViteConfig", *, asset_url_override: str | None = None, return_status: bool
) -> tuple[str, bool]: ...


def write_runtime_config_file(
    config: "ViteConfig", *, asset_url_override: str | None = None, return_status: bool = False
) -> str | tuple[str, bool]:
    """Write a JSON handoff file for the Vite plugin and return its path.

    The runtime config file is read by the JS plugin. We serialize with Litestar's JSON encoder for
    consistency and format output deterministically for easier debugging.

    Returns:
        The path to the written config file.
    """

    root = config.root_dir or Path.cwd()
    path = Path(root) / ".litestar.json"
    types = config.types if isinstance(config.types, TypeGenConfig) else None
    # Convert paths to relative strings for JS bridge
    resource_dir_value = _path_for_bridge(config.resource_dir, root)
    bundle_dir_value = _path_for_bridge(config.bundle_dir, root)
    static_dir_value = _path_for_bridge(config.static_dir, root)
    ssr_out_dir_value = _path_for_bridge(config.ssr_output_dir, root) if config.ssr_output_dir else None

    litestar_version = os.environ.get("LITESTAR_VERSION") or resolve_litestar_version()

    deploy_asset_url = None
    deploy = config.deploy_config
    if deploy is not None and deploy.asset_url:
        deploy_asset_url = deploy.asset_url

    payload = {
        "assetUrl": config.asset_url,
        "deployAssetUrl": deploy_asset_url,
        "bundleDir": bundle_dir_value,
        "hotFile": config.hot_file,
        "resourceDir": resource_dir_value,
        "staticDir": static_dir_value,
        "manifest": config.manifest_name,
        "mode": config.mode,
        "proxyMode": config.proxy_mode,
        "port": config.port,
        "host": config.host,
        "ssrOutDir": ssr_out_dir_value,
        "types": {
            "enabled": True,
            "output": _path_for_bridge(types.output, root),
            "openapiPath": _path_for_bridge(types.openapi_path, root) if types.openapi_path else None,
            "routesPath": _path_for_bridge(types.routes_path, root) if types.routes_path else None,
            "pagePropsPath": _path_for_bridge(types.page_props_path, root) if types.page_props_path else None,
            "routesTsPath": _path_for_bridge(types.routes_ts_path, root) if types.routes_ts_path else None,
            "schemasTsPath": _path_for_bridge(types.schemas_ts_path, root) if types.schemas_ts_path else None,
            "generateZod": types.generate_zod,
            "generateSdk": types.generate_sdk,
            "generateRoutes": types.generate_routes,
            "generatePageProps": types.generate_page_props,
            "generateSchemas": types.generate_schemas,
            "globalRoute": types.global_route,
        }
        if types
        else None,
        "logging": {
            "level": config.logging_config.level,
            "showPathsAbsolute": config.logging_config.show_paths_absolute,
            "suppressNpmOutput": config.logging_config.suppress_npm_output,
            "suppressViteBanner": config.logging_config.suppress_vite_banner,
            "timestamps": config.logging_config.timestamps,
        },
        "spa": {"useScriptElement": config.inertia.use_script_element}
        if isinstance(config.inertia, InertiaConfig)
        else None,
        "executor": config.runtime.executor,
        "litestarVersion": litestar_version,
    }

    import msgspec
    from litestar.serialization import encode_json

    content = msgspec.json.format(encode_json(payload), indent=2)
    changed = _write_if_changed(path, content)
    if return_status:
        return str(path), changed
    return str(path)


def set_environment(config: "ViteConfig", asset_url_override: str | None = None) -> None:
    """Configure environment variables for Vite integration.

    Sets environment variables that can be used by both the Python backend
    and the Vite frontend during development.

    Args:
        config: The Vite configuration.
        asset_url_override: Optional asset URL to force (e.g., CDN base during build).
    """
    litestar_version = os.environ.get("LITESTAR_VERSION") or resolve_litestar_version()
    asset_url = asset_url_override or config.asset_url
    if asset_url:
        os.environ.setdefault("ASSET_URL", asset_url)
    if config.base_url:
        os.environ.setdefault("VITE_BASE_URL", config.base_url)
    os.environ.setdefault("VITE_ALLOW_REMOTE", str(True))

    backend_host = os.environ.get("LITESTAR_HOST") or "127.0.0.1"
    backend_port = os.environ.get("LITESTAR_PORT") or os.environ.get("PORT") or infer_port_from_argv() or "8000"
    os.environ["LITESTAR_HOST"] = backend_host
    os.environ["LITESTAR_PORT"] = str(backend_port)
    os.environ.setdefault("APP_URL", f"http://{backend_host}:{backend_port}")

    os.environ.setdefault("VITE_PROTOCOL", config.protocol)
    if config.proxy_mode is not None:
        os.environ.setdefault("VITE_PROXY_MODE", config.proxy_mode)

    os.environ.setdefault("VITE_HOST", config.host)
    os.environ.setdefault("VITE_PORT", str(config.port))
    os.environ.setdefault("NUXT_HOST", config.host)
    os.environ.setdefault("NUXT_PORT", str(config.port))
    os.environ.setdefault("NITRO_HOST", config.host)
    os.environ.setdefault("NITRO_PORT", str(config.port))
    os.environ.setdefault("HOST", config.host)
    os.environ.setdefault("PORT", str(config.port))

    os.environ["LITESTAR_VERSION"] = litestar_version
    os.environ.setdefault("LITESTAR_VITE_RUNTIME", config.runtime.executor or "node")
    os.environ.setdefault("LITESTAR_VITE_INSTALL_CMD", " ".join(config.install_command))

    if config.is_dev_mode:
        os.environ.setdefault("VITE_DEV_MODE", str(config.is_dev_mode))

    config_path = write_runtime_config_file(config, asset_url_override=asset_url_override)
    os.environ["LITESTAR_VITE_CONFIG_PATH"] = config_path


def set_app_environment(app: "Litestar") -> None:
    """Set environment variables derived from the Litestar app instance.

    This is called after set_environment() once the app is available,
    to export app-specific configuration like OpenAPI paths.

    Args:
        app: The Litestar application instance.
    """
    openapi_config = app.openapi_config
    if openapi_config is not None and isinstance(openapi_config.path, str) and openapi_config.path:
        os.environ.setdefault("LITESTAR_OPENAPI_PATH", openapi_config.path)


def resolve_litestar_version() -> str:
    """Return the installed Litestar version string.

    Returns:
        The installed Litestar version, or "unknown" when unavailable.
    """
    try:
        return importlib.metadata.version("litestar")
    except importlib.metadata.PackageNotFoundError:
        return "unknown"


def pick_free_port() -> int:
    import socket

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def normalize_prefix(prefix: str) -> str:
    if not prefix.startswith("/"):
        prefix = f"/{prefix}"
    if not prefix.endswith("/"):
        prefix = f"{prefix}/"
    return prefix


class _RoutePrefixesState(Protocol):
    litestar_vite_route_prefixes: tuple[str, ...]


def get_litestar_route_prefixes(app: "Litestar") -> tuple[str, ...]:
    """Build a cached list of Litestar route prefixes for the given app.

    This function collects all registered route paths from the Litestar application
    and caches them for efficient lookup. The cache is stored in app.state to ensure
    it's automatically cleaned up when the app is garbage collected.

    Includes:
    - All registered Litestar route paths
    - OpenAPI schema path (customizable via openapi_config.path)
    - Common API prefixes as fallback (/api, /schema, /docs)

    Args:
        app: The Litestar application instance.

    Returns:
        A tuple of route prefix strings (without trailing slashes).
    """
    state = cast("_RoutePrefixesState", app.state)
    try:
        return state.litestar_vite_route_prefixes
    except AttributeError:
        pass

    prefixes: list[str] = []
    for route in app.routes:
        prefix = route.path.rstrip("/")
        if prefix:
            prefixes.append(prefix)

    openapi_config = app.openapi_config
    if openapi_config is not None:
        schema_path = openapi_config.path
        if schema_path:
            prefixes.append(schema_path.rstrip("/"))

    prefixes.extend(["/api", "/schema", "/docs"])

    unique_prefixes = sorted(set(prefixes), key=len, reverse=True)
    result = tuple(unique_prefixes)

    state.litestar_vite_route_prefixes = result

    if is_proxy_debug():
        console.print(f"[dim][route-detection] Cached prefixes: {result}[/]")

    return result


def is_litestar_route(path: str, app: "Litestar") -> bool:
    """Check if a path matches a registered Litestar route.

    This function determines if a request path should be handled by Litestar
    rather than proxied to the Vite dev server or served as SPA content.

    A path matches if it equals a registered prefix or starts with prefix + "/".

    Args:
        path: The request path to check (e.g., "/schema", "/api/users").
        app: The Litestar application instance.

    Returns:
        True if the path matches a Litestar route, False otherwise.
    """
    excluded = get_litestar_route_prefixes(app)
    return any(path == prefix or path.startswith(f"{prefix}/") for prefix in excluded)


def static_not_found_handler(
    _request: "Request[Any, Any, Any]", _exc: "NotFoundException"
) -> "Response[bytes]":  # pragma: no cover - trivial
    """Return an empty 404 response for static files routing misses.

    Returns:
        An empty 404 response.
    """
    from litestar import Response

    return Response(status_code=404, content=b"")


def vite_not_found_handler(request: "Request[Any, Any, Any]", exc: "NotFoundException") -> "Response[Any]":
    """Return a consistent 404 response for missing static assets / routes.

    Inertia requests are delegated to the Inertia exception handler to support
    redirect_404 configuration.

    Args:
        request: Incoming request.
        exc: NotFound exception raised by routing.

    Returns:
        Response instance for the 404.
    """
    from litestar import Response

    if request.headers.get("x-inertia", "").lower() == "true":
        from litestar_vite.inertia.exception_handler import exception_to_http_response

        return exception_to_http_response(request, exc)
    return Response(status_code=404, content=b"")
