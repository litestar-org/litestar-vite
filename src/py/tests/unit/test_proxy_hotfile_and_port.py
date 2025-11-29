from pathlib import Path

import pytest

from litestar_vite.config import RuntimeConfig, ViteConfig
from litestar_vite.plugin import VitePlugin


def test_proxy_target_set_but_no_hotfile_written(tmp_path: Path) -> None:
    """Ensure proxy target is computed but hotfile is NOT written by Python.

    The TypeScript Vite plugin now writes the hotfile when the dev server starts.
    Python only sets up the proxy target URL for internal use.
    """
    cfg = ViteConfig(dev_mode=True)
    cfg.paths.bundle_dir = tmp_path
    plugin = VitePlugin(config=cfg)

    # Ensure proxy target computed
    plugin._ensure_proxy_target()

    # Proxy target should be set
    assert plugin._proxy_target is not None
    assert plugin._proxy_target.startswith(f"{cfg.protocol}://{cfg.host}:")

    # Hotfile should NOT be written by Python (TypeScript writes it)
    hotfile = tmp_path / cfg.hot_file
    assert not hotfile.exists()


def test_auto_port_when_not_set(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Ensure a free port is auto-picked when VITE_PORT is not set."""
    monkeypatch.delenv("VITE_PORT", raising=False)
    cfg = ViteConfig(dev_mode=True)
    cfg.paths.bundle_dir = tmp_path
    original_port = cfg.port  # Should be 5173 by default

    plugin = VitePlugin(config=cfg)
    plugin._ensure_proxy_target()

    # Proxy target should have been set with an auto-picked port
    assert plugin._proxy_target is not None
    # Port should be auto-picked (not default 5173)
    # The config's port should have been updated to the auto-picked port
    assert cfg.port != original_port or cfg.port != 5173  # At least one should be true
    # Proxy target should contain the auto-picked port
    assert plugin._proxy_target.count(":") >= 2  # protocol://host:port
    assert str(cfg.port) in plugin._proxy_target


def test_direct_mode_does_not_write_hotfile(tmp_path: Path) -> None:
    cfg = ViteConfig(dev_mode=True, runtime=RuntimeConfig(proxy_mode="direct"))
    cfg.paths.bundle_dir = tmp_path
    plugin = VitePlugin(config=cfg)

    plugin._ensure_proxy_target()

    assert not (tmp_path / cfg.hot_file).exists()
