from pathlib import Path

from litestar.serialization import decode_json

from litestar_vite.config import ViteConfig
from litestar_vite.plugin._utils import write_runtime_config_file


def test_runtime_config_includes_litestar_version(tmp_path: Path, monkeypatch: object) -> None:
    # Arrange
    cfg = ViteConfig()
    cfg.paths.root = tmp_path
    # ensure a predictable version
    monkeypatch.setenv("LITESTAR_VERSION", "9.9.9")

    # Act
    path_str = write_runtime_config_file(cfg)
    data = decode_json(Path(path_str).read_text())

    # Assert
    assert data["litestarVersion"] == "9.9.9"
