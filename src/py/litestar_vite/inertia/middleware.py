from typing import TYPE_CHECKING, Any

from litestar.middleware import AbstractMiddleware
from litestar.types import Receive, Scope, Send

from litestar_vite.inertia.request import InertiaRequest
from litestar_vite.inertia.response import InertiaExternalRedirect
from litestar_vite.plugin import VitePlugin

if TYPE_CHECKING:
    from litestar.types import ASGIApp, Receive, Scope, Send


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
        request: InertiaRequest[Any, Any, Any] = InertiaRequest(scope=scope)
        redirect = redirect_on_asset_version_mismatch(request)
        if redirect is not None:
            response = redirect.to_asgi_response(app=None, request=request)  # pyright: ignore[reportUnknownMemberType]
            await response(scope, receive, send)
        else:
            await self.app(scope, receive, send)
