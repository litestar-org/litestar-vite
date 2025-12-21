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
    """Configuration for deferred props (v2 feature).

    Deferred props are loaded lazily after the initial page render.
    This allows for faster initial page loads by deferring non-critical data.
    """

    group: str = "default"
    props: list[str] = field(default_factory=_str_list_factory)


@dataclass
class ScrollPropsConfig:
    """Configuration for infinite scroll (v2 feature)."""

    page_name: str = "page"
    previous_page: "int | None" = None
    next_page: "int | None" = None
    current_page: int = 1


@dataclass
class ScrollPagination(Generic[T]):
    """Pagination container optimized for infinite scroll.

    A generic pagination type that works seamlessly with Inertia's infinite
    scroll feature. Can be constructed directly or created from any pagination
    container using ``create_from()``.

    Attributes:
        items: The paginated items for the current page.
        total: Total number of items across all pages.
        limit: Maximum items per page (page size).
        offset: Number of items skipped from the start.

    Example::

        from litestar_vite.inertia.types import ScrollPagination

        Direct construction::

        @get("/users", component="Users", infinite_scroll=True)
        async def list_users() -> ScrollPagination[User]:
            users = await fetch_users(limit=10, offset=0)
            return ScrollPagination(items=users, total=100, limit=10, offset=0)

        From an existing pagination container::

        @get("/posts", component="Posts", infinite_scroll=True)
        async def list_posts() -> ScrollPagination[Post]:
            pagination = await repo.list_paginated(limit=10, offset=0)
            return ScrollPagination.create_from(pagination)
    """

    items: list[T]
    total: int
    limit: int
    offset: int

    @classmethod
    def create_from(cls, pagination: Any) -> "ScrollPagination[T]":
        """Create from any pagination container (auto-detects type).

        Supports OffsetPagination, ClassicPagination, and any custom pagination
        class with standard pagination attributes.

        Args:
            pagination: Any pagination container with ``items`` attribute.

        Returns:
            A ScrollPagination instance with normalized offset-based metadata.

        Example::

            from litestar.pagination import OffsetPagination, ClassicPagination

            From OffsetPagination::

            offset_page = OffsetPagination(items=[...], limit=10, offset=20, total=100)
            scroll = ScrollPagination.create_from(offset_page)

            From ClassicPagination::

            classic_page = ClassicPagination(items=[...], page_size=10, current_page=3, total_pages=10)
            scroll = ScrollPagination.create_from(classic_page)
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
    """Inertia Page Props Type.

    This represents the page object sent to the Inertia client.
    See: https://inertiajs.com/the-protocol

    Note: Field names use snake_case in Python but are serialized to camelCase
    for the Inertia.js protocol using `to_inertia_dict()`.

    Attributes:
        component: JavaScript component name to render.
        url: Current page URL.
        version: Asset version identifier for cache busting.
        props: Page data/props passed to the component.
        encrypt_history: Whether to encrypt browser history state (v2).
        clear_history: Whether to clear encrypted history state (v2).
        merge_props: Props to append during navigation (v2).
        prepend_props: Props to prepend during navigation (v2).
        deep_merge_props: Props to deep merge during navigation (v2).
        match_props_on: Keys for matching items during merge (v2).
        deferred_props: Configuration for lazy-loaded props (v2).
        scroll_props: Configuration for infinite scroll (v2).
        flash: Flash messages as top-level property (v2.3+). Unlike props, flash
            messages are NOT persisted in browser history state.
    """

    component: str
    url: str
    version: str
    props: dict[str, Any]

    encrypt_history: bool = False
    clear_history: bool = False

    merge_props: "list[str] | None" = None
    prepend_props: "list[str] | None" = None
    deep_merge_props: "list[str] | None" = None
    match_props_on: "dict[str, list[str]] | None" = None

    deferred_props: "dict[str, list[str]] | None" = None

    # v2.2.20+ protocol: Props that should only be resolved once and cached client-side
    once_props: "list[str] | None" = None

    scroll_props: "ScrollPropsConfig | None" = None

    # v2.3+ protocol: Flash messages at top level (not in props)
    # This prevents flash from persisting in browser history state
    # Always send {} for empty flash to support router.flash((current) => ({ ...current }))
    flash: "dict[str, list[str]]" = field(default_factory=_empty_flash_factory)

    def to_dict(self) -> dict[str, Any]:
        """Convert to Inertia.js protocol format with camelCase keys.

        Returns:
            The Inertia protocol dictionary.
        """
        return to_inertia_dict(self, required_fields={"component", "url", "version", "props"})


@dataclass
class InertiaProps(Generic[T]):
    """Inertia Props Type."""

    page: PageProps[T]


class InertiaHeaderType(TypedDict, total=False):
    """Type for inertia_headers parameter in get_headers()."""

    enabled: "bool | None"
    version: "str | None"
    location: "str | None"
    partial_data: "str | None"
    partial_component: "str | None"
    partial_except: "str | None"
    reset: "str | None"
    error_bag: "str | None"
