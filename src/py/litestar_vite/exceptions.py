"""Litestar-Vite exception classes."""

__all__ = [
    "AssetNotFoundError",
    "LitestarViteError",
    "ManifestNotFoundError",
    "MissingDependencyError",
    "ViteExecutableNotFoundError",
    "ViteExecutionError",
    "ViteProcessError",
]


class LitestarViteError(Exception):
    """Base exception for Litestar-Vite related errors."""


class MissingDependencyError(LitestarViteError, ImportError):
    """Raised when a package is not installed but required."""

    def __init__(self, package: str, install_package: "str | None" = None) -> None:
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


class ViteExecutableNotFoundError(LitestarViteError):
    """Raised when the vite executable is not found."""

    def __init__(self, executable: str) -> None:
        super().__init__(f"Executable {executable!r} not found.")


class ViteExecutionError(LitestarViteError):
    """Raised when the vite execution fails."""

    def __init__(self, command: list[str], return_code: int, stderr: str) -> None:
        super().__init__(f"Command {command!r} failed with return code {return_code}.\nStderr: {stderr}")


class ManifestNotFoundError(LitestarViteError):
    """Raised when the manifest file is not found."""

    def __init__(self, manifest_path: str) -> None:
        super().__init__(f"Vite manifest file not found at {manifest_path!r}. Did you forget to build your assets?")


class ViteProcessError(LitestarViteError):
    """Raised when the Vite process fails to start or stop."""

    def __init__(
        self,
        message: str,
        command: list[str] | None = None,
        exit_code: int | None = None,
        stderr: str | None = None,
        stdout: str | None = None,
    ) -> None:
        super().__init__(message)
        self.command = command
        self.exit_code = exit_code
        self.stderr = stderr
        self.stdout = stdout


class AssetNotFoundError(LitestarViteError):
    """Raised when an asset is not found in the manifest."""

    def __init__(self, file_path: str, manifest_path: str) -> None:
        super().__init__(f"Asset {file_path!r} not found in manifest at {manifest_path!r}.")
