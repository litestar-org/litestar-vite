from __future__ import annotations

from typing import TYPE_CHECKING

import litestar.exceptions
from litestar.exceptions import HTTPException
from litestar.middleware import DefineMiddleware
from litestar.middleware.session import SessionMiddleware
from litestar.plugins import InitPluginProtocol
from litestar.security.session_auth.middleware import MiddlewareWrapper
from litestar.utils.predicates import is_class_and_subclass

from litestar_vite.inertia.exception_handler import default_httpexception_handler
from litestar_vite.inertia.request import InertiaRequest
from litestar_vite.inertia.response import InertiaResponse

if TYPE_CHECKING:
    from litestar.config.app import AppConfig

    from litestar_vite.inertia.config import InertiaConfig


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
            raise litestar.exceptions.ImproperlyConfiguredException(msg)
        app_config.exception_handlers = {HTTPException: default_httpexception_handler}
        app_config.request_class = InertiaRequest
        app_config.response_class = InertiaResponse
        # app_config.response_class = InertiaResponse  # noqa: ERA001
        return app_config
