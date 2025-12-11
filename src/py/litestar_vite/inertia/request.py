from functools import cached_property
from typing import TYPE_CHECKING, cast
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

if TYPE_CHECKING:
    from litestar.types import Receive, Scope, Send

    from litestar_vite.inertia.plugin import InertiaPlugin

__all__ = ("InertiaDetails", "InertiaHeaders", "InertiaRequest")

_DEFAULT_COMPONENT_OPT_KEYS: "tuple[str, ...]" = ("component", "page")


class InertiaDetails:
    """InertiaDetails holds all the values sent by Inertia client in headers and provide convenient properties."""

    def __init__(self, request: "Request[UserT, AuthT, StateT]") -> None:
        """Initialize :class:`InertiaDetails`"""
        self.request = request

    def _get_header_value(self, name: "InertiaHeaders") -> "str | None":
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

    def _get_route_component(self) -> "str | None":
        """Return the route component from handler opts if present."""
        rh = self.request.scope.get("route_handler")  # pyright: ignore[reportUnknownMemberType]
        if rh:
            component_opt_keys: "tuple[str, ...]" = _DEFAULT_COMPONENT_OPT_KEYS
            try:
                inertia_plugin: "InertiaPlugin" = self.request.app.plugins.get("InertiaPlugin")
                component_opt_keys = inertia_plugin.config.component_opt_keys
            except KeyError:
                pass

            for key in component_opt_keys:
                if (value := rh.opt.get(key)) is not None:
                    return cast("str", value)
        return None

    def __bool__(self) -> bool:
        """Return True when the request is sent by an Inertia client."""
        return self._get_header_value(InertiaHeaders.ENABLED) == "true"

    @cached_property
    def route_component(self) -> "str | None":
        """Return the route component name."""
        return self._get_route_component()

    @cached_property
    def partial_component(self) -> "str | None":
        """Return the partial component name from headers."""
        return self._get_header_value(InertiaHeaders.PARTIAL_COMPONENT)

    @cached_property
    def partial_data(self) -> "str | None":
        """Return partial-data keys requested by the client."""
        return self._get_header_value(InertiaHeaders.PARTIAL_DATA)

    @cached_property
    def partial_except(self) -> "str | None":
        """Return partial-except keys requested by the client."""
        return self._get_header_value(InertiaHeaders.PARTIAL_EXCEPT)

    @cached_property
    def reset_props(self) -> "str | None":
        """Return comma-separated props to reset on navigation."""
        return self._get_header_value(InertiaHeaders.RESET)

    @cached_property
    def error_bag(self) -> "str | None":
        """Return the error bag name for scoped validation errors."""
        return self._get_header_value(InertiaHeaders.ERROR_BAG)

    @cached_property
    def merge_intent(self) -> "str | None":
        """Return infinite-scroll merge intent (append/prepend)."""
        return self._get_header_value(InertiaHeaders.INFINITE_SCROLL_MERGE_INTENT)

    @cached_property
    def version(self) -> "str | None":
        """Return the Inertia asset version sent by the client."""
        return self._get_header_value(InertiaHeaders.VERSION)

    @cached_property
    def referer(self) -> "str | None":
        """Return the referer value if present."""
        return self._get_header_value(InertiaHeaders.REFERER)

    @cached_property
    def is_partial_render(self) -> bool:
        """Return True when the request is a partial render."""
        return bool(self.partial_component == self.route_component and (self.partial_data or self.partial_except))

    @cached_property
    def partial_keys(self) -> list[str]:
        """Return parsed partial-data keys."""
        return self.partial_data.split(",") if self.partial_data is not None else []

    @cached_property
    def partial_except_keys(self) -> list[str]:
        """Return parsed partial-except keys (takes precedence over partial_keys)."""
        return self.partial_except.split(",") if self.partial_except is not None else []

    @cached_property
    def reset_keys(self) -> list[str]:
        """Return parsed reset keys from headers."""
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
    def error_bag(self) -> "str | None":
        """Get the error bag name for scoped validation errors (v2)."""
        return self.inertia.error_bag

    @property
    def merge_intent(self) -> "str | None":
        """Get the infinite scroll merge intent (v2).

        Returns 'append' or 'prepend' for infinite scroll merging.
        """
        return self.inertia.merge_intent

    @property
    def inertia_version(self) -> "str | None":
        """Get the Inertia asset version sent by the client.

        The client sends this header so the server can detect version mismatches
        and trigger a hard refresh when assets have changed.

        Returns:
            The version string sent by the client, or None if not present.
        """
        return self.inertia.version
