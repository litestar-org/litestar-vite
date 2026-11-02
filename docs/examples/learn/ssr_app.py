"""Server-Side Rendering (SSR) configuration for development and production IPC."""

from __future__ import annotations

from pathlib import Path

from litestar import Litestar, get

from litestar_vite import InertiaConfig, InertiaSSRConfig, PathConfig, RuntimeConfig, ViteConfig, VitePlugin


@get("/articles/architecture", component="Articles/Show", sync_to_thread=False)
def show_article() -> dict[str, str]:
    """Return Inertia props rendered on the server during initial page load."""
    return {"slug": "architecture", "title": "Architecture Deep Dive"}


def create_app(*, dev_mode: bool = True) -> Litestar:
    """Configure SSR with automatic dev RunnableDevEnvironment and prod stdio worker."""
    vite_config = ViteConfig(
        mode="hybrid",
        dev_mode=dev_mode,
        paths=PathConfig(
            resource_dir=Path("resources"), bundle_dir=Path("public/build"), ssr_output_dir=Path("bootstrap/ssr")
        ),
        inertia=InertiaConfig(
            root_template="index.html", ssr=InertiaSSRConfig(enabled=True, timeout=2.0, fallback_to_client=True)
        ),
        runtime=RuntimeConfig(start_dev_server=False),
    )
    return Litestar(route_handlers=[show_article], plugins=[VitePlugin(config=vite_config)])


def main() -> None:
    """Verify SSR configuration resolves cleanly in development mode."""
    app = create_app(dev_mode=True)
    plugin = app.plugins.get(VitePlugin)
    assert isinstance(plugin.config.inertia, InertiaConfig)
    assert isinstance(plugin.config.inertia.ssr, InertiaSSRConfig)
    assert plugin.config.inertia.ssr.enabled is True


__all__ = ("create_app", "main", "show_article")
