"""Tests for litestar_vite.executor module."""

import importlib.util
import os
import subprocess
import sys
import types
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from litestar_vite.config import PathConfig, RuntimeConfig, ViteConfig
from litestar_vite.exceptions import ViteExecutableNotFoundError, ViteExecutionError
from litestar_vite.executor import BunExecutor, DenoExecutor, NodeenvExecutor, NodeExecutor, PnpmExecutor, YarnExecutor


@pytest.fixture(autouse=True)
def _isolate_venv_binaries(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Isolate unit tests from wheel-provisioned JS binaries installed in the host .venv."""
    monkeypatch.setattr(sys, "executable", str(tmp_path / "_isolated_venv" / "bin" / "python"))
    monkeypatch.setattr(
        "litestar_vite.executor.find_spec", lambda name: None if name == "deno" else importlib.util.find_spec(name)
    )


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
def test_executor_resolve_executable_uses_cache(mock_which: Mock) -> None:
    """Test executable resolution is cached after first lookup."""
    mock_which.return_value = "/usr/bin/npm"
    executor = NodeExecutor()

    first = executor._resolve_executable()
    second = executor._resolve_executable()

    assert first == "/usr/bin/npm"
    assert second == "/usr/bin/npm"
    mock_which.assert_called_once_with("npm")


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
def test_executor_run_command(mock_which: Mock, mock_popen: Mock, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test executor run command starts subprocess correctly."""
    monkeypatch.delenv("LITESTAR_VITE_MANAGED", raising=False)
    monkeypatch.setenv("LITESTAR_VITE_EXISTING", "preserved")
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
    assert kwargs["shell"] is False
    assert kwargs["start_new_session"] is True
    assert kwargs["stderr"] is subprocess.PIPE
    assert kwargs["env"]["LITESTAR_VITE_EXISTING"] == "preserved"
    assert kwargs["env"]["LITESTAR_VITE_MANAGED"] == "1"
    assert "LITESTAR_VITE_MANAGED" not in os.environ


@patch("subprocess.Popen")
@patch("shutil.which")
def test_executor_run_rewrites_bare_binary_when_resolved_name_has_extension(mock_which: Mock, mock_popen: Mock) -> None:
    """Short binary names should be rewritten to the resolved executable without duplication."""
    mock_which.return_value = "C:/Program Files/nodejs/npm.CMD"
    executor = NodeExecutor()
    mock_process = Mock()
    mock_popen.return_value = mock_process

    process = executor.run(["npm", "run", "dev"], Path("/tmp"))

    assert process == mock_process
    args, _kwargs = mock_popen.call_args
    assert args[0] == ["C:/Program Files/nodejs/npm.CMD", "run", "dev"]


@patch("litestar_vite.executor.platform.system", return_value="Windows")
@patch("subprocess.Popen")
@patch("shutil.which")
def test_executor_run_windows_uses_argv_without_shell(
    mock_which: Mock, mock_popen: Mock, mock_system: Mock, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Windows sidecars retain argv boundaries and a dedicated process group."""
    monkeypatch.setattr("litestar_vite.executor._create_new_process_group", 512)
    mock_which.return_value = "C:/Program Files/nodejs/npm.CMD"
    executor = NodeExecutor()

    executor.run(["npm", "run", "dev"], Path("C:/app"))

    args, kwargs = mock_popen.call_args
    assert args[0] == ["C:/Program Files/nodejs/npm.CMD", "run", "dev"]
    assert kwargs["shell"] is False
    assert kwargs["creationflags"] > 0
    mock_system.assert_called()


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
def test_executor_execute_rewrites_bare_binary_when_resolved_name_has_extension(
    mock_which: Mock, mock_run: Mock
) -> None:
    """Execute should drop the duplicated short binary when the resolved name has an extension."""
    mock_which.return_value = "C:/Program Files/nodejs/npm.CMD"
    mock_run.return_value = Mock(returncode=0)
    executor = NodeExecutor()

    executor.execute(["npm", "run", "build"], Path("/tmp"))

    args, _kwargs = mock_run.call_args
    assert args[0] == ["C:/Program Files/nodejs/npm.CMD", "run", "build"]


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


@patch("subprocess.run")
@patch("shutil.which")
def test_executor_deno_install(mock_which: Mock, mock_run: Mock) -> None:
    """Test DenoExecutor runs deno install."""
    mock_which.return_value = "/usr/bin/deno"
    mock_run.return_value = Mock(returncode=0)
    executor = DenoExecutor()

    executor.install(Path("/tmp"))

    mock_run.assert_called_once()
    args, _ = mock_run.call_args
    assert args[0] == ["/usr/bin/deno", "install"]


def test_executor_deno_commands() -> None:
    """Test DenoExecutor start_command and build_command use deno task."""
    executor = DenoExecutor()
    assert executor.start_command == ["deno", "task", "start"]
    assert executor.build_command == ["deno", "task", "build"]


@patch("subprocess.run")
@patch("shutil.which")
def test_executor_deno_execute_script_prepends_run_allow_all(mock_which: Mock, mock_run: Mock) -> None:
    """Test DenoExecutor.execute prepends run -A for script arguments."""
    mock_which.return_value = "/usr/bin/deno"
    mock_run.return_value = Mock(returncode=0)
    executor = DenoExecutor()

    executor.execute(["script.ts", "--flag"], Path("/tmp"))

    mock_run.assert_called_once()
    args, _ = mock_run.call_args
    assert args[0] == ["/usr/bin/deno", "run", "-A", "script.ts", "--flag"]


@patch("subprocess.run")
@patch("shutil.which")
def test_executor_deno_execute_preserves_task_subcommand(mock_which: Mock, mock_run: Mock) -> None:
    """Test DenoExecutor.execute preserves explicit Deno subcommands like task."""
    mock_which.return_value = "/usr/bin/deno"
    mock_run.return_value = Mock(returncode=0)
    executor = DenoExecutor()

    executor.execute(["deno", "task", "build"], Path("/tmp"))

    mock_run.assert_called_once()
    args, _ = mock_run.call_args
    assert args[0] == ["/usr/bin/deno", "task", "build"]


def test_hatch_build_deno_commands(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test tools/hatch_build.py supports deno install and deno task build."""
    stub_interface = types.ModuleType("hatchling.builders.hooks.plugin.interface")
    setattr(stub_interface, "BuildHookInterface", object)
    monkeypatch.setitem(sys.modules, "hatchling", types.ModuleType("hatchling"))
    monkeypatch.setitem(sys.modules, "hatchling.builders", types.ModuleType("hatchling.builders"))
    monkeypatch.setitem(sys.modules, "hatchling.builders.hooks", types.ModuleType("hatchling.builders.hooks"))
    monkeypatch.setitem(
        sys.modules, "hatchling.builders.hooks.plugin", types.ModuleType("hatchling.builders.hooks.plugin")
    )
    monkeypatch.setitem(sys.modules, "hatchling.builders.hooks.plugin.interface", stub_interface)

    hatch_build_path = Path(__file__).resolve().parents[4] / "tools" / "hatch_build.py"
    spec = importlib.util.spec_from_file_location("hatch_build", hatch_build_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    assert module._install_command("deno", tmp_path) == ["deno", "install"]
    assert module._build_command("deno") == ["deno", "task", "build"]


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


@patch("subprocess.run")
@patch("shutil.which")
def test_executor_deno_update(mock_which: Mock, mock_run: Mock) -> None:
    """Test DenoExecutor update runs deno outdated --update [--latest]."""
    mock_which.return_value = "/usr/bin/deno"
    mock_run.return_value = Mock(returncode=0)
    executor = DenoExecutor()

    executor.update(Path("/tmp"), latest=False)
    executor.update(Path("/tmp"), latest=True)

    assert mock_run.call_count == 2
    args1, _ = mock_run.call_args_list[0]
    assert args1[0] == ["/usr/bin/deno", "outdated", "--update"]
    args2, _ = mock_run.call_args_list[1]
    assert args2[0] == ["/usr/bin/deno", "outdated", "--update", "--latest"]


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
@patch("subprocess.run")
def test_nodeenv_install_raises_vite_execution_error(mock_run: Mock, mock_find: Mock) -> None:
    """Non-zero npm install returncode in NodeenvExecutor.install must raise ViteExecutionError."""
    config = ViteConfig(runtime=RuntimeConfig(detect_nodeenv=False))
    executor = NodeenvExecutor(config)
    mock_find.return_value = "/venv/bin/npm"
    mock_run.return_value = Mock(returncode=1)

    with pytest.raises(ViteExecutionError) as exc_info:
        executor.install(Path("/tmp/project"))

    assert "['/venv/bin/npm', 'install']" in str(exc_info.value)
    assert "return code 1" in str(exc_info.value)
    assert "package install failed" in str(exc_info.value)


@patch("litestar_vite.executor.NodeenvExecutor._find_npm_in_venv")
@patch("subprocess.run")
def test_nodeenv_install_succeeds_on_zero_returncode(mock_run: Mock, mock_find: Mock) -> None:
    """Zero returncode in NodeenvExecutor.install succeeds without exception."""
    config = ViteConfig(runtime=RuntimeConfig(detect_nodeenv=False))
    executor = NodeenvExecutor(config)
    mock_find.return_value = "/venv/bin/npm"
    mock_run.return_value = Mock(returncode=0)

    executor.install(Path("/tmp/project"))
    assert mock_run.call_count == 1


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
@patch("subprocess.Popen")
def test_nodeenv_executor_run_rewrites_bare_npm_to_venv_path(mock_popen: Mock, mock_find: Mock) -> None:
    """Bare npm commands should be rewritten to the nodeenv-local npm path."""
    config = ViteConfig()
    executor = NodeenvExecutor(config)
    mock_find.return_value = "/venv/bin/npm"
    mock_process = Mock()
    mock_popen.return_value = mock_process

    process = executor.run(["npm", "run", "dev"], Path("/tmp"))

    assert process == mock_process
    args, _kwargs = mock_popen.call_args
    assert args[0] == ["/venv/bin/npm", "run", "dev"]


@patch("litestar_vite.executor.NodeenvExecutor._find_npm_in_venv")
@patch("subprocess.Popen")
def test_nodeenv_executor_run_rewrites_bare_npm_with_silent_flag(mock_popen: Mock, mock_find: Mock) -> None:
    """Silent flag insertion should preserve normalized bare npm command order."""
    config = ViteConfig()
    executor = NodeenvExecutor(config, silent=True)
    mock_find.return_value = "/venv/bin/npm"
    mock_process = Mock()
    mock_popen.return_value = mock_process

    process = executor.run(["npm", "run", "dev"], Path("/tmp"))

    assert process == mock_process
    args, _kwargs = mock_popen.call_args
    assert args[0] == ["/venv/bin/npm", "run", "--silent", "dev"]


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
def test_nodeenv_executor_execute_rewrites_bare_npm_to_venv_path(mock_run: Mock, mock_find: Mock) -> None:
    """Bare npm execute commands should be rewritten to the nodeenv-local npm path."""
    config = ViteConfig()
    executor = NodeenvExecutor(config)
    mock_find.return_value = "/venv/bin/npm"
    mock_run.return_value = Mock(returncode=0)

    executor.execute(["npm", "run", "build"], Path("/tmp"))

    args, _kwargs = mock_run.call_args
    assert args[0] == ["/venv/bin/npm", "run", "build"]


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


def test_executor_resolve_executable_prioritizes_venv_bin(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """JSExecutor._resolve_executable prioritizes binaries in Path(sys.executable).parent over PATH."""
    fake_venv_bin = tmp_path / "venv" / "bin"
    fake_venv_bin.mkdir(parents=True)
    fake_python = fake_venv_bin / "python"
    fake_python.write_text("#!/bin/sh\n")
    fake_python.chmod(0o755)

    for bin_name in ("npm", "bun", "deno"):
        binary = fake_venv_bin / bin_name
        binary.write_text("#!/bin/sh\n")
        binary.chmod(0o755)

    monkeypatch.setattr(sys, "executable", str(fake_python))
    with patch("shutil.which", return_value="/usr/local/bin/fallback") as mock_which:
        assert NodeExecutor()._resolve_executable() == str(fake_venv_bin / "npm")
        assert BunExecutor()._resolve_executable() == str(fake_venv_bin / "bun")
        assert DenoExecutor()._resolve_executable() == str(fake_venv_bin / "deno")
        mock_which.assert_not_called()


def test_executor_resolve_executable_windows_venv_extensions(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """JSExecutor._resolve_executable resolves .cmd and .exe inside Windows virtualenv Scripts dir."""
    fake_scripts = tmp_path / "venv" / "Scripts"
    fake_scripts.mkdir(parents=True)
    fake_python = fake_scripts / "python.exe"
    fake_python.write_text("")
    npm_cmd = fake_scripts / "npm.cmd"
    npm_cmd.write_text("@echo off\n")

    monkeypatch.setattr(sys, "executable", str(fake_python))
    with (
        patch("litestar_vite.executor.platform.system", return_value="Windows"),
        patch("shutil.which", return_value=None),
    ):
        assert NodeExecutor()._resolve_executable() == str(npm_cmd)


def test_deno_executor_resolves_deno_wheel_find_deno_bin(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """DenoExecutor resolves deno.find_deno_bin() when the deno wheel package is installed."""
    fake_venv_bin = tmp_path / "venv" / "bin"
    fake_venv_bin.mkdir(parents=True)
    fake_python = fake_venv_bin / "python"
    fake_python.write_text("#!/bin/sh\n")
    fake_deno_wheel_bin = tmp_path / "site-packages" / "deno" / "bin" / "deno"
    fake_deno_wheel_bin.parent.mkdir(parents=True)
    fake_deno_wheel_bin.write_text("#!/bin/sh\n")
    fake_deno_wheel_bin.chmod(0o755)

    fake_deno_mod = types.ModuleType("deno")
    setattr(fake_deno_mod, "find_deno_bin", lambda: str(fake_deno_wheel_bin))

    monkeypatch.setattr(sys, "executable", str(fake_python))
    monkeypatch.setitem(sys.modules, "deno", fake_deno_mod)
    with patch("litestar_vite.executor.find_spec", return_value=object()), patch("shutil.which", return_value=None):
        assert DenoExecutor()._resolve_executable() == str(fake_deno_wheel_bin)


def test_runtime_config_provisioning_mode() -> None:
    """RuntimeConfig supports provisioning_mode Literal['auto', 'wheel', 'nodeenv', 'system']."""
    default_cfg = RuntimeConfig()
    assert default_cfg.provisioning_mode == "auto"
    assert default_cfg.detect_nodeenv is False

    wheel_cfg = RuntimeConfig(provisioning_mode="wheel")
    assert wheel_cfg.provisioning_mode == "wheel"

    nodeenv_cfg = RuntimeConfig(provisioning_mode="nodeenv")
    assert nodeenv_cfg.provisioning_mode == "nodeenv"
    assert nodeenv_cfg.detect_nodeenv is True


def test_pyproject_declares_wheel_provisioning_extras() -> None:
    """pyproject.toml declares node, deno, and bun optional dependency extras."""
    pyproject_path = Path(__file__).resolve().parents[4] / "pyproject.toml"
    content = pyproject_path.read_text(encoding="utf-8")
    assert 'node = ["nodejs-wheel>=22.0.0"]' in content
    assert 'deno = ["deno>=2.0.0"]' in content
    assert 'bun = ["bun-wheel>=1.2.0"]' in content


def test_executor_provisioning_mode_controls_binary_discovery(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """provisioning_mode selects between virtual-environment-only, PATH-only, and layered discovery."""
    venv_bin = tmp_path / "venv" / "bin"
    venv_bin.mkdir(parents=True)
    fake_python = venv_bin / "python3"
    fake_python.write_text("", encoding="utf-8")
    venv_bun = venv_bin / "bun"
    venv_bun.write_text("#!/bin/sh\n", encoding="utf-8")
    venv_bun.chmod(0o755)
    monkeypatch.setattr(sys, "executable", str(fake_python))
    monkeypatch.setattr("litestar_vite.executor.shutil.which", lambda name: f"/usr/local/bin/{name}")

    assert BunExecutor(provisioning_mode="auto")._resolve_executable() == str(venv_bun)
    assert BunExecutor(provisioning_mode="wheel")._resolve_executable() == str(venv_bun)
    assert BunExecutor(provisioning_mode="system")._resolve_executable() == "/usr/local/bin/bun"

    with pytest.raises(ViteExecutableNotFoundError):
        NodeExecutor(provisioning_mode="wheel")._resolve_executable()
    assert NodeExecutor(provisioning_mode="auto")._resolve_executable() == "/usr/local/bin/npm"

    config = ViteConfig(
        paths=PathConfig(root=tmp_path), runtime=RuntimeConfig(executor="bun", provisioning_mode="system")
    )
    assert config.executor.provisioning_mode == "system"


def test_ssr_command_honors_provisioning_mode(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """ssr_command resolves the runtime binary with the same provisioning_mode policy as _resolve_executable."""
    venv_bin = tmp_path / "venv" / "bin"
    venv_bin.mkdir(parents=True)
    fake_python = venv_bin / "python3"
    fake_python.write_text("", encoding="utf-8")
    venv_node = venv_bin / "node"
    venv_node.write_text("#!/bin/sh\n", encoding="utf-8")
    venv_node.chmod(0o755)
    monkeypatch.setattr(sys, "executable", str(fake_python))
    entry = tmp_path / "ssr.js"

    assert NodeExecutor(provisioning_mode="auto").ssr_command(entry) == [str(venv_node), str(entry)]
    assert NodeExecutor(provisioning_mode="wheel").ssr_command(entry) == [str(venv_node), str(entry)]
    assert NodeExecutor(provisioning_mode="system").ssr_command(entry) == ["node", str(entry)]

    assert BunExecutor(provisioning_mode="auto").ssr_command(entry) == ["bun", "run", str(entry)]
    assert BunExecutor(provisioning_mode="system").ssr_command(entry) == ["bun", "run", str(entry)]
    with pytest.raises(ViteExecutableNotFoundError):
        BunExecutor(provisioning_mode="wheel").ssr_command(entry)
    assert DenoExecutor(executable_path=tmp_path / "deno", provisioning_mode="wheel").ssr_command(entry)[0] == str(
        tmp_path / "deno"
    )
