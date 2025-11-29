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
from typing import TYPE_CHECKING, Literal, Optional, Union

if TYPE_CHECKING:
    from litestar_vite.executor import JSExecutor

__all__ = (
    "JINJA_INSTALLED",
    "InertiaConfig",
    "PathConfig",
    "RuntimeConfig",
    "SPAConfig",
    "TypeGenConfig",
    "ViteConfig",
)

TRUE_VALUES = {"True", "true", "1", "yes", "Y", "T"}
JINJA_INSTALLED = bool(find_spec("jinja2"))


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

    root: "Union[str, Path]" = field(default_factory=Path.cwd)
    bundle_dir: "Union[str, Path]" = field(default_factory=lambda: Path("public"))
    resource_dir: "Union[str, Path]" = field(default_factory=lambda: Path("src"))
    public_dir: "Union[str, Path]" = field(default_factory=lambda: Path("public"))
    manifest_name: str = "manifest.json"
    hot_file: str = "hot"
    asset_url: str = field(default_factory=lambda: os.getenv("ASSET_URL", "/static/"))
    ssr_output_dir: "Optional[Union[str, Path]]" = None

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
class RuntimeConfig:
    """Runtime execution settings.

    Attributes:
        dev_mode: Enable development mode with HMR/watch.
        hot_reload: Enable Hot Module Replacement (HMR).
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
        proxy_mode: Proxy mode for dev server requests.
        spa_handler: Auto-register catch-all SPA route when mode="spa".
        http2: Enable HTTP/2 for proxy HTTP requests (better multiplexing).
            WebSocket traffic (HMR) uses a separate connection and is unaffected.
    """

    dev_mode: bool = field(default_factory=lambda: os.getenv("VITE_DEV_MODE", "False") in TRUE_VALUES)
    hot_reload: bool = field(default_factory=lambda: os.getenv("VITE_HOT_RELOAD", "True") in TRUE_VALUES)
    host: str = field(default_factory=lambda: os.getenv("VITE_HOST", "localhost"))
    port: int = field(default_factory=lambda: int(os.getenv("VITE_PORT", "5173")))
    protocol: Literal["http", "https"] = "http"
    executor: "Optional[Literal['node', 'bun', 'deno', 'yarn', 'pnpm']]" = None
    run_command: "Optional[list[str]]" = None
    build_command: "Optional[list[str]]" = None
    build_watch_command: "Optional[list[str]]" = None
    install_command: "Optional[list[str]]" = None
    is_react: bool = False
    ssr_enabled: bool = False
    health_check: bool = field(default_factory=lambda: os.getenv("VITE_HEALTH_CHECK", "False") in TRUE_VALUES)
    detect_nodeenv: bool = False
    set_environment: bool = True
    set_static_folders: bool = True
    csp_nonce: "Optional[str]" = None
    proxy_mode: Literal["proxy", "direct"] = field(
        default_factory=lambda: "direct" if os.getenv("VITE_PROXY_MODE", "proxy").lower() == "direct" else "proxy"
    )
    spa_handler: bool = True
    http2: bool = True

    def __post_init__(self) -> None:
        """Set default commands based on executor."""
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


def _optional_str_list_factory() -> "Optional[list[str]]":
    """Factory function returning None for optional list fields."""
    return None


def _default_routes_exclude_factory() -> list[str]:
    """Factory function for default route exclusions."""
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
        cache_transformed_html: Cache transformed HTML in production for performance.
            Note: When inject_csrf=True, caching is disabled since CSRF tokens are per-request.

    Example:
        config = SPAConfig(
            inject_routes=True,
            inject_csrf=True,
            routes_exclude=["_internal_*"],
        )
    """

    inject_routes: bool = True
    inject_csrf: bool = True
    routes_var_name: str = "__LITESTAR_ROUTES__"
    csrf_var_name: str = "__LITESTAR_CSRF__"
    routes_include: "Optional[list[str]]" = field(default_factory=_optional_str_list_factory)
    routes_exclude: "Optional[list[str]]" = field(default_factory=_default_routes_exclude_factory)
    app_selector: str = "#app"
    cache_transformed_html: bool = True


def _str_object_dict_factory() -> dict[str, object]:
    """Factory function for empty dict (typed for pyright)."""
    return {}


def _str_list_factory() -> list[str]:
    """Factory function for empty string list (typed for pyright)."""
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

      - Checks for index.html in resource_dir -> SPA mode
      - Checks if Jinja2 template engine is configured -> Template mode
      - Otherwise defaults to SPA mode

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
    """

    mode: "Optional[Literal['spa', 'template', 'htmx']]" = None
    paths: PathConfig = field(default_factory=PathConfig)
    runtime: RuntimeConfig = field(default_factory=RuntimeConfig)
    types: "Union[TypeGenConfig, bool]" = field(default_factory=lambda: TypeGenConfig(enabled=True))
    inertia: "Union[InertiaConfig, bool]" = False
    spa: "Union[SPAConfig, bool, None]" = None
    dev_mode: bool = False
    base_url: "Optional[str]" = field(default_factory=lambda: os.getenv("VITE_BASE_URL"))

    # Internal: resolved executor instance
    _executor_instance: "Optional[JSExecutor]" = field(default=None, repr=False)
    _mode_auto_detected: bool = field(default=False, repr=False)

    def __post_init__(self) -> None:
        """Normalize configurations and apply shortcuts."""
        # Normalize bool shortcuts to full config objects
        if self.types is True:
            self.types = TypeGenConfig(enabled=True)
        elif self.types is False:
            self.types = TypeGenConfig(enabled=False)

        if self.inertia is True:
            self.inertia = InertiaConfig(enabled=True)
        elif self.inertia is False:
            self.inertia = InertiaConfig(enabled=False)

        if self.spa is True:
            self.spa = SPAConfig()
        # Note: spa=False is left as-is (bool), checked via spa_config property

        # Apply dev_mode shortcut
        if self.dev_mode:
            self.runtime.dev_mode = True

        # Auto-detect mode if not explicitly set
        if self.mode is None:
            self.mode = self._detect_mode()
            self._mode_auto_detected = True

        # Auto-enable SPA config when mode="spa" and spa not explicitly disabled
        # spa=None means "auto" (enabled for SPA mode), spa=False means "disabled"
        if self.mode == "spa" and self.spa is None:
            self.spa = SPAConfig()
        elif self.spa is None:
            # For non-SPA modes, default to disabled
            self.spa = False

    def _detect_mode(self) -> Literal["spa", "template", "htmx"]:
        """Auto-detect the serving mode based on project structure.

        Detection order:
        1. Check for index.html in resource_dir → SPA
        2. Check if Jinja2 is installed and likely to be used → Template
        3. Default to SPA

        Returns:
            The detected mode.
        """
        # Check for index.html in resource directory (SPA indicator)
        resource_dir = (
            self.paths.resource_dir if isinstance(self.paths.resource_dir, Path) else Path(self.paths.resource_dir)
        )
        index_html_path = resource_dir / "index.html"
        if index_html_path.exists():
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
            resource_dir = (
                self.paths.resource_dir if isinstance(self.paths.resource_dir, Path) else Path(self.paths.resource_dir)
            )
            index_html_path = resource_dir / "index.html"
            if not self.runtime.dev_mode and not index_html_path.exists():
                msg = (
                    f"SPA mode requires index.html at {index_html_path}. "
                    "Either create the file, run in dev mode, or switch to template mode."
                )
                raise ValueError(msg)

        elif self.mode in ("template", "htmx"):
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
        """Create the appropriate executor based on runtime config."""
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
        """Check if hot reload is enabled."""
        return self.runtime.hot_reload

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
    def proxy_mode(self) -> Literal["proxy", "direct"]:
        """Get proxy mode (proxy=single-port via ASGI, direct=expose Vite port)."""
        return self.runtime.proxy_mode

    @property
    def spa_handler(self) -> bool:
        """Check if SPA handler auto-registration is enabled."""
        return self.runtime.spa_handler

    @property
    def http2(self) -> bool:
        """Check if HTTP/2 is enabled for proxy connections."""
        return self.runtime.http2

    @property
    def ssr_output_dir(self) -> "Optional[Path]":
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
    def spa_config(self) -> "Optional[SPAConfig]":
        """Get SPA configuration if enabled, or None if disabled.

        Returns:
            SPAConfig instance if spa transformations are enabled, None otherwise.
        """
        if isinstance(self.spa, SPAConfig):
            return self.spa
        return None
