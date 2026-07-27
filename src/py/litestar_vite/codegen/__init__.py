"""Public code generation API.

This package provides code generation utilities for:

- Unified asset export (``export_integration_assets``)
- Route metadata export (``routes.json`` + Ziggy-compatible TS)
- Inertia page props metadata export

Internal implementation details (OpenAPI integration, TypeScript conversion)
are kept in private submodules to keep the public API clean.
"""

from litestar_vite.codegen._export import ExportResult, export_integration_assets, typegen_outputs_requested
from litestar_vite.codegen._inertia import InertiaPageMetadata, extract_inertia_pages, generate_inertia_pages_json
from litestar_vite.codegen._routes import (
    RouteMetadata,
    extract_route_metadata,
    generate_routes_json,
    generate_routes_ts,
)
from litestar_vite.codegen._utils import encode_deterministic_json, strip_timestamp_for_comparison, write_if_changed

__all__ = (
    "ExportResult",
    "InertiaPageMetadata",
    "RouteMetadata",
    "encode_deterministic_json",
    "export_integration_assets",
    "extract_inertia_pages",
    "extract_route_metadata",
    "generate_inertia_pages_json",
    "generate_routes_json",
    "generate_routes_ts",
    "strip_timestamp_for_comparison",
    "typegen_outputs_requested",
    "write_if_changed",
)
