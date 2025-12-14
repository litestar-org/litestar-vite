"""SPA route handlers and routing helpers."""

from contextlib import suppress
from typing import TYPE_CHECKING, Any, cast

from litestar import Response
from litestar.exceptions import ImproperlyConfiguredException, NotFoundException

from litestar_vite.plugin import is_litestar_route

if TYPE_CHECKING:
    from litestar.connection import Request


_HTML_MEDIA_TYPE = "text/html; charset=utf-8"


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


def get_route_asset_prefix(request: "Request[Any, Any, Any]") -> str | None:
    """Get the static asset prefix for the current SPA route handler.

    Returns:
        The asset URL prefix for this SPA route, or None if not configured.
    """
    opt = get_route_opt(request)
    if opt is None:
        return None
    asset_prefix = opt.get("_vite_asset_prefix")
    if isinstance(asset_prefix, str) and asset_prefix:
        return asset_prefix
    return None


def get_spa_handler_from_request(request: "Request[Any, Any, Any]") -> Any:
    """Resolve the SPA handler instance for the current request.

    This is stored on the SPA route handler's ``opt`` when the route is created.

    Args:
        request: Incoming request.

    Returns:
        The configured SPA handler instance.

    Raises:
        ImproperlyConfiguredException: If the SPA handler is not available on the route metadata.
    """
    opt = get_route_opt(request)
    handler = opt.get("_vite_spa_handler") if opt is not None else None
    if handler is not None:
        try:
            _ = handler.get_html
            _ = handler.get_bytes
        except AttributeError:
            pass
        else:
            return handler
    msg = "SPA handler is not available for this route. Ensure AppHandler.create_route_handler() was used."
    raise ImproperlyConfiguredException(msg)


async def spa_handler_dev(request: "Request[Any, Any, Any]") -> Response[str]:
    """Serve the SPA HTML (dev mode - proxied from Vite).

    Checks if the request path matches a static asset or Litestar route before serving.

    Raises:
        NotFoundException: If the path matches a static asset or Litestar route.

    Returns:
        The HTML response from the Vite dev server.
    """
    path = request.url.path
    asset_prefix = get_route_asset_prefix(request)
    if is_static_asset_path(path, asset_prefix):
        raise NotFoundException(detail=f"Static asset path: {path}")
    if path != "/" and is_litestar_route(path, request.app):
        raise NotFoundException(detail=f"Not an SPA route: {path}")

    spa_handler = get_spa_handler_from_request(request)
    html = await spa_handler.get_html(request)
    return Response(content=html, status_code=200, media_type="text/html")


async def spa_handler_prod(request: "Request[Any, Any, Any]") -> Response[bytes]:
    """Serve the SPA HTML (production - cached).

    Raises:
        NotFoundException: If the path matches a static asset or Litestar route.

    Returns:
        HTML bytes response from the cached SPA handler.
    """
    path = request.url.path
    asset_prefix = get_route_asset_prefix(request)
    if is_static_asset_path(path, asset_prefix):
        raise NotFoundException(detail=f"Static asset path: {path}")
    if path != "/" and is_litestar_route(path, request.app):
        raise NotFoundException(detail=f"Not an SPA route: {path}")

    spa_handler = get_spa_handler_from_request(request)
    body = await spa_handler.get_bytes()
    return Response(content=body, status_code=200, media_type=_HTML_MEDIA_TYPE)
