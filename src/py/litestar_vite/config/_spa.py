"""SPA and logging configuration."""

import os
from dataclasses import dataclass, field
from typing import Literal

__all__ = ("LoggingConfig", "SPAConfig")


@dataclass
class SPAConfig:
    """Configuration for SPA HTML transformations and CSRF token injection."""

    inject_csrf: bool = True
    """Whether to inject the Litestar CSRF token into the HTML document."""
    csrf_var_name: str = "__LITESTAR_CSRF__"
    """Global `window` variable name used when injecting the CSRF token."""
    app_selector: str = "#app"
    """CSS selector for the application root element receiving data attributes."""
    cache_transformed_html: bool = True
    """Cache transformed HTML in production when per-request `inject_csrf` is disabled."""
    cache_duration: int = 0
    """HTTP `Cache-Control: max-age` duration in seconds for SPA HTML responses."""


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
    """Logging configuration for Python and TypeScript console output."""

    level: "Literal['quiet', 'normal', 'verbose']" = field(default_factory=get_default_log_level)
    """Console verbosity level (`'quiet'`, `'normal'`, or `'verbose'`), overridable via `LITESTAR_VITE_LOG_LEVEL`."""
    show_paths_absolute: bool = False
    """Display absolute filesystem paths instead of workspace-relative paths in log output."""
    suppress_npm_output: bool = False
    """Suppress package-manager script echo lines (`> dev` / `> vite`) from console output."""
    suppress_vite_banner: bool = False
    """Suppress the Vite startup banner so only the Litestar startup banner is shown."""
    timestamps: bool = False
    """Include timestamps in console log messages."""
