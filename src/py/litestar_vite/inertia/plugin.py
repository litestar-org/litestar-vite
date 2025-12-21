from contextlib import asynccontextmanager
from typing import TYPE_CHECKING, Any

import httpx
from anyio.from_thread import start_blocking_portal
from litestar.plugins import InitPluginProtocol

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

    from anyio.from_thread import BlockingPortal
    from litestar import Litestar
    from litestar.config.app import AppConfig

    from litestar_vite.config import InertiaConfig


class InertiaPlugin(InitPluginProtocol):
    """Inertia plugin.

    This plugin configures Litestar for Inertia.js support, including:
    - Session middleware requirement validation
    - Exception handler for Inertia responses
    - InertiaRequest and InertiaResponse as default classes
    - Type encoders for StaticProp and DeferredProp

    BlockingPortal Behavior:
        The plugin creates a BlockingPortal during its lifespan for executing
        async DeferredProp callbacks from synchronous type encoders. This is
        necessary because Litestar's JSON serialization happens synchronously,
        but DeferredProp may contain async callables.

        The portal is shared across all requests during the app's lifetime.
        Type encoders for StaticProp and DeferredProp use ``val.render()``
        which may access this portal for async resolution.

        If you're using DeferredProp outside of InertiaResponse (e.g., in
        custom serialization), ensure the app lifespan is active and the
        portal is available via ``inertia_plugin.portal``.

    SSR Client Pooling:
        When SSR is enabled, the plugin maintains a shared ``httpx.AsyncClient``
        for all SSR requests. This provides significant performance benefits:
        - Connection pooling with keep-alive
        - TLS session reuse
        - HTTP/2 multiplexing (when available)

        The client is initialized during app lifespan and properly closed on shutdown.
        Access via ``inertia_plugin.ssr_client`` if needed.

    Example::

        from litestar_vite.inertia import InertiaPlugin, InertiaConfig

        app = Litestar(
            plugins=[InertiaPlugin(InertiaConfig())],
            middleware=[ServerSideSessionConfig().middleware],
        )
    """

    __slots__ = ("_portal", "_ssr_client", "config")

    def __init__(self, config: "InertiaConfig") -> "None":
        """Initialize the plugin with Inertia configuration."""
        self.config = config
        self._ssr_client: "httpx.AsyncClient | None" = None
        self._portal: "BlockingPortal | None" = None  # pyright: ignore[reportInvalidTypeForm]

    @asynccontextmanager
    async def lifespan(self, app: "Litestar") -> "AsyncGenerator[None, None]":
        """Lifespan to ensure the event loop is available.

        Initializes:
        - BlockingPortal for sync-to-async DeferredProp resolution
        - Shared httpx.AsyncClient for SSR requests (connection pooling)

        Args:
            app: The :class:`Litestar <litestar.app.Litestar>` instance.

        Yields:
            An asynchronous context manager.
        """
        # Initialize shared SSR client with connection pooling
        # These limits are tuned for typical SSR workloads:
        # - max_keepalive_connections: 10 per-host keep-alive connections
        # - max_connections: 20 total concurrent connections
        # - keepalive_expiry: 30s idle timeout before closing
        limits = httpx.Limits(max_keepalive_connections=10, max_connections=20, keepalive_expiry=30.0)
        self._ssr_client = httpx.AsyncClient(
            limits=limits,
            timeout=httpx.Timeout(10.0),  # Default timeout, can be overridden per-request
        )

        try:
            with start_blocking_portal() as portal:
                self._portal = portal
                yield
        finally:
            await self._ssr_client.aclose()
            self._ssr_client = None  # Reset to signal client is closed

    @property
    def portal(self) -> "BlockingPortal":
        """Return the blocking portal used for deferred prop resolution.

        Returns:
            The BlockingPortal instance.

        Raises:
            RuntimeError: If accessed before app lifespan is active.
        """
        if self._portal is None:
            msg = "BlockingPortal not available. Ensure app lifespan is active."
            raise RuntimeError(msg)
        return self._portal

    @property
    def ssr_client(self) -> "httpx.AsyncClient | None":
        """Return the shared httpx.AsyncClient for SSR requests.

        The client is initialized during app lifespan and provides connection
        pooling, TLS session reuse, and HTTP/2 multiplexing benefits.

        Returns:
            The shared AsyncClient instance, or None if not initialized.
        """
        return self._ssr_client

    def on_app_init(self, app_config: "AppConfig") -> "AppConfig":
        """Configure application for use with Vite.

        Args:
            app_config: The :class:`AppConfig <litestar.config.app.AppConfig>` instance.

        Raises:
            ImproperlyConfiguredException: If the Inertia plugin is not properly configured.

        Returns:
            The :class:`AppConfig <litestar.config.app.AppConfig>` instance.
        """

        from litestar.exceptions import HTTPException, ImproperlyConfiguredException, ValidationException
        from litestar.middleware import DefineMiddleware
        from litestar.middleware.session import SessionMiddleware
        from litestar.security.session_auth.middleware import MiddlewareWrapper
        from litestar.utils.predicates import is_class_and_subclass

        from litestar_vite.inertia.exception_handler import exception_to_http_response
        from litestar_vite.inertia.helpers import DeferredProp, StaticProp
        from litestar_vite.inertia.middleware import InertiaMiddleware
        from litestar_vite.inertia.request import InertiaRequest
        from litestar_vite.inertia.response import InertiaBack, InertiaResponse

        for mw in app_config.middleware:
            if isinstance(mw, DefineMiddleware) and is_class_and_subclass(
                mw.middleware, (MiddlewareWrapper, SessionMiddleware)
            ):
                break
        else:
            msg = "The Inertia plugin require a session middleware."
            raise ImproperlyConfiguredException(msg)

        # Register exception handlers
        exception_handlers: "dict[type[Exception] | int, Any]" = {
            Exception: exception_to_http_response,
            HTTPException: exception_to_http_response,
        }

        # Add Precognition exception handler when enabled
        # Note: The exception handler formats validation errors in Laravel's format.
        # For successful validation to return 204 (without executing the handler),
        # use the @precognition decorator on your route handlers.
        if self.config.precognition:
            from litestar_vite.inertia.precognition import create_precognition_exception_handler

            exception_handlers[ValidationException] = create_precognition_exception_handler(
                fallback_handler=exception_to_http_response
            )

        app_config.exception_handlers.update(exception_handlers)  # pyright: ignore[reportUnknownMemberType]
        app_config.request_class = InertiaRequest
        app_config.response_class = InertiaResponse
        app_config.middleware.append(InertiaMiddleware)
        app_config.signature_types.extend([InertiaRequest, InertiaResponse, InertiaBack, StaticProp, DeferredProp])
        # Type encoders for prop resolution
        # DeferredProp encoder passes the plugin's portal for efficient async resolution
        # This avoids creating a new BlockingPortal per DeferredProp (~5-10ms savings)
        app_config.type_encoders = {
            StaticProp: lambda val: val.render(),
            DeferredProp: lambda val: val.render(portal=getattr(self, "_portal", None)),
            **(app_config.type_encoders or {}),
        }
        app_config.type_decoders = [
            (lambda x: x is StaticProp, lambda t, v: t(v)),
            (lambda x: x is DeferredProp, lambda t, v: t(v)),
            *(app_config.type_decoders or []),
        ]
        app_config.lifespan.append(self.lifespan)  # pyright: ignore[reportUnknownMemberType]
        return app_config
