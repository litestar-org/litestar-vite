"""Unified asset export pipeline for deterministic code generation.

This module provides a single entry point for exporting all integration artifacts:
- openapi.json (OpenAPI schema with Inertia types registered)
- routes.json (route metadata)
- routes.ts (Ziggy-style typed routes)
- inertia-pages.json (Inertia page props metadata)

Both CLI and Plugin should call this function to guarantee byte-identical output.
"""

from dataclasses import dataclass, field
from functools import partial
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Callable

    from litestar import Litestar

    from litestar_vite.config import TypeGenConfig, ViteConfig


@dataclass
class ExportResult:
    """Result of the export operation."""

    exported_files: list[str] = field(default_factory=list)  # pyright: ignore[reportUnknownVariableType]
    """Files that were written (content changed)."""

    unchanged_files: list[str] = field(default_factory=list)  # pyright: ignore[reportUnknownVariableType]
    """Files that were skipped (content unchanged)."""

    openapi_schema: "dict[str, Any] | None" = None
    """The OpenAPI schema dict (for downstream use)."""


def fmt_path(path: Path) -> str:
    """Format path for display, using relative path when possible.

    Returns:
        The result.
    """
    try:
        return str(path.relative_to(Path.cwd()))
    except ValueError:
        return str(path)


def export_integration_assets(
    app: "Litestar", config: "ViteConfig", *, serializer: "Callable[[Any], bytes] | None" = None
) -> ExportResult:
    """Export all integration artifacts with deterministic output.

    This is the single source of truth for code generation. Both CLI commands
    and Plugin startup should call this function to ensure byte-identical output.

    The export order is critical:
    1. Register Inertia page prop types in OpenAPI schema (mutates schema_dict)
    2. Export openapi.json (now includes session prop types)
    3. Export routes.json (uses schema for component refs)
    4. Export routes.ts (if enabled)
    5. Export inertia-pages.json (if enabled)

    Args:
        app: The Litestar application instance.
        config: The ViteConfig instance.
        serializer: Optional custom serializer for OpenAPI schema encoding.

    Returns:
        ExportResult with lists of exported and unchanged files.
    """
    from litestar._openapi.plugin import OpenAPIPlugin
    from litestar.serialization import encode_json, get_serializer

    from litestar_vite.codegen._inertia import generate_inertia_pages_json
    from litestar_vite.config import InertiaConfig, InertiaTypeGenConfig, TypeGenConfig

    result = ExportResult()

    if not isinstance(config.types, TypeGenConfig):
        return result

    types_config = config.types

    # Check if OpenAPI is available
    openapi_plugin = next((p for p in app.plugins._plugins if isinstance(p, OpenAPIPlugin)), None)  # pyright: ignore[reportPrivateUsage]
    has_openapi = openapi_plugin is not None and openapi_plugin._openapi_config is not None  # pyright: ignore[reportPrivateUsage]

    if not has_openapi:
        return result

    # Get serializer for OpenAPI encoding
    if serializer is None:
        encoders: Any
        try:
            encoders = app.type_encoders  # pyright: ignore[reportUnknownMemberType]
        except AttributeError:
            encoders = None
        serializer = partial(encode_json, serializer=get_serializer(encoders if isinstance(encoders, dict) else None))  # pyright: ignore[reportUnknownArgumentType]

    # Step 1: Get OpenAPI schema and register Inertia types
    schema_dict = app.openapi_schema.to_schema()

    # Register Inertia page prop types in OpenAPI schema BEFORE exporting
    # This ensures types like EmailSent, NoProps, CurrentTeam are included
    inertia_pages_data: dict[str, Any] | None = None
    if isinstance(config.inertia, InertiaConfig) and types_config.generate_page_props:
        inertia_type_gen = config.inertia.type_gen or InertiaTypeGenConfig()
        inertia_pages_data = generate_inertia_pages_json(
            app,
            openapi_schema=schema_dict,
            include_default_auth=inertia_type_gen.include_default_auth,
            include_default_flash=inertia_type_gen.include_default_flash,
            inertia_config=config.inertia,
            types_config=types_config,
        )

    result.openapi_schema = schema_dict

    # Step 2: Export openapi.json
    export_openapi(schema_dict=schema_dict, types_config=types_config, serializer=serializer, result=result)

    # Step 3: Export routes.json (always pass openapi_schema for consistency)
    export_routes_json(app=app, types_config=types_config, openapi_schema=schema_dict, result=result)

    # Step 4: Export routes.ts (if enabled)
    if types_config.generate_routes:
        export_routes_ts(app=app, types_config=types_config, openapi_schema=schema_dict, result=result)

    # Step 5: Export inertia-pages.json (if enabled)
    if (
        isinstance(config.inertia, InertiaConfig)
        and types_config.generate_page_props
        and types_config.page_props_path
        and inertia_pages_data is not None
    ):
        export_inertia_pages(pages_data=inertia_pages_data, types_config=types_config, result=result)

    return result


def export_openapi(
    *,
    schema_dict: "dict[str, Any]",
    types_config: "TypeGenConfig",
    serializer: "Callable[[Any], bytes]",
    result: ExportResult,
) -> None:
    """Export OpenAPI schema to file."""
    from litestar_vite.codegen._utils import encode_deterministic_json, write_if_changed

    openapi_path = types_config.openapi_path
    if openapi_path is None:
        openapi_path = types_config.output / "openapi.json"

    schema_content = encode_deterministic_json(schema_dict, serializer=serializer)

    if write_if_changed(openapi_path, schema_content):
        result.exported_files.append(f"openapi: {fmt_path(openapi_path)}")
    else:
        result.unchanged_files.append("openapi.json")


def export_routes_json(
    *, app: "Litestar", types_config: "TypeGenConfig", openapi_schema: "dict[str, Any]", result: ExportResult
) -> None:
    """Export routes metadata to JSON file."""
    from litestar_vite.codegen._routes import generate_routes_json
    from litestar_vite.codegen._utils import encode_deterministic_json, write_if_changed

    try:
        from litestar import __version__ as _version

        litestar_version = str(_version)
    except ImportError:
        litestar_version = "unknown"

    routes_path = types_config.routes_path
    if routes_path is None:
        routes_path = types_config.output / "routes.json"

    # Always pass openapi_schema for consistent output between CLI and plugin
    routes_data = generate_routes_json(app, include_components=True, openapi_schema=openapi_schema)
    routes_data["litestar_version"] = litestar_version

    routes_content = encode_deterministic_json(routes_data)

    if write_if_changed(routes_path, routes_content):
        result.exported_files.append(fmt_path(routes_path))
    else:
        result.unchanged_files.append("routes.json")


def export_routes_ts(
    *, app: "Litestar", types_config: "TypeGenConfig", openapi_schema: "dict[str, Any]", result: ExportResult
) -> None:
    """Export typed routes TypeScript file."""
    from litestar_vite.codegen._routes import generate_routes_ts
    from litestar_vite.codegen._utils import write_if_changed

    routes_ts_path = types_config.routes_ts_path
    if routes_ts_path is None:
        routes_ts_path = types_config.output / "routes.ts"

    # Always pass openapi_schema for consistent output
    routes_ts_content = generate_routes_ts(app, openapi_schema=openapi_schema, global_route=types_config.global_route)

    if write_if_changed(routes_ts_path, routes_ts_content):
        result.exported_files.append(fmt_path(routes_ts_path))
    else:
        result.unchanged_files.append("routes.ts")


def export_inertia_pages(*, pages_data: "dict[str, Any]", types_config: "TypeGenConfig", result: ExportResult) -> None:
    """Export Inertia pages metadata to JSON file."""
    from litestar_vite.codegen._utils import encode_deterministic_json, write_if_changed

    page_props_path = types_config.page_props_path
    if page_props_path is None:
        return

    pages_content = encode_deterministic_json(pages_data)

    if write_if_changed(page_props_path, pages_content):
        result.exported_files.append(fmt_path(page_props_path))
    else:
        result.unchanged_files.append("inertia-pages.json")
