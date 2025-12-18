"""SPA and logging configuration."""

import os
from dataclasses import dataclass, field
from typing import Literal

__all__ = ("LoggingConfig", "SPAConfig")


@dataclass
class SPAConfig:
    """Configuration for SPA HTML transformations.

    This configuration controls how the SPA HTML is transformed before serving,
    including CSRF token injection.

    Note:
        Route metadata is now generated as TypeScript (routes.ts) at build time
        instead of runtime injection. Use TypeGenConfig.generate_routes to enable.

        For Inertia-specific settings like ``use_script_element``, see ``InertiaConfig``.

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


def get_default_log_level() -> "Literal['quiet', 'normal', 'verbose']":
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

    level: "Literal['quiet', 'normal', 'verbose']" = field(default_factory=get_default_log_level)
    show_paths_absolute: bool = False
    suppress_npm_output: bool = False
    suppress_vite_banner: bool = False
    timestamps: bool = False
