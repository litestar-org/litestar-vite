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

import os
from dataclasses import dataclass, field
from importlib.util import find_spec
from pathlib import Path
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from litestar_vite.executor import JSExecutor

from litestar_vite.deploy import DeployConfig

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


def _resolve_proxy_mode() -> Literal["vite_proxy", "vite_direct", "external_proxy"]:
    """Resolve proxy_mode from environment variable.

    Reads VITE_PROXY_MODE env var. Valid values:
    - "vite_proxy" (default): Proxy to internal Vite server
    - "vite_direct": Expose Vite port directly
    - "external_proxy": Proxy to external dev server

    Returns:
        The resolved proxy mode.
    """
    env_value = os.getenv("VITE_PROXY_MODE", "vite_proxy").lower()
    if env_value in {"vite_direct", "direct"}:
        return "vite_direct"
    if env_value in {"external_proxy", "external"}:
        return "external_proxy"
    return "vite_proxy"


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

    Attributes:
        target: The URL of the external dev server (e.g., "http://localhost:4200").
        http2: Enable HTTP/2 for proxy connections.
        enabled: Whether the external proxy is enabled.
    """

    target: str = "http://localhost:4200"
    http2: bool = False
    enabled: bool = True


@dataclass
class RuntimeConfig:
    """Runtime execution settings.

    Attributes:
        dev_mode: Enable development mode with HMR/watch.
        proxy_mode: Proxy handling mode:
            - "vite_proxy": Proxy to internal Vite server (default, single-port with HMR)
            - "vite_direct": Expose Vite port directly (multi-port)
            - "external_proxy": Proxy to external dev server (Angular CLI, Next.js, etc.)
        external_dev_server: Configuration for external dev server (required when proxy_mode="external_proxy").
        host: Vite dev server host.
        port: Vite dev server port.
        protocol: Protocol for dev server (http/https).
        executor: JavaScript runtime executor (node, bun, deno).
        run_command: Custom command to run Vite dev server (auto-detect if None).
        build_command: Custom command to build with Vite (auto-detect if None).
        build_watch_command: Custom command for watch mode build.
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
    proxy_mode: "Literal['vite_proxy', 'vite_direct', 'external_proxy']" = field(default_factory=_resolve_proxy_mode)
    external_dev_server: "ExternalDevServer | str | None" = None
    host: str = field(default_factory=lambda: os.getenv("VITE_HOST", "localhost"))
    port: int = field(default_factory=lambda: int(os.getenv("VITE_PORT", "5173")))
    protocol: Literal["http", "https"] = "http"
    executor: "Literal['node', 'bun', 'deno', 'yarn', 'pnpm'] | None" = None
    run_command: "list[str] | None" = None
    build_command: "list[str] | None" = None
    build_watch_command: "list[str] | None" = None
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
        # Normalize external_dev_server: string → ExternalDevServer
        if isinstance(self.external_dev_server, str):
            self.external_dev_server = ExternalDevServer(target=self.external_dev_server)

        # Validate external_proxy mode requires external_dev_server
        if self.proxy_mode == "external_proxy" and self.external_dev_server is None:
            msg = "external_dev_server is required when proxy_mode='external_proxy'"
            raise ValueError(msg)

        if self.executor is None:
            self.executor = "node"

        # Set default commands based on executor if not explicitly provided
        executor_commands = {
            "node": {
                "run": ["npm", "run", "dev"],
                "build": ["npm", "run", "build"],
                "build_watch": ["npm", "run", "watch"],
                "install": ["npm", "install"],
            },
            "bun": {
                "run": ["bun", "run", "dev"],
                "build": ["bun", "run", "build"],
                "build_watch": ["bun", "run", "watch"],
                "install": ["bun", "install"],
            },
            "deno": {
                "run": ["deno", "task", "dev"],
                "build": ["deno", "task", "build"],
                "build_watch": ["deno", "task", "watch"],
                "install": ["deno", "install"],
            },
            "yarn": {
                "run": ["yarn", "dev"],
                "build": ["yarn", "build"],
                "build_watch": ["yarn", "watch"],
                "install": ["yarn", "install"],
            },
            "pnpm": {
                "run": ["pnpm", "dev"],
                "build": ["pnpm", "build"],
                "build_watch": ["pnpm", "watch"],
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
            if self.install_command is None:
                self.install_command = cmds["install"]


@dataclass
class TypeGenConfig:
    """Type generation settings.

    Attributes:
        enabled: Enable type generation pipeline.
        output: Output directory for generated types.
        openapi_path: Path to export OpenAPI schema.
        routes_path: Path to export routes metadata.
        generate_zod: Generate Zod schemas from OpenAPI.
        generate_sdk: Generate SDK client from OpenAPI.
        watch_patterns: File patterns to watch for type regeneration.
    """

    enabled: bool = False
    output: Path = field(default_factory=lambda: Path("src/generated"))
    openapi_path: Path = field(default_factory=lambda: Path("src/generated/openapi.json"))
    routes_path: Path = field(default_factory=lambda: Path("src/generated/routes.json"))
    generate_zod: bool = True
    generate_sdk: bool = False
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


def _optional_str_list_factory() -> "list[str] | None":
    """Factory function returning None for optional list fields.

    Returns:
        None
    """
    return None


def _default_routes_exclude_factory() -> list[str]:
    """Factory function for default route exclusions.

    Returns:
        List of default route exclusion patterns.
    """
    return ["vite_spa"]  # Exclude the catch-all SPA handler route by default


@dataclass
class SPAConfig:
    """Configuration for SPA HTML transformations.

    This configuration controls how the SPA HTML is transformed before serving,
    including route metadata injection, CSRF token injection, and Inertia.js
    page data handling.

    Attributes:
        inject_routes: Whether to inject route metadata into HTML.
        inject_csrf: Whether to inject CSRF token into HTML (as window.__LITESTAR_CSRF__).
        routes_var_name: Global variable name for routes (e.g., window.__LITESTAR_ROUTES__).
        csrf_var_name: Global variable name for CSRF token (e.g., window.__LITESTAR_CSRF__).
        routes_include: Whitelist patterns for route filtering (None = include all).
        routes_exclude: Blacklist patterns for route filtering (None = exclude none).
        app_selector: CSS selector for the app root element (used for data attributes).
        cache_transformed_html: Cache transformed HTML in production; disabled when inject_csrf=True because CSRF tokens are per-request.
    """

    inject_routes: bool = True
    inject_csrf: bool = True
    routes_var_name: str = "__LITESTAR_ROUTES__"
    csrf_var_name: str = "__LITESTAR_CSRF__"
    routes_include: "list[str] | None" = field(default_factory=_optional_str_list_factory)
    routes_exclude: "list[str] | None" = field(default_factory=_default_routes_exclude_factory)
    app_selector: str = "#app"
    cache_transformed_html: bool = True


def _str_object_dict_factory() -> dict[str, object]:
    """Factory function for empty dict (typed for pyright).

    Returns:
        Empty dictionary.
    """
    return {}


def _str_list_factory() -> list[str]:
    """Factory function for empty string list (typed for pyright).

    Returns:
        Empty list.
    """
    return []


@dataclass
class InertiaConfig:
    """Inertia.js specific settings.

    Attributes:
        enabled: Enable Inertia.js integration.
        root_template: Root HTML template for Inertia.
        include_routes: Include routes metadata in page props.
        include_flash: Include flash messages in page props.
        include_errors: Include validation errors in page props.
        extra_static_page_props: Additional static props to include on every page.
        extra_session_page_props: Session keys to include as page props.
    """

    enabled: bool = False
    root_template: str = "index.html"
    include_routes: bool = True
    include_flash: bool = True
    include_errors: bool = True
    extra_static_page_props: dict[str, object] = field(default_factory=_str_object_dict_factory)
    extra_session_page_props: list[str] = field(default_factory=_str_list_factory)


@dataclass
class ViteConfig:
    """Root Vite configuration.

    This is the main configuration class that combines all sub-configurations.
    Supports shortcuts for common configurations:

    - dev_mode: Shortcut for runtime.dev_mode
    - types=True: Enable type generation with defaults
    - inertia=True: Enable Inertia.js with defaults

    Mode auto-detection:

    - If mode is not explicitly set:

      - Checks for index.html in common locations -> SPA mode
      - Checks if Jinja2 template engine is configured -> Template mode
      - Otherwise defaults to SPA mode

    Dev-mode auto-enable:

    - If mode="spa" and no built assets are found in bundle_dir, dev_mode is
      enabled automatically (unless VITE_AUTO_DEV_MODE=False).

    - Explicit mode parameter overrides auto-detection

    Attributes:
        mode: Serving mode - "spa", "template", or "htmx". Auto-detected if not set.
        paths: File system paths configuration.
        runtime: Runtime execution settings.
        types: Type generation settings (True enables with defaults).
        inertia: Inertia.js settings (True enables with defaults).
        spa: SPA transformation settings (True enables with defaults, False disables).
        dev_mode: Convenience shortcut for runtime.dev_mode.
        base_url: Base URL for production assets (CDN support).
        deploy: Deployment configuration for CDN publishing.
    """

    mode: "Literal['spa', 'template', 'htmx'] | None" = None
    paths: PathConfig = field(default_factory=PathConfig)
    runtime: RuntimeConfig = field(default_factory=RuntimeConfig)
    types: "TypeGenConfig | bool" = field(default_factory=lambda: TypeGenConfig(enabled=True))
    inertia: "InertiaConfig | bool" = False
    spa: "SPAConfig | bool | None" = None
    dev_mode: bool = False
    base_url: "str | None" = field(default_factory=lambda: os.getenv("VITE_BASE_URL"))
    deploy: "DeployConfig | bool" = False

    # Internal: resolved executor instance
    _executor_instance: "JSExecutor | None" = field(default=None, repr=False)
    _mode_auto_detected: bool = field(default=False, repr=False)

    def __post_init__(self) -> None:
        """Normalize configurations and apply shortcuts."""
        self._normalize_types()
        self._normalize_inertia()
        self._normalize_spa_flag()
        self._apply_dev_mode_shortcut()
        self._auto_detect_mode()
        self._normalize_deploy()
        self._ensure_spa_default()
        self._auto_enable_dev_mode()

    def _normalize_types(self) -> None:
        if self.types is True:
            self.types = TypeGenConfig(enabled=True)
        elif self.types is False:
            self.types = TypeGenConfig(enabled=False)
        self._resolve_type_paths(self.types)

    def _normalize_inertia(self) -> None:
        if self.inertia is True:
            self.inertia = InertiaConfig(enabled=True)
        elif self.inertia is False:
            self.inertia = InertiaConfig(enabled=False)

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

        types.output = _to_root(types.output)
        types.openapi_path = _to_root(types.openapi_path)
        types.routes_path = _to_root(types.routes_path)

    def _ensure_spa_default(self) -> None:
        if self.mode == "spa" and self.spa is None:
            self.spa = SPAConfig()
        elif self.spa is None:
            self.spa = False

    def _auto_enable_dev_mode(self) -> None:
        # Only auto-enable when mode was auto-detected (user didn't force spa/template)
        if not self._mode_auto_detected:
            return

        auto_dev_mode = os.getenv("VITE_AUTO_DEV_MODE", "True") in TRUE_VALUES
        if auto_dev_mode and not self.runtime.dev_mode and self.mode == "spa" and not self.has_built_assets():
            self.runtime.dev_mode = True

    def _detect_mode(self) -> Literal["spa", "template", "htmx"]:
        """Auto-detect the serving mode based on project structure.

        Detection order:
        1. Check for index.html in resource_dir, root_dir, or public_dir → SPA
        2. Check if Jinja2 is installed and likely to be used → Template
        3. Default to SPA

        Returns:
            The detected mode.
        """
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
        1. resource_dir/index.html
        2. root_dir/index.html
        3. public_dir/index.html
        """

        resource_dir = self._resolve_to_root(self.resource_dir)
        public_dir = self._resolve_to_root(self.public_dir)
        root_dir = self.root_dir

        candidates = [
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
        """Check if production assets exist (index.html present).

        Returns:
            True if any candidate index.html file exists, False otherwise.
        """

        # For SPA mode the critical artifact is index.html. Manifest is helpful,
        # but a stale manifest without an index leads to broken pages and
        # prevents dev_mode auto-enable. Use the index as the signal.
        return any(path.exists() for path in self.candidate_index_html_paths())

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

        HMR requires dev_mode=True AND a Vite mode (vite_proxy, vite_direct).
        External proxy mode never has HMR since it uses a non-Vite server.
        """
        return self.runtime.dev_mode and self.runtime.proxy_mode in {"vite_proxy", "vite_direct"}

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
        """Get the build watch command."""
        return self.runtime.build_watch_command or ["npm", "run", "watch"]

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
    def proxy_mode(self) -> Literal["vite_proxy", "vite_direct", "external_proxy"]:
        """Get proxy mode."""
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
