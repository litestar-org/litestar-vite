from contextlib import asynccontextmanager
from typing import TYPE_CHECKING

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

    Example::

        from litestar_vite.inertia import InertiaPlugin, InertiaConfig

        app = Litestar(
            plugins=[InertiaPlugin(InertiaConfig())],
            middleware=[ServerSideSessionConfig().middleware],
        )
    """

    __slots__ = ("_portal", "config")

    def __init__(self, config: "InertiaConfig") -> "None":
        """Initialize the plugin with Inertia configuration."""
        self.config = config

    @asynccontextmanager
    async def lifespan(self, app: "Litestar") -> "AsyncGenerator[None, None]":
        """Lifespan to ensure the event loop is available.

        Args:
            app: The :class:`Litestar <litestar.app.Litestar>` instance.

        Yields:
            An asynchronous context manager.
        """

        with start_blocking_portal() as portal:
            self._portal = portal
            yield

    @property
    def portal(self) -> "BlockingPortal":
        """Return the blocking portal used for deferred prop resolution.

        Returns:
            The BlockingPortal instance.
        """
        return self._portal

    def on_app_init(self, app_config: "AppConfig") -> "AppConfig":
        """Configure application for use with Vite.

        Args:
            app_config: The :class:`AppConfig <litestar.config.app.AppConfig>` instance.

        Raises:
            ImproperlyConfiguredException: If the Inertia plugin is not properly configured.

        Returns:
            The :class:`AppConfig <litestar.config.app.AppConfig>` instance.
        """

        from litestar.exceptions import ImproperlyConfiguredException
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
        from litestar.exceptions import HTTPException

        app_config.exception_handlers.update(  # pyright: ignore[reportUnknownMemberType]
            {Exception: exception_to_http_response, HTTPException: exception_to_http_response}
        )
        app_config.request_class = InertiaRequest
        app_config.response_class = InertiaResponse
        app_config.middleware.append(InertiaMiddleware)
        app_config.signature_types.extend([InertiaRequest, InertiaResponse, InertiaBack, StaticProp, DeferredProp])
        app_config.type_encoders = {
            StaticProp: lambda val: val.render(),
            DeferredProp: lambda val: val.render(),
            **(app_config.type_encoders or {}),
        }
        app_config.type_decoders = [
            (lambda x: x is StaticProp, lambda t, v: t(v)),
            (lambda x: x is DeferredProp, lambda t, v: t(v)),
            *(app_config.type_decoders or []),
        ]
        app_config.lifespan.append(self.lifespan)  # pyright: ignore[reportUnknownMemberType]
        return app_config
