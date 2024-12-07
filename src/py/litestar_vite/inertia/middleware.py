from __future__ import annotations

from typing import TYPE_CHECKING, Any

from litestar import Request
from litestar.middleware import AbstractMiddleware
from litestar.types import Receive, Scope, Send

from litestar_vite.inertia.response import InertiaRedirect
from litestar_vite.plugin import VitePlugin

if TYPE_CHECKING:
    from litestar.connection.base import (
        AuthT,
        StateT,
        UserT,
    )
    from litestar.types import ASGIApp, Receive, Scope, Send


async def redirect_on_asset_version_mismatch(request: Request[UserT, AuthT, StateT]) -> InertiaRedirect | None:
    if getattr(request, "is_inertia", None) is None:
        return None
    inertia_version = request.headers.get("X-Inertia-Version")
    if inertia_version is None:
        return None

    vite_plugin = request.app.plugins.get(VitePlugin)
    if inertia_version == vite_plugin.asset_loader.version_id:
        return None
    return InertiaRedirect(request, redirect_to=str(request.url))


class InertiaMiddleware(AbstractMiddleware):
    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)
        self.app = app

    async def __call__(
        self,
        scope: "Scope",
        receive: "Receive",
        send: "Send",
    ) -> None:
        request = Request[Any, Any, Any](scope=scope)
        redirect = await redirect_on_asset_version_mismatch(request)
        if redirect is not None:
            response = redirect.to_asgi_response(app=None, request=request)  # pyright: ignore[reportUnknownMemberType]
            await response(scope, receive, send)
        else:
            await self.app(scope, receive, send)
