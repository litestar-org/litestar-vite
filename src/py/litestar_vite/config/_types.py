"""Type generation configuration."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal, cast

__all__ = ("TypeGenConfig",)


@dataclass
class TypeGenConfig:
    """Type generation settings.

    Presence of this config enables type generation. Use ``types=None`` or
    ``types=False`` in ViteConfig to disable.

    Attributes:
        output: Output directory for generated types.
        openapi_path: Path to export OpenAPI schema.
        routes_path: Path to export routes metadata (JSON format).
        routes_ts_path: Path to export typed routes TypeScript file.
        generate_zod: Generate Zod schemas from OpenAPI.
        generate_sdk: Generate SDK client from OpenAPI.
        generate_routes: Generate typed routes.ts file (Ziggy-style).
        generate_page_props: Generate Inertia page props TypeScript file.
            Auto-enabled when both types and inertia are configured.
        generate_schemas: Generate schemas.ts with ergonomic form/response type helpers.
            Creates helper types like FormInput<'api:login'> and FormResponse<'api:login', 201>
            that wrap hey-api generated types with cleaner DX.
        page_props_path: Path to export page props metadata (JSON format).
        schemas_ts_path: Path to export schemas TypeScript file.
        global_route: Register route() function globally on window object.
            When True, adds ``window.route = route`` to generated routes.ts,
            providing global access without imports.
        fallback_type: Fallback value type for untyped containers in generated Inertia props.
            Controls whether untyped dict/list become `unknown` (default) or `any`.
        type_import_paths: Map schema/type names to TypeScript import paths for props types
            that are not present in OpenAPI (e.g., internal/excluded schemas).
    """

    output: Path = field(default_factory=lambda: Path("src/generated"))
    openapi_path: "Path | None" = field(default=None)
    routes_path: "Path | None" = field(default=None)
    routes_ts_path: "Path | None" = field(default=None)
    generate_zod: bool = False
    generate_sdk: bool = True
    generate_routes: bool = True
    generate_page_props: bool = True
    generate_schemas: bool = True
    """Generate schemas.ts with ergonomic form/response type helpers.

    When True, generates a schemas.ts file that wraps hey-api generated types
    with cleaner, more ergonomic type helpers:

    .. code-block:: typescript

        import { FormInput, FormResponse, SuccessResponse } from '@/generated/schemas'

        // Type-safe form data using route names
        type LoginForm = FormInput<'api:login'>  // { username: string; password: string }

        // Type-safe responses by status code
        type LoginSuccess = SuccessResponse<'api:login'>  // { access_token: string; ... }
        type LoginError = FormResponse<'api:login', 400>  // { detail: string; ... }

    Requires generate_sdk=True (hey-api types must be generated first).
    """
    schemas_ts_path: "Path | None" = field(default=None)
    """Path to export schemas TypeScript file.

    Defaults to output / "schemas.ts".
    """
    global_route: bool = False
    """Register route() function globally on window object.

    When True, the generated routes.ts will include code that registers
    the type-safe route() function on ``window.route``, similar to Laravel's
    Ziggy library. This allows using route() without imports:

    .. code-block:: typescript

        // With global_route=True, no import needed:
        window.route('user-profile', { userId: 123 })

        // TypeScript users should add to global.d.ts:
        // declare const route: typeof import('@/generated/routes').route

    Default is False to encourage explicit imports for better tree-shaking.
    """
    fallback_type: "Literal['unknown', 'any']" = "unknown"
    type_import_paths: dict[str, str] = field(default_factory=lambda: cast("dict[str, str]", {}))
    """Map schema/type names to TypeScript import paths for Inertia props.

    Use this for prop types that are not present in OpenAPI (e.g., internal schemas).
    """
    page_props_path: "Path | None" = field(default=None)
    """Path to export page props metadata JSON.

    The Vite plugin reads this file to generate page-props.ts.
    Defaults to output / "inertia-pages.json".
    """

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
