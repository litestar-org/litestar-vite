"""Constants and utility functions for configuration."""

from typing import Any

from litestar_vite.typing import FSSPEC_INSTALLED, JINJA_INSTALLED

__all__ = (
    "FSSPEC_INSTALLED",
    "JINJA_INSTALLED",
    "TRUE_VALUES",
    "default_content_types",
    "default_storage_options",
    "empty_dict_factory",
    "empty_set_factory",
)

TRUE_VALUES = {"True", "true", "1", "yes", "Y", "T"}


def empty_dict_factory() -> dict[str, Any]:
    """Return an empty ``dict[str, Any]``.

    Returns:
        An empty dictionary.
    """
    return {}


def empty_set_factory() -> set[str]:
    """Return an empty ``set[str]``.

    Returns:
        An empty set.
    """
    return set()


def default_content_types() -> dict[str, str]:
    """Default content-type mappings keyed by file extension.

    Returns:
        Dictionary mapping file extensions to MIME types.
    """
    return {
        ".js": "application/javascript",
        ".mjs": "application/javascript",
        ".cjs": "application/javascript",
        ".css": "text/css",
        ".html": "text/html",
        ".json": "application/json",
        ".svg": "image/svg+xml",
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".webp": "image/webp",
        ".woff2": "font/woff2",
        ".woff": "font/woff",
    }


def default_storage_options() -> dict[str, Any]:
    """Return an empty storage options dictionary.

    Returns:
        An empty dictionary.
    """
    return {}
