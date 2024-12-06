from pathlib import Path, PosixPath

from litestar_vite.config import ViteConfig


def test_default_vite_config() -> None:
    config = ViteConfig()
    assert isinstance(config.bundle_dir, Path)
    assert isinstance(config.public_dir, Path)
    assert config.ssr_output_dir is None
    assert isinstance(config.resource_dir, Path)
    assert isinstance(config.root_dir, (Path, PosixPath))
    assert config.root_dir == PosixPath(".")
