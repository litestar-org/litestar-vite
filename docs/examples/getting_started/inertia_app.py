"""Inertia.js v2 Hybrid Mode quick-start example with Litestar and Vite."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from litestar import Litestar, get
from msgspec import Struct

from litestar_vite import InertiaConfig, PathConfig, RuntimeConfig, ViteConfig, VitePlugin


class ProjectItem(Struct, frozen=True, gc=False):
    """Project summary rendered inside an Inertia page component."""

    id: int
    name: str
    status: str


@get("/", component="Dashboard/Index", sync_to_thread=False)
def dashboard() -> dict[str, Any]:
    """Return Inertia page props for the ``Dashboard/Index`` component."""
    return {
        "projects": [
            ProjectItem(id=1, name="Litestar API", status="healthy"),
            ProjectItem(id=2, name="Vite Asset Pipeline", status="building"),
        ]
    }


def create_app() -> Litestar:
    """Create a Litestar application configured for Inertia v2 hybrid mode."""
    vite_config = ViteConfig(
        mode="hybrid",
        dev_mode=True,
        paths=PathConfig(root=Path(), resource_dir=Path("resources"), bundle_dir=Path("public/build")),
        inertia=InertiaConfig(root_template="index.html"),
        runtime=RuntimeConfig(start_dev_server=False),
    )
    return Litestar(route_handlers=[dashboard], plugins=[VitePlugin(config=vite_config)])


def main() -> None:
    """Verify the Inertia hybrid application constructs cleanly."""
    app = create_app()
    plugin = app.plugins.get(VitePlugin)
    assert plugin.config.mode == "hybrid"
    assert ProjectItem(id=1, name="Litestar API", status="healthy").status == "healthy"


__all__ = ("ProjectItem", "create_app", "dashboard", "main")
