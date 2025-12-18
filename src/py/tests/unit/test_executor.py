"""Tests for litestar_vite.executor module."""

from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from litestar_vite.config import RuntimeConfig, ViteConfig
from litestar_vite.exceptions import ViteExecutableNotFoundError, ViteExecutionError
from litestar_vite.executor import BunExecutor, DenoExecutor, NodeenvExecutor, NodeExecutor, PnpmExecutor, YarnExecutor

# =====================================================
# Executor Base Tests (NodeExecutor, BunExecutor, etc.)
# =====================================================


@patch("shutil.which")
def test_executor_resolve_executable_found(mock_which: Mock) -> None:
    """Test that resolve_executable returns the path when found."""
    mock_which.return_value = "/usr/bin/npm"
    executor = NodeExecutor()
    assert executor._resolve_executable() == "/usr/bin/npm"


@patch("shutil.which")
def test_executor_resolve_executable_not_found(mock_which: Mock) -> None:
    """Test that resolve_executable raises when executable not found."""
    mock_which.return_value = None
    executor = NodeExecutor()
    with pytest.raises(ViteExecutableNotFoundError):
        executor._resolve_executable()


def test_executor_resolve_executable_custom_path() -> None:
    """Test that custom executable path is used directly."""
    executor = NodeExecutor(executable_path="/custom/npm")
    assert executor._resolve_executable() == "/custom/npm"


def test_apply_silent_flag_inserts_after_run() -> None:
    """Silent flag should be placed immediately after 'run'."""
    executor = NodeExecutor(silent=True)
    assert executor._apply_silent_flag(["run", "dev"]) == ["run", "--silent", "dev"]


def test_apply_silent_flag_appends_when_no_run() -> None:
    """Silent flag should be appended when no run subcommand is present."""
    executor = NodeExecutor(silent=True)
    assert executor._apply_silent_flag(["install"]) == ["install", "--silent"]


@patch("subprocess.Popen")
@patch("shutil.which")
def test_executor_run_command(mock_which: Mock, mock_popen: Mock) -> None:
    """Test executor run command starts subprocess correctly."""
    mock_which.return_value = "/usr/bin/npm"
    executor = NodeExecutor()
    mock_process = Mock()
    mock_popen.return_value = mock_process

    process = executor.run(["install"], Path("/tmp"))

    assert process == mock_process
    mock_popen.assert_called_once()
    args, kwargs = mock_popen.call_args
    assert args[0] == ["/usr/bin/npm", "install"]
    assert kwargs["cwd"] == Path("/tmp")


@patch("subprocess.run")
@patch("shutil.which")
def test_executor_execute_command_success(mock_which: Mock, mock_run: Mock) -> None:
    """Test executor execute command succeeds."""
    mock_which.return_value = "/usr/bin/npm"
    mock_run.return_value = Mock(returncode=0)
    executor = NodeExecutor()

    executor.execute(["install"], Path("/tmp"))

    mock_run.assert_called_once()


@patch("subprocess.run")
@patch("shutil.which")
def test_executor_execute_command_failure(mock_which: Mock, mock_run: Mock) -> None:
    """Test executor execute command raises on failure."""
    mock_which.return_value = "/usr/bin/npm"
    mock_run.return_value = Mock(returncode=1, stderr=b"error")
    executor = NodeExecutor()

    with pytest.raises(ViteExecutionError):
        executor.execute(["install"], Path("/tmp"))


@patch("subprocess.run")
@patch("shutil.which")
def test_executor_install_command(mock_which: Mock, mock_run: Mock) -> None:
    """Test executor install command runs correctly."""
    mock_which.return_value = "/usr/bin/npm"
    mock_run.return_value = Mock(returncode=0)
    executor = NodeExecutor()

    executor.install(Path("/tmp"))

    mock_run.assert_called_once()
    args, _ = mock_run.call_args
    assert args[0] == ["/usr/bin/npm", "install"]


@patch("subprocess.run")
@patch("shutil.which")
def test_executor_bun_install(mock_which: Mock, mock_run: Mock) -> None:
    """Test BunExecutor uses bun for install."""
    mock_which.return_value = "/usr/bin/bun"
    mock_run.return_value = Mock(returncode=0)
    executor = BunExecutor()

    executor.install(Path("/tmp"))

    mock_run.assert_called_once()
    args, _ = mock_run.call_args
    assert args[0] == ["/usr/bin/bun", "install"]


def test_executor_deno_install_no_op() -> None:
    """Test DenoExecutor install is a no-op."""
    executor = DenoExecutor()
    # Should not raise error
    executor.install(Path("/tmp"))


# =====================================================
# Update Command Tests
# =====================================================


@patch("subprocess.run")
@patch("shutil.which")
def test_executor_update_command(mock_which: Mock, mock_run: Mock) -> None:
    """Test executor update command runs correctly."""
    mock_which.return_value = "/usr/bin/npm"
    mock_run.return_value = Mock(returncode=0)
    executor = NodeExecutor()

    executor.update(Path("/tmp"))

    mock_run.assert_called_once()
    args, _ = mock_run.call_args
    assert args[0] == ["/usr/bin/npm", "update"]


@patch("subprocess.run")
@patch("shutil.which")
def test_executor_update_latest_npm(mock_which: Mock, mock_run: Mock) -> None:
    """Test NodeExecutor update with --latest uses --save flag."""
    mock_which.return_value = "/usr/bin/npm"
    mock_run.return_value = Mock(returncode=0)
    executor = NodeExecutor()

    executor.update(Path("/tmp"), latest=True)

    mock_run.assert_called_once()
    args, _ = mock_run.call_args
    assert args[0] == ["/usr/bin/npm", "update", "--save"]


@patch("subprocess.run")
@patch("shutil.which")
def test_executor_update_latest_yarn(mock_which: Mock, mock_run: Mock) -> None:
    """Test YarnExecutor update with --latest uses yarn upgrade --latest."""
    mock_which.return_value = "/usr/bin/yarn"
    mock_run.return_value = Mock(returncode=0)
    executor = YarnExecutor()

    executor.update(Path("/tmp"), latest=True)

    mock_run.assert_called_once()
    args, _ = mock_run.call_args
    assert args[0] == ["/usr/bin/yarn", "upgrade", "--latest"]


@patch("subprocess.run")
@patch("shutil.which")
def test_executor_update_latest_pnpm(mock_which: Mock, mock_run: Mock) -> None:
    """Test PnpmExecutor update with --latest uses pnpm update --latest."""
    mock_which.return_value = "/usr/bin/pnpm"
    mock_run.return_value = Mock(returncode=0)
    executor = PnpmExecutor()

    executor.update(Path("/tmp"), latest=True)

    mock_run.assert_called_once()
    args, _ = mock_run.call_args
    assert args[0] == ["/usr/bin/pnpm", "update", "--latest"]


@patch("subprocess.run")
@patch("shutil.which")
def test_executor_update_latest_bun(mock_which: Mock, mock_run: Mock) -> None:
    """Test BunExecutor update with --latest uses bun update --latest."""
    mock_which.return_value = "/usr/bin/bun"
    mock_run.return_value = Mock(returncode=0)
    executor = BunExecutor()

    executor.update(Path("/tmp"), latest=True)

    mock_run.assert_called_once()
    args, _ = mock_run.call_args
    assert args[0] == ["/usr/bin/bun", "update", "--latest"]


def test_executor_deno_update_no_op() -> None:
    """Test DenoExecutor update is a no-op."""
    executor = DenoExecutor()
    # Should not raise error
    executor.update(Path("/tmp"))
    executor.update(Path("/tmp"), latest=True)


@patch("subprocess.run")
@patch("shutil.which")
def test_executor_update_failure(mock_which: Mock, mock_run: Mock) -> None:
    """Test executor update command raises on failure."""
    mock_which.return_value = "/usr/bin/npm"
    mock_run.return_value = Mock(returncode=1)
    executor = NodeExecutor()

    with pytest.raises(ViteExecutionError):
        executor.update(Path("/tmp"))


# =====================================================
# NodeenvExecutor Tests
# =====================================================


@patch("litestar_vite.executor.NodeenvExecutor._find_npm_in_venv")
@patch("subprocess.run")
def test_nodeenv_executor_install_without_detection(mock_run: Mock, mock_find: Mock) -> None:
    """Test NodeenvExecutor install without nodeenv detection."""
    config = ViteConfig(runtime=RuntimeConfig(detect_nodeenv=False))
    executor = NodeenvExecutor(config)
    mock_find.return_value = "/venv/bin/npm"
    mock_run.return_value = Mock(returncode=0)

    executor.install(Path("/tmp"))

    # Should only run npm install
    assert mock_run.call_count == 1
    args, _ = mock_run.call_args
    assert args[0] == ["/venv/bin/npm", "install"]


@patch("litestar_vite.executor.NodeenvExecutor._get_nodeenv_command")
@patch("litestar_vite.executor.NodeenvExecutor._find_npm_in_venv")
@patch("subprocess.run")
@patch("importlib.util.find_spec")
def test_nodeenv_executor_install_with_detection(
    mock_find_spec: Mock, mock_run: Mock, mock_find_npm: Mock, mock_get_cmd: Mock
) -> None:
    """Test NodeenvExecutor install with nodeenv detection enabled."""
    config = ViteConfig(runtime=RuntimeConfig(detect_nodeenv=True))
    executor = NodeenvExecutor(config)
    mock_find_spec.return_value = True
    mock_get_cmd.return_value = "nodeenv"
    mock_find_npm.return_value = "/venv/bin/npm"
    mock_run.return_value = Mock(returncode=0)

    executor.install(Path("/tmp"))

    # Should run nodeenv install then npm install
    assert mock_run.call_count == 2
    args1, _ = mock_run.call_args_list[0]
    assert args1[0][0] == "nodeenv"
    args2, _ = mock_run.call_args_list[1]
    assert args2[0] == ["/venv/bin/npm", "install"]


@patch("litestar_vite.executor.NodeenvExecutor._find_npm_in_venv")
@patch("subprocess.Popen")
def test_nodeenv_executor_run(mock_popen: Mock, mock_find: Mock) -> None:
    """Test NodeenvExecutor run command."""
    config = ViteConfig()
    executor = NodeenvExecutor(config)
    mock_find.return_value = "/venv/bin/npm"
    mock_process = Mock()
    mock_popen.return_value = mock_process

    process = executor.run(["dev"], Path("/tmp"))

    assert process == mock_process
    mock_popen.assert_called_once()
    args, _kwargs = mock_popen.call_args
    assert args[0] == ["/venv/bin/npm", "dev"]


@patch("litestar_vite.executor.NodeenvExecutor._find_npm_in_venv")
@patch("subprocess.run")
def test_nodeenv_executor_execute_success(mock_run: Mock, mock_find: Mock) -> None:
    """Test NodeenvExecutor execute command succeeds."""
    config = ViteConfig()
    executor = NodeenvExecutor(config)
    mock_find.return_value = "/venv/bin/npm"
    mock_run.return_value = Mock(returncode=0)

    executor.execute(["build"], Path("/tmp"))

    mock_run.assert_called_once()
    args, _kwargs = mock_run.call_args
    assert args[0] == ["/venv/bin/npm", "build"]


@patch("litestar_vite.executor.NodeenvExecutor._find_npm_in_venv")
@patch("subprocess.run")
def test_nodeenv_executor_execute_failure(mock_run: Mock, mock_find: Mock) -> None:
    """Test NodeenvExecutor execute command raises on failure."""
    config = ViteConfig()
    executor = NodeenvExecutor(config)
    mock_find.return_value = "/venv/bin/npm"
    mock_run.return_value = Mock(returncode=1, stderr=b"error")

    with pytest.raises(ViteExecutionError):
        executor.execute(["build"], Path("/tmp"))


@patch("litestar_vite.executor.NodeenvExecutor._find_npm_in_venv")
@patch("subprocess.run")
def test_nodeenv_executor_update(mock_run: Mock, mock_find: Mock) -> None:
    """Test NodeenvExecutor update command."""
    config = ViteConfig()
    executor = NodeenvExecutor(config)
    mock_find.return_value = "/venv/bin/npm"
    mock_run.return_value = Mock(returncode=0)

    executor.update(Path("/tmp"))

    mock_run.assert_called_once()
    args, _ = mock_run.call_args
    assert args[0] == ["/venv/bin/npm", "update"]


@patch("litestar_vite.executor.NodeenvExecutor._find_npm_in_venv")
@patch("subprocess.run")
def test_nodeenv_executor_update_latest(mock_run: Mock, mock_find: Mock) -> None:
    """Test NodeenvExecutor update command with --latest."""
    config = ViteConfig()
    executor = NodeenvExecutor(config)
    mock_find.return_value = "/venv/bin/npm"
    mock_run.return_value = Mock(returncode=0)

    executor.update(Path("/tmp"), latest=True)

    mock_run.assert_called_once()
    args, _ = mock_run.call_args
    assert args[0] == ["/venv/bin/npm", "update", "--save"]
