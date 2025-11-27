from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from typing import Any, Generic, Literal, TypedDict, TypeVar

__all__ = (
    "DeferredPropsConfig",
    "InertiaHeaderType",
    "MergeStrategy",
    "PageProps",
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


def to_inertia_dict(obj: Any, required_fields: set[str] | None = None) -> dict[str, Any]:
    """Convert a dataclass to a dict with camelCase keys for Inertia.js protocol.

    Args:
        obj: A dataclass instance.
        required_fields: Set of field names that should always be included (even if None).

    Returns:
        A dictionary with camelCase keys, excluding None values for optional fields.
    """
    if not hasattr(obj, "__dataclass_fields__"):
        return obj

    required_fields = required_fields or set()
    result: dict[str, Any] = {}

    for key, value in asdict(obj).items():
        # Skip None values for optional fields (Inertia doesn't need them)
        # But keep required fields even if None
        if value is None and key not in required_fields:
            continue

        # Convert nested dataclasses
        if hasattr(value, "__dataclass_fields__"):
            value = to_inertia_dict(value)

        # Convert key to camelCase
        camel_key = to_camel_case(key)
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
    previous_page: int | None = None
    next_page: int | None = None
    current_page: int = 1


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
    merge_props: list[str] | None = None
    prepend_props: list[str] | None = None
    deep_merge_props: list[str] | None = None
    match_props_on: dict[str, list[str]] | None = None

    # v2 features - deferred/lazy loading
    deferred_props: dict[str, list[str]] | None = None

    # v2 features - infinite scroll
    scroll_props: ScrollPropsConfig | None = None

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

    enabled: bool | None
    version: str | None
    location: str | None
    partial_data: str | None
    partial_component: str | None
    partial_except: str | None  # v2
    reset: str | None  # v2
    error_bag: str | None  # v2
