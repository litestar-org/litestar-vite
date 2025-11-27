"""SPA mode handler for Vite integration.

This module provides the ViteSPAHandler class that manages serving
the Single Page Application (SPA) HTML in both development and production modes.

In dev mode, it proxies requests to the Vite dev server for HMR support.
In production, it serves the built index.html with async caching.
"""

from typing import TYPE_CHECKING, Any, Optional

import anyio
import httpx
from litestar import Response, get
from litestar.exceptions import ImproperlyConfiguredException

if TYPE_CHECKING:
    from litestar.connection import Request

    from litestar_vite.config import ViteConfig


class ViteSPAHandler:
    """Handler for serving SPA HTML in both dev and production modes.

    This handler manages the serving of the index.html file for SPAs.
    It supports:
    - Development mode: Proxies to Vite dev server for HMR
    - Production mode: Serves built index.html with caching

    Attributes:
        config: The Vite configuration.

    Example:
        handler = ViteSPAHandler(config)
        await handler.initialize()
        html = await handler.get_html(request)
    """

    __slots__ = ("_cached_html", "_config", "_http_client", "_initialized")

    def __init__(self, config: "ViteConfig") -> None:
        """Initialize the SPA handler.

        Args:
            config: The Vite configuration.
        """
        self._config = config
        self._cached_html: Optional[str] = None
        self._initialized = False
        self._http_client: Optional[httpx.AsyncClient] = None

    async def initialize(self) -> None:
        """Initialize the handler.

        This method should be called during app startup to:
        - Initialize the HTTP client for dev mode proxying
        - Load and cache the index.html in production mode
        """
        if self._initialized:
            return

        if self._config.is_dev_mode and self._config.hot_reload:
            # Create HTTP client for proxying to Vite dev server
            self._http_client = httpx.AsyncClient(
                base_url=f"{self._config.protocol}://{self._config.host}:{self._config.port}",
                timeout=httpx.Timeout(5.0),
            )
        else:
            # Load and cache index.html for production
            await self._load_index_html()

        self._initialized = True

    async def shutdown(self) -> None:
        """Shutdown the handler.

        Closes the HTTP client if it was created for dev mode.
        """
        if self._http_client is not None:
            await self._http_client.aclose()
            self._http_client = None

    async def _load_index_html(self) -> None:
        """Load index.html from disk and cache it in memory.

        Raises:
            ImproperlyConfiguredException: If index.html is not found.
        """
        index_path = anyio.Path(self._config.resource_dir / "index.html")
        if not await index_path.exists():
            msg = (
                f"index.html not found at {index_path}. "
                "SPA mode requires index.html in the resource directory. "
                "Did you forget to build your assets?"
            )
            raise ImproperlyConfiguredException(msg)

        self._cached_html = await index_path.read_text(encoding="utf-8")

    async def get_html(self, request: "Request[Any, Any, Any]") -> str:
        """Get the HTML for the SPA.

        In dev mode, proxies the request to the Vite dev server.
        In production mode, returns the cached index.html.

        Args:
            request: The incoming request.

        Returns:
            The HTML content as a string.

        Raises:
            ImproperlyConfiguredException: If the handler is not initialized.
            httpx.HTTPError: If the dev server proxy fails.
        """
        if not self._initialized:
            msg = "ViteSPAHandler not initialized. Call initialize() during app startup."
            raise ImproperlyConfiguredException(msg)

        if self._config.is_dev_mode and self._config.hot_reload:
            return await self._proxy_to_dev_server(request)

        # Production mode - return cached HTML
        if self._cached_html is None:
            # Fallback: try to load now if not cached
            await self._load_index_html()

        return self._cached_html or ""

    async def _proxy_to_dev_server(self, request: "Request[Any, Any, Any]") -> str:
        """Proxy the request to the Vite dev server.

        Args:
            request: The incoming request.

        Returns:
            The HTML content from the Vite dev server.

        Raises:
            httpx.HTTPError: If the request to the dev server fails.
        """
        if self._http_client is None:
            msg = "HTTP client not initialized for dev mode."
            raise ImproperlyConfiguredException(msg)

        try:
            # Request the root path from Vite dev server
            response = await self._http_client.get("/", follow_redirects=True)
            response.raise_for_status()
        except httpx.HTTPError as e:
            msg = (
                f"Failed to proxy request to Vite dev server at "
                f"{self._config.protocol}://{self._config.host}:{self._config.port}. "
                f"Is the dev server running? Error: {e!s}"
            )
            raise ImproperlyConfiguredException(msg) from e
        else:
            return response.text

    def create_route_handler(self) -> Any:
        """Create a Litestar route handler for the SPA.

        Returns:
            A Litestar route handler that serves the SPA HTML.

        Example:
            handler = ViteSPAHandler(config)
            spa_route = handler.create_route_handler()
            # Add spa_route to your Litestar app routes
        """

        @get(
            path=["/", "/{path:path}"],
            name="vite_spa",
            opt={"exclude_from_auth": True},
            include_in_schema=False,
        )
        async def spa_handler(request: "Request[Any, Any, Any]") -> Response[str]:
            """Serve the SPA HTML."""
            html = await self.get_html(request)
            return Response(
                content=html,
                status_code=200,
                media_type="text/html",
            )

        return spa_handler
