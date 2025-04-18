from dataclasses import dataclass
from typing import Any, Generic, Optional, TypedDict, TypeVar

__all__ = (
    "InertiaHeaderType",
    "PageProps",
)


T = TypeVar("T")


@dataclass
class PageProps(Generic[T]):
    """Inertia Page Props Type."""

    component: str
    url: str
    version: str
    props: dict[str, Any]


@dataclass
class InertiaProps(Generic[T]):
    """Inertia Props Type."""

    page: PageProps[T]


class InertiaHeaderType(TypedDict, total=False):
    """Type for inertia_headers parameter in get_headers()."""

    enabled: "Optional[bool]"
    version: "Optional[str]"
    location: "Optional[str]"
    partial_data: "Optional[str]"
    partial_component: "Optional[str]"
