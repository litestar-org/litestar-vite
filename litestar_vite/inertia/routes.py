from __future__ import annotations

from dataclasses import dataclass
from functools import cached_property
from typing import TYPE_CHECKING

from litestar.app import DEFAULT_OPENAPI_CONFIG
from litestar.cli._utils import (
    remove_default_schema_routes,
    remove_routes_with_patterns,
)
from litestar.routes import ASGIRoute, WebSocketRoute
from litestar.serialization import encode_json

if TYPE_CHECKING:
    from litestar import Litestar


@dataclass(frozen=True)
class Routes:
    routes: dict[str, str]

    @cached_property
    def formatted_routes(self) -> str:
        return encode_json(self.routes).decode(encoding="utf-8")


EXCLUDED_METHODS = {"HEAD", "OPTIONS", "TRACE"}


def generate_js_routes(
    app: Litestar,
    exclude: tuple[str, ...] | None = None,
    schema: bool = False,
) -> Routes:
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

    return Routes(routes=route_list)
