"""Type generation configuration."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Literal, cast

if TYPE_CHECKING:
    from collections.abc import Sequence

__all__ = ("TypeGenConfig",)


@dataclass
class TypeGenConfig:
    """Configuration for OpenAPI, AsyncAPI, route, and Inertia page-props TypeScript code generation."""

    output: Path = field(default_factory=lambda: Path("src/generated"))
    """Output directory for generated schemas and TypeScript files."""
    openapi_path: "Path | None" = field(default=None)
    """Path to export the deterministic `openapi.json` schema (`output / 'openapi.json'` when `None`)."""
    routes_path: "Path | None" = field(default=None)
    """Path to export route metadata JSON (`output / 'routes.json'` when `None`)."""
    routes_ts_path: "Path | None" = field(default=None)
    """Path to export the generated `routes.ts` module (`output / 'routes.ts'` when `None`)."""
    asyncapi_path: "Path | None" = field(default=None)
    """Path to export the normalized `asyncapi.json` document (`output / 'asyncapi.json'` when `None`)."""
    generate_zod: bool = False
    """Generate Zod validation schemas alongside OpenAPI TypeScript types."""
    generate_sdk: bool = True
    """Generate the `@hey-api/openapi-ts` client SDK and types from `openapi.json`."""
    generate_routes: bool = True
    """Generate the typed Ziggy-style `routes.ts` helper module."""
    generate_page_props: bool = True
    """Generate `page-props.ts` mapping Inertia component names to Python handler prop types."""
    generate_channels: bool = True
    """Generate `channels.ts` and `createTypedChannels()` from `asyncapi.json` when an AsyncAPI plugin is present."""
    channels_ts_path: "Path | None" = field(default=None)
    """Path to export the generated `channels.ts` module (`output / 'channels.ts'` when `None`)."""
    generate_schemas: bool = True
    """Generate `schemas.ts` with `FormInput`, `FormResponse`, and `SuccessResponse` type helpers."""
    schemas_ts_path: "Path | None" = field(default=None)
    """Path to export the generated `schemas.ts` helper module (`output / 'schemas.ts'` when `None`)."""
    global_route: bool = False
    """Register the generated `route()` helper globally on `window.route`."""
    fail_on_error: "bool | None" = None
    """Fail the Vite command when type generation errors occur (`None` fails in build and warns in dev)."""
    fallback_type: "Literal['unknown', 'any']" = "unknown"
    """Fallback TypeScript value type (`'unknown'` or `'any'`) for untyped containers in generated props."""
    type_import_paths: dict[str, str] = field(default_factory=lambda: cast("dict[str, str]", {}))
    """Map of schema/type names to custom TypeScript import paths for types excluded from OpenAPI."""
    page_props_path: "Path | None" = field(default=None)
    """Path to export Inertia page metadata JSON (`output / 'inertia-pages.json'` when `None`)."""
    extra_commands: "Sequence[Sequence[str]]" = field(default_factory=lambda: cast("list[Sequence[str]]", []))
    """Additional CLI commands (`[binary, *args]`) executed via the JS runtime during type generation."""

    def __post_init__(self) -> None:
        """Normalize path types and compute defaults based on output directory."""
        if isinstance(self.output, str):
            self.output = Path(self.output)
        if self.openapi_path is None:
            self.openapi_path = self.output / "openapi.json"
        elif isinstance(self.openapi_path, str):
            self.openapi_path = Path(self.openapi_path)
        if self.routes_path is None:
            self.routes_path = self.output / "routes.json"
        elif isinstance(self.routes_path, str):
            self.routes_path = Path(self.routes_path)
        if self.routes_ts_path is None:
            self.routes_ts_path = self.output / "routes.ts"
        elif isinstance(self.routes_ts_path, str):
            self.routes_ts_path = Path(self.routes_ts_path)
        if self.page_props_path is None:
            self.page_props_path = self.output / "inertia-pages.json"
        elif isinstance(self.page_props_path, str):
            self.page_props_path = Path(self.page_props_path)
        if self.schemas_ts_path is None:
            self.schemas_ts_path = self.output / "schemas.ts"
        elif isinstance(self.schemas_ts_path, str):
            self.schemas_ts_path = Path(self.schemas_ts_path)
        if self.asyncapi_path is None:
            self.asyncapi_path = self.output / "asyncapi.json"
        elif isinstance(self.asyncapi_path, str):
            self.asyncapi_path = Path(self.asyncapi_path)
        if self.channels_ts_path is None:
            self.channels_ts_path = self.output / "channels.ts"
        elif isinstance(self.channels_ts_path, str):
            self.channels_ts_path = Path(self.channels_ts_path)
