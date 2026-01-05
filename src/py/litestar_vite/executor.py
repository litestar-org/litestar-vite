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
from importlib.util import find_spec
from pathlib import Path
from typing import Any, ClassVar, Protocol, runtime_checkable

from litestar.cli._utils import console

from litestar_vite.exceptions import ViteExecutableNotFoundError, ViteExecutionError


def _windows_create_new_process_group_flag() -> int:
    """Return the Windows-only process creation flag for new process groups.

    When available, ``subprocess.CREATE_NEW_PROCESS_GROUP`` is used as ``creationflags`` for long-lived dev servers.
    This improves process lifecycle management on Windows (notably console signal / Ctrl+C behavior). On non-Windows
    platforms the constant is not defined, so this returns ``0``.

    Returns:
        The ``creationflags`` value to start a new process group on Windows, otherwise ``0``.
    """
    try:
        return subprocess.CREATE_NEW_PROCESS_GROUP  # type: ignore[attr-defined]
    except AttributeError:
        return 0


_create_new_process_group = _windows_create_new_process_group_flag()


def _popen_server_kwargs(cwd: Path) -> dict[str, Any]:
    """Return Popen kwargs that keep server processes alive and grouped.

    Returns:
        Keyword arguments for ``subprocess.Popen`` suitable for long-lived dev servers.
    """
    kwargs: dict[str, Any] = {"cwd": cwd, "stdin": subprocess.PIPE, "stdout": None, "stderr": None}
    if platform.system() == "Windows":
        kwargs["shell"] = True
        kwargs["creationflags"] = _create_new_process_group
    else:
        kwargs["shell"] = False
        kwargs["start_new_session"] = True
    return kwargs


class JSExecutor(ABC):
    """Abstract base class for Javascript executors.

    The default ``silent_flag`` matches npm-style CLIs (``--silent``). Executors that do not support a silent flag
    (e.g., Deno) override it with an empty string.
    """

    bin_name: ClassVar[str]
    silent_flag: ClassVar[str] = "--silent"

    def __init__(self, executable_path: "Path | str | None" = None, *, silent: bool = False) -> None:
        self.executable_path = executable_path
        self.silent = silent

    @abstractmethod
    def install(self, cwd: Path) -> None:
        """Install dependencies."""

    @abstractmethod
    def update(self, cwd: Path, *, latest: bool = False) -> None:
        """Update dependencies.

        Args:
            cwd: The working directory.
            latest: If True, update to latest versions (ignoring semver constraints where supported).
        """

    @abstractmethod
    def run(self, args: list[str], cwd: Path) -> "subprocess.Popen[Any]":
        """Run a command.

        Returns:
            The result.
        """

    @abstractmethod
    def execute(self, args: list[str], cwd: Path) -> None:
        """Execute a command and wait for it to finish."""

    def _resolve_executable(self) -> str:
        """Return the executable path or raise if not found.

        Returns:
            Path to the resolved executable.

        Raises:
            ViteExecutableNotFoundError: If the binary cannot be located.
        """
        if self.executable_path:
            return str(self.executable_path)
        path = shutil.which(self.bin_name)
        if path is None:
            raise ViteExecutableNotFoundError(self.bin_name)
        return path

    def _apply_silent_flag(self, args: list[str]) -> list[str]:
        """Apply silent flag to command args if silent mode is enabled.

        The silent flag is inserted after 'run' in npm-style commands
        (e.g., ['npm', 'run', 'dev'] -> ['npm', 'run', '--silent', 'dev']).

        Args:
            args: The command arguments.

        Returns:
            Modified args with silent flag inserted if applicable.
        """
        if not self.silent or not self.silent_flag:
            return args

        if args and args[0] == "run" and len(args) >= 2:
            return [args[0], self.silent_flag, *args[1:]]

        if "run" in args:
            run_idx = args.index("run")
            return [*args[: run_idx + 1], self.silent_flag, *args[run_idx + 1 :]]

        return [*args, self.silent_flag]

    @property
    def start_command(self) -> list[str]:
        """Get the default command to start the dev server (e.g., npm run start).

        Returns:
            The argv list used to start the dev server.
        """
        return [self.bin_name, "run", "start"]

    @property
    def build_command(self) -> list[str]:
        """Get the default command to build for production (e.g., npm run build).

        Returns:
            The argv list used to build production assets.
        """
        return [self.bin_name, "run", "build"]


class CommandExecutor(JSExecutor):
    """Generic command executor."""

    # Subclasses override to customize update behavior
    update_command: ClassVar[str] = "update"
    update_latest_flag: ClassVar[str] = "--latest"

    def install(self, cwd: Path) -> None:
        executable = self._resolve_executable()
        command = [executable, "install"]
        process = subprocess.run(command, cwd=cwd, shell=platform.system() == "Windows", check=False)
        if process.returncode != 0:
            raise ViteExecutionError(command, process.returncode, "package install failed")

    def update(self, cwd: Path, *, latest: bool = False) -> None:
        executable = self._resolve_executable()
        command = [executable, self.update_command]
        if latest and self.update_latest_flag:
            command.append(self.update_latest_flag)
        process = subprocess.run(command, cwd=cwd, shell=platform.system() == "Windows", check=False)
        if process.returncode != 0:
            raise ViteExecutionError(command, process.returncode, "package update failed")

    def run(self, args: list[str], cwd: Path) -> "subprocess.Popen[Any]":
        executable = self._resolve_executable()
        args = self._apply_silent_flag(args)
        command = args if args and Path(args[0]).name == Path(executable).name else [executable, *args]
        return subprocess.Popen(command, **_popen_server_kwargs(cwd))

    def execute(self, args: list[str], cwd: Path) -> None:
        executable = self._resolve_executable()
        args = self._apply_silent_flag(args)
        command = args if args and Path(args[0]).name == Path(executable).name else [executable, *args]
        process = subprocess.run(
            command,
            cwd=cwd,
            shell=platform.system() == "Windows",
            check=False,
            stdin=subprocess.PIPE,
            stdout=None,
            stderr=subprocess.PIPE,
        )
        if process.returncode != 0:
            stderr = process.stderr.decode() if process.stderr else ""
            raise ViteExecutionError(command, process.returncode, stderr)


class NodeExecutor(CommandExecutor):
    """Node.js executor."""

    bin_name = "npm"
    # npm doesn't have --latest; use --save to update package.json
    update_latest_flag: ClassVar[str] = "--save"


class BunExecutor(CommandExecutor):
    """Bun executor."""

    bin_name = "bun"


class DenoExecutor(CommandExecutor):
    """Deno executor."""

    bin_name = "deno"
    silent_flag: ClassVar[str] = ""
    update_latest_flag: ClassVar[str] = ""

    def install(self, cwd: Path) -> None:
        pass

    def update(self, cwd: Path, *, latest: bool = False) -> None:
        """Deno doesn't have traditional package management."""
        del cwd, latest  # unused


class YarnExecutor(CommandExecutor):
    """Yarn executor."""

    bin_name = "yarn"
    # yarn uses "upgrade" command (not "update")
    update_command: ClassVar[str] = "upgrade"


class PnpmExecutor(CommandExecutor):
    """PNPM executor."""

    bin_name = "pnpm"


class NodeenvExecutor(JSExecutor):
    """Nodeenv executor.

    This executor detects and uses nodeenv in a Python virtual environment.
    It installs nodeenv if not present and uses the npm from within the virtualenv.
    """

    bin_name = "nodeenv"

    @runtime_checkable
    class _SupportsDetectNodeenv(Protocol):
        detect_nodeenv: bool

    def __init__(self, config: Any = None, *, silent: bool = False) -> None:
        """Initialize NodeenvExecutor.

        Args:
            config: Optional ViteConfig for detecting nodeenv. Can be the new
                    ViteConfig or legacy config. Only used to check detect_nodeenv.
            silent: Whether to suppress npm output with --silent flag.
        """
        super().__init__(None, silent=silent)
        self.config = config
        self._detect_nodeenv = bool(config.detect_nodeenv) if isinstance(config, self._SupportsDetectNodeenv) else False

    def _get_nodeenv_command(self) -> str:
        """Return the nodeenv executable to run.

        Returns:
            Absolute path to the nodeenv binary if present next to the Python
            interpreter, otherwise the string ``"nodeenv"`` for PATH lookup.
        """
        candidate = Path(sys.executable).with_name("nodeenv")
        if candidate.exists():
            return str(candidate)
        return "nodeenv"

    def install_nodeenv(self, cwd: Path) -> None:
        """Install nodeenv when available in the environment."""
        if find_spec("nodeenv") is None:
            console.print("[yellow]Nodeenv not found. Skipping installation.[/]")
            return

        install_dir = os.environ.get("VIRTUAL_ENV", sys.prefix)
        console.rule("Starting [blue]Nodeenv[/] installation", align="left")

        command = [self._get_nodeenv_command(), install_dir, "--force", "--quiet"]
        subprocess.run(command, cwd=cwd, check=False)

    def install(self, cwd: Path) -> None:
        if self._detect_nodeenv:
            self.install_nodeenv(cwd)

        npm_path = self._find_npm_in_venv()
        command = [npm_path, "install"]
        subprocess.run(command, cwd=cwd, check=True)

    def update(self, cwd: Path, *, latest: bool = False) -> None:
        npm_path = self._find_npm_in_venv()
        command = [npm_path, "update"]
        if latest:
            command.append("--save")
        process = subprocess.run(command, cwd=cwd, shell=platform.system() == "Windows", check=False)
        if process.returncode != 0:
            raise ViteExecutionError(command, process.returncode, "package update failed")

    def run(self, args: list[str], cwd: Path) -> "subprocess.Popen[Any]":
        npm_path = self._find_npm_in_venv()
        args = self._apply_silent_flag(args)
        command = [npm_path, *args]
        return subprocess.Popen(command, **_popen_server_kwargs(cwd))

    def execute(self, args: list[str], cwd: Path) -> None:
        npm_path = self._find_npm_in_venv()
        args = self._apply_silent_flag(args)
        command = [npm_path, *args]
        process = subprocess.run(
            command, cwd=cwd, shell=platform.system() == "Windows", check=False, capture_output=True
        )
        if process.returncode != 0:
            raise ViteExecutionError(command, process.returncode, process.stderr.decode())

    def _find_npm_in_venv(self) -> str:
        """Locate npm within the active virtual environment or fall back to PATH.

        Returns:
            Path to ``npm`` inside the virtual environment when available, or
            ``"npm"`` to defer to PATH resolution.
        """
        venv_path = os.environ.get("VIRTUAL_ENV", sys.prefix)
        bin_dir = "Scripts" if platform.system() == "Windows" else "bin"
        npm_path = Path(venv_path) / bin_dir / "npm"
        if platform.system() == "Windows":
            npm_path = npm_path.with_suffix(".cmd")

        if npm_path.exists():
            return str(npm_path)
        return "npm"

    @property
    def start_command(self) -> list[str]:
        """Get the default command to start the dev server using nodeenv npm.

        Returns:
            The argv list used to start the dev server.
        """
        return [self._find_npm_in_venv(), "run", "start"]

    @property
    def build_command(self) -> list[str]:
        """Get the default command to build for production using nodeenv npm.

        Returns:
            The argv list used to build production assets.
        """
        return [self._find_npm_in_venv(), "run", "build"]
