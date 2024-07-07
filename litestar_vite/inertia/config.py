from __future__ import annotations

from dataclasses import dataclass

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
