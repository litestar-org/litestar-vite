"""Inertia.js v2 shared session props, flash messages, validation errors, and Precognition."""

from __future__ import annotations

from typing import Annotated, Any

from litestar import Litestar, Request, post
from litestar.params import Body
from msgspec import Struct

from litestar_vite import InertiaConfig, RuntimeConfig, ViteConfig, VitePlugin
from litestar_vite.inertia import error, flash, precognition, share


class AuthenticatedUser(Struct, frozen=True, gc=False):
    """Typed current user model registered in ``shared_page_prop_types``."""

    id: int
    email: str
    role: str


class CreateProjectPayload(Struct, frozen=True, gc=False):
    """Form payload validated by both live Precognition and final submission."""

    name: str
    slug: str


@post("/projects", component="Projects/Index", sync_to_thread=False)
@precognition
def create_project(request: Request[Any, Any, Any], data: Annotated[CreateProjectPayload, Body()]) -> dict[str, Any]:
    """Validate and create a project with Precognition and flash notifications."""
    share(request, "currentUser", AuthenticatedUser(id=7, email="ada@example.com", role="admin"))
    if data.slug == "reserved":
        error(request, "slug", "The 'reserved' slug is unavailable.")
        flash(request, "error", "Please choose a different project slug.")
        return {"created": False}

    flash(request, "success", f"Project '{data.name}' created.")
    return {"created": True, "slug": data.slug}


def create_app() -> Litestar:
    """Create a Litestar app with typed shared props and Precognition enabled."""
    vite_config = ViteConfig(
        mode="hybrid",
        dev_mode=True,
        inertia=InertiaConfig(
            root_template="index.html",
            precognition=True,
            extra_static_page_props={"environment": "staging"},
            shared_page_prop_types={"currentUser": AuthenticatedUser},
        ),
        runtime=RuntimeConfig(start_dev_server=False),
    )
    return Litestar(route_handlers=[create_project], plugins=[VitePlugin(config=vite_config)])


def main() -> None:
    """Verify ``InertiaConfig`` shared prop typing and Precognition registration."""
    app = create_app()
    plugin = app.plugins.get(VitePlugin)
    assert isinstance(plugin.config.inertia, InertiaConfig)
    assert plugin.config.inertia.precognition is True
    assert plugin.config.inertia.shared_page_prop_types == {"currentUser": AuthenticatedUser}


__all__ = ("AuthenticatedUser", "CreateProjectPayload", "create_app", "create_project", "main")
