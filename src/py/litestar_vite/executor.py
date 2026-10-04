"""JavaScript runtime executors for Vite commands.

This module provides executor classes for different JavaScript runtimes
(Node.js/npm, Bun, Deno, Yarn, pnpm) to run Vite commands.
"""

import importlib
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

from litestar_vite.config import InertiaConfig, InertiaSSRConfig, PathConfig, ViteConfig
from litestar_vite.config._paths import resolve_ssr_bundle_path
from litestar_vite.exceptions import ViteExecutableNotFoundError, ViteExecutionError

_DENO_SUBCOMMANDS: frozenset[str] = frozenset({
    "add",
    "bench",
    "cache",
    "check",
    "clean",
    "compile",
    "completions",
    "coverage",
    "doc",
    "eval",
    "fmt",
    "info",
    "init",
    "install",
    "jupyter",
    "lint",
    "outdated",
    "publish",
    "remove",
    "repl",
    "run",
    "serve",
    "task",
    "test",
    "types",
    "uninstall",
    "upgrade",
    "vendor",
})


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
    kwargs: dict[str, Any] = {
        "cwd": cwd,
        "env": {**os.environ, "LITESTAR_VITE_MANAGED": "1"},
        "stdin": subprocess.PIPE,
        "stdout": None,
        "stderr": subprocess.PIPE,
        "shell": False,
    }
    if platform.system() == "Windows":
        kwargs["creationflags"] = _create_new_process_group
    else:
        kwargs["start_new_session"] = True
    return kwargs


def _normalize_command(resolved_executable: str, args: list[str], *, binary_name: str) -> list[str]:
    """Normalize command args to the resolved executable without duplicating argv[0].

    If the incoming command already names the binary via bare name, full path, or a platform-specific variant
    (for example ``npm`` vs ``npm.CMD``), rewrite the first token to the resolved executable path and keep the
    remaining args. Otherwise prepend the resolved executable.
    """
    if not args:
        return [resolved_executable]

    first = Path(args[0])
    resolved = Path(resolved_executable)
    match_names = {resolved.name, resolved.stem, binary_name}

    if first == resolved or first.name in match_names or first.stem in match_names:
        return [resolved_executable, *args[1:]]

    return [resolved_executable, *args]


def _resolve_venv_executable(bin_name: str) -> "str | None":
    """Locate an executable inside the current Python virtual environment or wheel package.

    Checks ``Path(sys.executable).parent`` first (supporting ``nodejs-wheel``, ``bun-wheel``,
    ``deno``, and PyApp distributions), and falls back to ``deno.find_deno_bin()`` when
    ``bin_name == "deno"`` and the ``deno`` Python package is installed.

    Args:
        bin_name: Bare binary name (e.g., ``"npm"``, ``"node"``, ``"bun"``, ``"deno"``).

    Returns:
        Absolute path string to the executable if found in the virtualenv/wheel, otherwise ``None``.
    """
    venv_bin_dir = Path(sys.executable).parent
    is_windows = platform.system() == "Windows"
    suffixes = (".exe", ".cmd", ".bat", "") if is_windows else ("",)
    for suffix in suffixes:
        candidate = venv_bin_dir / f"{bin_name}{suffix}"
        if candidate.is_file() and (is_windows or os.access(candidate, os.X_OK)):
            return str(candidate)

    if bin_name == "deno" and find_spec("deno") is not None:
        try:
            deno_mod = importlib.import_module("deno")
            find_deno_bin = getattr(deno_mod, "find_deno_bin", None)
            if callable(find_deno_bin):
                deno_bin = str(find_deno_bin())
                if Path(deno_bin).is_file():
                    return deno_bin
        except (ImportError, OSError, TypeError, ValueError, AttributeError):
            return None

    return None


class JSExecutor(ABC):
    """Abstract base class for Javascript executors.

    The default ``silent_flag`` matches npm-style CLIs (``--silent``). Executors that do not support a silent flag
    (e.g., Deno) override it with an empty string.
    """

    bin_name: ClassVar[str]
    silent_flag: ClassVar[str] = "--silent"
    __slots__ = ("_resolved_executable", "executable_path", "silent")

    def __init__(self, executable_path: "Path | str | None" = None, *, silent: bool = False) -> None:
        self.executable_path = executable_path
        self.silent = silent
        self._resolved_executable: "str | None" = None

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

    @staticmethod
    def _which(bin_name: str) -> "str | None":
        """Locate an executable in the active virtualenv/wheel or system PATH.

        Args:
            bin_name: Bare binary name to resolve.

        Returns:
            Resolved executable path string if found, otherwise ``None``.
        """
        venv_path = _resolve_venv_executable(bin_name)
        if venv_path is not None:
            return venv_path
        return shutil.which(bin_name)

    @classmethod
    def which(cls, bin_name: str) -> "str | None":
        """Public helper to locate an executable in the active virtualenv/wheel or system PATH.

        Args:
            bin_name: Bare binary name to resolve.

        Returns:
            Resolved executable path string if found, otherwise ``None``.
        """
        return cls._which(bin_name)

    def _resolve_executable(self) -> str:
        """Return the executable path or raise if not found.

        Checks explicit ``executable_path`` first, then the active Python virtual
        environment / PEP 425 wheel binary directory (``Path(sys.executable).parent``
        and ``deno.find_deno_bin()``), and finally falls back to ``shutil.which``.

        Returns:
            Path to the resolved executable.

        Raises:
            ViteExecutableNotFoundError: If the binary cannot be located.
        """
        if self._resolved_executable is not None:
            return self._resolved_executable
        if self.executable_path:
            self._resolved_executable = str(self.executable_path)
            return self._resolved_executable
        path = self._which(self.bin_name)
        if path is None:
            raise ViteExecutableNotFoundError(self.bin_name)
        self._resolved_executable = path
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

    def ssr_command(self, entry_point: Path) -> list[str]:
        """Return the command list to run a production SSR bundle.

        Args:
            entry_point: Path to the built SSR bundle file.

        Returns:
            Command list suitable for ``StdioIPCTransport``.
        """
        node_bin = _resolve_venv_executable("node") or "node"
        return [node_bin, str(entry_point)]


class CommandExecutor(JSExecutor):
    """Generic command executor."""

    __slots__ = ()
    update_command: ClassVar[str] = "update"
    update_latest_flag: ClassVar[str] = "--latest"

    def install(self, cwd: Path) -> None:
        executable = self._resolve_executable()
        command = [executable, "install"]
        process = subprocess.run(command, cwd=cwd, shell=False, check=False)
        if process.returncode != 0:
            raise ViteExecutionError(command, process.returncode, "package install failed")

    def update(self, cwd: Path, *, latest: bool = False) -> None:
        executable = self._resolve_executable()
        command = [executable, self.update_command]
        if latest and self.update_latest_flag:
            command.append(self.update_latest_flag)
        process = subprocess.run(command, cwd=cwd, shell=False, check=False)
        if process.returncode != 0:
            raise ViteExecutionError(command, process.returncode, "package update failed")

    def run(self, args: list[str], cwd: Path) -> "subprocess.Popen[Any]":
        executable = self._resolve_executable()
        args = self._apply_silent_flag(args)
        command = _normalize_command(executable, args, binary_name=self.bin_name)
        return subprocess.Popen(command, **_popen_server_kwargs(cwd))

    def execute(self, args: list[str], cwd: Path) -> None:
        executable = self._resolve_executable()
        args = self._apply_silent_flag(args)
        command = _normalize_command(executable, args, binary_name=self.bin_name)
        process = subprocess.run(
            command, cwd=cwd, shell=False, check=False, stdin=subprocess.PIPE, stdout=None, stderr=subprocess.PIPE
        )
        if process.returncode != 0:
            stderr = process.stderr.decode() if process.stderr else ""
            raise ViteExecutionError(command, process.returncode, stderr)


class NodeExecutor(CommandExecutor):
    """Node.js executor."""

    __slots__ = ()
    bin_name = "npm"
    update_latest_flag: ClassVar[str] = "--save"


class BunExecutor(CommandExecutor):
    """Bun executor."""

    __slots__ = ()
    bin_name = "bun"

    def ssr_command(self, entry_point: Path) -> list[str]:
        """Return the Bun command list to run a production SSR bundle."""
        executable = (
            str(self.executable_path)
            if self.executable_path
            else (_resolve_venv_executable(self.bin_name) or self.bin_name)
        )
        return [executable, "run", str(entry_point)]


class DenoExecutor(CommandExecutor):
    """Deno executor."""

    __slots__ = ()
    bin_name = "deno"
    silent_flag: ClassVar[str] = ""
    update_latest_flag: ClassVar[str] = "--latest"

    @property
    def start_command(self) -> list[str]:
        """Get the default command to start the dev server using Deno tasks.

        Returns:
            The argv list used to start the dev server.
        """
        return [self.bin_name, "task", "start"]

    @property
    def build_command(self) -> list[str]:
        """Get the default command to build for production using Deno tasks.

        Returns:
            The argv list used to build production assets.
        """
        return [self.bin_name, "task", "build"]

    def ssr_command(self, entry_point: Path) -> list[str]:
        """Return the Deno command list to run a production SSR bundle."""
        executable = (
            str(self.executable_path)
            if self.executable_path
            else (_resolve_venv_executable(self.bin_name) or self.bin_name)
        )
        return [executable, "run", "--allow-read", "--allow-env", str(entry_point)]

    def update(self, cwd: Path, *, latest: bool = False) -> None:
        """Update dependencies via ``deno outdated --update [--latest]``."""
        executable = self._resolve_executable()
        command = [executable, "outdated", "--update"]
        if latest and self.update_latest_flag:
            command.append(self.update_latest_flag)
        process = subprocess.run(command, cwd=cwd, shell=False, check=False)
        if process.returncode != 0:
            raise ViteExecutionError(command, process.returncode, "package update failed")

    def execute(self, args: list[str], cwd: Path) -> None:
        """Execute a Deno command or script and wait for completion.

        When ``args`` does not begin with a native Deno subcommand (such as
        ``task`` or ``run``), ``["run", "-A"]`` is prepended before the script
        or module arguments.
        """
        executable = self._resolve_executable()
        normalized = _normalize_command(executable, args, binary_name=self.bin_name)
        rest = normalized[1:]
        command = [executable, "run", "-A", *rest] if rest and rest[0] not in _DENO_SUBCOMMANDS else normalized
        process = subprocess.run(
            command, cwd=cwd, shell=False, check=False, stdin=subprocess.PIPE, stdout=None, stderr=subprocess.PIPE
        )
        if process.returncode != 0:
            stderr = process.stderr.decode() if process.stderr else ""
            raise ViteExecutionError(command, process.returncode, stderr)


class YarnExecutor(CommandExecutor):
    """Yarn executor."""

    __slots__ = ()
    bin_name = "yarn"
    update_command: ClassVar[str] = "upgrade"


class PnpmExecutor(CommandExecutor):
    """PNPM executor."""

    __slots__ = ()
    bin_name = "pnpm"


class NodeenvExecutor(JSExecutor):
    """Nodeenv executor.

    This executor detects and uses nodeenv in a Python virtual environment.
    It installs nodeenv if not present and uses the npm from within the virtualenv.
    """

    bin_name = "nodeenv"
    __slots__ = ("_detect_nodeenv", "config")

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
        """Run npm install within the nodeenv environment.

        Args:
            cwd: The working directory for the installation.

        Raises:
            ViteExecutionError: If package installation exits with a non-zero status.
        """
        if self._detect_nodeenv:
            self.install_nodeenv(cwd)

        npm_path = self._find_npm_in_venv()
        command = [npm_path, "install"]
        process = subprocess.run(command, cwd=cwd, shell=False, check=False)
        if process.returncode != 0:
            raise ViteExecutionError(command, process.returncode, "package install failed")

    def update(self, cwd: Path, *, latest: bool = False) -> None:
        npm_path = self._find_npm_in_venv()
        command = [npm_path, "update"]
        if latest:
            command.append("--save")
        process = subprocess.run(command, cwd=cwd, shell=False, check=False)
        if process.returncode != 0:
            raise ViteExecutionError(command, process.returncode, "package update failed")

    def run(self, args: list[str], cwd: Path) -> "subprocess.Popen[Any]":
        npm_path = self._find_npm_in_venv()
        args = self._apply_silent_flag(args)
        command = _normalize_command(npm_path, args, binary_name="npm")
        return subprocess.Popen(command, **_popen_server_kwargs(cwd))

    def execute(self, args: list[str], cwd: Path) -> None:
        npm_path = self._find_npm_in_venv()
        args = self._apply_silent_flag(args)
        command = _normalize_command(npm_path, args, binary_name="npm")
        process = subprocess.run(command, cwd=cwd, shell=False, check=False, capture_output=True)
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


def find_bundled_ssr_worker() -> Path | None:
    """Detect a compiled standalone SSR worker binary co-located with the Python executable.

    When packaged with PyApp (``PYAPP_FULL_ISOLATION=1``) or staged into a virtual
    environment, ``litestar-ssr-worker`` (or ``litestar-ssr-worker.exe`` on Windows)
    resides in ``Path(sys.executable).parent``.

    Returns:
        Resolved path to the compiled SSR worker binary if present and executable,
        otherwise ``None``.
    """
    bin_dir = Path(sys.executable).parent
    candidates = (
        [bin_dir / "litestar-ssr-worker.exe", bin_dir / "litestar-ssr-worker"]
        if platform.system() == "Windows"
        else [bin_dir / "litestar-ssr-worker", bin_dir / "litestar-ssr-worker.exe"]
    )
    for candidate in candidates:
        if candidate.is_file() and os.access(candidate, os.X_OK):
            return candidate
    return None


def resolve_ssr_command(config: "ViteConfig | None" = None, ssr_config: "InertiaSSRConfig | None" = None) -> list[str]:
    """Resolve the production SSR worker command for the active JS runtime.

    Honors an explicit ``ssr_config.command`` override first, then checks for a
    compiled ``litestar-ssr-worker`` binary co-located with ``sys.executable``.
    Otherwise resolves the built SSR bundle path and returns the runtime-appropriate
    invocation via the configured executor (``bun run <path>``,
    ``deno run --allow-read --allow-env <path>``, or ``node <path>``).

    Args:
        config: Optional active ``ViteConfig`` instance.
        ssr_config: Optional resolved ``InertiaSSRConfig`` instance.

    Returns:
        Command list suitable for ``StdioIPCTransport``.
    """
    if ssr_config is None and config is not None and isinstance(config.inertia, InertiaConfig):
        ssr_config = config.inertia.ssr_config
    if ssr_config is not None and ssr_config.command:
        return list(ssr_config.command)
    bundled_worker = find_bundled_ssr_worker()
    if bundled_worker is not None:
        return [str(bundled_worker)]
    if config is not None:
        bundle_path = resolve_ssr_bundle_path(config.paths)
        return config.executor.ssr_command(bundle_path)
    cwd = (ssr_config.cwd if ssr_config is not None else None) or Path.cwd()
    fallback_config = ViteConfig(paths=PathConfig(root=cwd))
    bundle_path = resolve_ssr_bundle_path(fallback_config.paths)
    return fallback_config.executor.ssr_command(bundle_path)
