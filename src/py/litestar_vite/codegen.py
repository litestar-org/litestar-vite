"""Public code generation API.

The internal implementation lives in ``litestar_vite._codegen``.

This module provides a stable import surface for:

- Route metadata export (``routes.json`` + Ziggy-compatible TS)
- Inertia page props metadata export
"""

from litestar_vite._codegen.inertia import (  # noqa: F401
    InertiaPageMetadata,
    _get_openapi_schema_ref,  # pyright: ignore[reportPrivateUsage,reportUnusedImport]
    _get_return_type_name,  # pyright: ignore[reportPrivateUsage,reportUnusedImport]
    extract_inertia_pages,
    generate_inertia_pages_json,
)
from litestar_vite._codegen.routes import (  # noqa: F401
    RouteMetadata,
    _escape_ts_string,  # pyright: ignore[reportPrivateUsage,reportUnusedImport]
    _is_type_required,  # pyright: ignore[reportPrivateUsage,reportUnusedImport]
    _ts_type_for_param,  # pyright: ignore[reportPrivateUsage,reportUnusedImport]
    extract_route_metadata,
    generate_routes_json,
    generate_routes_ts,
)
from litestar_vite._codegen.ts import (
    ts_type_from_openapi as _ts_type_from_openapi,  # noqa: F401  # pyright: ignore[reportUnusedImport]
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
