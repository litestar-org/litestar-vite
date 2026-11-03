"""Jinja2 server-rendered templates with Vite assets and interactive islands."""

from __future__ import annotations

from pathlib import Path

from litestar import Litestar, get
from litestar.plugins.jinja import JinjaTemplateEngine
from litestar.response import Template
from litestar.template.config import TemplateConfig

from litestar_vite import ComponentResponse, PathConfig, RuntimeConfig, ViteConfig, VitePlugin


@get("/", sync_to_thread=False)
def home_page() -> Template:
    """Render a server-driven Jinja2 template with Vite asset tags."""
    return Template(template_name="home.html.j2", context={"title": "Orders Overview", "initial_count": 42})


@get("/fragments/metrics-card", sync_to_thread=False)
def metrics_fragment() -> ComponentResponse:
    """Return a pre-rendered UI component fragment for HTMX swap targets."""
    return ComponentResponse(component="components/MetricsCard.tsx", props={"activeOrders": 42, "latencyMs": 11.4})


def create_app(templates_dir: Path | None = None) -> Litestar:
    """Create a Litestar application in ``template`` mode with Jinja2."""
    resolved_dir = templates_dir or Path()
    vite_config = ViteConfig(
        mode="template",
        dev_mode=True,
        paths=PathConfig(root=Path(), resource_dir=Path("resources"), bundle_dir=Path("public/build")),
        runtime=RuntimeConfig(start_dev_server=False),
    )
    return Litestar(
        route_handlers=[home_page, metrics_fragment],
        template_config=TemplateConfig(directory=resolved_dir, engine=JinjaTemplateEngine),
        plugins=[VitePlugin(config=vite_config)],
    )


def main() -> None:
    """Verify the template mode application and component fragment response."""
    app = create_app()
    plugin = app.plugins.get(VitePlugin)
    assert plugin.config.mode == "template"
    fragment = ComponentResponse(component="components/MetricsCard.tsx", props={"activeOrders": 42, "latencyMs": 11.4})
    assert fragment.component == "components/MetricsCard.tsx"
    assert fragment.props["activeOrders"] == 42


__all__ = ("create_app", "home_page", "main", "metrics_fragment")
