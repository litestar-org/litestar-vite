"""Internal code generation implementation.

This package contains the implementation behind the public functions exposed via
``litestar_vite.codegen``.

We keep Litestar private OpenAPI integration and TypeScript conversion details
isolated here to make the public module easier to navigate and maintain.
"""

from litestar_vite._codegen.inertia import InertiaPageMetadata, extract_inertia_pages, generate_inertia_pages_json
from litestar_vite._codegen.routes import (
    RouteMetadata,
    extract_route_metadata,
    generate_routes_json,
    generate_routes_ts,
)

__all__ = (
    "InertiaPageMetadata",
    "RouteMetadata",
    "extract_inertia_pages",
    "extract_route_metadata",
    "generate_inertia_pages_json",
    "generate_routes_json",
    "generate_routes_ts",
)
