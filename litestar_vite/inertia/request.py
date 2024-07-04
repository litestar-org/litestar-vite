from __future__ import annotations

from functools import cached_property
from typing import TYPE_CHECKING
from urllib.parse import unquote

from litestar import Request
from litestar.connection.base import (
    AuthT,
    StateT,
    UserT,
    empty_receive,
    empty_send,
)

from litestar_vite.inertia._utils import InertiaHeaders

__all__ = ("InertiaDetails", "InertiaRequest")


if TYPE_CHECKING:
    from litestar.types import Receive, Scope, Send


class InertiaDetails:
    """InertiaDetails holds all the values sent by Inertia client in headers and provide convenient properties."""

    def __init__(self, request: Request[UserT, AuthT, StateT]) -> None:
        """Initialize :class:`InertiaDetails`"""
        self.request = request

    def _get_header_value(self, name: InertiaHeaders) -> str | None:
        """Parse request header

        Check for uri encoded header and unquotes it in readable format.
        """

        if value := self.request.headers.get(name.value.lower()):
            is_uri_encoded = self.request.headers.get(f"{name.value.lower()}-uri-autoencoded") == "true"
            return unquote(value) if is_uri_encoded else value
        return None

    def _get_route_component(self) -> str | None:
        """Get the route component.

        Checks for the `component` key within the route  configuration.
        """

        return self.request.scope["route_handler"].opt.get("component")

    def __bool__(self) -> bool:
        """Check if request is sent by an Inertia client."""
        return self._get_header_value(InertiaHeaders.ENABLED) == "true"

    @cached_property
    def route_component(self) -> str | None:
        """Partial Data Reload."""
        return self._get_route_component()

    @cached_property
    def partial_component(self) -> str | None:
        """Partial Data Reload."""
        return self._get_header_value(InertiaHeaders.PARTIAL_COMPONENT)

    @cached_property
    def partial_data(self) -> str | None:
        """Partial Data Reload."""
        return self._get_header_value(InertiaHeaders.PARTIAL_DATA)


class InertiaRequest(Request[UserT, AuthT, StateT]):
    """Inertia Request class to work with Inertia client."""

    __slots__ = (
        "_json",
        "_form",
        "_body",
        "_msgpack",
        "_content_type",
        "_accept",
        "is_connected",
        "supports_push_promise",
        "_inertia",
    )

    def __init__(self, scope: Scope, receive: Receive = empty_receive, send: Send = empty_send) -> None:
        """Initialize :class:`InertiaRequest`"""
        super().__init__(scope=scope, receive=receive, send=send)
        self._inertia = InertiaDetails(self)

    @property
    def is_inertia(self) -> bool:
        """True if the request contained inertia headers."""
        return bool(self._inertia)

    @property
    def inertia_enabled(self) -> bool:
        """True if the route handler contains an inertia enabled configuration."""
        return bool(self._inertia.route_component is not None)
