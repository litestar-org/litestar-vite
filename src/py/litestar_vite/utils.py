"""Utility helpers for litestar-vite."""

from importlib.util import find_spec
from pathlib import Path


def get_package_path(*parts: str) -> Path:
    """Resolve a path inside the installed litestar-vite package.

    Args:
        *parts: Path segments relative to the package root.

    Returns:
        The resolved package path.
    """
    spec = find_spec("litestar_vite")
    if spec and spec.origin:
        return Path(spec.origin).parent.joinpath(*parts)
    # Fallback for uncommon import contexts.
    return Path(__file__).resolve().parent.joinpath(*parts)


def get_static_resource_path(filename: str) -> Path:
    """Resolve a bundled static resource path.

    Args:
        filename: Static file name inside the package static directory.

    Returns:
        Path to the bundled resource.
    """
    return get_package_path("static", filename)


def read_text_file(path: Path, *, encoding: str = "utf-8") -> str:
    """Read a text file with consistent encoding.

    Args:
        path: File path to read.
        encoding: Text encoding.

    Returns:
        File contents.
    """
    return path.read_text(encoding=encoding)


def read_hotfile_url(hotfile_path: Path) -> str:
    """Read and normalize the Vite hotfile URL.

    Returns:
        The Vite server URL from the hotfile, stripped of surrounding whitespace.
    """
    return read_text_file(hotfile_path).strip()
