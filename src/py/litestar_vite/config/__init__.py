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
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal, Protocol, cast, runtime_checkable

from litestar.exceptions import SerializationException
from litestar.serialization import decode_json

from litestar_vite.config._constants import (  # pyright: ignore[reportPrivateUsage]
    FSSPEC_INSTALLED,
    JINJA_INSTALLED,
    TRUE_VALUES,
)
from litestar_vite.config._deploy import DeployConfig  # pyright: ignore[reportPrivateUsage]
from litestar_vite.config._inertia import (  # pyright: ignore[reportPrivateUsage]
    InertiaConfig,
    InertiaSSRConfig,
    InertiaTypeGenConfig,
)
from litestar_vite.config._paths import PathConfig  # pyright: ignore[reportPrivateUsage]
from litestar_vite.config._runtime import ExternalDevServer, RuntimeConfig  # pyright: ignore[reportPrivateUsage]
from litestar_vite.config._spa import LoggingConfig, SPAConfig  # pyright: ignore[reportPrivateUsage]
from litestar_vite.config._types import TypeGenConfig  # pyright: ignore[reportPrivateUsage]

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
        mode: Serving mode - "spa", "template", "htmx", "hybrid", "framework", "ssr", "ssg", or "external".
            Auto-detected if not set. Use "external" for non-Vite frameworks (Angular CLI, etc.)
            that have their own build system - auto-serves bundle_dir in production.
        paths: File system paths configuration.
        runtime: Runtime execution settings.
        types: Type generation settings (True/TypeGenConfig enables, False/None disables).
        inertia: Inertia.js settings (True/InertiaConfig enables, False/None disables).
        spa: SPA transformation settings (True enables with defaults, False disables).
        logging: Logging configuration (True enables with defaults, None uses defaults).
        dev_mode: Convenience shortcut for runtime.dev_mode.
        base_url: Base URL for the app entry point.
        deploy: Deployment configuration for CDN publishing.
    """

    mode: "Literal['spa', 'template', 'htmx', 'hybrid', 'inertia', 'framework', 'ssr', 'ssg', 'external'] | None" = None
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
    SPA index.html (mode="spa"/"framework" with spa_handler=True).
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
        self._apply_framework_mode_defaults()
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
        - 'framework': Canonical name for meta-framework integration mode (Astro/Nuxt/SvelteKit, etc.)
          that uses dev-time proxying to a frontend dev server and optional SSR/SSG output handling.

        - 'ssr' / 'ssg' → 'framework': Aliases for framework proxy mode.
          Static Site Generation (SSG) uses the same dev-time proxy behavior as SSR:
          forward non-API routes to the framework dev server. SSG pre-renders at build time,
          SSR renders per-request, but their dev-time proxy behavior is identical.

        - 'inertia' → 'hybrid': Inertia.js apps without Jinja templates use hybrid mode.
          This is clearer terminology since "hybrid" refers to the SPA-with-server-routing
          pattern that Inertia implements.
        """
        if self.mode in {"ssr", "ssg"}:
            self.mode = "framework"
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

    def _apply_framework_mode_defaults(self) -> None:
        """Apply intelligent defaults for framework proxy mode.

        When mode='framework' is set, automatically configure proxy_mode and spa_handler
        based on dev_mode and whether built assets exist:

        - Dev mode: proxy_mode='proxy', spa_handler=False
          (Proxy all non-API routes to the SSR/SSG framework dev server)
        - Prod mode with built assets: proxy_mode=None, spa_handler=True
          (Serve static SSG output like Astro's dist/)
        - Prod mode without built assets: proxy_mode=None, spa_handler=False
          (True SSR - Node server handles HTML, Litestar only serves API)
        """
        if self.mode != "framework":
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

        candidates = self.candidate_manifest_paths()
        manifest_locations = " or ".join(str(path) for path in candidates)
        logger.warning(
            "Vite manifest not found at %s. "
            "Run 'litestar assets build' (or 'npm run build') to build assets, "
            "or set dev_mode=True for development. "
            "Assets will not load correctly without built files or a running Vite dev server.",
            manifest_locations,
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

    def candidate_manifest_paths(self) -> list[Path]:
        """Return possible manifest.json locations in the bundle directory.

        Some meta-frameworks emit the manifest under a ``.vite/`` subdirectory
        (e.g. ``<bundle_dir>/.vite/manifest.json``), while plain Vite builds may
        write it directly to ``<bundle_dir>/manifest.json``.

        Returns:
            A de-duplicated list of candidate manifest paths, ordered by preference.
        """
        bundle_path = self._resolve_to_root(self.bundle_dir)
        manifest_rel = Path(self.manifest_name)

        candidates: list[Path] = [bundle_path / manifest_rel]
        if not manifest_rel.is_absolute() and (not manifest_rel.parts or manifest_rel.parts[0] != ".vite"):
            candidates.append(bundle_path / ".vite" / manifest_rel)

        unique: list[Path] = []
        seen: set[Path] = set()
        for path in candidates:
            if path in seen:
                continue
            seen.add(path)
            unique.append(path)
        return unique

    def resolve_manifest_path(self) -> Path:
        """Resolve the most likely manifest path.

        Returns:
            The first existing manifest path, or the highest-priority candidate when none exist.
        """
        candidates = self.candidate_manifest_paths()
        for candidate in candidates:
            if candidate.exists():
                return candidate
        return candidates[0]

    def has_built_assets(self) -> bool:
        """Check if production assets exist in the bundle directory.

        Returns:
            True if a manifest or built index.html exists in bundle_dir.

        Note:
            This method checks the bundle_dir (output directory) for built artifacts,
            NOT source directories. The presence of source index.html in resource_dir
            does not indicate built assets exist.
        """
        bundle_path = self._resolve_to_root(self.bundle_dir)
        index_path = bundle_path / "index.html"

        return any(path.exists() for path in self.candidate_manifest_paths()) or index_path.exists()

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

        HMR requires dev_mode=True AND a Vite-based proxy mode (vite, direct, or proxy).
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
    def csp_nonce(self) -> "str | None":
        """Return the CSP nonce used for injected inline scripts.

        Returns:
            CSP nonce string when configured, otherwise None.
        """
        return self.runtime.csp_nonce

    @property
    def trusted_proxies(self) -> "list[str] | str | None":
        """Get trusted proxies configuration.

        When set, enables ProxyHeadersMiddleware to handle X-Forwarded-* headers
        from reverse proxies (Railway, Heroku, AWS ALB, nginx, etc.).

        Returns:
            The trusted proxies configuration, or None if disabled.
        """
        return self.runtime.trusted_proxies

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
