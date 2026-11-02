"""Single-Page Application (SPA) quick-start example with Litestar and Vite."""

from __future__ import annotations

from pathlib import Path

from litestar import Litestar, get
from msgspec import Struct

from litestar_vite import PathConfig, RuntimeConfig, TypeGenConfig, ViteConfig, VitePlugin


class SummaryStats(Struct, frozen=True, gc=False):
    """Dashboard summary payload returned by the JSON API."""

    active_users: int
    requests_per_second: float
    region: str


@get("/api/summary", sync_to_thread=False)
def get_summary() -> SummaryStats:
    """Return typed summary metrics for the SPA frontend."""
    return SummaryStats(active_users=128, requests_per_second=412.5, region="us-east-1")


def create_app() -> Litestar:
    """Create a Litestar application configured for SPA mode."""
    vite_config = ViteConfig(
        mode="spa",
        dev_mode=True,
        paths=PathConfig(root=Path(), resource_dir=Path("src"), bundle_dir=Path("public/build")),
        runtime=RuntimeConfig(start_dev_server=False),
        types=TypeGenConfig(generate_sdk=True, generate_routes=True),
    )
    return Litestar(route_handlers=[get_summary], plugins=[VitePlugin(config=vite_config)])


def main() -> None:
    """Verify the SPA example application constructs cleanly."""
    app = create_app()
    plugin = app.plugins.get(VitePlugin)
    assert plugin.config.mode == "spa"
    assert SummaryStats(active_users=128, requests_per_second=412.5, region="us-east-1").active_users == 128


__all__ = ("SummaryStats", "create_app", "get_summary", "main")
