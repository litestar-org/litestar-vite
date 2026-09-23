"""Public code generation API.

This package provides code generation utilities for:

- Unified asset export (``export_integration_assets``)
- Route metadata export (``routes.json`` + Ziggy-compatible TS)
- Inertia page props metadata export

Internal implementation details (OpenAPI integration, TypeScript conversion)
are kept in private submodules to keep the public API clean.
"""

from litestar_vite.codegen._asyncapi import (
    ASYNCAPI_PAYLOAD_OPT_KEY,
    AsyncAPIChannel,
    AsyncAPIComponents,
    AsyncAPIDocument,
    AsyncAPIInfo,
    AsyncAPIMessage,
    AsyncAPIOperation,
    AsyncAPIParameter,
    AsyncAPIServer,
    create_asyncapi_document,
    extract_channels_plugin_channels,
    extract_payload_schema,
    extract_realtime_channels,
    extract_sse_routes,
    extract_websocket_routes,
)
from litestar_vite.codegen._export import (
    ExportResult,
    export_asyncapi,
    export_integration_assets,
    typegen_outputs_requested,
)
from litestar_vite.codegen._inertia import InertiaPageMetadata, extract_inertia_pages, generate_inertia_pages_json
from litestar_vite.codegen._routes import (
    RouteMetadata,
    extract_route_metadata,
    generate_routes_json,
    generate_routes_ts,
)
from litestar_vite.codegen._utils import encode_deterministic_json, strip_timestamp_for_comparison, write_if_changed

__all__ = (
    "ASYNCAPI_PAYLOAD_OPT_KEY",
    "AsyncAPIChannel",
    "AsyncAPIComponents",
    "AsyncAPIDocument",
    "AsyncAPIInfo",
    "AsyncAPIMessage",
    "AsyncAPIOperation",
    "AsyncAPIParameter",
    "AsyncAPIServer",
    "ExportResult",
    "InertiaPageMetadata",
    "RouteMetadata",
    "create_asyncapi_document",
    "encode_deterministic_json",
    "export_asyncapi",
    "export_integration_assets",
    "extract_channels_plugin_channels",
    "extract_inertia_pages",
    "extract_payload_schema",
    "extract_realtime_channels",
    "extract_route_metadata",
    "extract_sse_routes",
    "extract_websocket_routes",
    "generate_inertia_pages_json",
    "generate_routes_json",
    "generate_routes_ts",
    "strip_timestamp_for_comparison",
    "typegen_outputs_requested",
    "write_if_changed",
)
