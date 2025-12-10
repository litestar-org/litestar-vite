import re
from dataclasses import dataclass, field
from typing import Any, Generic, Literal, TypedDict, TypeVar

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

# Merge strategy type for props
MergeStrategy = Literal["append", "prepend", "deep"]

# Compiled regex for snake_case to camelCase conversion
_SNAKE_CASE_PATTERN = re.compile(r"_([a-z])")


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


def _convert_value(value: Any) -> Any:
    """Recursively convert a value for Inertia.js protocol.

    Handles nested dataclasses, dicts, and lists without using asdict()
    to avoid Python 3.10/3.11 bugs with dict[str, list[str]] types.

    Returns:
        The converted value.
    """
    if hasattr(value, "__dataclass_fields__"):
        # Recursively convert nested dataclasses
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
    if not hasattr(obj, "__dataclass_fields__"):
        return obj

    required_fields = required_fields or set()
    result: dict[str, Any] = {}

    # Iterate through dataclass fields directly instead of using asdict()
    for field_name in obj.__dataclass_fields__:
        value = getattr(obj, field_name)

        # Skip None values for optional fields (Inertia doesn't need them)
        # But keep required fields even if None
        if value is None and field_name not in required_fields:
            continue

        # Convert the value (handles nested dataclasses, dicts, lists)
        value = _convert_value(value)

        # Convert key to camelCase
        camel_key = to_camel_case(field_name)
        result[camel_key] = value

    return result


def _str_list_factory() -> list[str]:
    """Factory function for empty string list (typed for pyright)."""
    return []


@dataclass
class DeferredPropsConfig:
    """Configuration for deferred props (v2 feature).

    Deferred props are loaded lazily after the initial page render.
    This allows for faster initial page loads by deferring non-critical data.
    """

    # Group name for the deferred props
    group: str = "default"
    # Props to load in this deferred group
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

        # Direct construction
        @get("/users", component="Users", infinite_scroll=True)
        async def list_users() -> ScrollPagination[User]:
            users = await fetch_users(limit=10, offset=0)
            return ScrollPagination(items=users, total=100, limit=10, offset=0)

        # From existing pagination
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

            # From OffsetPagination
            offset_page = OffsetPagination(items=[...], limit=10, offset=20, total=100)
            scroll = ScrollPagination.create_from(offset_page)

            # From ClassicPagination
            classic_page = ClassicPagination(items=[...], page_size=10, current_page=3, total_pages=10)
            scroll = ScrollPagination.create_from(classic_page)
        """
        items = pagination.items

        # Offset-style (OffsetPagination, etc.)
        if hasattr(pagination, "offset") and hasattr(pagination, "limit"):
            return cls(
                items=items,
                total=getattr(pagination, "total", len(items)),
                limit=pagination.limit,
                offset=pagination.offset,
            )

        # Classic-style (ClassicPagination, etc.)
        if hasattr(pagination, "current_page") and hasattr(pagination, "page_size"):
            page_size = pagination.page_size
            offset = (pagination.current_page - 1) * page_size
            total = getattr(pagination, "total_pages", 1) * page_size
            return cls(items=items, total=total, limit=page_size, offset=offset)

        # Fallback - just use items
        return cls(items=items, total=len(items), limit=len(items), offset=0)


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
    """

    component: str
    url: str
    version: str
    props: dict[str, Any]

    # v2 features - history encryption
    encrypt_history: bool = False
    clear_history: bool = False

    # v2 features - merge props
    merge_props: "list[str] | None" = None
    prepend_props: "list[str] | None" = None
    deep_merge_props: "list[str] | None" = None
    match_props_on: "dict[str, list[str]] | None" = None

    # v2 features - deferred/lazy loading
    deferred_props: "dict[str, list[str]] | None" = None

    # v2 features - infinite scroll
    scroll_props: "ScrollPropsConfig | None" = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to Inertia.js protocol format with camelCase keys."""
        # These fields are always required by the Inertia.js protocol
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
    partial_except: "str | None"  # v2
    reset: "str | None"  # v2
    error_bag: "str | None"  # v2
