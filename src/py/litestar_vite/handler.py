"""SPA mode handler for Vite integration.

This module provides the AppHandler class that manages serving
the Single Page Application (SPA) HTML in both development and production modes.

In dev mode, it proxies requests to the Vite dev server for HMR support.
In production, it serves the built index.html with async caching.

HTML transformations are applied based on SPAConfig settings:
- CSRF token injection (window.__LITESTAR_CSRF__)
- Page data injection for Inertia.js (data-page attribute)
- Asset URL transformation using Vite manifest (production only)

Note:
    Route metadata is now generated as TypeScript (routes.ts) at build time.
    See TypeGenConfig.generate_routes to enable typed route generation.
"""

import logging
from contextlib import suppress
from pathlib import Path
from typing import TYPE_CHECKING, Any, NoReturn, cast

import anyio
import httpx
from litestar import Response, get
from litestar.exceptions import ImproperlyConfiguredException, NotFoundException, SerializationException
from litestar.serialization import decode_json, encode_json

from litestar_vite.html_transform import inject_head_script, set_data_attribute, transform_asset_urls
from litestar_vite.plugin import is_litestar_route

if TYPE_CHECKING:
    from litestar.connection import Request
    from litestar.types import Guard  # pyright: ignore[reportUnknownVariableType]

    from litestar_vite.config import SPAConfig, ViteConfig

logger = logging.getLogger("litestar_vite")

# Pre-encoded content type header for production responses
_HTML_MEDIA_TYPE = "text/html; charset=utf-8"


def _is_static_asset_path(request_path: str, asset_prefix: str | None) -> bool:
    """Check if a request path targets static assets rather than SPA routes.

    Args:
        request_path: Incoming request path.
        asset_prefix: Normalized asset URL prefix (e.g., ``/static``) or None.

    Returns:
        True when ``request_path`` matches the asset prefix (or a descendant path), otherwise False.
    """
    if not asset_prefix:
        return False
    return request_path == asset_prefix or request_path.startswith(f"{asset_prefix}/")


def _get_route_opt(request: "Request[Any, Any, Any]") -> "dict[str, Any] | None":
    """Return the current route handler opt dict when available."""
    route_handler = request.scope["route_handler"]  # pyright: ignore[reportUnknownMemberType]
    return cast("dict[str, Any] | None", getattr(route_handler, "opt", None))


def _get_route_asset_prefix(request: "Request[Any, Any, Any]") -> str | None:
    """Get the static asset prefix for the current SPA route handler."""
    opt = _get_route_opt(request)
    if opt is None:
        return None
    asset_prefix = opt.get("_vite_asset_prefix")
    if isinstance(asset_prefix, str) and asset_prefix:
        return asset_prefix
    return None


def _get_spa_handler_from_request(request: "Request[Any, Any, Any]") -> "AppHandler":
    """Resolve the AppHandler instance for the current request.

    This is stored on the SPA route handler's ``opt`` when the route is created.

    Args:
        request: Incoming request.

    Returns:
        The configured AppHandler.

    Raises:
        ImproperlyConfiguredException: If the SPA handler is not available on the route metadata.
    """
    opt = _get_route_opt(request)
    handler = opt.get("_vite_spa_handler") if opt is not None else None
    if isinstance(handler, AppHandler):
        return handler
    msg = "SPA handler is not available for this route. Ensure AppHandler.create_route_handler() was used."
    raise ImproperlyConfiguredException(msg)
    return None


async def _spa_handler_dev(request: "Request[Any, Any, Any]") -> Response[str]:
    """Serve the SPA HTML (dev mode - proxied from Vite).

    Checks if the request path matches a static asset or Litestar route before serving.

    Raises:
        NotFoundException: If the path matches a static asset or Litestar route.

    Returns:
        The HTML response from the Vite dev server.
    """
    path = request.url.path
    asset_prefix = _get_route_asset_prefix(request)
    if _is_static_asset_path(path, asset_prefix):
        raise NotFoundException(detail=f"Static asset path: {path}")
    if path != "/" and is_litestar_route(path, request.app):
        raise NotFoundException(detail=f"Not an SPA route: {path}")

    spa_handler = _get_spa_handler_from_request(request)
    html = await spa_handler.get_html(request)
    return Response(content=html, status_code=200, media_type="text/html")


async def _spa_handler_prod(request: "Request[Any, Any, Any]") -> Response[bytes]:
    """Serve the SPA HTML (production - cached).

    Raises:
        NotFoundException: If the path matches a static asset or Litestar route.

    Returns:
        HTML bytes response from the cached SPA handler.
    """
    path = request.url.path
    asset_prefix = _get_route_asset_prefix(request)
    if _is_static_asset_path(path, asset_prefix):
        raise NotFoundException(detail=f"Static asset path: {path}")
    if path != "/" and is_litestar_route(path, request.app):
        raise NotFoundException(detail=f"Not an SPA route: {path}")

    spa_handler = _get_spa_handler_from_request(request)
    body = await spa_handler.get_bytes()
    return Response(content=body, status_code=200, media_type=_HTML_MEDIA_TYPE)


class AppHandler:
    """Handler for serving SPA HTML in both dev and production modes.

    This handler manages the serving of the index.html file for SPAs.
    It supports:
    - Development mode: Proxies to Vite dev server for HMR
    - Production mode: Serves built index.html with caching
    - CSRF token injection: Injects token for form submissions
    - Page data injection: Injects Inertia.js page props as data attributes

    Performance optimizations:
    - Production: HTML cached as bytes at startup, zero per-request allocation
    - Development: Reuses httpx.AsyncClient for connection pooling
    - Transformed HTML cached in production to avoid repeated transformations
    - Uses __slots__ for reduced memory footprint

    Note:
        Route metadata is now generated as TypeScript (routes.ts) at build time.
        See TypeGenConfig.generate_routes to enable typed route generation.

    Attributes:
        config: The Vite configuration.

    Example:
        handler = AppHandler(config)
        await handler.initialize()
        html = await handler.get_html(request)

        # With page data (for Inertia.js)
        html = await handler.get_html(request, page_data={"component": "Home", "props": {...}})
    """

    __slots__ = (
        "_cached_bytes",
        "_cached_html",
        "_cached_transformed_html",
        "_config",
        "_http_client",
        "_http_client_sync",
        "_initialized",
        "_manifest",
        "_spa_config",
        "_vite_url",
    )

    def __init__(self, config: "ViteConfig") -> None:
        """Initialize the SPA handler.

        Args:
            config: The Vite configuration.
        """
        self._config = config
        self._spa_config: "SPAConfig | None" = config.spa_config
        self._cached_html: "str | None" = None
        self._cached_bytes: "bytes | None" = None
        self._cached_transformed_html: "str | None" = None
        self._initialized = False
        self._http_client: "httpx.AsyncClient | None" = None
        self._http_client_sync: "httpx.Client | None" = None
        self._vite_url: "str | None" = None
        self._manifest: "dict[str, Any]" = {}

    @property
    def is_initialized(self) -> bool:
        """Whether the handler has been initialized."""
        return self._initialized

    async def initialize_async(self, vite_url: "str | None" = None) -> None:
        """Initialize the handler asynchronously.

        This method should be called during app startup to:
        - Initialize the HTTP client for dev mode proxying
        - Load and cache the index.html in production mode
        - Load the Vite manifest for asset URL transformation

        Args:
            vite_url: Optional Vite server URL to use for proxying. If provided,
                     this takes precedence over hotfile resolution. This is typically
                     passed by VitePlugin which knows the correct URL.
        """
        if self._initialized:
            return

        if self._config.is_dev_mode and self._config.hot_reload:
            self._init_http_clients(vite_url)
        else:
            await self._load_production_assets_async()

        self._initialized = True

    def initialize_sync(self, vite_url: "str | None" = None) -> None:
        """Initialize the handler synchronously.

        This method should be called during app startup to:
        - Initialize the HTTP client for dev mode proxying
        - Load and cache the index.html in production mode
        - Load the Vite manifest for asset URL transformation

        This is the preferred initialization method for lifespan hooks
        since file I/O during startup is negligible.

        Args:
            vite_url: Optional Vite server URL to use for proxying. If provided,
                     this takes precedence over hotfile resolution. This is typically
                     passed by VitePlugin which knows the correct URL.
        """
        if self._initialized:
            return

        if self._config.is_dev_mode and self._config.hot_reload:
            self._init_http_clients(vite_url)
        else:
            self._load_production_assets_sync()

        self._initialized = True

    def _init_http_clients(self, vite_url: "str | None" = None) -> None:
        """Initialize HTTP clients for dev mode proxying.

        Args:
            vite_url: Optional Vite server URL to use for proxying.
        """
        self._vite_url = vite_url or self._resolve_vite_url()

        http2_enabled = self._config.http2
        if http2_enabled:
            try:
                import h2  # noqa: F401  # pyright: ignore[reportMissingImports,reportUnusedImport]
            except ImportError:
                http2_enabled = False

        self._http_client = httpx.AsyncClient(timeout=httpx.Timeout(5.0), http2=http2_enabled)
        self._http_client_sync = httpx.Client(timeout=httpx.Timeout(5.0))

    async def shutdown_async(self) -> None:
        """Shutdown the handler asynchronously.

        Closes the HTTP clients if they were created for dev mode.
        This method is async because httpx.AsyncClient.aclose() is async.
        """
        if self._http_client is not None:
            # Ignore RuntimeError if transport is already closed (uvloop edge case)
            with suppress(RuntimeError):
                await self._http_client.aclose()
            self._http_client = None
        if self._http_client_sync is not None:
            with suppress(RuntimeError):
                self._http_client_sync.close()
            self._http_client_sync = None

    def _load_production_assets_sync(self) -> None:
        """Load manifest and index.html synchronously in production modes."""
        if self._config.mode != "external":
            self._load_manifest_sync()
        self._load_index_html_sync()

    async def _load_production_assets_async(self) -> None:
        """Load manifest and index.html asynchronously in production modes."""
        if self._config.mode != "external":
            await self._load_manifest_async()
        await self._load_index_html_async()

    def _transform_html(
        self, html: str, page_data: "dict[str, Any] | None" = None, csrf_token: "str | None" = None
    ) -> str:
        """Transform HTML by injecting CSRF token and/or page data.

        This method applies transformations based on SPAConfig settings:
        - Injects CSRF token as a global JavaScript variable
        - Injects page data as a data attribute on the app element

        Uses Litestar's JSON serialization.

        Note:
            Route metadata is now generated as TypeScript (routes.ts) at build time
            instead of runtime injection. See TypeGenConfig.generate_routes.

        Args:
            html: The raw HTML content to transform.
            page_data: Optional page data to inject (e.g., Inertia.js page props).
            csrf_token: Optional CSRF token to inject.

        Returns:
            The transformed HTML with injected content.
        """
        if self._spa_config is None:
            # SPA transformations disabled, return as-is
            # But still inject page_data if provided
            if page_data is not None:
                json_data = encode_json(page_data).decode("utf-8")
                html = set_data_attribute(html, "#app", "data-page", json_data)
            return html

        # Inject CSRF token if configured
        if self._spa_config.inject_csrf and csrf_token:
            # Inject as a simple string assignment (not JSON object)
            script = f'window.{self._spa_config.csrf_var_name} = "{csrf_token}";'
            html = inject_head_script(html, script, escape=False)

        # Inject page data as data-page attribute if provided
        if page_data is not None:
            json_data = encode_json(page_data).decode("utf-8")
            html = set_data_attribute(html, self._spa_config.app_selector, "data-page", json_data)

        return html

    async def _load_index_html_async(self) -> None:
        """Asynchronously load index.html from disk and cache it in memory.

        Caches both string and bytes representations to avoid
        encoding overhead on each request.

        In production mode, transforms source asset URLs (e.g., /resources/main.tsx)
        to their hashed equivalents using the Vite manifest. This transformation
        is done once at load time for optimal performance.
        """
        resolved_path: anyio.Path | None = None
        for candidate in self._config.candidate_index_html_paths():
            candidate_path = anyio.Path(candidate)
            if await candidate_path.exists():
                resolved_path = candidate_path
                break

        if resolved_path is None:
            self._raise_index_not_found()

        raw_bytes = await resolved_path.read_bytes()
        html = raw_bytes.decode("utf-8")

        # This is critical for library mode builds where Vite doesn't transform index.html
        html = self._transform_asset_urls_in_html(html)

        self._cached_html = html
        self._cached_bytes = html.encode("utf-8")

    def _load_index_html_sync(self) -> None:
        """Synchronously load index.html from disk and cache it in memory.

        Caches both string and bytes representations to avoid
        encoding overhead on each request.

        In production mode, transforms source asset URLs (e.g., /resources/main.tsx)
        to their hashed equivalents using the Vite manifest. This transformation
        is done once at load time for optimal performance.
        """
        resolved_path: Path | None = None
        for candidate in self._config.candidate_index_html_paths():
            candidate_path = Path(candidate)
            if candidate_path.exists():
                resolved_path = candidate_path
                break

        if resolved_path is None:
            self._raise_index_not_found()

        raw_bytes = resolved_path.read_bytes()
        html = raw_bytes.decode("utf-8")

        # This is critical for library mode builds where Vite doesn't transform index.html
        html = self._transform_asset_urls_in_html(html)

        self._cached_html = html
        self._cached_bytes = html.encode("utf-8")

    def _raise_index_not_found(self) -> NoReturn:
        """Raise an exception when index.html is not found.

        Raises:
            ImproperlyConfiguredException: Always raised with paths checked.
        """
        joined_paths = ", ".join(str(path) for path in self._config.candidate_index_html_paths())
        msg = (
            "index.html not found. "
            f"Checked: {joined_paths}. "
            "SPA mode requires index.html in one of the expected locations. "
            "Did you forget to build your assets?"
        )
        raise ImproperlyConfiguredException(msg)

    def _get_manifest_path(self) -> Path:
        """Get the path to the Vite manifest file.

        Returns:
            Absolute path to the manifest file.
        """
        bundle_dir = self._config.bundle_dir
        if not bundle_dir.is_absolute():
            bundle_dir = self._config.root_dir / bundle_dir
        return bundle_dir / self._config.manifest_name

    async def _load_manifest_async(self) -> None:
        """Asynchronously load the Vite manifest for asset URL transformation.

        The manifest is used to replace source asset paths (e.g., /resources/main.tsx)
        with their hashed production equivalents (e.g., /static/assets/main-abc123.js).

        Logs a warning if manifest not found in production mode (assets may not load).
        """
        manifest_path = anyio.Path(self._get_manifest_path())
        try:
            if await manifest_path.exists():
                content = await manifest_path.read_bytes()
                self._manifest = decode_json(content)
            else:
                # In production mode, missing manifest is likely a build issue
                logger.warning(
                    "Vite manifest not found at %s. "
                    "Asset URLs in index.html will not be transformed. "
                    "Run 'litestar assets build' to generate the manifest.",
                    manifest_path,
                )
        except OSError as exc:
            logger.warning("Failed to read Vite manifest file: %s", exc)
        except SerializationException as exc:
            logger.warning("Failed to parse Vite manifest JSON: %s", exc)

    def _load_manifest_sync(self) -> None:
        """Synchronously load the Vite manifest for asset URL transformation.

        The manifest is used to replace source asset paths (e.g., /resources/main.tsx)
        with their hashed production equivalents (e.g., /static/assets/main-abc123.js).

        Logs a warning if manifest not found in production mode (assets may not load).
        """
        manifest_path = self._get_manifest_path()
        try:
            if manifest_path.exists():
                content = manifest_path.read_bytes()
                self._manifest = decode_json(content)
            else:
                # In production mode, missing manifest is likely a build issue
                logger.warning(
                    "Vite manifest not found at %s. "
                    "Asset URLs in index.html will not be transformed. "
                    "Run 'litestar assets build' to generate the manifest.",
                    manifest_path,
                )
        except OSError as exc:
            logger.warning("Failed to read Vite manifest file: %s", exc)
        except SerializationException as exc:
            logger.warning("Failed to parse Vite manifest JSON: %s", exc)

    def _transform_asset_urls_in_html(self, html: str) -> str:
        """Transform source asset URLs to production hashed URLs using manifest.

        This is critical for production mode when using Vite's library mode
        (input: ["resources/main.tsx"]) where Vite doesn't transform index.html.

        Args:
            html: The HTML content to transform.

        Returns:
            HTML with transformed asset URLs, or original if no manifest.
        """
        if not self._manifest:
            return html
        return transform_asset_urls(
            html, self._manifest, asset_url=self._config.asset_url, base_url=self._config.base_url
        )

    def _get_csrf_token(self, request: "Request[Any, Any, Any]") -> "str | None":
        """Extract CSRF token from the request scope.

        Args:
            request: The incoming request.

        Returns:
            The CSRF token or None if not available.
        """
        from litestar.utils.empty import value_or_default
        from litestar.utils.scope.state import ScopeState

        return value_or_default(ScopeState.from_scope(request.scope).csrf_token, None)

    async def get_html(self, request: "Request[Any, Any, Any]", *, page_data: "dict[str, Any] | None" = None) -> str:
        """Get the HTML for the SPA with optional transformations.

        In dev mode, proxies the request to the Vite dev server and applies
        transformations on each request (no caching for HMR compatibility).

        In production mode, returns the cached index.html with route metadata
        injected. If page_data is provided, it's injected fresh on each request.

        Args:
            request: The incoming request.
            page_data: Optional page data to inject as data-page attribute.
                       When provided, disables transformed HTML caching for
                       this request since page data varies per request.

        Returns:
            The HTML content as a string, optionally transformed.

        Raises:
            ImproperlyConfiguredException: If the handler is not initialized.
        """
        if not self._initialized:
            msg = "AppHandler not initialized. Call initialize() during app startup."
            raise ImproperlyConfiguredException(msg)

        needs_transform = self._spa_config is not None or page_data is not None
        needs_csrf = self._spa_config is not None and self._spa_config.inject_csrf
        csrf_token = self._get_csrf_token(request) if needs_csrf else None

        if self._config.is_dev_mode and self._config.hot_reload:
            html = await self._proxy_to_dev_server(request)
            # In dev mode, always transform fresh (no caching for HMR)
            if needs_transform:
                html = self._transform_html(html, page_data, csrf_token)
            return html

        # Production mode
        if self._cached_html is None:
            # Fallback: try to load now if not cached
            await self._load_index_html_async()

        base_html = self._cached_html or ""

        # If no transformations needed, return raw cached HTML
        if not needs_transform:
            return base_html

        # If page_data is provided OR csrf is needed, we can't use cached transformed HTML
        # since these vary per request
        if page_data is not None or csrf_token is not None:
            return self._transform_html(base_html, page_data, csrf_token)

        if self._spa_config is not None and self._spa_config.cache_transformed_html:
            if self._cached_transformed_html is not None:
                return self._cached_transformed_html
            self._cached_transformed_html = self._transform_html(base_html, None, None)
            return self._cached_transformed_html

        # Caching disabled, transform fresh
        return self._transform_html(base_html, None, None)

    def get_html_sync(self, *, page_data: "dict[str, Any] | None" = None, csrf_token: "str | None" = None) -> str:
        """Get the HTML for the SPA synchronously.

        This method is for use in synchronous contexts where async is not
        available (e.g., Litestar's Response.to_asgi_response).

        In dev mode, uses a synchronous HTTP client to fetch from Vite.
        In production mode, uses cached HTML.

        Note:
            CSRF token injection requires passing the token explicitly since
            this method doesn't have access to the request scope.

            If the handler is not initialized, this method will lazily
            initialize it with a warning. This is a fallback for cases
            where the lifespan hook didn't run properly.

        Args:
            page_data: Optional page data to inject as data-page attribute.
            csrf_token: Optional CSRF token to inject.

        Raises:
            ImproperlyConfiguredException: If the handler is not initialized

        Returns:
            The HTML content as a string, optionally transformed.
        """
        if not self._initialized:
            # Lazy initialization fallback - lifespan may not have run properly
            logger.warning(
                "AppHandler lazy init triggered - lifespan may not have run. "
                "Consider calling initialize_sync() explicitly during app startup."
            )
            self.initialize_sync()

        # Dev mode: fetch from Vite dev server synchronously
        if self._config.is_dev_mode and self._config.hot_reload:
            base_html = self._proxy_to_dev_server_sync()
            # In dev mode, always transform fresh (no caching for HMR)
            needs_transform = self._spa_config is not None or page_data is not None
            if needs_transform:
                return self._transform_html(base_html, page_data, csrf_token)
            return base_html

        # Production mode: use cached HTML
        if self._cached_html is None:
            msg = "No cached HTML available. Ensure initialize() was called in production mode."
            raise ImproperlyConfiguredException(msg)

        base_html = self._cached_html

        needs_transform = self._spa_config is not None or page_data is not None

        if not needs_transform:
            return base_html

        # If page_data is provided OR csrf is needed, we can't use cached transformed HTML
        if page_data is not None or csrf_token is not None:
            return self._transform_html(base_html, page_data, csrf_token)

        if self._spa_config is not None and self._spa_config.cache_transformed_html:
            if self._cached_transformed_html is None:
                self._cached_transformed_html = self._transform_html(base_html, None, None)
            return self._cached_transformed_html

        # Caching disabled, transform fresh
        return self._transform_html(base_html, None, None)

    async def get_bytes(self) -> bytes:
        """Get the HTML as bytes for the SPA (production only).

        This is more efficient than get_html() when you need bytes,
        as it avoids the string->bytes encoding step.

        Returns:
            The HTML content as bytes.
        """
        if not self._initialized:
            # Lazily initialize if a worker didn't run lifespan hooks (e.g., multi-proc servers)
            await self.initialize_async()

        if self._cached_bytes is None:
            await self._load_index_html_async()

        return self._cached_bytes or b""

    async def _proxy_to_dev_server(self, request: "Request[Any, Any, Any]") -> str:
        """Proxy the request to the Vite server.

        Args:
            request: The incoming request.

        Returns:
            The HTML content from the Vite server.

        Raises:
            ImproperlyConfiguredException: If the HTTP client is not initialized.
        """
        if self._http_client is None:
            msg = "HTTP client not initialized for dev mode."
            raise ImproperlyConfiguredException(msg)

        if self._vite_url is None:
            msg = "Vite URL not resolved. Ensure initialize_sync() or initialize_async() was called."
            raise ImproperlyConfiguredException(msg)

        target_url = f"{self._vite_url}/"

        try:
            # Request the root path from Vite server
            response = await self._http_client.get(target_url, follow_redirects=True)
            response.raise_for_status()
        except httpx.HTTPError as e:
            msg = f"Failed to proxy request to Vite server at {target_url}. Is the dev server running? Error: {e!s}"
            raise ImproperlyConfiguredException(msg) from e
        else:
            return response.text

    def _proxy_to_dev_server_sync(self) -> str:
        """Synchronously proxy the request to the Vite server.

        This method is used by Inertia's synchronous response rendering
        to avoid deadlocks when calling async code from sync context
        within the same event loop thread.

        Returns:
            The HTML content from the Vite server.

        Raises:
            ImproperlyConfiguredException: If the HTTP client is not initialized.
        """
        if self._http_client_sync is None:
            msg = "Synchronous HTTP client not initialized for dev mode."
            raise ImproperlyConfiguredException(msg)

        if self._vite_url is None:
            msg = "Vite URL not resolved. Ensure initialize_sync() or initialize_async() was called."
            raise ImproperlyConfiguredException(msg)

        target_url = f"{self._vite_url}/"

        try:
            response = self._http_client_sync.get(target_url, follow_redirects=True)
            response.raise_for_status()
        except httpx.HTTPError as e:
            msg = f"Failed to proxy request to Vite server at {target_url}. Is the dev server running? Error: {e!s}"
            raise ImproperlyConfiguredException(msg) from e
        else:
            return response.text

    def _resolve_vite_url(self) -> str:
        """Resolve the Vite server URL from hotfile or config.

        This is called once at initialization time. The URL is cached
        and only refreshed when the Python server restarts/reloads.

        Prefer the hotfile URL if present (written by the JS plugin),
        otherwise fall back to the configured protocol/host/port.

        Returns:
            The base URL of the Vite server (without trailing slash).
        """
        hotfile = self._config.bundle_dir / self._config.hot_file
        if not hotfile.is_absolute():
            hotfile = self._config.root_dir / hotfile

        if hotfile.exists():
            try:
                url = hotfile.read_text().strip()
                if url:
                    return url.rstrip("/")
            except OSError:
                pass

        return f"{self._config.protocol}://{self._config.host}:{self._config.port}"

    def create_route_handler(self) -> Any:
        """Create a Litestar route handler for the SPA.

        The handler includes route exclusion logic to prevent the SPA catch-all
        from shadowing Litestar-registered routes (e.g., ``/schema``, ``/api``).
        When a request matches a Litestar route, NotFoundException is raised
        to let the router handle it properly.

        Returns:
            A Litestar route handler that serves the SPA HTML.

        Example:
            handler = AppHandler(config)
            spa_route = handler.create_route_handler()
            # Add spa_route to your Litestar app routes
        """
        is_dev = self._config.is_dev_mode and self._config.hot_reload

        opt: dict[str, Any] = {}
        if self._config.exclude_static_from_auth:
            opt["exclude_from_auth"] = True
        opt["_vite_spa_handler"] = self

        guards: "list[Guard] | None" = list(self._config.guards) if self._config.guards else None  # pyright: ignore[reportUnknownVariableType,reportUnknownMemberType,reportUnknownArgumentType]

        # Build paths based on spa_path
        # spa_path controls where the SPA handler serves index.html (defaults to "/")
        # asset_url controls where static files are served
        #
        # Common scenarios:
        # 1. spa_path="/" (default) with asset_url="/web/" → SPA at /, exclude /web/ from catch-all
        # 2. spa_path="/web/" with asset_url="/web/" → SPA and assets both at /web/ (Angular --base-href)
        # 3. spa_path="/" (default) with asset_url="/static/" → SPA at /, exclude /static/ from catch-all
        asset_url = self._config.asset_url
        spa_path = self._config.spa_path

        # spa_path defaults to "/" if not explicitly set
        effective_spa_path = spa_path if spa_path is not None else "/"
        include_root = self._config.include_root_spa_paths

        # Build route paths
        if effective_spa_path and effective_spa_path != "/":
            base = effective_spa_path.rstrip("/")
            paths: list[str] = [f"{base}/", f"{base}/{{path:path}}"]
            # Optionally also serve at root (for Angular --base-href /web/ with root access)
            if include_root:
                paths.extend(["/", "/{path:path}"])
        else:
            paths = ["/", "/{path:path}"]

        # Build asset_url prefix for exclusion check
        # Needed when:
        # 1. spa_path="/" but asset_url="/web/" (default case with custom asset_url)
        # 2. spa_path="/web/" with include_root_spa_paths=True (root paths need to exclude /web/)
        needs_exclusion = asset_url and asset_url != "/" and (effective_spa_path == "/" or include_root)
        asset_prefix = asset_url.rstrip("/") if needs_exclusion else None
        if asset_prefix:
            opt["_vite_asset_prefix"] = asset_prefix

        if is_dev:
            return get(path=paths, name="vite_spa", opt=opt, include_in_schema=False, guards=guards)(_spa_handler_dev)

        # Production mode: serve cached bytes with cache headers
        return get(path=paths, name="vite_spa", opt=opt, include_in_schema=False, cache=3600, guards=guards)(
            _spa_handler_prod
        )
