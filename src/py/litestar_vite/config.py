"""Litestar-Vite Configuration.

This module provides the configuration dataclasses for the Vite integration.
The configuration is split into logical groups:

- PathConfig: File system paths
- RuntimeConfig: Execution settings
- TypeGenConfig: Type generation settings
- ViteConfig: Root configuration combining all sub-configs

Example usage::

    # Minimal - SPA mode with defaults
    VitePlugin(config=ViteConfig())

    # Development mode
    VitePlugin(config=ViteConfig(dev_mode=True))

    # With type generation
    VitePlugin(config=ViteConfig(dev_mode=True, types=True))

    # Template mode for HTMX
    VitePlugin(config=ViteConfig(mode="template", dev_mode=True))
"""

import logging
import os
from dataclasses import dataclass, field, replace
from importlib.util import find_spec
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal, Protocol, cast, runtime_checkable

from litestar.exceptions import SerializationException
from litestar.serialization import decode_json

logger = logging.getLogger("litestar_vite")

if TYPE_CHECKING:
    from collections.abc import Sequence

    from litestar.types import Guard  # pyright: ignore[reportUnknownVariableType]

    from litestar_vite.executor import JSExecutor

__all__ = (
    "FSSPEC_INSTALLED",
    "JINJA_INSTALLED",
    "DeployConfig",
    "ExternalDevServer",
    "InertiaConfig",
    "InertiaSSRConfig",
    "InertiaTypeGenConfig",
    "LoggingConfig",
    "PaginationContainer",
    "PathConfig",
    "RuntimeConfig",
    "SPAConfig",
    "TypeGenConfig",
    "ViteConfig",
)


@runtime_checkable
class PaginationContainer(Protocol):
    """Protocol for pagination containers that can be unwrapped for Inertia scroll.

    Any type that has `items` and pagination metadata can implement this protocol.
    The response will extract items and calculate scroll_props automatically.

    Built-in support:
    - litestar.pagination.OffsetPagination
    - litestar.pagination.ClassicPagination
    - advanced_alchemy.service.OffsetPagination

    Custom types can implement this protocol::

        @dataclass
        class MyPagination:
            items: list[T]
            total: int
            limit: int
            offset: int
    """

    items: "Sequence[Any]"


TRUE_VALUES = {"True", "true", "1", "yes", "Y", "T"}
JINJA_INSTALLED = bool(find_spec("jinja2"))
FSSPEC_INSTALLED = bool(find_spec("fsspec"))


def _empty_dict_factory() -> dict[str, Any]:
    """Return an empty ``dict[str, Any]``.

    Returns:
        An empty dictionary.
    """
    return {}


def _empty_set_factory() -> set[str]:
    """Return an empty ``set[str]``.

    Returns:
        An empty set.
    """
    return set()


def _default_content_types() -> dict[str, str]:
    """Default content-type mappings keyed by file extension.

    Returns:
        Dictionary mapping file extensions to MIME types.
    """
    return {
        ".js": "application/javascript",
        ".mjs": "application/javascript",
        ".cjs": "application/javascript",
        ".css": "text/css",
        ".html": "text/html",
        ".json": "application/json",
        ".svg": "image/svg+xml",
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".webp": "image/webp",
        ".woff2": "font/woff2",
        ".woff": "font/woff",
    }


def _default_storage_options() -> dict[str, Any]:
    """Return an empty storage options dictionary.

    Returns:
        An empty dictionary.
    """
    return {}


@dataclass
class DeployConfig:
    """CDN deployment configuration.

    Attributes:
        enabled: Enable deployment features.
        storage_backend: fsspec URL for the target location (e.g., ``gcs://bucket/path``).
        storage_options: Provider options forwarded to ``fsspec`` (credentials, region, etc.).
        delete_orphaned: Remove remote files not present in the local bundle.
        include_manifest: Upload ``manifest.json`` alongside assets.
        content_types: Optional content-type overrides keyed by file extension.
    """

    enabled: bool = False
    storage_backend: "str | None" = field(default_factory=lambda: os.getenv("VITE_DEPLOY_STORAGE"))
    storage_options: dict[str, Any] = field(default_factory=_default_storage_options)
    delete_orphaned: bool = field(default_factory=lambda: os.getenv("VITE_DEPLOY_DELETE", "true") in TRUE_VALUES)
    include_manifest: bool = True
    content_types: dict[str, str] = field(default_factory=_default_content_types)

    def __post_init__(self) -> None:
        """Apply environment fallbacks."""
        if self.storage_backend is None:
            self.storage_backend = os.getenv("VITE_DEPLOY_STORAGE")

    def with_overrides(
        self,
        storage_backend: "str | None" = None,
        storage_options: "dict[str, Any] | None" = None,
        delete_orphaned: "bool | None" = None,
    ) -> "DeployConfig":
        """Return a copy with overrides applied.

        Args:
            storage_backend: Override for the storage URL.
            storage_options: Override for backend options.
            delete_orphaned: Override deletion behaviour.

        Returns:
            DeployConfig copy with updated fields.
        """
        return replace(
            self,
            storage_backend=storage_backend or self.storage_backend,
            storage_options=storage_options or self.storage_options,
            delete_orphaned=self.delete_orphaned if delete_orphaned is None else delete_orphaned,
        )


@dataclass
class InertiaSSRConfig:
    """Server-side rendering settings for Inertia.js.

    Inertia SSR runs a separate Node server that renders the initial HTML for an
    Inertia page object. Litestar sends the page payload to the SSR server (by
    default at ``http://127.0.0.1:13714/render``) and injects the returned head
    tags and body markup into the HTML response.

    Notes:
        - This is *not* Litestar-Vite's ``mode="ssr"`` (Astro/Nuxt/SvelteKit proxy mode).
        - When enabled, failures to contact the SSR server are treated as errors (no silent fallback).
    """

    enabled: bool = True
    url: str = "http://127.0.0.1:13714/render"
    timeout: float = 2.0


@dataclass
class InertiaConfig:
    """Configuration for InertiaJS support.

    This is the canonical configuration class for Inertia.js integration.
    Presence of an InertiaConfig instance indicates Inertia is enabled.

    Note:
        SPA mode (HTML transformation vs Jinja2 templates) is controlled by
        ViteConfig.mode='hybrid'. The app_selector for data-page injection
        is configured via SPAConfig.app_selector.

    Attributes:
        root_template: Name of the root template to use.
        component_opt_keys: Identifiers for getting inertia component from route opts.
        redirect_unauthorized_to: Path for unauthorized request redirects.
        redirect_404: Path for 404 request redirects.
        extra_static_page_props: Static props added to every page response.
        extra_session_page_props: Session keys to include in page props.
    """

    root_template: str = "index.html"
    """Name of the root template to use.

    This must be a path that is found by the Vite Plugin template config
    """
    component_opt_keys: "tuple[str, ...]" = ("component", "page")
    """Identifiers to use on routes to get the inertia component to render.

    The first key found in the route handler opts will be used. This allows
    semantic flexibility - use "component" or "page" depending on preference.

    Example:
        # All equivalent:
        @get("/", component="Home")
        @get("/", page="Home")

        # Custom keys:
        InertiaConfig(component_opt_keys=("view", "component", "page"))
    """
    redirect_unauthorized_to: "str | None" = None
    """Optionally supply a path where unauthorized requests should redirect."""
    redirect_404: "str | None" = None
    """Optionally supply a path where 404 requests should redirect."""
    extra_static_page_props: "dict[str, Any]" = field(default_factory=_empty_dict_factory)
    """A dictionary of values to automatically add in to page props on every response."""
    extra_session_page_props: "set[str]" = field(default_factory=_empty_set_factory)
    """A set of session keys for which the value automatically be added (if it exists) to the response."""
    encrypt_history: bool = False
    """Enable browser history encryption globally (v2 feature).

    When True, all Inertia responses will include `encryptHistory: true`
    in the page object. The Inertia client will encrypt history state
    using browser's crypto API before pushing to history.

    This prevents sensitive data from being visible in browser history
    after a user logs out. Individual responses can override this setting.

    Note: Encryption happens client-side; requires HTTPS in production.
    See: https://inertiajs.com/history-encryption
    """
    type_gen: "InertiaTypeGenConfig | None" = None
    """Type generation options for Inertia page props.

    Controls default types in generated page-props.ts. Set to InertiaTypeGenConfig()
    or leave as None for defaults. Use InertiaTypeGenConfig(include_default_auth=False)
    to disable default User/AuthData interfaces for non-standard user models.
    """

    ssr: "InertiaSSRConfig | bool | None" = None
    """Enable server-side rendering (SSR) for Inertia responses.

    When enabled, full-page HTML responses will be pre-rendered by a Node SSR server
    and injected into the SPA HTML before returning to the client.

    Supports:
        - True: enable with defaults -> ``InertiaSSRConfig()``
        - False/None: disabled -> ``None``
        - InertiaSSRConfig: use as-is
    """

    def __post_init__(self) -> None:
        """Normalize optional sub-configs."""
        if self.ssr is True:
            self.ssr = InertiaSSRConfig()
        elif self.ssr is False:
            self.ssr = None

    @property
    def ssr_config(self) -> "InertiaSSRConfig | None":
        """Return the SSR config when enabled, otherwise None.

        Returns:
            The resolved SSR config when enabled, otherwise None.
        """
        if isinstance(self.ssr, InertiaSSRConfig) and self.ssr.enabled:
            return self.ssr
        return None


@dataclass
class InertiaTypeGenConfig:
    """Type generation options for Inertia page props.

    Controls which default types are included in the generated page-props.ts file.
    This follows Laravel Jetstream patterns - sensible defaults for common auth patterns.

    Attributes:
        include_default_auth: Include default User and AuthData interfaces.
            Default User has: id, email, name. Users extend via module augmentation.
            Set to False if your User model doesn't have these fields (uses uuid, username, etc.)
        include_default_flash: Include default FlashMessages interface.
            Uses { [category: string]: string[] } pattern for flash messages.

    Example:
        Standard auth (95% of users) - just extend defaults::

            # Python: use defaults
            ViteConfig(inertia=InertiaConfig())

            # TypeScript: extend User interface
            declare module 'litestar-vite-plugin/inertia' {
                interface User {
                    avatarUrl?: string
                    roles: Role[]
                }
            }

        Custom auth (5% of users) - define from scratch::

            # Python: disable defaults
            ViteConfig(inertia=InertiaConfig(
                type_gen=InertiaTypeGenConfig(include_default_auth=False)
            ))

            # TypeScript: define your custom User
            declare module 'litestar-vite-plugin/inertia' {
                interface User {
                    uuid: string  // No id!
                    username: string  // No email!
                }
            }
    """

    include_default_auth: bool = True
    """Include default User and AuthData interfaces.

    When True, generates:
    - User: { id: string, email: string, name?: string | null }
    - AuthData: { isAuthenticated: boolean, user?: User }

    Users extend via TypeScript module augmentation.
    Set to False if your User model has different required fields.
    """

    include_default_flash: bool = True
    """Include default FlashMessages interface.

    When True, generates:
    - FlashMessages: { [category: string]: string[] }

    Standard flash message pattern used by most web frameworks.
    """


def _resolve_proxy_mode() -> "Literal['vite', 'direct', 'proxy'] | None":
    """Resolve proxy_mode from environment variable.

    Reads VITE_PROXY_MODE env var. Valid values:
    - "vite" (default): Proxy to internal Vite server (allow list - assets only)
    - "direct": Expose Vite port directly (no proxy)
    - "proxy": Proxy everything except Litestar routes (deny list)
    - "none": Disable proxy (for production)

    Raises:
        ValueError: If an invalid value is provided.

    Returns:
        The resolved proxy mode, or None if disabled.
    """
    env_value = os.getenv("VITE_PROXY_MODE")
    match env_value.strip().lower() if env_value is not None else None:
        case None:
            return "vite"
        case "none":
            return None
        case "direct":
            return "direct"
        case "proxy":
            return "proxy"
        case "vite":
            return "vite"
        case _:
            msg = f"Invalid VITE_PROXY_MODE: {env_value!r}. Expected one of: vite, direct, proxy, none"
            raise ValueError(msg)


@dataclass
class PathConfig:
    """File system paths configuration.

    Attributes:
        root: The root directory of the project. Defaults to current working directory.
        bundle_dir: Location of compiled assets and manifest.json.
        resource_dir: TypeScript/JavaScript source directory (equivalent to ./src in Vue/React).
        static_dir: Static public assets directory (served as-is by Vite).
        manifest_name: Name of the Vite manifest file.
        hot_file: Name of the hot file indicating dev server URL.
        asset_url: Base URL for static asset references (prepended to Vite output).
        ssr_output_dir: SSR output directory (optional).
    """

    root: "str | Path" = field(default_factory=Path.cwd)
    bundle_dir: "str | Path" = field(default_factory=lambda: Path("public"))
    resource_dir: "str | Path" = field(default_factory=lambda: Path("src"))
    static_dir: "str | Path" = field(default_factory=lambda: Path("public"))
    manifest_name: str = "manifest.json"
    hot_file: str = "hot"
    asset_url: str = field(default_factory=lambda: os.getenv("ASSET_URL", "/static/"))
    ssr_output_dir: "str | Path | None" = None

    def __post_init__(self) -> None:
        """Normalize path types to Path objects.

        This also adjusts defaults to prevent Vite's ``publicDir`` (input) from
        colliding with ``outDir`` (output). ``bundle_dir`` is treated as the build
        output directory. When ``static_dir`` equals ``bundle_dir``, Vite may warn
        and effectively disable public asset copying, so ``static_dir`` defaults to
        ``<resource_dir>/public`` in that case.
        """
        if isinstance(self.root, str):
            object.__setattr__(self, "root", Path(self.root))
        if isinstance(self.bundle_dir, str):
            object.__setattr__(self, "bundle_dir", Path(self.bundle_dir))
        if isinstance(self.resource_dir, str):
            object.__setattr__(self, "resource_dir", Path(self.resource_dir))
        if isinstance(self.static_dir, str):
            object.__setattr__(self, "static_dir", Path(self.static_dir))
        if isinstance(self.ssr_output_dir, str):
            object.__setattr__(self, "ssr_output_dir", Path(self.ssr_output_dir))

        if (
            isinstance(self.bundle_dir, Path)
            and isinstance(self.static_dir, Path)
            and self.static_dir == self.bundle_dir
        ):
            object.__setattr__(self, "static_dir", Path(self.resource_dir) / "public")


@dataclass
class ExternalDevServer:
    """Configuration for external (non-Vite) dev servers.

    Use this when your frontend uses a framework with its own dev server
    (Angular CLI, Next.js, Create React App, etc.) instead of Vite.

    For SSR frameworks (Astro, Nuxt, SvelteKit) using Vite internally, leave
    target as None - the proxy will read the dynamic port from the hotfile.

    Attributes:
        target: The URL of the external dev server (e.g., "http://localhost:4200").
            If None, the proxy reads the target URL from the Vite hotfile.
        command: Custom command to start the dev server (e.g., ["ng", "serve"]).
            If None and start_dev_server=True, uses executor's default start command.
        build_command: Custom command to build for production (e.g., ["ng", "build"]).
            If None, uses executor's default build command (e.g., "npm run build").
        http2: Enable HTTP/2 for proxy connections.
        enabled: Whether the external proxy is enabled.
    """

    target: "str | None" = None
    command: "list[str] | None" = None
    build_command: "list[str] | None" = None
    http2: bool = False
    enabled: bool = True


@dataclass
class RuntimeConfig:
    """Runtime execution settings.

    Attributes:
        dev_mode: Enable development mode with HMR/watch.
        proxy_mode: Proxy handling mode:
            - "vite" (default): Proxy Vite assets only (allow list - SPA mode)
            - "direct": Expose Vite port directly (no proxy)
            - "proxy": Proxy everything except Litestar routes (deny list - SSR mode)
            - None: No proxy (production mode)
        external_dev_server: Configuration for external dev server (used with proxy_mode="proxy").
        host: Vite dev server host.
        port: Vite dev server port.
        protocol: Protocol for dev server (http/https).
        executor: JavaScript runtime executor (node, bun, deno).
        run_command: Custom command to run Vite dev server (auto-detect if None).
        build_command: Custom command to build with Vite (auto-detect if None).
        build_watch_command: Custom command for watch mode build.
        serve_command: Custom command to run production server (for SSR frameworks).
        install_command: Custom command to install dependencies.
        is_react: Enable React Fast Refresh support.
        ssr_enabled: Enable Server-Side Rendering.
        health_check: Enable health check for dev server startup.
        detect_nodeenv: Detect and use nodeenv in virtualenv (opt-in).
        set_environment: Set Vite environment variables from config.
        set_static_folders: Automatically configure static file serving.
        csp_nonce: Content Security Policy nonce for inline scripts.
        spa_handler: Auto-register catch-all SPA route when mode="spa".
        http2: Enable HTTP/2 for proxy HTTP requests (better multiplexing).
            WebSocket traffic (HMR) uses a separate connection and is unaffected.
    """

    dev_mode: bool = field(default_factory=lambda: os.getenv("VITE_DEV_MODE", "False") in TRUE_VALUES)
    proxy_mode: "Literal['vite', 'direct', 'proxy'] | None" = field(default_factory=_resolve_proxy_mode)
    external_dev_server: "ExternalDevServer | str | None" = None
    host: str = field(default_factory=lambda: os.getenv("VITE_HOST", "127.0.0.1"))
    port: int = field(default_factory=lambda: int(os.getenv("VITE_PORT", "5173")))
    protocol: Literal["http", "https"] = "http"
    executor: "Literal['node', 'bun', 'deno', 'yarn', 'pnpm'] | None" = None
    run_command: "list[str] | None" = None
    build_command: "list[str] | None" = None
    build_watch_command: "list[str] | None" = None
    serve_command: "list[str] | None" = None
    install_command: "list[str] | None" = None
    is_react: bool = False
    ssr_enabled: bool = False
    health_check: bool = field(default_factory=lambda: os.getenv("VITE_HEALTH_CHECK", "False") in TRUE_VALUES)
    detect_nodeenv: bool = False
    set_environment: bool = True
    set_static_folders: bool = True
    csp_nonce: "str | None" = None
    spa_handler: bool = True
    http2: bool = True
    start_dev_server: bool = True

    def __post_init__(self) -> None:
        """Normalize runtime settings and apply derived defaults."""
        if isinstance(self.external_dev_server, str):
            self.external_dev_server = ExternalDevServer(target=self.external_dev_server)

        if self.external_dev_server is not None and self.proxy_mode in {None, "vite"}:
            self.proxy_mode = "proxy"

        if self.executor is None:
            self.executor = "node"

        executor_commands = {
            "node": {
                "run": ["npm", "run", "dev"],
                "build": ["npm", "run", "build"],
                "build_watch": ["npm", "run", "watch"],
                "serve": ["npm", "run", "serve"],
                "install": ["npm", "install"],
            },
            "bun": {
                "run": ["bun", "run", "dev"],
                "build": ["bun", "run", "build"],
                "build_watch": ["bun", "run", "watch"],
                "serve": ["bun", "run", "serve"],
                "install": ["bun", "install"],
            },
            "deno": {
                "run": ["deno", "task", "dev"],
                "build": ["deno", "task", "build"],
                "build_watch": ["deno", "task", "watch"],
                "serve": ["deno", "task", "serve"],
                "install": ["deno", "install"],
            },
            "yarn": {
                "run": ["yarn", "dev"],
                "build": ["yarn", "build"],
                "build_watch": ["yarn", "watch"],
                "serve": ["yarn", "serve"],
                "install": ["yarn", "install"],
            },
            "pnpm": {
                "run": ["pnpm", "dev"],
                "build": ["pnpm", "build"],
                "build_watch": ["pnpm", "watch"],
                "serve": ["pnpm", "serve"],
                "install": ["pnpm", "install"],
            },
        }

        if self.executor in executor_commands:
            cmds = executor_commands[self.executor]
            if self.run_command is None:
                self.run_command = cmds["run"]
            if self.build_command is None:
                self.build_command = cmds["build"]
            if self.build_watch_command is None:
                self.build_watch_command = cmds["build_watch"]
            if self.serve_command is None:
                self.serve_command = cmds["serve"]
            if self.install_command is None:
                self.install_command = cmds["install"]


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
        page_props_path: Path to export page props metadata (JSON format).
        watch_patterns: File patterns to watch for type regeneration.
        global_route: Register route() function globally on window object.
            When True, adds ``window.route = route`` to generated routes.ts,
            providing Laravel/Ziggy-style global access without imports.
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
    watch_patterns: list[str] = field(
        default_factory=lambda: ["**/routes.py", "**/handlers.py", "**/controllers/**/*.py"]
    )

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


@dataclass
class SPAConfig:
    """Configuration for SPA HTML transformations.

    This configuration controls how the SPA HTML is transformed before serving,
    including CSRF token injection and Inertia.js page data handling.

    Note:
        Route metadata is now generated as TypeScript (routes.ts) at build time
        instead of runtime injection. Use TypeGenConfig.generate_routes to enable.

    Attributes:
        inject_csrf: Whether to inject CSRF token into HTML (as window.__LITESTAR_CSRF__).
        csrf_var_name: Global variable name for CSRF token (e.g., window.__LITESTAR_CSRF__).
        app_selector: CSS selector for the app root element (used for data attributes).
        cache_transformed_html: Cache transformed HTML in production; disabled when inject_csrf=True because CSRF tokens are per-request.
    """

    inject_csrf: bool = True
    csrf_var_name: str = "__LITESTAR_CSRF__"
    app_selector: str = "#app"
    cache_transformed_html: bool = True


def _get_default_log_level() -> "Literal['quiet', 'normal', 'verbose']":
    """Get default log level from environment variable.

    Checks LITESTAR_VITE_LOG_LEVEL environment variable.
    Falls back to "normal" if not set or invalid.

    Returns:
        The log level from environment or "normal" default.
    """
    env_level = os.getenv("LITESTAR_VITE_LOG_LEVEL", "").lower()
    match env_level:
        case "quiet" | "normal" | "verbose":
            return env_level
        case _:
            return "normal"


def _to_root_path(root_dir: Path, path: Path) -> Path:
    """Resolve a path relative to the configured root directory.

    Args:
        root_dir: Application root directory.
        path: Path to resolve.

    Returns:
        Absolute path rooted at ``root_dir`` when ``path`` is relative, otherwise ``path`` unchanged.
    """
    return path if path.is_absolute() else (root_dir / path)


@dataclass
class LoggingConfig:
    """Logging configuration for console output.

    Controls the verbosity and style of console output from both Python
    and TypeScript (via .litestar.json bridge).

    Attributes:
        level: Logging verbosity level.
            - "quiet": Minimal output (errors only)
            - "normal": Standard operational messages (default)
            - "verbose": Detailed debugging information
            Can also be set via LITESTAR_VITE_LOG_LEVEL environment variable.
            Precedence: explicit config > env var > default ("normal")
        show_paths_absolute: Show absolute paths instead of relative paths.
            Default False shows cleaner relative paths in output.
        suppress_npm_output: Suppress npm/yarn/pnpm script echo lines.
            When True, hides lines like "> dev" / "> vite" from output.
        suppress_vite_banner: Suppress the Vite startup banner.
            When True, only the LITESTAR banner is shown.
        timestamps: Include timestamps in log messages.

    Example:
        Quiet mode for CI/CD::

            ViteConfig(logging=LoggingConfig(level="quiet"))

        Verbose debugging::

            ViteConfig(logging=LoggingConfig(level="verbose", show_paths_absolute=True))

        Environment variable::

            export LITESTAR_VITE_LOG_LEVEL=quiet
    """

    level: "Literal['quiet', 'normal', 'verbose']" = field(default_factory=_get_default_log_level)
    show_paths_absolute: bool = False
    suppress_npm_output: bool = False
    suppress_vite_banner: bool = False
    timestamps: bool = False


@dataclass
class ViteConfig:
    """Root Vite configuration.

    This is the main configuration class that combines all sub-configurations.
    Supports shortcuts for common configurations:

    - dev_mode: Shortcut for runtime.dev_mode
    - types=True or TypeGenConfig(): Enable type generation (presence = enabled)
    - inertia=True or InertiaConfig(): Enable Inertia.js (presence = enabled)

    Mode auto-detection:

    - If mode is not explicitly set:

      - If Inertia is enabled and index.html exists -> Hybrid mode
      - If Inertia is enabled without index.html -> Template mode
      - Checks for index.html in common locations -> SPA mode
      - Checks if Jinja2 template engine is configured -> Template mode
      - Otherwise defaults to SPA mode

    Dev-mode auto-enable:

    - If mode="spa" and no built assets are found in bundle_dir, dev_mode is
      enabled automatically (unless VITE_AUTO_DEV_MODE=False).

    - Explicit mode parameter overrides auto-detection

    Attributes:
        mode: Serving mode - "spa", "template", "htmx", "hybrid", "ssr", "ssg", or "external".
            Auto-detected if not set. Use "external" for non-Vite frameworks (Angular CLI, etc.)
            that have their own build system - auto-serves bundle_dir in production.
        paths: File system paths configuration.
        runtime: Runtime execution settings.
        types: Type generation settings (True/TypeGenConfig enables, False/None disables).
        inertia: Inertia.js settings (True/InertiaConfig enables, False/None disables).
        spa: SPA transformation settings (True enables with defaults, False disables).
        logging: Logging configuration (True enables with defaults, None uses defaults).
        dev_mode: Convenience shortcut for runtime.dev_mode.
        base_url: Base URL for production assets (CDN support).
        deploy: Deployment configuration for CDN publishing.
    """

    mode: "Literal['spa', 'template', 'htmx', 'hybrid', 'inertia', 'ssr', 'ssg', 'external'] | None" = None
    paths: PathConfig = field(default_factory=PathConfig)
    runtime: RuntimeConfig = field(default_factory=RuntimeConfig)
    types: "TypeGenConfig | bool | None" = None
    inertia: "InertiaConfig | bool | None" = None
    spa: "SPAConfig | bool | None" = None
    logging: "LoggingConfig | bool | None" = None
    dev_mode: bool = False
    base_url: "str | None" = field(default_factory=lambda: os.getenv("VITE_BASE_URL"))
    deploy: "DeployConfig | bool" = False
    guards: "Sequence[Guard] | None" = None  # pyright: ignore[reportUnknownVariableType]
    """Custom guards for the SPA catch-all route.

    When set, these guards are applied to the SPA handler route that serves the
    SPA index.html (mode="spa"/"ssr" with spa_handler=True).
    """
    exclude_static_from_auth: bool = True
    """Exclude static file routes from authentication.

    When True (default), static file routes are served with
    opt={"exclude_from_auth": True}, which tells auth middleware to skip
    authentication for asset requests. Set to False if you need to protect
    static assets with authentication.
    """
    spa_path: "str | None" = None
    """Path where the SPA handler serves index.html.

    Controls where AppHandler registers its catch-all routes.

    - Default: "/" (root)
    - Non-root (e.g. "/web/"): optionally set `include_root_spa_paths=True` to
      also serve at "/" and "/{path:path}".
    """
    include_root_spa_paths: bool = False
    """Also register SPA routes at root when spa_path is non-root.

    When True and spa_path is set to a non-root path (e.g., "/web/"),
    the SPA handler will also serve at "/" and "/{path:path}" in addition
    to the spa_path routes.

    This is useful for Angular apps with --base-href /web/ that also
    want to serve the SPA from the root path for convenience.
    """

    _executor_instance: "JSExecutor | None" = field(default=None, repr=False)
    _mode_auto_detected: bool = field(default=False, repr=False)

    def __post_init__(self) -> None:
        """Normalize configurations and apply shortcuts."""
        self._normalize_mode()
        self._normalize_types()
        self._normalize_inertia()
        self._normalize_spa_flag()
        self._normalize_logging()
        self._apply_dev_mode_shortcut()
        self._auto_detect_mode()
        self._auto_configure_inertia()
        self._auto_detect_react()
        self._apply_ssr_mode_defaults()
        self._normalize_deploy()
        self._ensure_spa_default()
        self._auto_enable_dev_mode()
        self._warn_missing_assets()

    def _auto_detect_react(self) -> None:
        """Enable React Fast Refresh automatically for React templates.

        When serving HTML outside Vite's native index.html pipeline (template/hybrid modes),
        @vitejs/plugin-react requires the React preamble to be injected into the HTML.
        The asset loader handles this when `runtime.is_react` is enabled.

        We auto-enable it when `@vitejs/plugin-react` is present in the project's package.json.
        """
        if self.runtime.is_react:
            return

        package_json = self.root_dir / "package.json"
        if not package_json.exists():
            return

        try:
            payload = decode_json(package_json.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, SerializationException):  # pragma: no cover - defensive
            return

        deps_any = payload.get("dependencies")
        dev_deps_any = payload.get("devDependencies")

        deps: dict[str, Any] = {}
        dev_deps: dict[str, Any] = {}

        if isinstance(deps_any, dict):
            deps = cast("dict[str, Any]", deps_any)
        if isinstance(dev_deps_any, dict):
            dev_deps = cast("dict[str, Any]", dev_deps_any)

        if "@vitejs/plugin-react" in deps or "@vitejs/plugin-react" in dev_deps:
            self.runtime.is_react = True

    def _normalize_mode(self) -> None:
        """Normalize mode aliases.

        Aliases:
        - 'ssg' → 'ssr': Static Site Generation uses the same proxy behavior as SSR.
          Both use deny list proxy in dev mode (forward non-API routes to framework's
          dev server). SSG pre-renders at build time, SSR renders per-request, but
          their dev-time proxy behavior is identical.

        - 'inertia' → 'hybrid': Inertia.js apps without Jinja templates use hybrid mode.
          This is clearer terminology since "hybrid" refers to the SPA-with-server-routing
          pattern that Inertia implements.
        """
        if self.mode == "ssg":
            self.mode = "ssr"
        elif self.mode == "inertia":
            self.mode = "hybrid"

    def _normalize_types(self) -> None:
        """Normalize type generation configuration.

        Supports:
        - True: Enable with defaults -> TypeGenConfig()
        - False/None: Disabled -> None
        - TypeGenConfig: Use as-is (presence = enabled)
        """
        if self.types is True:
            self.types = TypeGenConfig()
        elif self.types is False or self.types is None:
            self.types = None
            return
        self._resolve_type_paths(self.types)

    def _normalize_inertia(self) -> None:
        """Normalize inertia configuration.

        Supports:
        - True: Enable with defaults -> InertiaConfig()
        - False/None: Disabled -> None
        - InertiaConfig: Use as-is
        """
        if self.inertia is True:
            self.inertia = InertiaConfig()
        elif self.inertia is False:
            self.inertia = None

    def _normalize_spa_flag(self) -> None:
        if self.spa is True:
            self.spa = SPAConfig()

    def _normalize_logging(self) -> None:
        """Normalize logging configuration.

        Supports:
        - True: Enable with defaults -> LoggingConfig()
        - False/None: Use defaults -> LoggingConfig()
        - LoggingConfig: Use as-is
        """
        if self.logging is True or self.logging is None or self.logging is False:
            self.logging = LoggingConfig()

    def _apply_dev_mode_shortcut(self) -> None:
        if self.dev_mode:
            self.runtime.dev_mode = True

    def _auto_detect_mode(self) -> None:
        if self.mode is None:
            self.mode = self._detect_mode()
            self._mode_auto_detected = True

    def _auto_configure_inertia(self) -> None:
        """Auto-configure settings when Inertia is enabled.

        When Inertia is configured, automatically enable CSRF token injection
        in the SPA config, since Inertia forms need CSRF protection.
        """
        if isinstance(self.inertia, InertiaConfig) and isinstance(self.spa, SPAConfig) and not self.spa.inject_csrf:
            self.spa = replace(self.spa, inject_csrf=True)

    def _apply_ssr_mode_defaults(self) -> None:
        """Apply intelligent defaults for mode='ssr'.

        When mode='ssr' is set, automatically configure proxy_mode and spa_handler
        based on dev_mode and whether built assets exist:

        - Dev mode: proxy_mode='proxy', spa_handler=False
          (Proxy all non-API routes to the SSR/SSG framework dev server)
        - Prod mode with built assets: proxy_mode=None, spa_handler=True
          (Serve static SSG output like Astro's dist/)
        - Prod mode without built assets: proxy_mode=None, spa_handler=False
          (True SSR - Node server handles HTML, Litestar only serves API)
        """
        if self.mode != "ssr":
            return

        if self.runtime.dev_mode:
            env_proxy = os.getenv("VITE_PROXY_MODE")
            if env_proxy is None:
                self.runtime.proxy_mode = "proxy"
            self.runtime.spa_handler = False
        else:
            self.runtime.proxy_mode = None
            if self.has_built_assets():
                self.runtime.spa_handler = True
            else:
                self.runtime.spa_handler = False

    def _normalize_deploy(self) -> None:
        if self.deploy is True:
            self.deploy = DeployConfig(enabled=True)
        elif self.deploy is False:
            self.deploy = DeployConfig(enabled=False)

    def _resolve_type_paths(self, types: TypeGenConfig) -> None:
        """Resolve type generation paths relative to the configured root.

        Args:
            types: Type generation configuration to mutate.

        """
        root_dir = self.root_dir

        default_rel = Path("src/generated")
        default_openapi = default_rel / "openapi.json"
        default_routes = default_rel / "routes.json"
        default_page_props = default_rel / "inertia-pages.json"

        if types.openapi_path == default_openapi and types.output != default_rel:
            types.openapi_path = types.output / "openapi.json"
        if types.routes_path == default_routes and types.output != default_rel:
            types.routes_path = types.output / "routes.json"
        if types.page_props_path == default_page_props and types.output != default_rel:
            types.page_props_path = types.output / "inertia-pages.json"

        if types.routes_ts_path is None or (
            types.routes_ts_path == default_rel / "routes.ts" and types.output != default_rel
        ):
            types.routes_ts_path = types.output / "routes.ts"

        types.output = _to_root_path(root_dir, types.output)
        types.openapi_path = (
            _to_root_path(root_dir, types.openapi_path) if types.openapi_path else types.output / "openapi.json"
        )
        types.routes_path = (
            _to_root_path(root_dir, types.routes_path) if types.routes_path else types.output / "routes.json"
        )
        types.routes_ts_path = (
            _to_root_path(root_dir, types.routes_ts_path) if types.routes_ts_path else types.output / "routes.ts"
        )
        types.page_props_path = (
            _to_root_path(root_dir, types.page_props_path)
            if types.page_props_path
            else types.output / "inertia-pages.json"
        )

    def _ensure_spa_default(self) -> None:
        if self.mode in {"spa", "hybrid"} and self.spa is None:
            self.spa = SPAConfig()
        elif self.spa is None:
            self.spa = False

    def _auto_enable_dev_mode(self) -> None:
        if not self._mode_auto_detected:
            return

        auto_dev_mode = os.getenv("VITE_AUTO_DEV_MODE", "True") in TRUE_VALUES
        if (
            auto_dev_mode
            and not self.runtime.dev_mode
            and self.mode in {"spa", "hybrid"}
            and not self.has_built_assets()
        ):
            self.runtime.dev_mode = True

    def _warn_missing_assets(self) -> None:
        """Warn if running in production mode without built assets."""
        import sys

        if self.mode not in {"spa", "hybrid"}:
            return
        if self.runtime.dev_mode:
            return
        if self.has_built_assets():
            return

        cli_commands_skip_warning = {
            "install",
            "build",
            "init",
            "serve",
            "deploy",
            "doctor",
            "generate-types",
            "export-routes",
            "status",
        }
        argv_str = " ".join(sys.argv)
        if any(f"assets {cmd}" in argv_str for cmd in cli_commands_skip_warning):
            return

        if self.runtime.external_dev_server is not None:
            return

        bundle_path = self._resolve_to_root(self.bundle_dir)
        manifest_path = bundle_path / ".vite" / self.manifest_name
        logger.warning(
            "Vite manifest not found at %s. "
            "Run 'litestar assets build' (or 'npm run build') to build assets, "
            "or set dev_mode=True for development. "
            "Assets will not load correctly without built files or a running Vite dev server.",
            manifest_path,
        )

    def _detect_mode(self) -> Literal["spa", "template", "htmx", "hybrid"]:
        """Auto-detect the serving mode based on project structure.

        Detection order:
        1. If Inertia is enabled:
           a. Default to hybrid mode for SPA-style Inertia applications
           b. Hybrid mode works with AppHandler + HTML transformation
           c. index.html is served by Vite dev server in dev mode or built assets in production
           Note: If using Jinja2 templates with Inertia, set mode="template" explicitly.
        2. Check for index.html in resource_dir, root_dir, or static_dir → SPA
        3. Check if Jinja2 is installed and likely to be used → Template
        4. Default to SPA

        Returns:
            The detected mode.
        """
        inertia_enabled = isinstance(self.inertia, InertiaConfig)

        if inertia_enabled:
            return "hybrid"

        if any(path.exists() for path in self.candidate_index_html_paths()):
            return "spa"

        if JINJA_INSTALLED:
            return "template"

        return "spa"

    def validate_mode(self) -> None:
        """Validate the mode configuration against the project structure.

        Raises:
            ValueError: If the configuration is invalid for the selected mode.
        """
        if self.mode == "spa":
            index_candidates = self.candidate_index_html_paths()
            if not self.runtime.dev_mode and not any(path.exists() for path in index_candidates):
                joined_paths = ", ".join(str(path) for path in index_candidates)
                msg = (
                    "SPA mode requires index.html at one of: "
                    f"{joined_paths}. "
                    "Either create the file, run in dev mode, or switch to template mode."
                )
                raise ValueError(msg)

        elif self.mode == "hybrid":
            index_candidates = self.candidate_index_html_paths()
            if not self.runtime.dev_mode and not any(path.exists() for path in index_candidates):
                joined_paths = ", ".join(str(path) for path in index_candidates)
                msg = (
                    "Hybrid mode requires index.html at one of: "
                    f"{joined_paths}. "
                    "Either create the file or run in dev mode."
                )
                raise ValueError(msg)

        elif self.mode in {"template", "htmx"}:
            if not JINJA_INSTALLED:
                msg = (
                    f"{self.mode} mode requires Jinja2 to be installed. "
                    "Install it with: pip install litestar-vite[jinja]"
                )
                raise ValueError(msg)

    @property
    def executor(self) -> "JSExecutor":
        """Get the JavaScript executor instance.

        Returns:
            The configured JavaScript executor.
        """
        if self._executor_instance is None:
            self._executor_instance = self._create_executor()
        return self._executor_instance

    def reset_executor(self) -> None:
        """Reset the cached executor instance.

        Call this after modifying logging config to pick up new settings.
        """
        self._executor_instance = None

    def _create_executor(self) -> "JSExecutor":
        """Create the appropriate executor based on runtime config.

        Returns:
            An instance of the selected JSExecutor.
        """
        from litestar_vite.executor import (
            BunExecutor,
            DenoExecutor,
            NodeenvExecutor,
            NodeExecutor,
            PnpmExecutor,
            YarnExecutor,
        )

        executor_type = self.runtime.executor or "node"
        silent = self.logging_config.suppress_npm_output

        if executor_type == "bun":
            return BunExecutor(silent=silent)
        if executor_type == "deno":
            return DenoExecutor(silent=silent)
        if executor_type == "yarn":
            return YarnExecutor(silent=silent)
        if executor_type == "pnpm":
            return PnpmExecutor(silent=silent)
        if self.runtime.detect_nodeenv:
            return NodeenvExecutor(self, silent=silent)
        return NodeExecutor(silent=silent)

    @property
    def bundle_dir(self) -> Path:
        """Get bundle directory path.

        Returns:
            The configured bundle directory path.
        """
        return self.paths.bundle_dir if isinstance(self.paths.bundle_dir, Path) else Path(self.paths.bundle_dir)

    @property
    def resource_dir(self) -> Path:
        """Get resource directory path.

        Returns:
            The configured resource directory path.
        """
        return self.paths.resource_dir if isinstance(self.paths.resource_dir, Path) else Path(self.paths.resource_dir)

    @property
    def static_dir(self) -> Path:
        """Get static directory path.

        Returns:
            The configured static directory path.
        """
        return self.paths.static_dir if isinstance(self.paths.static_dir, Path) else Path(self.paths.static_dir)

    @property
    def root_dir(self) -> Path:
        """Get root directory path.

        Returns:
            The configured project root directory path.
        """
        return self.paths.root if isinstance(self.paths.root, Path) else Path(self.paths.root)

    @property
    def manifest_name(self) -> str:
        """Get manifest file name.

        Returns:
            The configured Vite manifest filename.
        """
        return self.paths.manifest_name

    @property
    def hot_file(self) -> str:
        """Get hot file name.

        Returns:
            The configured hotfile filename.
        """
        return self.paths.hot_file

    @property
    def asset_url(self) -> str:
        """Get asset URL.

        Returns:
            The configured asset URL prefix.
        """
        return self.paths.asset_url

    def _resolve_to_root(self, path: Path) -> Path:
        """Resolve a path relative to the configured root directory.

        Returns:
            The resolved absolute Path.
        """

        if path.is_absolute():
            return path
        return self.root_dir / path

    def candidate_index_html_paths(self) -> list[Path]:
        """Return possible index.html locations for SPA mode detection.

        Order mirrors the JS plugin auto-detection:
        1. bundle_dir/index.html (for production static builds like Astro/Nuxt/SvelteKit)
        2. resource_dir/index.html
        3. root_dir/index.html
        4. static_dir/index.html

        Returns:
            A de-duplicated list of candidate index.html paths, ordered by preference.
        """

        bundle_dir = self._resolve_to_root(self.bundle_dir)
        resource_dir = self._resolve_to_root(self.resource_dir)
        static_dir = self._resolve_to_root(self.static_dir)
        root_dir = self.root_dir

        candidates = [
            bundle_dir / "index.html",
            resource_dir / "index.html",
            root_dir / "index.html",
            static_dir / "index.html",
        ]

        unique: list[Path] = []
        seen: set[Path] = set()
        for path in candidates:
            if path in seen:
                continue
            seen.add(path)
            unique.append(path)
        return unique

    def has_built_assets(self) -> bool:
        """Check if production assets exist in the bundle directory.

        Returns:
            True if manifest.json or built index.html exists in bundle_dir.

        Note:
            This method checks the bundle_dir (output directory) for built artifacts,
            NOT source directories. The presence of source index.html in resource_dir
            does not indicate built assets exist.
        """
        bundle_path = self._resolve_to_root(self.bundle_dir)
        manifest_path = bundle_path / self.manifest_name
        index_path = bundle_path / "index.html"

        return manifest_path.exists() or index_path.exists()

    @property
    def host(self) -> str:
        """Get dev server host.

        Returns:
            The configured Vite dev server host.
        """
        return self.runtime.host

    @property
    def port(self) -> int:
        """Get dev server port.

        Returns:
            The configured Vite dev server port.
        """
        return self.runtime.port

    @property
    def protocol(self) -> str:
        """Get dev server protocol.

        Returns:
            The configured Vite dev server protocol.
        """
        return self.runtime.protocol

    @property
    def hot_reload(self) -> bool:
        """Check if hot reload is enabled (derived from dev_mode and proxy_mode).

        HMR requires dev_mode=True AND a Vite-based mode (vite, direct, or proxy/ssr).
        All modes support HMR since even SSR frameworks use Vite internally.

        Returns:
            True if hot reload is enabled, otherwise False.
        """
        return self.runtime.dev_mode and self.runtime.proxy_mode in {"vite", "direct", "proxy"}

    @property
    def is_dev_mode(self) -> bool:
        """Check if dev mode is enabled.

        Returns:
            True if dev mode is enabled, otherwise False.
        """
        return self.runtime.dev_mode

    @property
    def is_react(self) -> bool:
        """Check if React mode is enabled.

        Returns:
            True if React mode is enabled, otherwise False.
        """
        return self.runtime.is_react

    @property
    def ssr_enabled(self) -> bool:
        """Check if SSR is enabled.

        Returns:
            True if SSR is enabled, otherwise False.
        """
        return self.runtime.ssr_enabled

    @property
    def run_command(self) -> list[str]:
        """Get the run command.

        Returns:
            The argv list used to start the Vite dev server.
        """
        return self.runtime.run_command or ["npm", "run", "dev"]

    @property
    def build_command(self) -> list[str]:
        """Get the build command.

        Returns:
            The argv list used to build production assets.
        """
        return self.runtime.build_command or ["npm", "run", "build"]

    @property
    def build_watch_command(self) -> list[str]:
        """Get the watch command for building frontend in watch mode.

        Used by `litestar assets serve` when hot_reload is disabled.

        Returns:
            The command argv list used for watch builds.
        """
        return self.runtime.build_watch_command or ["npm", "run", "build", "--", "--watch"]

    @property
    def serve_command(self) -> "list[str] | None":
        """Get the serve command for running production server.

        Used by `litestar assets serve --production` for SSR frameworks.
        Returns None if not configured.

        Returns:
            The command argv list used to serve production assets, or None if not configured.
        """
        return self.runtime.serve_command

    @property
    def install_command(self) -> list[str]:
        """Get the install command.

        Returns:
            The argv list used to install frontend dependencies.
        """
        return self.runtime.install_command or ["npm", "install"]

    @property
    def health_check(self) -> bool:
        """Check if health check is enabled.

        Returns:
            True if health checks are enabled, otherwise False.
        """
        return self.runtime.health_check

    @property
    def set_environment(self) -> bool:
        """Check if environment should be set.

        Returns:
            True if Vite environment variables should be set, otherwise False.
        """
        return self.runtime.set_environment

    @property
    def set_static_folders(self) -> bool:
        """Check if static folders should be configured.

        Returns:
            True if static folders should be configured, otherwise False.
        """
        return self.runtime.set_static_folders

    @property
    def detect_nodeenv(self) -> bool:
        """Check if nodeenv detection is enabled.

        Returns:
            True if nodeenv detection is enabled, otherwise False.
        """
        return self.runtime.detect_nodeenv

    @property
    def proxy_mode(self) -> "Literal['vite', 'direct', 'proxy'] | None":
        """Get proxy mode.

        Returns:
            The configured proxy mode, or None if proxying is disabled.
        """
        return self.runtime.proxy_mode

    @property
    def external_dev_server(self) -> "ExternalDevServer | None":
        """Get external dev server config.

        Returns:
            External dev server configuration, or None if not configured.
        """
        if isinstance(self.runtime.external_dev_server, ExternalDevServer):
            return self.runtime.external_dev_server
        return None

    @property
    def spa_handler(self) -> bool:
        """Check if SPA handler auto-registration is enabled.

        Returns:
            True if the SPA handler should be auto-registered, otherwise False.
        """
        return self.runtime.spa_handler

    @property
    def http2(self) -> bool:
        """Check if HTTP/2 is enabled for proxy connections.

        Returns:
            True if HTTP/2 is enabled for proxy connections, otherwise False.
        """
        return self.runtime.http2

    @property
    def ssr_output_dir(self) -> "Path | None":
        """Get SSR output directory.

        Returns:
            The configured SSR output directory, or None if not configured.
        """
        if self.paths.ssr_output_dir is None:
            return None
        return (
            self.paths.ssr_output_dir
            if isinstance(self.paths.ssr_output_dir, Path)
            else Path(self.paths.ssr_output_dir)
        )

    @property
    def spa_config(self) -> "SPAConfig | None":
        """Get SPA configuration if enabled, or None if disabled.

        Returns:
            SPAConfig instance if spa transformations are enabled, None otherwise.
        """
        if isinstance(self.spa, SPAConfig):
            return self.spa
        return None

    @property
    def deploy_config(self) -> "DeployConfig | None":
        """Get deploy configuration if enabled.

        Returns:
            DeployConfig instance when deployment is configured, None otherwise.
        """
        if isinstance(self.deploy, DeployConfig) and self.deploy.enabled:
            return self.deploy
        return None

    @property
    def logging_config(self) -> LoggingConfig:
        """Get logging configuration.

        Returns:
            LoggingConfig instance (always available after normalization).
        """
        if isinstance(self.logging, LoggingConfig):
            return self.logging
        return LoggingConfig()
