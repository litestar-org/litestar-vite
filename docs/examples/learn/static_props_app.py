"""Build-time Static Props injected into the Vite virtual module bridge."""

from __future__ import annotations

from litestar import Litestar
from msgspec import Struct

from litestar_vite import RuntimeConfig, TypeGenConfig, ViteConfig, VitePlugin


class PublicFeatureFlags(Struct, frozen=True, gc=False):
    """Typed feature flags serialized into ``.litestar.json`` at startup."""

    enable_billing_v2: bool
    support_email: str
    max_upload_mb: int


def create_app() -> Litestar:
    """Create a Litestar application exposing build-time static props to Vite."""
    flags = PublicFeatureFlags(enable_billing_v2=True, support_email="support@example.com", max_upload_mb=50)
    vite_config = ViteConfig(
        mode="spa",
        dev_mode=True,
        static_props={"appName": "Billing Portal", "features": flags},
        runtime=RuntimeConfig(start_dev_server=False),
        types=TypeGenConfig(generate_sdk=False, generate_routes=True),
    )
    return Litestar(plugins=[VitePlugin(config=vite_config)])


def main() -> None:
    """Verify static props are normalized on ``ViteConfig``."""
    app = create_app()
    vite_plugin = app.plugins.get(VitePlugin)
    assert vite_plugin.config.static_props["appName"] == "Billing Portal"


__all__ = ("PublicFeatureFlags", "create_app", "main")
