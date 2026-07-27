"""Server-neutral static-serving contract.

Describes where a Litestar Vite app's production static assets should be served
from: either directly by the web server (``NATIVE``) or by Litestar's static
router over ASGI (``ASGI``). The result is a plain dataclass with an explicit
``placement`` discriminator so an external consumer such as litestar-granian can
compare structurally (``config.placement == "native"``) without importing this
package. This module deliberately carries no litestar-granian import.
"""

from dataclasses import dataclass, fields
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, Any, ClassVar

if TYPE_CHECKING:
    from collections.abc import Sequence

    from litestar.datastructures import CacheControlHeader
    from litestar.openapi.spec import SecurityRequirement
    from litestar.types import (
        AfterRequestHookHandler,  # pyright: ignore[reportUnknownVariableType]
        AfterResponseHookHandler,  # pyright: ignore[reportUnknownVariableType]
        BeforeRequestHookHandler,  # pyright: ignore[reportUnknownVariableType]
        ExceptionHandlersMap,
        Guard,  # pyright: ignore[reportUnknownVariableType]
        Middleware,
    )


class StaticPlacement(str, Enum):
    """Where static files are served from.

    Subclassing ``str`` is deliberate: consumers compare structurally against the
    literal value (``config.placement == "native"``) without importing this package.
    """

    NATIVE = "native"  # eligible: the web server may serve mounts directly
    ASGI = "asgi"  # Litestar's static router must serve


@dataclass(frozen=True, slots=True)
class StaticServerMount:
    """Describe one static directory exposed to a native server."""

    route: str
    directory: Path
    directory_index: str | None = None


@dataclass(frozen=True, slots=True)
class StaticServerConfig:
    """Describe where static files should be served from.

    ``reason`` is diagnostic detail that is meaningful only when ``placement`` is
    ``ASGI``; it explains why Litestar's static router must serve (development mode,
    framework/SSR routing, manifest/build-state problems, and similar).
    """

    placement: StaticPlacement = StaticPlacement.ASGI
    mounts: tuple[StaticServerMount, ...] = ()
    reason: str | None = None

    def __post_init__(self) -> None:
        """Enforce the placement invariants.

        Raises:
            ValueError: If ``NATIVE`` has no mounts, ``NATIVE`` carries a reason, or
                ``ASGI`` lacks a non-empty reason.
        """
        if self.placement is StaticPlacement.NATIVE:
            if not self.mounts:
                msg = "StaticServerConfig with NATIVE placement requires at least one mount."
                raise ValueError(msg)
            if self.reason is not None:
                msg = "StaticServerConfig with NATIVE placement must not carry a reason; reason is ASGI-only detail."
                raise ValueError(msg)
        elif not self.reason:
            msg = "StaticServerConfig with ASGI placement requires a non-empty reason."
            raise ValueError(msg)


@dataclass
class StaticFilesConfig:
    """Configuration for static file serving.

    Field names must match keyword parameters of Litestar's ``create_static_files_router``;
    :meth:`as_router_kwargs` forwards the set fields to it.
    """

    after_request: "AfterRequestHookHandler | None" = None
    after_response: "AfterResponseHookHandler | None" = None
    before_request: "BeforeRequestHookHandler | None" = None
    cache_control: "CacheControlHeader | None" = None
    exception_handlers: "ExceptionHandlersMap | None" = None
    guards: "list[Guard] | None" = None  # pyright: ignore[reportUnknownVariableType]
    middleware: "Sequence[Middleware] | None" = None
    opt: "dict[str, Any] | None" = None
    security: "Sequence[SecurityRequirement] | None" = None
    tags: "Sequence[str] | None" = None

    _NOT_ROUTER_KWARGS: "ClassVar[frozenset[str]]" = frozenset({"opt"})

    def as_router_kwargs(self) -> "dict[str, Any]":
        """Return the explicitly-set fields as ``create_static_files_router`` keyword arguments.

        ``opt`` is excluded because the plugin merges it with its own options. Unset fields
        are omitted so Litestar's defaults apply.

        Returns:
            Keyword arguments for ``create_static_files_router``.
        """
        kwargs: "dict[str, Any]" = {}
        for field_info in fields(self):
            if field_info.name in self._NOT_ROUTER_KWARGS:
                continue
            value: "Any" = getattr(self, field_info.name)
            if value is not None:
                kwargs[field_info.name] = value
        return kwargs
