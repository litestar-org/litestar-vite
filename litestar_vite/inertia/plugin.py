from __future__ import annotations

from typing import TYPE_CHECKING

from litestar.exceptions import ImproperlyConfiguredException
from litestar.middleware import DefineMiddleware
from litestar.middleware.session import SessionMiddleware
from litestar.plugins import InitPluginProtocol
from litestar.security.session_auth.middleware import MiddlewareWrapper
from litestar.utils.predicates import is_class_and_subclass

from litestar_vite.inertia.exception_handler import exception_to_http_response
from litestar_vite.inertia.middleware import InertiaMiddleware
from litestar_vite.inertia.request import InertiaRequest
from litestar_vite.inertia.response import InertiaResponse
from litestar_vite.inertia.routes import generate_js_routes

if TYPE_CHECKING:
    from litestar import Litestar
    from litestar.config.app import AppConfig

    from litestar_vite.inertia.config import InertiaConfig


def set_js_routes(app: Litestar) -> None:
    """Generate the route structure of the application on startup."""
    js_routes = generate_js_routes(app)
    app.state.js_routes = js_routes


class InertiaPlugin(InitPluginProtocol):
    """Inertia plugin."""

    __slots__ = ("config",)

    def __init__(self, config: InertiaConfig) -> None:
        """Initialize ``Inertia``.

        Args:
            config: configure and start Vite.
        """
        self.config = config

    def on_app_init(self, app_config: AppConfig) -> AppConfig:
        """Configure application for use with Vite.

        Args:
            app_config: The :class:`AppConfig <.config.app.AppConfig>` instance.
        """
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
        return app_config
