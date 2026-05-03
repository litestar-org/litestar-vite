import functools
import inspect
from collections.abc import Mapping
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING, Any, cast

import httpx
from litestar.handlers.http_handlers.base import HTTPRouteHandler
from litestar.plugins import InitPluginProtocol
from litestar.response import Response

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

    from litestar import Litestar, Request
    from litestar.config.app import AppConfig

    from litestar_vite.config import InertiaConfig


class InertiaPlugin(InitPluginProtocol):
    """Inertia plugin.

    This plugin configures Litestar for Inertia.js support, including:
    - Session middleware requirement validation
    - Exception handler for Inertia responses
    - InertiaRequest and InertiaResponse as default classes
    - Type encoders for StaticProp and DeferredProp

    Async Prop Resolution:
        Async ``optional()``/``defer()``/``lazy()``/``once()`` callbacks are
        pre-resolved by ``InertiaResponse`` on the request event loop before
        the body is serialized. This guarantees they share the loop with
        request-scoped async resources (asyncpg/aiosqlite/sqlspec sessions),
        so callbacks can safely use those resources.

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

    __slots__ = ("_ssr_client", "config")

    def __init__(self, config: "InertiaConfig") -> "None":
        """Initialize the plugin with Inertia configuration."""
        self.config = config
        self._ssr_client: "httpx.AsyncClient | None" = None

    @asynccontextmanager
    async def lifespan(self, app: "Litestar") -> "AsyncGenerator[None, None]":
        """Lifespan to manage the shared SSR HTTP client.

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
            yield
        finally:
            await self._ssr_client.aclose()
            self._ssr_client = None  # Reset to signal client is closed

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

        if app_config.response_class is InertiaResponse:
            return app_config

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
        # Type encoders for prop resolution. Async DeferredProp callbacks are
        # pre-resolved on the request loop by InertiaResponse before the encoder
        # ever runs, so render() short-circuits at the cached _result.
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

        # Wrap every HTTP route handler at app startup so async Inertia prop
        # callbacks resolve inside Litestar's _call_handler_function
        # AsyncExitStack frame (where DI-scoped resources are still alive).
        # Runs at startup (NOT on_app_init) because the layered handler
        # objects are only fully resolved with runtime attributes
        # (has_sync_callable, signature_model, etc.) after route registration
        # completes.
        app_config.on_startup.append(_wrap_app_handlers)  # pyright: ignore[reportUnknownMemberType]

        return app_config


def _request_from_context(kwargs: "dict[str, Any]") -> "Request[Any, Any, Any] | None":
    request = kwargs.get("request")
    if request is not None:
        return cast("Request[Any, Any, Any]", request)

    from litestar_vite.inertia.middleware import get_current_inertia_request

    return get_current_inertia_request()


async def _resolve_inertia_response_data(data: "Any", request: "Request[Any, Any, Any]") -> "Any":
    from litestar_vite.inertia.response import InertiaResponse

    if isinstance(data, InertiaResponse):
        await data.resolve_async_props(request)
        return cast("Any", data)
    if isinstance(data, Response):
        return cast("Any", data)

    if isinstance(data, Mapping) or data is None:
        response: InertiaResponse[Any] = InertiaResponse(content=cast("Any", data))
        await response.resolve_async_props(request)
        return cast("Any", response)

    return data


def _wrap_handler_fn(handler: "HTTPRouteHandler") -> None:
    """Wrap ``handler.fn`` so async Inertia prop callbacks resolve inside the
    DI ``AsyncExitStack`` frame.

    Litestar resolves layered ``after_request`` hooks by keeping only
    ``after_request_handlers[-1]`` (see ``litestar/handlers/http_handlers/base.py``),
    so a plugin-registered hook can be silently dropped by any user-defined
    ``after_request`` at router/controller/handler level. Wrapping ``fn`` directly
    sidesteps that — the wrapper IS the handler, and runs inside the
    ``async with stack:`` block in ``_call_handler_function`` where
    yield-based dependencies are still alive.
    """
    if getattr(handler.fn, "_inertia_wrapped", False):  # idempotent guard
        return

    original = handler.fn

    @functools.wraps(original)  # pyright: ignore[reportUnknownArgumentType]
    async def wrapped(**kwargs: "Any") -> "Any":
        result = original(**kwargs)
        if inspect.isawaitable(result):
            result = await result

        request = _request_from_context(kwargs)
        if request is None:
            return result

        return await _resolve_inertia_response_data(result, request)

    wrapped._inertia_wrapped = True  # type: ignore[attr-defined]  # pyright: ignore[reportFunctionMemberAccess]
    # ``handler.fn`` is a property; the backing attribute is ``_fn``.
    handler._fn = wrapped  # pyright: ignore[reportPrivateUsage]
    handler.has_sync_callable = False


def _wrap_app_handlers(app: "Litestar") -> None:
    """Idempotently wrap every HTTP route handler on the live app.

    Run after Litestar's full route registration so dynamically-attached
    handlers (controllers instantiated late, plugins, etc.) are also wrapped.
    """
    for route in app.routes:
        for handler in getattr(route, "route_handlers", ()):
            if isinstance(handler, HTTPRouteHandler):
                _wrap_handler_fn(handler)
