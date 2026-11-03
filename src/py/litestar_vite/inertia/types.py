"""Inertia protocol types and serialization helpers.

This module defines the Python-side data structures for the Inertia.js protocol and provides
helpers to serialize dataclass instances into the camelCase shape expected by the client.
"""

import re
from dataclasses import dataclass, field, fields, is_dataclass
from typing import Any, Generic, Literal, TypedDict, TypeVar, cast

__all__ = (
    "DeferredPropsConfig",
    "InertiaHeaderType",
    "MergeStrategy",
    "PageProps",
    "ScrollPagination",
    "ScrollPropsConfig",
    "to_camel_case",
    "to_inertia_dict",
)


T = TypeVar("T")

MergeStrategy = Literal["append", "prepend", "deep"]

_SNAKE_CASE_PATTERN = re.compile(r"_([a-z])")


def _empty_flash_factory() -> "dict[str, list[str]]":
    """Return an empty flash dict with proper type annotation.

    Returns:
        Empty dict[str, list[str]] for flash messages.
    """
    return {}


def to_camel_case(snake_str: str) -> str:
    """Convert snake_case string to camelCase.

    Args:
        snake_str: A snake_case string.

    Returns:
        The camelCase equivalent.

    Examples:
        >>> to_camel_case("encrypt_history")
        'encryptHistory'
        >>> to_camel_case("deep_merge_props")
        'deepMergeProps'
    """
    return _SNAKE_CASE_PATTERN.sub(lambda m: m.group(1).upper(), snake_str)


def _is_dataclass_instance(value: Any) -> bool:
    return is_dataclass(value) and not isinstance(value, type)


def _convert_value(value: Any) -> Any:
    """Recursively convert a value for Inertia.js protocol.

    Handles nested dataclasses, dicts, and lists without using asdict()
    to avoid Python 3.10/3.11 bugs with dict[str, list[str]] types.

    Returns:
        The converted value.
    """
    if _is_dataclass_instance(value):
        return to_inertia_dict(value)
    if isinstance(value, dict):
        return {k: _convert_value(v) for k, v in value.items()}  # pyright: ignore[reportUnknownVariableType]
    if isinstance(value, (list, tuple)):
        return type(value)(_convert_value(v) for v in value)  # pyright: ignore[reportUnknownArgumentType,reportUnknownVariableType]
    return value


def to_inertia_dict(obj: Any, required_fields: "set[str] | None" = None) -> dict[str, Any]:
    """Convert a dataclass to a dict with camelCase keys for Inertia.js protocol.

    Args:
        obj: A dataclass instance.
        required_fields: Set of field names that should always be included (even if None).

    Returns:
        A dictionary with camelCase keys, excluding None values for optional fields.

    Note:
        This function avoids using dataclasses.asdict() directly because of a bug
        in Python 3.10/3.11 that fails when processing dict[str, list[str]] types.
        See: https://github.com/python/cpython/issues/103000
    """
    if not _is_dataclass_instance(obj):
        return cast("dict[str, Any]", obj)

    required_fields = required_fields or set()
    result: dict[str, Any] = {}

    for dc_field in fields(obj):
        field_name = dc_field.name
        value = getattr(obj, field_name)
        if value is None and field_name not in required_fields:
            continue

        value = _convert_value(value)
        camel_key = to_camel_case(field_name)
        result[camel_key] = value

    return result


def _str_list_factory() -> list[str]:
    """Factory function for empty string list (typed for pyright).

    Returns:
        An empty list.
    """
    return []


@dataclass
class DeferredPropsConfig:
    """Configuration for Inertia v2 deferred prop groups."""

    group: str = "default"
    """Group name used to batch deferred prop requests after initial render."""
    props: list[str] = field(default_factory=_str_list_factory)
    """List of prop keys belonging to this deferred group."""


@dataclass
class ScrollPropsConfig:
    """Configuration for Inertia v2 infinite scroll pagination metadata."""

    page_name: str = "page"
    """Query parameter name used to request a specific page."""
    previous_page: "int | None" = None
    """Previous page number, or `None` when on the first page."""
    next_page: "int | None" = None
    """Next page number, or `None` when on the last page."""
    current_page: int = 1
    """Current 1-based page number."""


@dataclass
class ScrollPagination(Generic[T]):
    """Generic offset-normalized pagination container optimized for Inertia v2 infinite scroll."""

    items: list[T]
    """Paginated items for the current page."""
    total: int
    """Total number of items across all pages."""
    limit: int
    """Maximum number of items per page."""
    offset: int
    """Number of items skipped from the beginning of the dataset."""

    @classmethod
    def create_from(cls, pagination: Any) -> "ScrollPagination[T]":
        """Create from any pagination container (auto-detects type).

        Supports OffsetPagination, ClassicPagination, and any custom pagination
        class with standard pagination attributes.

        Args:
            pagination: Any pagination container with `items` attribute.

        Returns:
            A ScrollPagination instance with normalized offset-based metadata.

        Example:
            ```python
            from litestar.pagination import OffsetPagination, ClassicPagination

            offset_page = OffsetPagination(items=[...], limit=10, offset=20, total=100)
            scroll = ScrollPagination.create_from(offset_page)

            classic_page = ClassicPagination(items=[...], page_size=10, current_page=3, total_pages=10)
            scroll = ScrollPagination.create_from(classic_page)
            ```
        """
        items = pagination.items
        if meta := _extract_offset_pagination(pagination, items):
            total, limit, offset = meta
            return cls(items=items, total=total, limit=limit, offset=offset)
        if meta := _extract_classic_pagination(pagination, items):
            total, limit, offset = meta
            return cls(items=items, total=total, limit=limit, offset=offset)
        return cls(items=items, total=len(items), limit=len(items), offset=0)


def _extract_offset_pagination(pagination: Any, items: list[Any]) -> tuple[int, int, int] | None:
    try:
        limit = pagination.limit
        offset = pagination.offset
    except AttributeError:
        return None

    try:
        total = pagination.total
    except AttributeError:
        total = len(items)

    if not (isinstance(limit, int) and isinstance(offset, int) and isinstance(total, int)):
        return None

    return total, limit, offset


def _extract_classic_pagination(pagination: Any, items: list[Any]) -> tuple[int, int, int] | None:
    try:
        page_size = pagination.page_size
        current_page = pagination.current_page
    except AttributeError:
        return None

    try:
        total_pages = pagination.total_pages
    except AttributeError:
        total_pages = 1

    if not (isinstance(page_size, int) and isinstance(current_page, int) and isinstance(total_pages, int)):
        return None

    offset = (current_page - 1) * page_size
    total = total_pages * page_size
    return total, page_size, offset


@dataclass
class PageProps(Generic[T]):
    """Inertia v2 page object serialized to camelCase JSON via `to_dict()`."""

    component: str
    """JavaScript page component name to render."""
    url: str
    """Current request URL path and query string."""
    version: str
    """Asset bundle version identifier used for `409 Conflict` cache busting."""
    props: dict[str, Any]
    """Resolved dictionary of page and shared props passed to the frontend component."""
    encrypt_history: bool = False
    """Whether the Inertia client should encrypt browser history state for this page."""
    clear_history: bool = False
    """Whether the Inertia client should clear previously encrypted history state."""
    merge_props: "list[str] | None" = None
    """Prop keys whose values should be appended during partial navigation."""
    prepend_props: "list[str] | None" = None
    """Prop keys whose values should be prepended during partial navigation."""
    deep_merge_props: "list[str] | None" = None
    """Prop keys whose nested dictionaries should be deep-merged during partial navigation."""
    match_props_on: "list[str] | None" = None
    """Dotted property paths (such as `'items.id'`) used to deduplicate merged array items."""
    deferred_props: "dict[str, list[str]] | None" = None
    """Mapping of deferred group names to lists of prop keys fetched after initial render."""
    once_props: "dict[str, dict[str, str | int | None]] | None" = None
    """Metadata mapping for props resolved once and cached client-side across navigations."""
    scroll_props: "dict[str, ScrollPropsConfig] | None" = None
    """Infinite scroll pagination metadata keyed by prop name."""
    flash: "dict[str, list[str]]" = field(default_factory=_empty_flash_factory)
    """Top-level flash messages grouped by category (`v2.3+`, excluded from history state)."""

    def to_dict(self) -> dict[str, Any]:
        """Convert to Inertia.js protocol format with camelCase keys.

        Returns:
            The Inertia protocol dictionary.
        """
        data = to_inertia_dict(self, required_fields={"component", "url", "version", "props"})
        if data.get("encryptHistory") is False:
            del data["encryptHistory"]
        if data.get("clearHistory") is False:
            del data["clearHistory"]
        return data


class InertiaHeaderType(TypedDict, total=False):
    """TypedDict describing Inertia.js HTTP request/response header values."""

    enabled: "bool | None"
    """Whether the `X-Inertia` protocol header is enabled (`'true'`)."""
    version: "str | None"
    """Asset version string carried in the `X-Inertia-Version` header."""
    location: "str | None"
    """External redirect URL carried in the `X-Inertia-Location` response header."""
    partial_data: "str | None"
    """Comma-separated prop keys requested via `X-Inertia-Partial-Data`."""
    partial_component: "str | None"
    """Component name specified in `X-Inertia-Partial-Component` for partial reloads."""
    partial_except: "str | None"
    """Comma-separated prop keys excluded via `X-Inertia-Partial-Except`."""
    except_once_props: "str | None"
    """Comma-separated cached once-prop keys omitted via `X-Inertia-Except-Once-Props`."""
    reset: "str | None"
    """Comma-separated prop keys to reset on client navigation via `X-Inertia-Reset`."""
    error_bag: "str | None"
    """Scoped validation error bag name sent in `X-Inertia-Error-Bag`."""
