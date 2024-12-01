from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

__all__ = ("InertiaConfig",)


@dataclass
class InertiaConfig:
    """Configuration for InertiaJS support."""

    root_template: str = "index.html"
    """Name of the root template to use.

    This must be a path that is found by the Vite Plugin template config
    """
    component_opt_key: str = "component"
    """An identifier to use on routes to get the inertia component to render."""
    exclude_from_js_routes_key: str = "exclude_from_routes"
    """An identifier to use on routes to exclude a route from the generated routes typescript file."""
    redirect_unauthorized_to: str | None = None
    """Optionally supply a path where unauthorized requests should redirect."""
    redirect_404: str | None = None
    """Optionally supply a path where 404 requests should redirect."""
    extra_static_page_props: dict[str, Any] = field(default_factory=dict)
    """A dictionary of values to automatically add in to page props on every response."""
    extra_session_page_props: set[str] = field(default_factory=set)
    """A set of session keys for which the value automatically be added (if it exists) to the response."""
