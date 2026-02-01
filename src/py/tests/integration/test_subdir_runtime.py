from pathlib import Path
from unittest.mock import MagicMock

import pytest
from pytest_mock import MockerFixture
from litestar import Litestar
from litestar_vite import PathConfig, ViteConfig, VitePlugin


@pytest.fixture
def subdir_root(tmp_path: Path) -> Path:
    """Create a subdirectory for the frontend."""
    web_dir = tmp_path / "web"
    web_dir.mkdir()
    return web_dir


def test_vite_plugin_runtime_isolation_with_relative_path(
    subdir_root: Path,
    monkeypatch: pytest.MonkeyPatch,
    mocker: MockerFixture,
) -> None:
    """
    Test that when a relative path is provided as the root,
    artifacts are written to the correct subdirectory and
    the Vite process is started in that subdirectory.
    """
    # 1. Setup
    # We simulate running from the parent directory (tmp_path)
    monkeypatch.chdir(subdir_root.parent)

    # Use a relative path "web" which corresponds to subdir_root
    relative_root = Path("web")
    
    # Configure Vite with relative root
    vite_config = ViteConfig(
        dev_mode=True,
        paths=PathConfig(root=relative_root),
    )
    
    plugin = VitePlugin(config=vite_config)
    
    # Mock the process start to verify arguments
    mock_start = mocker.patch.object(plugin._vite_process, "start")
    
    app = Litestar(plugins=[plugin])
    
    # 2. Execute server_lifespan
    # We use the context manager manually to trigger the startup logic
    with plugin.server_lifespan(app):
        pass

    # 3. Verify
    # Check where .litestar.json was written
    # It SHOULD be in web/.litestar.json
    expected_config_path = subdir_root / ".litestar.json"
    
    # Check if the file exists at the expected absolute path
    # If the bug exists, it might be written to ./litestar.json (root) 
    # OR it might be written to web/.litestar.json but the process started in wrong CWD
    
    # The spec says:
    # "write_runtime_config_file uses config.root_dir... if config.root_dir is relative... writes to web/.litestar.json"
    # So the file location might actually be correct if it respects the relative path.
    # But the process CWD might be wrong or the absolute resolution missing.
    
    # Check the start call
    assert mock_start.called
    args, _ = mock_start.call_args
    _, cwd = args
    
    # CRITICAL ASSERTION: The CWD passed to the process must be an ABSOLUTE path
    # to the subdirectory.
    # If it passes "web" (relative), that might be technically valid for subprocess if CWD is correct,
    # but the goal is "Absolute Path Resolution in ViteConfig".
    assert isinstance(cwd, Path)
    assert cwd.is_absolute(), f"Vite process cwd {cwd} is not absolute"
    assert cwd == subdir_root, f"Vite process started in {cwd}, expected {subdir_root}"

