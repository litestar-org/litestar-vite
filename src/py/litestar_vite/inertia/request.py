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
        rh = self.request.scope.get("route_handler")  # pyright: ignore[reportUnknownMemberType]
        if rh:
            return rh.opt.get("component")
        return None

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

    @cached_property
    def referer(self) -> str | None:
        """Partial Data Reload."""
        return self._get_header_value(InertiaHeaders.REFERER)

    @cached_property
    def is_partial_render(self) -> bool:
        """Is Partial Data Reload."""
        return bool(self.partial_component == self.route_component and self.partial_data)

    @cached_property
    def partial_keys(self) -> list[str]:
        """Is Partial Data Reload."""
        return self.partial_data.split(",") if self.partial_data is not None else []


class InertiaRequest(Request[UserT, AuthT, StateT]):
    """Inertia Request class to work with Inertia client."""

    __slots__ = ("inertia",)

    def __init__(self, scope: Scope, receive: Receive = empty_receive, send: Send = empty_send) -> None:
        """Initialize :class:`InertiaRequest`"""
        super().__init__(scope=scope, receive=receive, send=send)
        self.inertia = InertiaDetails(self)

    @property
    def is_inertia(self) -> bool:
        """True if the request contained inertia headers."""
        return bool(self.inertia)

    @property
    def inertia_enabled(self) -> bool:
        """True if the route handler contains an inertia enabled configuration."""
        return bool(self.inertia.route_component is not None)

    @property
    def is_partial_render(self) -> bool:
        """True if the route handler contains an inertia enabled configuration."""
        return self.inertia.is_partial_render

    @property
    def partial_keys(self) -> set[str]:
        """True if the route handler contains an inertia enabled configuration."""
        return set(self.inertia.partial_keys)
