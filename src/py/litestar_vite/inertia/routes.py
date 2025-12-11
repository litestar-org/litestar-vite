from typing import TYPE_CHECKING

from litestar.app import DEFAULT_OPENAPI_CONFIG
from litestar.cli._utils import (
    remove_default_schema_routes,  # pyright: ignore[reportPrivateImportUsage]
    remove_routes_with_patterns,  # pyright: ignore[reportPrivateImportUsage]
)
from litestar.routes import ASGIRoute, WebSocketRoute

if TYPE_CHECKING:
    from litestar import Litestar


EXCLUDED_METHODS = {"HEAD", "OPTIONS", "TRACE"}


def generate_js_routes(
    app: "Litestar",
    exclude: "tuple[str, ...] | None" = None,
    schema: "bool" = False,
) -> dict[str, str]:
    """Generate route mapping for client-side usage.

    Returns:
        A dictionary mapping route names to their paths.
    """
    sorted_routes = sorted(app.routes, key=lambda r: r.path)
    if not schema:
        openapi_config = app.openapi_config or DEFAULT_OPENAPI_CONFIG
        sorted_routes = remove_default_schema_routes(sorted_routes, openapi_config)
    if exclude is not None:
        sorted_routes = remove_routes_with_patterns(sorted_routes, exclude)
    route_list: dict[str, str] = {}
    for route in sorted_routes:
        if isinstance(route, (ASGIRoute, WebSocketRoute)):
            route_name = route.route_handler.name or route.route_handler.handler_name
            if len(route.methods.difference(EXCLUDED_METHODS)) > 0:
                route_list[route_name] = route.path
        else:
            for handler in route.route_handlers:
                route_name = handler.name or handler.handler_name
                if handler.http_methods.isdisjoint(EXCLUDED_METHODS):
                    route_list[route_name] = route.path

    return route_list
