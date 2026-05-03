"""SSR /render Node process auto-start lifecycle.

VitePlugin.server_lifespan is responsible for starting/stopping the Inertia SSR
Node process when ``InertiaSSRConfig.command`` is configured. These tests
exercise the lifecycle without actually spawning a real Node process — the
``ViteProcess`` is patched to return mocks.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from litestar import Litestar
from litestar.middleware.session.client_side import CookieBackendConfig

from litestar_vite.config import InertiaConfig, InertiaSSRConfig, PathConfig, RuntimeConfig, SPAConfig, ViteConfig
from litestar_vite.plugin import VitePlugin

_SESSION = CookieBackendConfig(secret=b"x" * 32).middleware


def _build_hybrid_plugin_with_ssr(
    tmp_path: Path,
    *,
    command: "list[str] | None" = None,
    auto_start: bool = True,
    health_check: bool = False,
    dev_mode: bool = True,
) -> VitePlugin:
    resource_dir = tmp_path / "resources"
    resource_dir.mkdir()
    (resource_dir / "index.html").write_text(
        '<!DOCTYPE html><html><head></head><body><div id="app"></div></body></html>'
    )
    ssr_config = InertiaSSRConfig(command=command, auto_start=auto_start, health_check=health_check)
    return VitePlugin(
        config=ViteConfig(
            mode="hybrid",
            paths=PathConfig(root=tmp_path, resource_dir=resource_dir),
            runtime=RuntimeConfig(dev_mode=dev_mode, start_dev_server=False),
            spa=SPAConfig(app_selector="#app"),
            inertia=InertiaConfig(ssr=ssr_config),
        )
    )


def test_ssr_config_defaults_have_no_command_so_plugin_does_nothing() -> None:
    """Without a command, the plugin must not attempt to start any SSR process."""
    config = InertiaSSRConfig()
    assert config.command is None
    assert config.auto_start is True
    # health_check is opt-in (False default) so SSR starts non-blocking and Litestar
    # is ready to serve requests immediately.
    assert config.health_check is False
    assert config.health_check_timeout > 0
    assert config.cwd is None


def test_server_lifespan_starts_and_stops_ssr_process_when_command_set(tmp_path: Path) -> None:
    """server_lifespan must spawn the SSR process and stop it on shutdown."""
    plugin = _build_hybrid_plugin_with_ssr(
        tmp_path, command=["npm", "run", "start:ssr"], auto_start=True, health_check=False
    )
    app = Litestar(plugins=[plugin], middleware=[_SESSION])

    fake_process = MagicMock(name="ssr_process")
    with patch.object(VitePlugin, "_get_ssr_process", return_value=fake_process):
        with plugin.server_lifespan(app):
            fake_process.start.assert_called_once_with(["npm", "run", "start:ssr"], plugin.config.root_dir)
            fake_process.stop.assert_not_called()
        fake_process.stop.assert_called_once()


def test_server_lifespan_skips_ssr_start_when_auto_start_false(tmp_path: Path) -> None:
    """auto_start=False keeps the command as documentation but does not spawn anything."""
    plugin = _build_hybrid_plugin_with_ssr(
        tmp_path, command=["npm", "run", "start:ssr"], auto_start=False, health_check=False
    )
    app = Litestar(plugins=[plugin], middleware=[_SESSION])

    fake_process = MagicMock(name="ssr_process")
    with patch.object(VitePlugin, "_get_ssr_process", return_value=fake_process):
        with plugin.server_lifespan(app):
            pass

    fake_process.start.assert_not_called()
    fake_process.stop.assert_not_called()


def test_server_lifespan_uses_ssr_cwd_when_set(tmp_path: Path) -> None:
    """InertiaSSRConfig.cwd overrides the default ViteConfig.root_dir."""
    custom_cwd = tmp_path / "ssr-app"
    custom_cwd.mkdir()
    plugin = _build_hybrid_plugin_with_ssr(tmp_path, command=["npm", "run", "start:ssr"], health_check=False)
    ssr = plugin._resolved_ssr_config()
    assert ssr is not None
    ssr.cwd = custom_cwd

    app = Litestar(plugins=[plugin], middleware=[_SESSION])
    fake_process = MagicMock(name="ssr_process")
    with patch.object(VitePlugin, "_get_ssr_process", return_value=fake_process):
        with plugin.server_lifespan(app):
            pass

    fake_process.start.assert_called_once_with(["npm", "run", "start:ssr"], custom_cwd)


def test_server_lifespan_runs_health_check_when_enabled(tmp_path: Path) -> None:
    """health_check=True invokes _run_ssr_health_check after starting the process."""
    plugin = _build_hybrid_plugin_with_ssr(tmp_path, command=["npm", "run", "start:ssr"], health_check=True)
    app = Litestar(plugins=[plugin], middleware=[_SESSION])

    fake_process = MagicMock(name="ssr_process")
    with (
        patch.object(VitePlugin, "_get_ssr_process", return_value=fake_process),
        patch.object(VitePlugin, "_run_ssr_health_check") as mock_health,
    ):
        with plugin.server_lifespan(app):
            mock_health.assert_called_once()


def test_server_lifespan_starts_ssr_in_production_mode_too(tmp_path: Path) -> None:
    """SSR auto-start works in dev_mode=False (the Vite branch is skipped, SSR runs)."""
    plugin = _build_hybrid_plugin_with_ssr(
        tmp_path, command=["npm", "run", "start:ssr"], health_check=False, dev_mode=False
    )
    app = Litestar(plugins=[plugin], middleware=[_SESSION])

    fake_process = MagicMock(name="ssr_process")
    with patch.object(VitePlugin, "_get_ssr_process", return_value=fake_process):
        with plugin.server_lifespan(app):
            fake_process.start.assert_called_once_with(["npm", "run", "start:ssr"], plugin.config.root_dir)
        fake_process.stop.assert_called_once()


def test_server_lifespan_no_ssr_process_when_inertia_disabled(tmp_path: Path) -> None:
    """No Inertia config → no SSR process even with hybrid-shaped ViteConfig."""
    resource_dir = tmp_path / "resources"
    resource_dir.mkdir()
    (resource_dir / "index.html").write_text("<html><body><div id='app'></div></body></html>")
    plugin = VitePlugin(
        config=ViteConfig(
            mode="hybrid",
            paths=PathConfig(root=tmp_path, resource_dir=resource_dir),
            runtime=RuntimeConfig(dev_mode=False, start_dev_server=False),
            spa=SPAConfig(app_selector="#app"),
            inertia=InertiaConfig(ssr=None),
        )
    )
    app = Litestar(plugins=[plugin], middleware=[_SESSION])

    fake_process = MagicMock(name="ssr_process")
    with patch.object(VitePlugin, "_get_ssr_process", return_value=fake_process):
        with plugin.server_lifespan(app):
            pass

    fake_process.start.assert_not_called()


def test_server_lifespan_does_not_spawn_when_command_none(tmp_path: Path) -> None:
    """Backward-compat: when the user manages the SSR Node process separately.

    InertiaSSRConfig() with no ``command`` keeps the URL contract but the plugin must not
    spawn anything. Users running ``npm run start:ssr`` in a separate terminal continue
    to work as before.
    """
    plugin = _build_hybrid_plugin_with_ssr(tmp_path, command=None, health_check=False)
    app = Litestar(plugins=[plugin], middleware=[_SESSION])

    fake_process = MagicMock(name="ssr_process")
    with patch.object(VitePlugin, "_get_ssr_process", return_value=fake_process):
        with plugin.server_lifespan(app):
            pass

    fake_process.start.assert_not_called()
    # Confirm SSR config is still wired (URL contract preserved for the Inertia fetcher)
    ssr = plugin._resolved_ssr_config()
    assert ssr is not None
    assert ssr.url == "http://127.0.0.1:13714/render"


@pytest.mark.parametrize(
    "command", [["npm", "run", "start:ssr"], ["bun", "run", "start:ssr"], ["node", "bootstrap/ssr/ssr.js"]]
)
def test_resolved_ssr_config_returns_command_intact(tmp_path: Path, command: list[str]) -> None:
    """The plugin returns the configured command verbatim — no rewriting."""
    plugin = _build_hybrid_plugin_with_ssr(tmp_path, command=command, health_check=False)
    ssr = plugin._resolved_ssr_config()
    assert ssr is not None
    assert ssr.command == command
