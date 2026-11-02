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
from litestar_vite.config._vite import PaginationContainer, ViteConfig  # pyright: ignore[reportPrivateUsage]

__all__ = (
    "FSSPEC_INSTALLED",
    "JINJA_INSTALLED",
    "TRUE_VALUES",
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
