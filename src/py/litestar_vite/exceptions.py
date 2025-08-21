"""Litestar-Vite exception classes."""

from __future__ import annotations

__all__ = ["LitestarViteError", "MissingDependencyError"]


class LitestarViteError(Exception):
    """Base exception for Litestar-Vite related errors."""


class MissingDependencyError(LitestarViteError, ImportError):
    """Raised when a package is not installed but required."""

    def __init__(self, package: str, install_package: str | None = None) -> None:
        """Initialize the exception.

        Args:
            package: The name of the missing package.
            install_package: Optional alternative package name for installation.
        """
        super().__init__(
            f"Package {package!r} is not installed but required. You can install it by running "
            f"'pip install litestar-vite[{install_package or package}]' to install litestar-vite with the required extra "
            f"or 'pip install {install_package or package}' to install the package separately"
        )
