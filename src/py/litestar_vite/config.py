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
from typing import TYPE_CHECKING, Any, Literal, cast

logger = logging.getLogger("litestar_vite")

if TYPE_CHECKING:
    from litestar_vite.executor import JSExecutor

__all__ = (
    "FSSPEC_INSTALLED",
    "JINJA_INSTALLED",
    "DeployConfig",
    "ExternalDevServer",
    "InertiaConfig",
    "PathConfig",
    "RuntimeConfig",
    "SPAConfig",
    "TypeGenConfig",
    "ViteConfig",
)

TRUE_VALUES = {"True", "true", "1", "yes", "Y", "T"}
JINJA_INSTALLED = bool(find_spec("jinja2"))
FSSPEC_INSTALLED = bool(find_spec("fsspec"))


def _empty_dict_factory() -> dict[str, Any]:
    """Factory for empty dict with proper type annotation.

    Returns:
        An empty dictionary for storing page props.
    """
    return {}


def _empty_set_factory() -> set[str]:
    """Factory for empty set with proper type annotation.

    Returns:
        An empty set for storing session property keys.
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
    """Factory for empty storage options dict.

    Returns:
        An empty dictionary for storage provider options.
    """
    return cast("dict[str, Any]", {})


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
class InertiaConfig:
    """Configuration for InertiaJS support.

    This is the canonical configuration class for Inertia.js integration.
    Presence of an InertiaConfig instance indicates Inertia is enabled.

    Attributes:
        root_template: Name of the root template to use.
        component_opt_keys: Identifiers for getting inertia component from route opts.
        exclude_from_js_routes_key: Identifier to exclude route from generated routes.
        redirect_unauthorized_to: Path for unauthorized request redirects.
        redirect_404: Path for 404 request redirects.
        extra_static_page_props: Static props added to every page response.
        extra_session_page_props: Session keys to include in page props.
        spa_mode: Use SPA mode (HtmlTransformer) instead of Jinja2 templates.
        app_selector: CSS selector for the app root element in SPA mode.
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
    exclude_from_js_routes_key: str = "exclude_from_routes"
    """An identifier to use on routes to exclude a route from the generated routes typescript file."""
    redirect_unauthorized_to: "str | None" = None
    """Optionally supply a path where unauthorized requests should redirect."""
    redirect_404: "str | None" = None
    """Optionally supply a path where 404 requests should redirect."""
    extra_static_page_props: "dict[str, Any]" = field(default_factory=_empty_dict_factory)
    """A dictionary of values to automatically add in to page props on every response."""
    extra_session_page_props: "set[str]" = field(default_factory=_empty_set_factory)
    """A set of session keys for which the value automatically be added (if it exists) to the response."""
    spa_mode: bool = False
    """Enable SPA mode to render without Jinja2 templates.

    When True, InertiaResponse uses ViteSPAHandler and HtmlTransformer
    to inject page data instead of rendering Jinja2 templates.
    This allows template-less Inertia applications.
    """
    app_selector: str = "#app"
    """CSS selector for the app root element.

    Used in SPA mode to locate the element where data-page attribute
    should be injected. Defaults to "#app".
    """


def _resolve_proxy_mode() -> "Literal['vite', 'direct', 'proxy'] | None":
    """Resolve proxy_mode from environment variable.

    Reads VITE_PROXY_MODE env var. Valid values:
    - "vite" (default): Proxy to internal Vite server (whitelist - assets only)
    - "direct": Expose Vite port directly (no proxy)
    - "proxy" / "ssr": Proxy everything except Litestar routes (blacklist)
    - "none": Disable proxy (for production)

    Returns:
        The resolved proxy mode, or None if disabled.
    """
    env_value = os.getenv("VITE_PROXY_MODE", "vite").lower()
    if env_value in {"none", "disabled", "off"}:
        return None
    if env_value in {"vite_direct", "direct"}:
        return "direct"
    if env_value in {"external_proxy", "proxy", "ssr", "external"}:
        return "proxy"
    if env_value in {"vite_proxy", "vite"}:
        return "vite"
    return "vite"


@dataclass
class PathConfig:
    """File system paths configuration.

    Attributes:
        root: The root directory of the project. Defaults to current working directory.
        bundle_dir: Location of compiled assets and manifest.json.
        resource_dir: TypeScript/JavaScript source directory (equivalent to ./src in Vue/React).
        public_dir: Static public assets directory (served as-is by Vite).
        manifest_name: Name of the Vite manifest file.
        hot_file: Name of the hot file indicating dev server URL.
        asset_url: Base URL for static asset references (prepended to Vite output).
        ssr_output_dir: SSR output directory (optional).
    """

    root: "str | Path" = field(default_factory=Path.cwd)
    bundle_dir: "str | Path" = field(default_factory=lambda: Path("public"))
    resource_dir: "str | Path" = field(default_factory=lambda: Path("src"))
    public_dir: "str | Path" = field(default_factory=lambda: Path("public"))
    manifest_name: str = "manifest.json"
    hot_file: str = "hot"
    asset_url: str = field(default_factory=lambda: os.getenv("ASSET_URL", "/static/"))
    ssr_output_dir: "str | Path | None" = None

    def __post_init__(self) -> None:
        """Normalize path types to Path objects."""
        if isinstance(self.root, str):
            object.__setattr__(self, "root", Path(self.root))
        if isinstance(self.bundle_dir, str):
            object.__setattr__(self, "bundle_dir", Path(self.bundle_dir))
        if isinstance(self.resource_dir, str):
            object.__setattr__(self, "resource_dir", Path(self.resource_dir))
        if isinstance(self.public_dir, str):
            object.__setattr__(self, "public_dir", Path(self.public_dir))
        if isinstance(self.ssr_output_dir, str):
            object.__setattr__(self, "ssr_output_dir", Path(self.ssr_output_dir))


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
            - "vite" (default): Proxy Vite assets only (whitelist - SPA mode)
            - "direct": Expose Vite port directly (no proxy)
            - "proxy" / "ssr": Proxy everything except Litestar routes (blacklist - SSR mode)
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
    proxy_mode: "Literal['vite', 'direct', 'proxy', 'ssr'] | None" = field(default_factory=_resolve_proxy_mode)
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
        # Normalize proxy_mode: "ssr" is an alias for "proxy"
        if self.proxy_mode == "ssr":
            self.proxy_mode = "proxy"

        # Normalize external_dev_server: string → ExternalDevServer
        if isinstance(self.external_dev_server, str):
            self.external_dev_server = ExternalDevServer(target=self.external_dev_server)

        # Auto-set proxy_mode="proxy" when external_dev_server is configured
        # External dev servers (Angular CLI, Next.js, etc.) need blacklist proxy mode
        # Override default "vite" mode which only proxies Vite-specific routes
        if self.external_dev_server is not None and self.proxy_mode in (None, "vite"):
            self.proxy_mode = "proxy"

        # Note: proxy mode no longer requires external_dev_server - it can read
        # the target URL from the hotfile for SSR frameworks using Vite internally

        if self.executor is None:
            self.executor = "node"

        # Set default commands based on executor if not explicitly provided
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
        watch_patterns: File patterns to watch for type regeneration.
    """

    output: Path = field(default_factory=lambda: Path("src/generated"))
    openapi_path: Path = field(default_factory=lambda: Path("src/generated/openapi.json"))
    routes_path: Path = field(default_factory=lambda: Path("src/generated/routes.json"))
    routes_ts_path: "Path | None" = None
    generate_zod: bool = False
    generate_sdk: bool = True
    generate_routes: bool = True
    watch_patterns: list[str] = field(
        default_factory=lambda: ["**/routes.py", "**/handlers.py", "**/controllers/**/*.py"]
    )

    def __post_init__(self) -> None:
        """Normalize path types."""
        if isinstance(self.output, str):
            self.output = Path(self.output)
        if isinstance(self.openapi_path, str):
            self.openapi_path = Path(self.openapi_path)
        if isinstance(self.routes_path, str):
            self.routes_path = Path(self.routes_path)
        if isinstance(self.routes_ts_path, str):
            self.routes_ts_path = Path(self.routes_ts_path)


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

      - If Inertia is enabled with spa_mode=True -> Hybrid mode
      - If Inertia is enabled without spa_mode -> Template mode
      - Checks for index.html in common locations -> SPA mode
      - Checks if Jinja2 template engine is configured -> Template mode
      - Otherwise defaults to SPA mode

    Dev-mode auto-enable:

    - If mode="spa" and no built assets are found in bundle_dir, dev_mode is
      enabled automatically (unless VITE_AUTO_DEV_MODE=False).

    - Explicit mode parameter overrides auto-detection

    Attributes:
        mode: Serving mode - "spa", "template", "htmx", or "hybrid". Auto-detected if not set.
        paths: File system paths configuration.
        runtime: Runtime execution settings.
        types: Type generation settings (True/TypeGenConfig enables, False/None disables).
        inertia: Inertia.js settings (True/InertiaConfig enables, False/None disables).
        spa: SPA transformation settings (True enables with defaults, False disables).
        dev_mode: Convenience shortcut for runtime.dev_mode.
        base_url: Base URL for production assets (CDN support).
        deploy: Deployment configuration for CDN publishing.
    """

    mode: "Literal['spa', 'template', 'htmx', 'hybrid', 'ssr', 'ssg'] | None" = None
    paths: PathConfig = field(default_factory=PathConfig)
    runtime: RuntimeConfig = field(default_factory=RuntimeConfig)
    types: "TypeGenConfig | bool | None" = None
    inertia: "InertiaConfig | bool | None" = None
    spa: "SPAConfig | bool | None" = None
    dev_mode: bool = False
    base_url: "str | None" = field(default_factory=lambda: os.getenv("VITE_BASE_URL"))
    deploy: "DeployConfig | bool" = False

    # Internal: resolved executor instance
    _executor_instance: "JSExecutor | None" = field(default=None, repr=False)
    _mode_auto_detected: bool = field(default=False, repr=False)

    def __post_init__(self) -> None:
        """Normalize configurations and apply shortcuts."""
        self._normalize_mode()
        self._normalize_types()
        self._normalize_inertia()
        self._normalize_spa_flag()
        self._apply_dev_mode_shortcut()
        self._auto_detect_mode()
        self._sync_inertia_spa_mode()
        self._apply_ssr_mode_defaults()
        self._normalize_deploy()
        self._ensure_spa_default()
        self._auto_enable_dev_mode()
        self._warn_missing_assets()

    def _normalize_mode(self) -> None:
        """Normalize mode aliases.

        - 'ssg' (Static Site Generation) is an alias for 'ssr' since both need
          proxy mode in development (to forward to framework dev server) but
          serve static files in production. The key difference is just semantic:
          SSG builds static HTML at build time, SSR renders at request time,
          but the Litestar integration behavior is identical.
        """
        if self.mode == "ssg":
            self.mode = "ssr"

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
        # TypeGenConfig instance - resolve paths
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
        # InertiaConfig instance is used as-is

    def _normalize_spa_flag(self) -> None:
        if self.spa is True:
            self.spa = SPAConfig()
        # spa=False left as-is; spa=None handled later

    def _apply_dev_mode_shortcut(self) -> None:
        if self.dev_mode:
            self.runtime.dev_mode = True

    def _auto_detect_mode(self) -> None:
        if self.mode is None:
            self.mode = self._detect_mode()
            self._mode_auto_detected = True

    def _sync_inertia_spa_mode(self) -> None:
        """Sync InertiaConfig.spa_mode with detected mode.

        When mode='hybrid' is detected (from index.html presence),
        set InertiaConfig.spa_mode=True so InertiaResponse uses
        HtmlTransformer instead of Jinja templates.
        """
        if self.mode == "hybrid" and isinstance(self.inertia, InertiaConfig):
            self.inertia.spa_mode = True

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
            # Dev mode: proxy to framework dev server (Astro/Nuxt/SvelteKit)
            # Only override proxy_mode if user didn't explicitly set it via env var
            env_proxy = os.getenv("VITE_PROXY_MODE")
            if env_proxy is None:
                self.runtime.proxy_mode = "proxy"
            # Disable SPA handler to avoid route conflicts with SSR proxy controller
            self.runtime.spa_handler = False
        else:
            # Production mode: no proxy needed
            self.runtime.proxy_mode = None
            # Auto-detect: if built assets exist (SSG), enable SPA handler to serve them
            # Otherwise (true SSR), assume external Node server handles HTML
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
        """Resolve type generation paths relative to the configured root."""

        def _to_root(p: Path) -> Path:
            return p if p.is_absolute() else (self.paths.root / p)

        default_rel = Path("src/generated")
        default_openapi = default_rel / "openapi.json"
        default_routes = default_rel / "routes.json"

        # If user only set output, cascade defaults under that output
        if types.openapi_path == default_openapi and types.output != default_rel:
            types.openapi_path = types.output / "openapi.json"
        if types.routes_path == default_routes and types.output != default_rel:
            types.routes_path = types.output / "routes.json"

        # Set default routes_ts_path if not specified
        if types.routes_ts_path is None or (
            types.routes_ts_path == default_rel / "routes.ts" and types.output != default_rel
        ):
            types.routes_ts_path = types.output / "routes.ts"

        types.output = _to_root(types.output)
        types.openapi_path = _to_root(types.openapi_path)
        types.routes_path = _to_root(types.routes_path)
        types.routes_ts_path = _to_root(types.routes_ts_path)

    def _ensure_spa_default(self) -> None:
        if self.mode in {"spa", "hybrid"} and self.spa is None:
            self.spa = SPAConfig()
        elif self.spa is None:
            self.spa = False

    def _auto_enable_dev_mode(self) -> None:
        # Only auto-enable when mode was auto-detected (user didn't force spa/template)
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

        # Skip warning for CLI commands that don't serve the app
        # These commands just need the config but don't need built assets
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

        # Skip warning when using external dev server (e.g., Angular CLI, Next.js)
        # These don't use Vite's manifest but have their own build system
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
           a. If spa_mode=True (explicit) → Hybrid
           b. If spa_mode=False (explicit) → Template (Jinja-based)
           c. If index.html exists → Hybrid (auto-detected)
           d. Otherwise → Template (Jinja-based)
        2. Check for index.html in resource_dir, root_dir, or public_dir → SPA
        3. Check if Jinja2 is installed and likely to be used → Template
        4. Default to SPA

        Returns:
            The detected mode.
        """
        # Check if Inertia is enabled (presence of config = enabled)
        inertia_enabled = isinstance(self.inertia, InertiaConfig)

        if inertia_enabled:
            # If spa_mode is explicitly True, use hybrid mode
            if self.inertia.spa_mode:  # type: ignore[union-attr]
                return "hybrid"

            # Auto-detect: if index.html exists, use hybrid mode (HtmlTransformer)
            # This means users don't need to set spa_mode=True when they have an index.html
            if any(path.exists() for path in self.candidate_index_html_paths()):
                return "hybrid"

            # No index.html found - fall back to template mode (Jinja-based Inertia)
            return "template"

        # Check for index.html in expected locations (SPA indicator)
        if any(path.exists() for path in self.candidate_index_html_paths()):
            return "spa"

        # If Jinja2 is installed, default to template mode
        # (User may be using Jinja templates for server-rendered pages)
        if JINJA_INSTALLED:
            return "template"

        # Default to SPA
        return "spa"

    def validate_mode(self) -> None:
        """Validate the mode configuration against the project structure.

        Raises:
            ValueError: If the configuration is invalid for the selected mode.
        """
        if self.mode == "spa":
            # SPA mode validation
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
            # Hybrid mode validation - needs index.html like SPA mode
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
            # Template mode should have Jinja2 available
            if not JINJA_INSTALLED:
                msg = (
                    f"{self.mode} mode requires Jinja2 to be installed. "
                    "Install it with: pip install litestar-vite[jinja]"
                )
                raise ValueError(msg)

    @property
    def executor(self) -> "JSExecutor":
        """Get the JavaScript executor instance."""
        if self._executor_instance is None:
            self._executor_instance = self._create_executor()
        return self._executor_instance

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

        if executor_type == "bun":
            return BunExecutor()
        if executor_type == "deno":
            return DenoExecutor()
        if executor_type == "yarn":
            return YarnExecutor()
        if executor_type == "pnpm":
            return PnpmExecutor()
        # Default to node
        if self.runtime.detect_nodeenv:
            return NodeenvExecutor(self)
        return NodeExecutor()

    # Convenience properties for backward compatibility and ease of use
    @property
    def bundle_dir(self) -> Path:
        """Get bundle directory path."""
        # __post_init__ normalizes strings to Path
        return self.paths.bundle_dir if isinstance(self.paths.bundle_dir, Path) else Path(self.paths.bundle_dir)

    @property
    def resource_dir(self) -> Path:
        """Get resource directory path."""
        # __post_init__ normalizes strings to Path
        return self.paths.resource_dir if isinstance(self.paths.resource_dir, Path) else Path(self.paths.resource_dir)

    @property
    def public_dir(self) -> Path:
        """Get public directory path."""
        # __post_init__ normalizes strings to Path
        return self.paths.public_dir if isinstance(self.paths.public_dir, Path) else Path(self.paths.public_dir)

    @property
    def root_dir(self) -> Path:
        """Get root directory path."""
        # __post_init__ normalizes strings to Path
        return self.paths.root if isinstance(self.paths.root, Path) else Path(self.paths.root)

    @property
    def manifest_name(self) -> str:
        """Get manifest file name."""
        return self.paths.manifest_name

    @property
    def hot_file(self) -> str:
        """Get hot file name."""
        return self.paths.hot_file

    @property
    def asset_url(self) -> str:
        """Get asset URL."""
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
        4. public_dir/index.html
        """

        bundle_dir = self._resolve_to_root(self.bundle_dir)
        resource_dir = self._resolve_to_root(self.resource_dir)
        public_dir = self._resolve_to_root(self.public_dir)
        root_dir = self.root_dir

        candidates = [
            bundle_dir / "index.html",
            resource_dir / "index.html",
            root_dir / "index.html",
            public_dir / "index.html",
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

        # Check for Vite manifest (primary indicator of built assets)
        # or index.html in the bundle output directory
        return manifest_path.exists() or index_path.exists()

    @property
    def host(self) -> str:
        """Get dev server host."""
        return self.runtime.host

    @property
    def port(self) -> int:
        """Get dev server port."""
        return self.runtime.port

    @property
    def protocol(self) -> str:
        """Get dev server protocol."""
        return self.runtime.protocol

    @property
    def hot_reload(self) -> bool:
        """Check if hot reload is enabled (derived from dev_mode and proxy_mode).

        HMR requires dev_mode=True AND a Vite-based mode (vite, direct, or proxy/ssr).
        All modes support HMR since even SSR frameworks use Vite internally.
        """
        return self.runtime.dev_mode and self.runtime.proxy_mode in {"vite", "direct", "proxy"}

    @property
    def is_dev_mode(self) -> bool:
        """Check if dev mode is enabled."""
        return self.runtime.dev_mode

    @property
    def is_react(self) -> bool:
        """Check if React mode is enabled."""
        return self.runtime.is_react

    @property
    def ssr_enabled(self) -> bool:
        """Check if SSR is enabled."""
        return self.runtime.ssr_enabled

    @property
    def run_command(self) -> list[str]:
        """Get the run command."""
        return self.runtime.run_command or ["npm", "run", "dev"]

    @property
    def build_command(self) -> list[str]:
        """Get the build command."""
        return self.runtime.build_command or ["npm", "run", "build"]

    @property
    def build_watch_command(self) -> list[str]:
        """Get the watch command for building frontend in watch mode.

        Used by `litestar assets serve` when hot_reload is disabled.
        """
        return self.runtime.build_watch_command or ["npm", "run", "build", "--", "--watch"]

    @property
    def serve_command(self) -> "list[str] | None":
        """Get the serve command for running production server.

        Used by `litestar assets serve --production` for SSR frameworks.
        Returns None if not configured.
        """
        return self.runtime.serve_command

    @property
    def install_command(self) -> list[str]:
        """Get the install command."""
        return self.runtime.install_command or ["npm", "install"]

    @property
    def health_check(self) -> bool:
        """Check if health check is enabled."""
        return self.runtime.health_check

    @property
    def set_environment(self) -> bool:
        """Check if environment should be set."""
        return self.runtime.set_environment

    @property
    def set_static_folders(self) -> bool:
        """Check if static folders should be configured."""
        return self.runtime.set_static_folders

    @property
    def detect_nodeenv(self) -> bool:
        """Check if nodeenv detection is enabled."""
        return self.runtime.detect_nodeenv

    @property
    def proxy_mode(self) -> "Literal['vite', 'direct', 'proxy', 'ssr'] | None":
        """Get proxy mode. Note: 'ssr' is normalized to 'proxy' at runtime."""
        return self.runtime.proxy_mode

    @property
    def external_dev_server(self) -> "ExternalDevServer | None":
        """Get external dev server config."""
        if isinstance(self.runtime.external_dev_server, ExternalDevServer):
            return self.runtime.external_dev_server
        return None

    @property
    def spa_handler(self) -> bool:
        """Check if SPA handler auto-registration is enabled."""
        return self.runtime.spa_handler

    @property
    def http2(self) -> bool:
        """Check if HTTP/2 is enabled for proxy connections."""
        return self.runtime.http2

    @property
    def ssr_output_dir(self) -> "Path | None":
        """Get SSR output directory."""
        # __post_init__ normalizes strings to Path
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
