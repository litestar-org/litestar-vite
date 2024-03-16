from pathlib import Path

from litestar_vite.config import ViteConfig


def test_default_vite_config() -> None:
    config = ViteConfig()
    assert isinstance(config.bundle_dir, Path)
