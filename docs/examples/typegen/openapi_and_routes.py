"""OpenAPI SDK and Ziggy-style typed route metadata export."""

from __future__ import annotations

from pathlib import Path

from litestar import Litestar, get
from msgspec import Struct

from litestar_vite import RuntimeConfig, TypeGenConfig, ViteConfig, VitePlugin
from litestar_vite.codegen import generate_routes_json, generate_routes_ts


class CustomerRecord(Struct, frozen=True, gc=False):
    """Customer response schema exported to OpenAPI and TypeScript."""

    id: int
    name: str
    tier: str


@get("/api/customers", name="customers:list", sync_to_thread=False)
def list_customers() -> list[CustomerRecord]:
    """Return all customers for the generated OpenAPI SDK."""
    return [CustomerRecord(id=1, name="Acme Corp", tier="enterprise")]


def create_app() -> Litestar:
    """Create a Litestar app with OpenAPI SDK and route codegen enabled."""
    vite_config = ViteConfig(
        mode="spa",
        dev_mode=True,
        runtime=RuntimeConfig(start_dev_server=False),
        types=TypeGenConfig(
            output=Path("src/generated"), generate_sdk=True, generate_routes=True, generate_page_props=False
        ),
    )
    return Litestar(route_handlers=[list_customers], plugins=[VitePlugin(config=vite_config)])


def main() -> None:
    """Verify deterministic route metadata and TypeScript route generation."""
    app = create_app()
    routes_data = generate_routes_json(app)
    routes_ts = generate_routes_ts(app)
    assert "customers:list" in routes_data["routes"]
    assert "customers:list" in routes_ts


__all__ = ("CustomerRecord", "create_app", "list_customers", "main")
