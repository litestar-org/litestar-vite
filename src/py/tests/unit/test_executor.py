from __future__ import annotations

from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from litestar_vite.config import RuntimeConfig, ViteConfig
from litestar_vite.exceptions import ViteExecutableNotFoundError, ViteExecutionError
from litestar_vite.executor import (
    BunExecutor,
    DenoExecutor,
    NodeenvExecutor,
    NodeExecutor,
)


class TestExecutors:
    @patch("shutil.which")
    def test_resolve_executable_found(self, mock_which: Mock) -> None:
        mock_which.return_value = "/usr/bin/npm"
        executor = NodeExecutor()
        assert executor._resolve_executable() == "/usr/bin/npm"

    @patch("shutil.which")
    def test_resolve_executable_not_found(self, mock_which: Mock) -> None:
        mock_which.return_value = None
        executor = NodeExecutor()
        with pytest.raises(ViteExecutableNotFoundError):
            executor._resolve_executable()

    def test_resolve_executable_custom_path(self) -> None:
        executor = NodeExecutor(executable_path="/custom/npm")
        assert executor._resolve_executable() == "/custom/npm"

    @patch("subprocess.Popen")
    @patch("shutil.which")
    def test_run_command(self, mock_which: Mock, mock_popen: Mock) -> None:
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
    def test_execute_command_success(self, mock_which: Mock, mock_run: Mock) -> None:
        mock_which.return_value = "/usr/bin/npm"
        mock_run.return_value = Mock(returncode=0)
        executor = NodeExecutor()

        executor.execute(["install"], Path("/tmp"))

        mock_run.assert_called_once()

    @patch("subprocess.run")
    @patch("shutil.which")
    def test_execute_command_failure(self, mock_which: Mock, mock_run: Mock) -> None:
        mock_which.return_value = "/usr/bin/npm"
        mock_run.return_value = Mock(returncode=1, stderr=b"error")
        executor = NodeExecutor()

        with pytest.raises(ViteExecutionError):
            executor.execute(["install"], Path("/tmp"))

    @patch("subprocess.run")
    @patch("shutil.which")
    def test_install_command(self, mock_which: Mock, mock_run: Mock) -> None:
        mock_which.return_value = "/usr/bin/npm"
        mock_run.return_value = Mock(returncode=0)
        executor = NodeExecutor()

        executor.install(Path("/tmp"))

        mock_run.assert_called_once()
        args, _ = mock_run.call_args
        assert args[0] == ["/usr/bin/npm", "install"]

    @patch("subprocess.run")
    @patch("shutil.which")
    def test_bun_executor(self, mock_which: Mock, mock_run: Mock) -> None:
        mock_which.return_value = "/usr/bin/bun"
        mock_run.return_value = Mock(returncode=0)
        executor = BunExecutor()

        executor.install(Path("/tmp"))

        mock_run.assert_called_once()
        args, _ = mock_run.call_args
        assert args[0] == ["/usr/bin/bun", "install"]

    def test_deno_executor_install_no_op(self) -> None:
        executor = DenoExecutor()
        # Should not raise error
        executor.install(Path("/tmp"))


class TestNodeenvExecutor:
    @patch("litestar_vite.executor.NodeenvExecutor._find_npm_in_venv")
    @patch("subprocess.run")
    def test_install_without_nodeenv_detection(self, mock_run: Mock, mock_find: Mock) -> None:
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
    def test_install_with_nodeenv_detection(
        self, mock_find_spec: Mock, mock_run: Mock, mock_find_npm: Mock, mock_get_cmd: Mock
    ) -> None:
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
    def test_run(self, mock_popen: Mock, mock_find: Mock) -> None:
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
    def test_execute_success(self, mock_run: Mock, mock_find: Mock) -> None:
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
    def test_execute_failure(self, mock_run: Mock, mock_find: Mock) -> None:
        config = ViteConfig()
        executor = NodeenvExecutor(config)
        mock_find.return_value = "/venv/bin/npm"
        mock_run.return_value = Mock(returncode=1, stderr=b"error")

        with pytest.raises(ViteExecutionError):
            executor.execute(["build"], Path("/tmp"))
