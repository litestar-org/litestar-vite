from contextvars import ContextVar
from typing import TYPE_CHECKING, Any

from litestar.middleware import AbstractMiddleware
from litestar.types import Receive, Scope, Send

from litestar_vite.inertia.request import InertiaRequest
from litestar_vite.inertia.response import InertiaExternalRedirect
from litestar_vite.plugin import VitePlugin

if TYPE_CHECKING:
    from collections.abc import Iterable

    from litestar.types import ASGIApp, Receive, Scope, Send


_current_inertia_scope: ContextVar["Scope | None"] = ContextVar("current_inertia_scope", default=None)


class InertiaMiddleware(AbstractMiddleware):
    """Middleware for handling Inertia.js protocol requirements.

    This middleware:
    1. Detects version mismatches between client and server assets
    2. Returns 409 Conflict with X-Inertia-Location header when versions differ
    3. Triggers client-side hard refresh to reload the updated assets
    """

    def __init__(self, app: "ASGIApp") -> None:
        super().__init__(app)
        self.app = app

    async def __call__(self, scope: "Scope", receive: "Receive", send: "Send") -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        token = _current_inertia_scope.set(scope)
        try:
            if not _is_inertia_request(scope["headers"]):
                await self.app(scope, receive, send)
                return

            request: InertiaRequest[Any, Any, Any] = InertiaRequest(scope=scope)
            redirect = redirect_on_asset_version_mismatch(request)
            if redirect is not None:
                response = redirect.to_asgi_response(app=None, request=request)  # pyright: ignore[reportUnknownMemberType]
                await response(scope, receive, send)
            else:
                await self.app(scope, receive, send)
        finally:
            _current_inertia_scope.reset(token)


def get_current_inertia_request() -> "InertiaRequest[Any, Any, Any] | None":
    """Return the current request from the Inertia middleware context."""
    scope = _current_inertia_scope.get()
    return InertiaRequest(scope=scope) if scope is not None else None


def _is_inertia_request(scope_headers: "Iterable[tuple[bytes, bytes]]") -> bool:
    """Return ``True`` when this request explicitly identifies as an Inertia request."""
    return any(key == b"x-inertia" and value == b"true" for key, value in scope_headers)


def redirect_on_asset_version_mismatch(request: "InertiaRequest[Any, Any, Any]") -> "InertiaExternalRedirect | None":
    """Return redirect response when client and server asset versions differ.

    Returns:
        An InertiaExternalRedirect when versions differ, otherwise None.
    """
    if not request.is_inertia:
        return None

    inertia_version = request.inertia_version
    if inertia_version is None:
        return None

    vite_plugin = request.app.plugins.get(VitePlugin)
    if inertia_version == vite_plugin.asset_loader.version_id:
        return None

    return InertiaExternalRedirect(request, redirect_to=str(request.url))
