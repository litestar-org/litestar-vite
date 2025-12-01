"""JavaScript runtime executors for Vite commands.

This module provides executor classes for different JavaScript runtimes
(Node.js/npm, Bun, Deno, Yarn, pnpm) to run Vite commands.
"""

import os
import platform
import shutil
import subprocess
import sys
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, ClassVar

from litestar.cli._utils import console

from litestar_vite.exceptions import ViteExecutableNotFoundError, ViteExecutionError

# Windows-only constant for creating new process groups
_CREATE_NEW_PROCESS_GROUP: int = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)


class JSExecutor(ABC):
    """Abstract base class for Javascript executors."""

    bin_name: ClassVar[str]

    def __init__(self, executable_path: "Path | str | None" = None) -> None:
        self.executable_path = executable_path

    @abstractmethod
    def install(self, cwd: Path) -> None:
        """Install dependencies."""

    @abstractmethod
    def run(self, args: list[str], cwd: Path) -> "subprocess.Popen[Any]":
        """Run a command."""

    @abstractmethod
    def execute(self, args: list[str], cwd: Path) -> None:
        """Execute a command and wait for it to finish."""

    def _resolve_executable(self) -> str:
        if self.executable_path:
            return str(self.executable_path)
        path = shutil.which(self.bin_name)
        if path is None:
            raise ViteExecutableNotFoundError(self.bin_name)
        return path

    @property
    def start_command(self) -> list[str]:
        """Get the default command to start the dev server (e.g., npm run start)."""
        return [self.bin_name, "run", "start"]

    @property
    def build_command(self) -> list[str]:
        """Get the default command to build for production (e.g., npm run build)."""
        return [self.bin_name, "run", "build"]


class CommandExecutor(JSExecutor):
    """Generic command executor."""

    def install(self, cwd: Path) -> None:
        executable = self._resolve_executable()
        command = ["install"] if Path("install").name == Path(executable).name else [executable, "install"]
        process = subprocess.run(
            command,
            cwd=cwd,
            shell=platform.system() == "Windows",
            check=False,
        )
        if process.returncode != 0:
            raise ViteExecutionError(command, process.returncode, "package install failed")

    def run(self, args: list[str], cwd: Path) -> "subprocess.Popen[Any]":
        executable = self._resolve_executable()
        # Avoid double-prefixing the executable when callers pass it explicitly
        command = args if args and Path(args[0]).name == Path(executable).name else [executable, *args]
        # Use start_new_session=True on Unix to create a new process group.
        # This ensures all child processes (node, astro, nuxt, vite, etc.) can be
        # terminated together using os.killpg() on the process group.
        # On Windows, use CREATE_NEW_PROCESS_GROUP flag.
        kwargs: dict[str, Any] = {
            "cwd": cwd,
            "stdout": None,  # inherit for live output
            "stderr": None,
        }
        if platform.system() == "Windows":
            kwargs["shell"] = True
            kwargs["creationflags"] = _CREATE_NEW_PROCESS_GROUP
        else:
            kwargs["shell"] = False
            kwargs["start_new_session"] = True
        return subprocess.Popen(command, **kwargs)

    def execute(self, args: list[str], cwd: Path) -> None:
        executable = self._resolve_executable()
        command = args if args and Path(args[0]).name == Path(executable).name else [executable, *args]
        process = subprocess.run(
            command,
            cwd=cwd,
            shell=platform.system() == "Windows",
            check=False,
            stdout=None,  # inherit for live output
            stderr=subprocess.PIPE,
        )
        if process.returncode != 0:
            stderr = process.stderr.decode() if process.stderr else ""
            raise ViteExecutionError(command, process.returncode, stderr)


class NodeExecutor(CommandExecutor):
    """Node.js executor."""

    bin_name = "npm"


class BunExecutor(CommandExecutor):
    """Bun executor."""

    bin_name = "bun"


class DenoExecutor(CommandExecutor):
    """Deno executor."""

    bin_name = "deno"

    def install(self, cwd: Path) -> None:
        # Deno doesn't strictly have an "install" command for deps in the same way,
        # but it caches them. Often 'deno cache' or just running the task is enough.
        # For compatibility, we might not do anything, or run 'deno install' if using local deps.
        # Deno 1.45+ supports 'deno install' for caching.
        pass


class YarnExecutor(CommandExecutor):
    """Yarn executor."""

    bin_name = "yarn"


class PnpmExecutor(CommandExecutor):
    """PNPM executor."""

    bin_name = "pnpm"


class NodeenvExecutor(JSExecutor):
    """Nodeenv executor.

    This executor detects and uses nodeenv in a Python virtual environment.
    It installs nodeenv if not present and uses the npm from within the virtualenv.
    """

    bin_name = "nodeenv"

    def __init__(self, config: Any = None) -> None:
        """Initialize NodeenvExecutor.

        Args:
            config: Optional ViteConfig for detecting nodeenv. Can be the new
                    ViteConfig or legacy config. Only used to check detect_nodeenv.
        """
        super().__init__(None)
        self.config = config
        # Extract detect_nodeenv flag - works with both old and new config (opt-in default)
        self._detect_nodeenv = getattr(config, "detect_nodeenv", False) if config else False

    def _get_nodeenv_command(self) -> str:
        """Get the nodeenv command."""
        if Path(Path(sys.executable) / "nodeenv").exists():
            return str(Path(Path(sys.executable) / "nodeenv"))
        return "nodeenv"

    def install_nodeenv(self, cwd: Path) -> None:
        """Install nodeenv."""
        from importlib.util import find_spec

        if find_spec("nodeenv") is None:
            console.print("[yellow]Nodeenv not found. Skipping installation.[/]")
            return

        install_dir = os.environ.get("VIRTUAL_ENV", sys.prefix)
        console.rule("[yellow]Starting Nodeenv installation process[/]", align="left")

        command = [self._get_nodeenv_command(), install_dir, "--force", "--quiet"]
        subprocess.run(command, cwd=cwd, check=False)

    def install(self, cwd: Path) -> None:
        if self._detect_nodeenv:
            self.install_nodeenv(cwd)

        # After nodeenv install, we use the npm in the virtualenv
        # This logic mirrors the existing logic where it just runs the install command
        # But we need to make sure we use the *correct* npm
        # The current logic in cli.py just runs `config.install_command` which defaults to `npm install`
        # Assuming `npm` is now in the path because nodeenv was installed into VIRTUAL_ENV

        # For robustness, we should try to find npm in the VIRTUAL_ENV/bin or Scripts

        npm_path = self._find_npm_in_venv()
        command = [npm_path, "install"]
        subprocess.run(command, cwd=cwd, check=True)

    def run(self, args: list[str], cwd: Path) -> "subprocess.Popen[Any]":
        npm_path = self._find_npm_in_venv()
        command = [npm_path, *args]
        # Use start_new_session=True on Unix to create a new process group.
        # This ensures all child processes (node, astro, nuxt, vite, etc.) can be
        # terminated together using os.killpg() on the process group.
        kwargs: dict[str, Any] = {
            "cwd": cwd,
            "stdout": None,
            "stderr": None,
        }
        if platform.system() == "Windows":
            kwargs["shell"] = True
            kwargs["creationflags"] = _CREATE_NEW_PROCESS_GROUP
        else:
            kwargs["shell"] = False
            kwargs["start_new_session"] = True
        return subprocess.Popen(command, **kwargs)

    def execute(self, args: list[str], cwd: Path) -> None:
        npm_path = self._find_npm_in_venv()
        command = [npm_path, *args]
        process = subprocess.run(
            command,
            cwd=cwd,
            shell=platform.system() == "Windows",
            check=False,
            capture_output=True,
        )
        if process.returncode != 0:
            raise ViteExecutionError(command, process.returncode, process.stderr.decode())

    def _find_npm_in_venv(self) -> str:
        venv_path = os.environ.get("VIRTUAL_ENV", sys.prefix)
        bin_dir = "Scripts" if platform.system() == "Windows" else "bin"
        npm_path = Path(venv_path) / bin_dir / "npm"
        if platform.system() == "Windows":
            npm_path = npm_path.with_suffix(".cmd")

        if npm_path.exists():
            return str(npm_path)
        return "npm"  # Fallback to system npm

    @property
    def start_command(self) -> list[str]:
        """Get the default command to start the dev server using nodeenv npm."""
        return [self._find_npm_in_venv(), "run", "start"]

    @property
    def build_command(self) -> list[str]:
        """Get the default command to build for production using nodeenv npm."""
        return [self._find_npm_in_venv(), "run", "build"]
