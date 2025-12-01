"""SPA mode handler for Vite integration.

This module provides the ViteSPAHandler class that manages serving
the Single Page Application (SPA) HTML in both development and production modes.

In dev mode, it proxies requests to the Vite dev server for HMR support.
In production, it serves the built index.html with async caching.

HTML transformations are applied based on SPAConfig settings:
- Route metadata injection (window.__LITESTAR_ROUTES__)
- Page data injection for Inertia.js (data-page attribute)
"""

from contextlib import suppress
from typing import TYPE_CHECKING, Any

import anyio
import httpx
import msgspec
from litestar import Response, get
from litestar.exceptions import ImproperlyConfiguredException

from litestar_vite.html_transform import HtmlTransformer

if TYPE_CHECKING:
    from litestar.connection import Request

    from litestar_vite.config import SPAConfig, ViteConfig

# Pre-encoded content type header for production responses
_HTML_MEDIA_TYPE = "text/html; charset=utf-8"


class ViteSPAHandler:
    """Handler for serving SPA HTML in both dev and production modes.

    This handler manages the serving of the index.html file for SPAs.
    It supports:
    - Development mode: Proxies to Vite dev server for HMR
    - Production mode: Serves built index.html with caching
    - Route metadata injection: Injects route info for client-side routing
    - Page data injection: Injects Inertia.js page props as data attributes

    Performance optimizations:
    - Production: HTML cached as bytes at startup, zero per-request allocation
    - Development: Reuses httpx.AsyncClient for connection pooling
    - Transformed HTML cached in production to avoid repeated transformations
    - Uses __slots__ for reduced memory footprint

    Attributes:
        config: The Vite configuration.

    Example:
        handler = ViteSPAHandler(config)
        await handler.initialize()
        html = await handler.get_html(request)

        # With route metadata injection
        handler.set_routes_metadata({"home": {"uri": "/", "methods": ["GET"]}})
        html = await handler.get_html(request)  # Includes window.__LITESTAR_ROUTES__

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
        "_routes_metadata",
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
        self._routes_metadata: "dict[str, Any] | None" = None
        self._initialized = False
        self._http_client: "httpx.AsyncClient | None" = None
        self._http_client_sync: "httpx.Client | None" = None
        self._vite_url: "str | None" = None

    @property
    def is_initialized(self) -> bool:
        """Whether the handler has been initialized."""
        return self._initialized

    async def initialize(self, vite_url: "str | None" = None) -> None:
        """Initialize the handler.

        This method should be called during app startup to:
        - Initialize the HTTP client for dev mode proxying
        - Load and cache the index.html in production mode

        Args:
            vite_url: Optional Vite server URL to use for proxying. If provided,
                     this takes precedence over hotfile resolution. This is typically
                     passed by VitePlugin which knows the correct URL.
        """
        if self._initialized:
            return

        if self._config.is_dev_mode and self._config.hot_reload:
            # Use provided URL if available (from VitePlugin), otherwise resolve from hotfile
            # The VitePlugin knows the correct URL because it selects the port
            self._vite_url = vite_url or self._resolve_vite_url()

            # Create HTTP client for proxying to Vite server
            # Uses connection pooling for efficient reuse
            # HTTP/2 is controlled by config and requires the h2 package
            http2_enabled = self._config.http2
            if http2_enabled:
                try:
                    import h2  # noqa: F401  # pyright: ignore[reportMissingImports,reportUnusedImport]
                except ImportError:
                    http2_enabled = False

            self._http_client = httpx.AsyncClient(
                timeout=httpx.Timeout(5.0),
                http2=http2_enabled,
            )
            # Also create a synchronous client for use in sync contexts (e.g., Inertia response)
            self._http_client_sync = httpx.Client(
                timeout=httpx.Timeout(5.0),
            )
        else:
            # Load and cache index.html for production
            await self._load_index_html()

        self._initialized = True

    async def shutdown(self) -> None:
        """Shutdown the handler.

        Closes the HTTP clients if they were created for dev mode.
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

    def set_routes_metadata(self, routes: dict[str, Any]) -> None:
        """Set route metadata for injection into HTML.

        This method stores route metadata that will be injected as a global
        JavaScript variable (e.g., window.__LITESTAR_ROUTES__) when get_html()
        is called with a configured SPAConfig.

        Args:
            routes: Route metadata dictionary from generate_routes_json().
                    Expected format: {"routes": {"name": {"uri": "/path", "methods": [...]}}}

        Note:
            Calling this method invalidates any cached transformed HTML,
            ensuring the next request gets fresh content with updated routes.
        """
        self._routes_metadata = routes
        # Invalidate cached transformed HTML when routes change
        self._cached_transformed_html = None

    def _transform_html(
        self,
        html: str,
        page_data: "dict[str, Any] | None" = None,
        csrf_token: "str | None" = None,
    ) -> str:
        """Transform HTML by injecting route metadata, CSRF token, and/or page data.

        This method applies transformations based on SPAConfig settings:
        - Injects route metadata as a global JavaScript variable
        - Injects CSRF token as a global JavaScript variable
        - Injects page data as a data attribute on the app element

        Uses msgspec for fast JSON serialization.

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
                json_data = msgspec.json.encode(page_data).decode("utf-8")
                html = HtmlTransformer.set_data_attribute(html, "#app", "data-page", json_data)
            return html

        # Inject route metadata if configured
        if self._spa_config.inject_routes and self._routes_metadata is not None:
            html = HtmlTransformer.inject_json_script(
                html,
                self._spa_config.routes_var_name,
                self._routes_metadata,
            )

        # Inject CSRF token if configured
        if self._spa_config.inject_csrf and csrf_token:
            # Inject as a simple string assignment (not JSON object)
            script = f'window.{self._spa_config.csrf_var_name} = "{csrf_token}";'
            html = HtmlTransformer.inject_head_script(html, script, escape=False)

        # Inject page data as data-page attribute if provided
        if page_data is not None:
            json_data = msgspec.json.encode(page_data).decode("utf-8")
            html = HtmlTransformer.set_data_attribute(
                html,
                self._spa_config.app_selector,
                "data-page",
                json_data,
            )

        return html

    async def _load_index_html(self) -> None:
        """Load index.html from disk and cache it in memory.

        Caches both string and bytes representations to avoid
        encoding overhead on each request.

        Raises:
            ImproperlyConfiguredException: If index.html is not found.
        """
        resolved_path: anyio.Path | None = None
        for candidate in self._config.candidate_index_html_paths():
            candidate_path = anyio.Path(candidate)
            if await candidate_path.exists():
                resolved_path = candidate_path
                break

        if resolved_path is None:
            joined_paths = ", ".join(str(path) for path in self._config.candidate_index_html_paths())
            msg = (
                "index.html not found. "
                f"Checked: {joined_paths}. "
                "SPA mode requires index.html in one of the expected locations. "
                "Did you forget to build your assets?"
            )
            raise ImproperlyConfiguredException(msg)

        # Read as bytes first (more efficient), then decode
        self._cached_bytes = await resolved_path.read_bytes()
        self._cached_html = self._cached_bytes.decode("utf-8")

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

    async def get_html(
        self,
        request: "Request[Any, Any, Any]",
        *,
        page_data: "dict[str, Any] | None" = None,
    ) -> str:
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
            msg = "ViteSPAHandler not initialized. Call initialize() during app startup."
            raise ImproperlyConfiguredException(msg)

        # Check if transformations are needed
        needs_transform = self._spa_config is not None or page_data is not None

        # Check if CSRF injection is enabled (per-request, cannot cache)
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
            await self._load_index_html()

        base_html = self._cached_html or ""

        # If no transformations needed, return raw cached HTML
        if not needs_transform:
            return base_html

        # If page_data is provided OR csrf is needed, we can't use cached transformed HTML
        # since these vary per request
        if page_data is not None or csrf_token is not None:
            return self._transform_html(base_html, page_data, csrf_token)

        # Check if we can use cached transformed HTML (routes only, no page_data, no csrf)
        if self._spa_config is not None and self._spa_config.cache_transformed_html:
            if self._cached_transformed_html is not None:
                return self._cached_transformed_html
            # Transform and cache (routes only)
            self._cached_transformed_html = self._transform_html(base_html, None, None)
            return self._cached_transformed_html

        # Caching disabled, transform fresh
        return self._transform_html(base_html, None, None)

    def get_html_sync(
        self,
        *,
        page_data: "dict[str, Any] | None" = None,
        csrf_token: "str | None" = None,
    ) -> str:
        """Get the HTML for the SPA synchronously.

        This method is for use in synchronous contexts where async is not
        available (e.g., Litestar's Response.to_asgi_response).

        In dev mode, uses a synchronous HTTP client to fetch from Vite.
        In production mode, uses cached HTML.

        Note:
            CSRF token injection requires passing the token explicitly since
            this method doesn't have access to the request scope.

        Args:
            page_data: Optional page data to inject as data-page attribute.
            csrf_token: Optional CSRF token to inject.

        Returns:
            The HTML content as a string, optionally transformed.

        Raises:
            ImproperlyConfiguredException: If not initialized or no cached HTML.
        """
        if not self._initialized:
            msg = "ViteSPAHandler not initialized. Call initialize() during app startup."
            raise ImproperlyConfiguredException(msg)

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

        # Check if transformations are needed
        needs_transform = self._spa_config is not None or page_data is not None

        if not needs_transform:
            return base_html

        # If page_data is provided OR csrf is needed, we can't use cached transformed HTML
        if page_data is not None or csrf_token is not None:
            return self._transform_html(base_html, page_data, csrf_token)

        # Check if we can use cached transformed HTML (routes only)
        if self._spa_config is not None and self._spa_config.cache_transformed_html:
            if self._cached_transformed_html is None:
                # Transform and cache (routes only)
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
            await self.initialize()

        if self._cached_bytes is None:
            await self._load_index_html()

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
            msg = "Vite URL not resolved. Ensure initialize() was called."
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
            msg = "Vite URL not resolved. Ensure initialize() was called."
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

        Returns:
            A Litestar route handler that serves the SPA HTML.

        Example:
            handler = ViteSPAHandler(config)
            spa_route = handler.create_route_handler()
            # Add spa_route to your Litestar app routes
        """
        # Capture references for the closure (avoids self lookup in hot path)
        get_html = self.get_html
        get_bytes = self.get_bytes
        is_dev = self._config.is_dev_mode and self._config.hot_reload

        if is_dev:
            # Dev mode: proxy to Vite, no caching
            @get(
                path=["/", "/{path:path}"],
                name="vite_spa",
                opt={"exclude_from_auth": True},
                include_in_schema=False,
            )
            async def spa_handler_dev(request: "Request[Any, Any, Any]") -> Response[str]:
                """Serve the SPA HTML (dev mode - proxied from Vite)."""
                html = await get_html(request)
                return Response(
                    content=html,
                    status_code=200,
                    media_type="text/html",
                )

            return spa_handler_dev

        # Production mode: serve cached bytes with cache headers
        @get(
            path=["/", "/{path:path}"],
            name="vite_spa",
            opt={"exclude_from_auth": True},
            include_in_schema=False,
            cache=3600,  # Cache for 1 hour
        )
        async def spa_handler_prod(request: "Request[Any, Any, Any]") -> Response[bytes]:
            """Serve the SPA HTML (production - cached)."""
            content = await get_bytes()
            return Response(content=content, status_code=200, media_type=_HTML_MEDIA_TYPE)

        return spa_handler_prod
