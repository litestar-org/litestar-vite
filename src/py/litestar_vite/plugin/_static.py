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

    NATIVE = "native"
    ASGI = "asgi"


@dataclass(frozen=True, slots=True)
class StaticServerMount:
    """Describe one static directory exposed to a native server."""

    route: str
    """URL prefix mounted by the static file server (for example, `'/static'`)."""
    directory: Path
    """Resolved filesystem directory containing static assets."""
    directory_index: str | None = None
    """Optional index filename (such as `'index.html'`) served for directory requests."""


@dataclass(frozen=True, slots=True)
class StaticServerConfig:
    """Describe where static files should be served from.

    ``reason`` is diagnostic detail that is meaningful only when ``placement`` is
    ``ASGI``; it explains why Litestar's static router must serve (development mode,
    framework/SSR routing, manifest/build-state problems, and similar).
    """

    placement: StaticPlacement = StaticPlacement.ASGI
    """Static serving tier (`StaticPlacement.NATIVE` for Granian Rust or `StaticPlacement.ASGI` for Litestar)."""
    mounts: tuple[StaticServerMount, ...] = ()
    """Ordered tuple of static directory mounts."""
    reason: str | None = None
    """Diagnostic explanation when `placement` falls back to `StaticPlacement.ASGI`."""

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
    `as_router_kwargs()` forwards the set fields to it.
    """

    after_request: "AfterRequestHookHandler | None" = None
    """Optional Litestar `after_request` hook handler applied to static asset responses."""
    after_response: "AfterResponseHookHandler | None" = None
    """Optional Litestar `after_response` hook handler applied to static asset requests."""
    before_request: "BeforeRequestHookHandler | None" = None
    """Optional Litestar `before_request` hook handler executed before static file lookup."""
    cache_control: "CacheControlHeader | None" = None
    """Default `Cache-Control` header configuration for the static files router."""
    exception_handlers: "ExceptionHandlersMap | None" = None
    """Custom exception handlers registered on the static files router."""
    guards: "list[Guard] | None" = None  # pyright: ignore[reportUnknownVariableType]
    """Route guards applied to static asset requests."""
    middleware: "Sequence[Middleware] | None" = None
    """ASGI middleware sequence applied to the static files router."""
    opt: "dict[str, Any] | None" = None
    """Route `opt` metadata dictionary merged onto the static files router."""
    security: "Sequence[SecurityRequirement] | None" = None
    """OpenAPI security requirements attached to the static files router."""
    tags: "Sequence[str] | None" = None
    """OpenAPI tags attached to the static files router."""

    _NOT_ROUTER_KWARGS: "ClassVar[frozenset[str]]" = frozenset({"opt"})
    _METADATA_FIELDS: "ClassVar[frozenset[str]]" = frozenset({"opt", "security", "tags"})

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

    def asgi_override_fields(self) -> list[str]:
        """Return the list of configured fields that require ASGI request/response serving.

        Empty containers count as unset: they configure no runtime behavior.

        Returns:
            Names of set non-metadata fields that modify runtime ASGI behavior.
        """
        return [
            field_info.name
            for field_info in fields(self)
            if field_info.name not in self._METADATA_FIELDS and getattr(self, field_info.name)
        ]

    def has_asgi_overrides(self) -> bool:
        """Return True if any configured field alters runtime ASGI request/response behavior.

        Returns:
            True if any ASGI-dependent field is set, False if the configuration is pure metadata.
        """
        return bool(self.asgi_override_fields())
