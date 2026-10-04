"""SPA route handlers and routing helpers."""

from contextlib import suppress
from typing import TYPE_CHECKING, Any, cast

from litestar import Response
from litestar.exceptions import ImproperlyConfiguredException, NotFoundException

from litestar_vite.loader import EarlyHintsASGIResponse
from litestar_vite.plugin import is_litestar_route

if TYPE_CHECKING:
    from litestar.connection import Request
    from litestar.response.base import ASGIResponse

    from litestar_vite.handler._app import AppHandler


_HTML_MEDIA_TYPE = "text/html; charset=utf-8"


class _PreloadHTMLResponse(Response[bytes]):
    """HTML response that optionally emits ASGI 103 Early Hints before 200 OK."""

    __slots__ = ("_early_hints", "_preload_headers")

    def __init__(
        self,
        content: bytes,
        *,
        preload_headers: list[str],
        early_hints: bool,
        **kwargs: Any,
    ) -> None:
        super().__init__(content=content, **kwargs)
        self._preload_headers = preload_headers
        self._early_hints = early_hints

    def to_asgi_response(self, app: Any, request: "Request[Any, Any, Any]", **kwargs: Any) -> "ASGIResponse":
        asgi_response = super().to_asgi_response(app, request, **kwargs)  # pyright: ignore[reportUnknownMemberType]
        if self._early_hints and self._preload_headers:
            return cast("ASGIResponse", EarlyHintsASGIResponse(asgi_response, self._preload_headers))
        return asgi_response



def is_static_asset_path(request_path: str, asset_prefix: str | None) -> bool:
    """Check if a request path targets static assets rather than SPA routes.

    Args:
        request_path: Incoming request path.
        asset_prefix: Normalized asset URL prefix (e.g., ``/static``) or None.

    Returns:
        True when ``request_path`` matches the asset prefix (or a descendant path), otherwise False.
    """
    if not asset_prefix:
        return False
    return request_path == asset_prefix or request_path.startswith(f"{asset_prefix}/")


def get_route_opt(request: "Request[Any, Any, Any]") -> "dict[str, Any] | None":
    """Return the current route handler opt dict when available.

    Returns:
        The route handler ``opt`` mapping, or None if unavailable.
    """
    route_handler = request.scope.get("route_handler")  # pyright: ignore[reportUnknownMemberType]
    with suppress(AttributeError):
        opt_any = cast("Any", route_handler).opt
        return cast("dict[str, Any] | None", opt_any)
    return None  # pragma: no cover


def get_route_asset_prefix(request: "Request[Any, Any, Any]", opt: "dict[str, Any] | None" = None) -> str | None:
    """Get the static asset prefix for the current SPA route handler.

    Returns:
        The asset URL prefix for this SPA route, or None if not configured.
    """
    if opt is None:
        opt = get_route_opt(request)
    if opt is None:
        return None
    asset_prefix = opt.get("_vite_asset_prefix")
    if isinstance(asset_prefix, str) and asset_prefix:
        return asset_prefix
    return None


def get_spa_handler_from_request(
    request: "Request[Any, Any, Any]", opt: "dict[str, Any] | None" = None
) -> "AppHandler":
    """Resolve the SPA handler instance for the current request.

    This is stored on the SPA route handler's ``opt`` when the route is created.

    Args:
        request: Incoming request.
        opt: Optional pre-resolved route handler opt mapping.

    Returns:
        The configured SPA handler instance.

    Raises:
        ImproperlyConfiguredException: If the SPA handler is not available on the route metadata.
    """
    from litestar_vite.handler._app import AppHandler

    if opt is None:
        opt = get_route_opt(request)
    handler = opt.get("_vite_spa_handler") if opt is not None else None

    if isinstance(handler, AppHandler):
        return handler
    msg = "SPA handler is not available for this route. Ensure AppHandler.create_route_handler() was used."
    raise ImproperlyConfiguredException(msg)


def _resolve_spa_route(request: "Request[Any, Any, Any]") -> "AppHandler":
    """Reject non-SPA paths and resolve the handler for an SPA request.

    Both the dev and production handlers apply identical routing guards; only the body
    they produce differs.

    Args:
        request: Incoming request.

    Returns:
        The SPA handler configured for this route.

    Raises:
        NotFoundException: If the path matches a static asset or a Litestar route.
    """
    path = request.url.path
    opt = get_route_opt(request)
    asset_prefix = get_route_asset_prefix(request, opt=opt)
    if is_static_asset_path(path, asset_prefix):
        raise NotFoundException(detail=f"Static asset path: {path}")
    if path != "/" and is_litestar_route(path, request.app):
        raise NotFoundException(detail=f"Not an SPA route: {path}")
    return get_spa_handler_from_request(request, opt=opt)


async def spa_handler_dev(request: "Request[Any, Any, Any]") -> Response[str]:
    """Serve the SPA HTML (dev mode - proxied from Vite).

    Returns:
        The HTML response from the Vite dev server.
    """
    spa_handler = _resolve_spa_route(request)
    html = await spa_handler.get_html(request)
    return Response(content=html, status_code=200, media_type=_HTML_MEDIA_TYPE)


async def spa_handler_prod(request: "Request[Any, Any, Any]") -> Response[bytes]:
    """Serve the SPA HTML (production - cached or transformed).

    Returns:
        HTML bytes response from the cached or transformed SPA handler.
    """
    spa_handler = _resolve_spa_route(request)
    body = await spa_handler.get_bytes(request)
    preload_headers = spa_handler.get_preload_headers()
    headers: dict[str, str] | None = None
    if preload_headers and spa_handler.config.link_preload_headers:
        headers = {"Link": ", ".join(preload_headers)}
    if preload_headers and spa_handler.config.early_hints:
        return _PreloadHTMLResponse(
            content=body,
            status_code=200,
            media_type=_HTML_MEDIA_TYPE,
            headers=headers,
            preload_headers=preload_headers,
            early_hints=True,
        )
    return Response(content=body, status_code=200, media_type=_HTML_MEDIA_TYPE, headers=headers)

