"""Litestar-Vite exception classes."""

__all__ = (
    "AssetNotFoundError",
    "LitestarViteError",
    "ManifestNotFoundError",
    "MissingDependencyError",
    "ViteExecutableNotFoundError",
    "ViteExecutionError",
    "ViteProcessError",
)


class LitestarViteError(Exception):
    """Base exception for Litestar-Vite related errors."""


class MissingDependencyError(LitestarViteError, ImportError):
    """Raised when a package is not installed but required."""

    def __init__(self, package: str, extra: "str | None" = None) -> None:
        """Initialize the exception.

        Args:
            package: PyPI distribution name of the missing package (e.g. ``"jinja2"``).
            extra: Optional ``litestar-vite`` extra providing ``package`` (e.g. ``"jinja"``).
                When omitted, only the direct install hint is shown.
        """
        hint = f"'pip install {package}'"
        if extra is not None:
            hint = f"'pip install litestar-vite[{extra}]' to install litestar-vite with the required extra, or {hint}"
        super().__init__(f"Package {package!r} is not installed but required. You can install it by running {hint}")


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

    def __init__(self, manifest_path: str | None = None) -> None:
        """Initialize the exception.

        Args:
            manifest_path: Path the manifest was searched for. Kept out of the message so
                filesystem paths do not leak into error pages; exposed as an attribute.
        """
        super().__init__("Vite manifest file not found. Run 'litestar assets build' and retry.")
        self.manifest_path = manifest_path


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

    def __init__(self, file_path: str, manifest_path: str | None = None) -> None:
        """Initialize the exception.

        Args:
            file_path: The asset path that was requested.
            manifest_path: Path of the manifest searched. Kept out of the message so
                filesystem paths do not leak into error pages; exposed as an attribute.
        """
        super().__init__(f"Asset {file_path!r} not found in Vite manifest. Run 'litestar assets build' and retry.")
        self.file_path = file_path
        self.manifest_path = manifest_path
