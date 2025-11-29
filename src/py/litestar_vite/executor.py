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


class JSExecutor(ABC):
    """Abstract base class for Javascript executors."""

    bin_name: ClassVar[str]

    def __init__(self, executable_path: "Path | str | None" = None) -> None:
        self.executable_path = executable_path

    @abstractmethod
    def install(self, cwd: Path) -> None:
        """Install dependencies."""

    @abstractmethod
    def run(self, args: list[str], cwd: Path) -> subprocess.Popen[bytes]:
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


class CommandExecutor(JSExecutor):
    """Generic command executor."""

    def install(self, cwd: Path) -> None:
        self.execute(["install"], cwd)

    def run(self, args: list[str], cwd: Path) -> subprocess.Popen[bytes]:
        executable = self._resolve_executable()
        # Avoid double-prefixing the executable when callers pass it explicitly
        command = args if args and Path(args[0]).name == Path(executable).name else [executable, *args]
        return subprocess.Popen(
            command,
            cwd=cwd,
            shell=platform.system() == "Windows",
            # Inherit stdio so long-running dev servers don't block on full pipes and
            # so users can see Vite output in real time.
            stdout=None,
            stderr=None,
        )

    def execute(self, args: list[str], cwd: Path) -> None:
        executable = self._resolve_executable()
        command = args if args and Path(args[0]).name == Path(executable).name else [executable, *args]
        process = subprocess.run(
            command,
            cwd=cwd,
            shell=platform.system() == "Windows",
            check=False,
            capture_output=True,
        )
        if process.returncode != 0:
            raise ViteExecutionError(command, process.returncode, process.stderr.decode())


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

    def run(self, args: list[str], cwd: Path) -> subprocess.Popen[bytes]:
        npm_path = self._find_npm_in_venv()
        command = [npm_path, *args]
        return subprocess.Popen(
            command,
            cwd=cwd,
            shell=platform.system() == "Windows",
            stdout=None,
            stderr=None,
        )

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
