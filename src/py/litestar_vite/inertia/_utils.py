from enum import Enum
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Callable

    from litestar_vite.inertia.types import InertiaHeaderType


class InertiaHeaders(str, Enum):
    """Enum for Inertia Headers.

    See: https://inertiajs.com/the-protocol

    This includes both core protocol headers and v2 extensions (partial excludes, reset, error bags,
    and infinite scroll merge intent).
    """

    ENABLED = "X-Inertia"
    VERSION = "X-Inertia-Version"
    LOCATION = "X-Inertia-Location"
    REFERER = "Referer"

    PARTIAL_DATA = "X-Inertia-Partial-Data"
    PARTIAL_COMPONENT = "X-Inertia-Partial-Component"
    PARTIAL_EXCEPT = "X-Inertia-Partial-Except"

    RESET = "X-Inertia-Reset"
    ERROR_BAG = "X-Inertia-Error-Bag"

    INFINITE_SCROLL_MERGE_INTENT = "X-Inertia-Infinite-Scroll-Merge-Intent"

    # Precognition headers (Laravel Precognition protocol)
    PRECOGNITION = "Precognition"
    PRECOGNITION_SUCCESS = "Precognition-Success"
    PRECOGNITION_VALIDATE_ONLY = "Precognition-Validate-Only"


def get_enabled_header(enabled: bool = True) -> "dict[str, Any]":
    """True if inertia is enabled.

    Args:
        enabled: Whether inertia is enabled.

    Returns:
        The headers for inertia.
    """

    return {InertiaHeaders.ENABLED.value: "true" if enabled else "false"}


def get_version_header(version: str) -> "dict[str, Any]":
    """Return headers for change swap method response.

    Args:
        version: The version of the inertia.

    Returns:
        The headers for inertia.
    """
    return {InertiaHeaders.VERSION.value: version}


def get_partial_data_header(partial: str) -> "dict[str, Any]":
    """Return headers for a partial data response.

    Args:
        partial: The partial data.

    Returns:
        The headers for inertia.
    """
    return {InertiaHeaders.PARTIAL_DATA.value: partial}


def get_partial_component_header(partial: str) -> "dict[str, Any]":
    """Return headers for a partial data response.

    Args:
        partial: The partial data.

    Returns:
        The headers for inertia.
    """
    return {InertiaHeaders.PARTIAL_COMPONENT.value: partial}


def get_headers(inertia_headers: "InertiaHeaderType") -> "dict[str, Any]":
    """Return headers for Inertia responses.

    Args:
        inertia_headers: The inertia headers.

    Raises:
        ValueError: If the inertia headers are None.

    Returns:
        The headers for inertia.
    """
    if not inertia_headers:
        msg = "Value for inertia_headers cannot be None."
        raise ValueError(msg)
    inertia_headers_dict: "dict[str, Callable[..., dict[str, Any]]]" = {
        "enabled": get_enabled_header,
        "partial_data": get_partial_data_header,
        "partial_component": get_partial_component_header,
        "version": get_version_header,
    }

    header: "dict[str, Any]" = {}
    response: "dict[str, Any]"
    key: "str"
    value: "Any"

    for key, value in inertia_headers.items():
        if value is not None:
            response = inertia_headers_dict[key](value)
            header.update(response)
    return header
