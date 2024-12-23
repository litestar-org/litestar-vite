from __future__ import annotations

from typing import TYPE_CHECKING

from anyio.from_thread import BlockingPortalProvider
from litestar.plugins import InitPluginProtocol

if TYPE_CHECKING:
    from litestar import Litestar
    from litestar.config.app import AppConfig

    from litestar_vite.inertia.config import InertiaConfig


def set_js_routes(app: Litestar) -> None:
    """Generate the route structure of the application on startup."""
    from litestar_vite.inertia.routes import generate_js_routes

    js_routes = generate_js_routes(app)
    app.state.js_routes = js_routes


class InertiaPlugin(InitPluginProtocol):
    """Inertia plugin."""

    __slots__ = ("config", "portal")

    def __init__(self, config: InertiaConfig) -> None:
        """Initialize ``Inertia``.

        Args:
            config: Inertia configuration.
        """
        self.config = config

        self.portal = BlockingPortalProvider()

    def get_portal(self) -> BlockingPortalProvider:
        return self.portal

    def on_app_init(self, app_config: AppConfig) -> AppConfig:
        """Configure application for use with Vite.

        Args:
            app_config: The :class:`AppConfig <litestar.config.app.AppConfig>` instance.
        """

        from litestar.exceptions import ImproperlyConfiguredException
        from litestar.middleware import DefineMiddleware
        from litestar.middleware.session import SessionMiddleware
        from litestar.security.session_auth.middleware import MiddlewareWrapper
        from litestar.utils.predicates import is_class_and_subclass

        from litestar_vite.inertia.exception_handler import exception_to_http_response
        from litestar_vite.inertia.middleware import InertiaMiddleware
        from litestar_vite.inertia.request import InertiaRequest
        from litestar_vite.inertia.response import DeferredProp, InertiaBack, InertiaResponse, StaticProp

        for mw in app_config.middleware:
            if isinstance(mw, DefineMiddleware) and is_class_and_subclass(
                mw.middleware,
                (MiddlewareWrapper, SessionMiddleware),
            ):
                break
        else:
            msg = "The Inertia plugin require a session middleware."
            raise ImproperlyConfiguredException(msg)
        app_config.exception_handlers.update({Exception: exception_to_http_response})  # pyright: ignore[reportUnknownMemberType]
        app_config.request_class = InertiaRequest
        app_config.response_class = InertiaResponse
        app_config.middleware.append(InertiaMiddleware)
        app_config.on_startup.append(set_js_routes)
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
        return app_config
