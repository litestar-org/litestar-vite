from __future__ import annotations

from pathlib import Path

from litestar_vite.config import ViteConfig
from litestar_vite.plugin import VitePlugin


def test_hotfile_written_with_proxy_target(tmp_path: Path) -> None:
    cfg = ViteConfig(dev_mode=True)
    cfg.paths.bundle_dir = tmp_path
    plugin = VitePlugin(config=cfg)

    # Ensure proxy target computed and hotfile written
    plugin._ensure_proxy_target()

    hotfile = tmp_path / cfg.hot_file
    assert hotfile.exists()
    target = hotfile.read_text().strip()
    assert target.startswith(f"{cfg.protocol}://{cfg.host}:")
    assert target.count(":") >= 2  # host:port present


def test_auto_port_when_not_set(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.delenv("VITE_PORT", raising=False)
    cfg = ViteConfig(dev_mode=True)
    cfg.paths.bundle_dir = tmp_path
    plugin = VitePlugin(config=cfg)

    plugin._ensure_proxy_target()

    hotfile = tmp_path / cfg.hot_file
    target = hotfile.read_text().strip()
    # ensure port is not default 5173 when auto-picked (likely different)
    assert target != f"{cfg.protocol}://{cfg.host}:5173"
