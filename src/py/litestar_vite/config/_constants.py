"""Constants and utility functions for configuration."""

from importlib.util import find_spec
from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

if TYPE_CHECKING:
    from collections.abc import Sequence

__all__ = (
    "FSSPEC_INSTALLED",
    "JINJA_INSTALLED",
    "TRUE_VALUES",
    "PaginationContainer",
    "default_content_types",
    "default_storage_options",
    "empty_dict_factory",
    "empty_set_factory",
)

TRUE_VALUES = {"True", "true", "1", "yes", "Y", "T"}
JINJA_INSTALLED = bool(find_spec("jinja2"))
FSSPEC_INSTALLED = bool(find_spec("fsspec"))


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
