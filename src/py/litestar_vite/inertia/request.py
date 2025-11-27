from functools import cached_property
from typing import TYPE_CHECKING, Optional
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

    def __init__(self, request: "Request[UserT, AuthT, StateT]") -> None:
        """Initialize :class:`InertiaDetails`"""
        self.request = request

    def _get_header_value(self, name: "InertiaHeaders") -> "Optional[str]":
        """Parse request header

        Check for uri encoded header and unquotes it in readable format.

        Args:
            name: The header name.

        Returns:
            The header value.
        """

        if value := self.request.headers.get(name.value.lower()):
            is_uri_encoded = self.request.headers.get(f"{name.value.lower()}-uri-autoencoded") == "true"
            return unquote(value) if is_uri_encoded else value
        return None

    def _get_route_component(self) -> "Optional[str]":
        """Get the route component.

        Checks for the `component` key within the route handler configuration.

        Args:
            request: The request object.

        Returns:
            The route component.
        """
        rh = self.request.scope.get("route_handler")  # pyright: ignore[reportUnknownMemberType]
        if rh:
            return rh.opt.get("component")
        return None

    def __bool__(self) -> bool:
        """Check if request is sent by an Inertia client.

        Returns:
            True if the request is sent by an Inertia client, False otherwise.
        """
        return self._get_header_value(InertiaHeaders.ENABLED) == "true"

    @cached_property
    def route_component(self) -> "Optional[str]":
        """Get the route component.

        Returns:
            The route component.
        """
        return self._get_route_component()

    @cached_property
    def partial_component(self) -> "Optional[str]":
        """Get the partial component.

        Returns:
            The partial component.
        """
        return self._get_header_value(InertiaHeaders.PARTIAL_COMPONENT)

    @cached_property
    def partial_data(self) -> "Optional[str]":
        """Get the partial data (props to include).

        Returns:
            The partial data.
        """
        return self._get_header_value(InertiaHeaders.PARTIAL_DATA)

    @cached_property
    def partial_except(self) -> "Optional[str]":
        """Get the partial except data (props to exclude).

        v2 feature: X-Inertia-Partial-Except header.
        Takes precedence over partial_data if both are present.

        Returns:
            The partial except data.
        """
        return self._get_header_value(InertiaHeaders.PARTIAL_EXCEPT)

    @cached_property
    def reset_props(self) -> "Optional[str]":
        """Get props to reset on navigation.

        v2 feature: X-Inertia-Reset header.

        Returns:
            Comma-separated props to reset.
        """
        return self._get_header_value(InertiaHeaders.RESET)

    @cached_property
    def error_bag(self) -> "Optional[str]":
        """Get the error bag name.

        v2 feature: X-Inertia-Error-Bag header.
        Used for scoped validation errors.

        Returns:
            The error bag name.
        """
        return self._get_header_value(InertiaHeaders.ERROR_BAG)

    @cached_property
    def merge_intent(self) -> "Optional[str]":
        """Get the infinite scroll merge intent.

        v2 feature: X-Inertia-Infinite-Scroll-Merge-Intent header.

        Returns:
            'append' or 'prepend' for infinite scroll merging.
        """
        return self._get_header_value(InertiaHeaders.INFINITE_SCROLL_MERGE_INTENT)

    @cached_property
    def referer(self) -> "Optional[str]":
        """Get the referer.

        Returns:
            The referer.
        """
        return self._get_header_value(InertiaHeaders.REFERER)

    @cached_property
    def is_partial_render(self) -> bool:
        """Check if the request is a partial render.

        Returns:
            True if the request is a partial render, False otherwise.
        """
        return bool(self.partial_component == self.route_component and (self.partial_data or self.partial_except))

    @cached_property
    def partial_keys(self) -> list[str]:
        """Get the partial keys (props to include).

        Returns:
            The partial keys.
        """
        return self.partial_data.split(",") if self.partial_data is not None else []

    @cached_property
    def partial_except_keys(self) -> list[str]:
        """Get the partial except keys (props to exclude).

        v2 feature: Takes precedence over partial_keys if both present.

        Returns:
            The partial except keys.
        """
        return self.partial_except.split(",") if self.partial_except is not None else []

    @cached_property
    def reset_keys(self) -> list[str]:
        """Get the props to reset on navigation.

        v2 feature.

        Returns:
            The reset keys.
        """
        return self.reset_props.split(",") if self.reset_props is not None else []


class InertiaRequest(Request[UserT, AuthT, StateT]):
    """Inertia Request class to work with Inertia client."""

    __slots__ = ("inertia",)

    def __init__(self, scope: "Scope", receive: "Receive" = empty_receive, send: "Send" = empty_send) -> None:
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
        """True if the request is a partial reload."""
        return self.inertia.is_partial_render

    @property
    def partial_keys(self) -> "set[str]":
        """Get the props to include in partial render."""
        return set(self.inertia.partial_keys)

    @property
    def partial_except_keys(self) -> "set[str]":
        """Get the props to exclude from partial render (v2).

        Takes precedence over partial_keys if both present.
        """
        return set(self.inertia.partial_except_keys)

    @property
    def reset_keys(self) -> "set[str]":
        """Get the props to reset on navigation (v2)."""
        return set(self.inertia.reset_keys)

    @property
    def error_bag(self) -> "Optional[str]":
        """Get the error bag name for scoped validation errors (v2)."""
        return self.inertia.error_bag

    @property
    def merge_intent(self) -> "Optional[str]":
        """Get the infinite scroll merge intent (v2).

        Returns 'append' or 'prepend' for infinite scroll merging.
        """
        return self.inertia.merge_intent
