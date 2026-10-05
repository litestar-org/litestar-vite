"""PyApp single-file executable staging and compilation engine for Litestar-Vite."""

import os
import platform
import re
import shutil
import subprocess
import tarfile
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any

from litestar_vite.config._bundle import DEFAULT_PBS_FULL_VERSIONS, BundleConfig
from litestar_vite.config._paths import resolve_ssr_bundle_path
from litestar_vite.config._vite import ViteConfig
from litestar_vite.exceptions import LitestarViteError, ViteExecutionError

__all__ = (
    "DEFAULT_PLATFORMS",
    "DEFAULT_TARGET_TRIPLES",
    "PBS_URL_TEMPLATE",
    "PYAPP_REPOSITORY_URL",
    "BundleConfigurationError",
    "PyAppBundler",
    "default_pbs_url",
    "detect_host_target_triple",
    "patch_pyapp_install_dir",
    "patch_pyapp_static_bzip2",
)

PYAPP_REPOSITORY_URL = "https://github.com/ofek/pyapp.git"

PBS_URL_TEMPLATE = (
    "https://github.com/astral-sh/python-build-standalone/releases/download/"
    "{release}/cpython-{full_version}%2B{release}-{triple}-install_only_stripped.tar.gz"
)

DEFAULT_TARGET_TRIPLES: tuple[str, ...] = (
    "x86_64-unknown-linux-gnu",
    "aarch64-unknown-linux-gnu",
    "x86_64-apple-darwin",
    "aarch64-apple-darwin",
    "x86_64-pc-windows-msvc",
)


def default_pbs_url(target_triple: str, python_version: str, pbs_release: str) -> str | None:
    """Derive the default ``python-build-standalone`` archive URL for a target.

    Args:
        target_triple: Rust target triple (e.g. ``x86_64-unknown-linux-gnu``).
        python_version: ``major.minor`` CPython version (e.g. ``"3.12"``).
        pbs_release: ``python-build-standalone`` release tag (e.g. ``"20241016"``).

    Returns:
        The archive URL, or ``None`` when the release/version pair is not in
        :data:`~litestar_vite.config._bundle.DEFAULT_PBS_FULL_VERSIONS`.
    """
    full_version = DEFAULT_PBS_FULL_VERSIONS.get(pbs_release, {}).get(python_version)
    if full_version is None:
        return None
    return PBS_URL_TEMPLATE.format(release=pbs_release, full_version=full_version, triple=target_triple)


DEFAULT_PLATFORMS: dict[str, str] = {
    "x86_64-unknown-linux-gnu": "manylinux_2_28_x86_64",
    "aarch64-unknown-linux-gnu": "manylinux_2_28_aarch64",
    "x86_64-apple-darwin": "macosx_11_0_x86_64",
    "aarch64-apple-darwin": "macosx_11_0_arm64",
    "x86_64-pc-windows-msvc": "win_amd64",
}

_INSTALL_DIR_EXPR_RE = re.compile(
    r"platform_dirs\(\)\s*\.data_local_dir\(\)"
    r"(?P<suffix>(?:\s*\.join\(\s*(?:project_name|distribution_id|project_version)\(\)\s*\))+)"
)
_BZIP2_SIMPLE_DEP_RE = re.compile(r'(?m)^bzip2[ \t]*=[ \t]*"([^"]+)"[ \t]*$')
_BZIP2_TABLE_DEP_RE = re.compile(r"(?m)^bzip2[ \t]*=[ \t]*\{([^\n}]+)\}")


class BundleConfigurationError(LitestarViteError):
    """Raised when PyApp bundle configuration or source patching fails validation."""


def detect_host_target_triple() -> str:
    """Detect the Rust target triple corresponding to the current host OS and CPU architecture."""
    sys_name = platform.system().lower()
    machine = platform.machine().lower()
    is_arm = machine in {"aarch64", "arm64"}
    if sys_name == "darwin":
        return "aarch64-apple-darwin" if is_arm else "x86_64-apple-darwin"
    if sys_name == "windows":
        return "x86_64-pc-windows-msvc"
    return "aarch64-unknown-linux-gnu" if is_arm else "x86_64-unknown-linux-gnu"


def _rust_install_root_expr(install_root: str) -> str:
    """Format a Rust ``PathBuf`` expression for ``install_root`` in PyApp's ``src/app.rs``."""
    stripped = install_root.strip()
    if stripped == "~" or stripped.startswith(("~/", "~\\")):
        rel_part = stripped[1:].lstrip("/\\")
        escaped_rel = rel_part.replace("\\", "\\\\").replace('"', '\\"')
        if escaped_rel:
            return (
                'directories::BaseDirs::new().expect("could not find base directories")'
                f'.home_dir().join("{escaped_rel}")'
            )
        return 'directories::BaseDirs::new().expect("could not find base directories").home_dir().to_path_buf()'

    escaped_abs = stripped.replace("\\", "\\\\").replace('"', '\\"')
    return f'std::path::PathBuf::from("{escaped_abs}")'


def patch_pyapp_install_dir(pyapp_dir: Path, install_root: str) -> None:
    """Patch PyApp's ``src/app.rs`` installation directory base to use ``install_root``.

    PyApp (``initialize()`` in ``src/app.rs``) resolves the installation directory as
    ``platform_dirs().data_local_dir().join(project_name()).join(distribution_id()).join(project_version())``
    unless the ``PYAPP_INSTALL_DIR_<PROJECT_NAME>`` environment variable is set at runtime.
    Only the ``platform_dirs().data_local_dir()`` base is replaced; the project, distribution
    and version segments are preserved so upgraded binaries never reuse a stale runtime.
    The runtime environment override continues to take precedence.

    Supports both ``$HOME``-relative paths (e.g. ``~/.my-app/runtime``, expanded at runtime
    via ``directories::BaseDirs``) and literal/absolute paths.

    Args:
        pyapp_dir: Root directory of the PyApp Rust source tree.
        install_root: Base installation directory string.

    Raises:
        BundleConfigurationError: If ``src/app.rs`` is missing or the target expression is not found.
    """
    app_rs_path = pyapp_dir / "src" / "app.rs"
    if not app_rs_path.is_file():
        msg = f"PyApp source file not found at {app_rs_path}"
        raise BundleConfigurationError(msg)

    original = app_rs_path.read_text(encoding="utf-8")
    rust_expr = _rust_install_root_expr(install_root)
    patched, count = _INSTALL_DIR_EXPR_RE.subn(lambda m: f"{rust_expr}{m.group('suffix')}", original)
    if count == 0:
        msg = (
            f"Could not locate PyApp install_dir expression in {app_rs_path} to patch "
            f"install_root={install_root!r}; the pinned pyapp_version may not be supported."
        )
        raise BundleConfigurationError(msg)

    app_rs_path.write_text(patched, encoding="utf-8")


def patch_pyapp_static_bzip2(pyapp_dir: Path) -> dict[str, str]:
    """Patch PyApp's ``Cargo.toml`` to enable static ``bzip2`` linking and return static build env vars.

    Args:
        pyapp_dir: Root directory of the PyApp Rust source tree.

    Returns:
        Environment variable mapping setting ``BZIP2_SYS_STATIC=1`` and ``LZMA_API_STATIC=1``.

    Raises:
        BundleConfigurationError: If ``Cargo.toml`` does not exist in ``pyapp_dir``.
    """
    cargo_toml_path = pyapp_dir / "Cargo.toml"
    if not cargo_toml_path.is_file():
        msg = f"PyApp Cargo.toml not found at {cargo_toml_path}"
        raise BundleConfigurationError(msg)

    content = cargo_toml_path.read_text(encoding="utf-8")
    updated, count = _BZIP2_SIMPLE_DEP_RE.subn(r'bzip2 = { version = "\1", features = ["static"] }', content)
    if count == 0:
        updated = _BZIP2_TABLE_DEP_RE.sub(_inject_static_feature, content)

    cargo_toml_path.write_text(updated, encoding="utf-8")
    return {"BZIP2_SYS_STATIC": "1", "LZMA_API_STATIC": "1"}


def _inject_static_feature(match: re.Match[str]) -> str:
    """Ensure ``features = ["static"]`` is present in a ``Cargo.toml`` inline dependency table."""
    inner = match.group(1)
    if '"static"' in inner or "'static'" in inner:
        return match.group(0)
    if "features" in inner:
        updated_inner = re.sub(r"features\s*=\s*\[", 'features = ["static", ', inner, count=1)
        return f"bzip2 = {{{updated_inner}}}"
    return f'bzip2 = {{{inner.rstrip()}, features = ["static"] }}'


def _validate_tar_member(member: tarfile.TarInfo, dest: Path, resolved_dest: Path) -> None:
    """Reject tar members that could write outside ``dest`` or create special files.

    Raises:
        BundleConfigurationError: If the member path, link target, or type is unsafe.
    """
    member_path = (dest / member.name).resolve()
    if not member_path.is_relative_to(resolved_dest):
        msg = f"Unsafe tar member path detected: {member.name!r}"
        raise BundleConfigurationError(msg)
    if member.issym() or member.islnk():
        link_base = member_path.parent if member.issym() else dest
        link_target = (link_base / member.linkname).resolve()
        if not link_target.is_relative_to(resolved_dest):
            msg = f"Unsafe tar link detected: {member.name!r} -> {member.linkname!r}"
            raise BundleConfigurationError(msg)
        return
    if not (member.isfile() or member.isdir()):
        msg = f"Unsupported tar member type for {member.name!r}"
        raise BundleConfigurationError(msg)


def _safe_extract_tar(tar: tarfile.TarFile, dest: Path) -> None:
    """Safely extract a tar archive into ``dest``.

    Every member is validated against path traversal, escaping symlink and
    hardlink targets, and device/FIFO entries before extraction. When the
    interpreter provides :func:`tarfile.data_filter` (PEP 706) it is applied
    as an additional defense layer.
    """
    resolved_dest = dest.resolve()
    use_data_filter = hasattr(tarfile, "data_filter")
    for member in tar.getmembers():
        _validate_tar_member(member, dest, resolved_dest)
        if use_data_filter:
            tar.extract(member, path=dest, filter="data")
        else:
            tar.extract(member, path=dest)


def _default_subprocess_runner(cmd: list[str], *, cwd: Path | None = None, env: dict[str, str] | None = None) -> None:
    """Execute a subprocess command and raise ``ViteExecutionError`` on non-zero exit."""
    completed = subprocess.run(cmd, cwd=cwd, env=env, shell=False, check=False, capture_output=True, text=True)
    if completed.returncode != 0:
        raise ViteExecutionError(cmd, completed.returncode, completed.stderr or completed.stdout)


class PyAppBundler:
    """Stages ``python-build-standalone`` distributions and compiles single-file PyApp binaries."""

    __slots__ = ("_bundle_config", "_config", "_runner")

    def __init__(
        self, config: ViteConfig, bundle_config: BundleConfig | None = None, *, runner: Callable[..., Any] | None = None
    ) -> None:
        """Initialize the PyApp bundler.

        Args:
            config: Active ``ViteConfig`` instance.
            bundle_config: Optional explicit ``BundleConfig`` override.
            runner: Optional subprocess runner callable for testing.
        """
        self._config = config
        if bundle_config is not None:
            self._bundle_config = bundle_config
        elif isinstance(config.bundle, BundleConfig):
            self._bundle_config = config.bundle
        else:
            self._bundle_config = BundleConfig(enabled=True)
        self._runner = runner or _default_subprocess_runner

    @property
    def config(self) -> ViteConfig:
        """Return the active ``ViteConfig``."""
        return self._config

    @property
    def bundle_config(self) -> BundleConfig:
        """Return the active ``BundleConfig``."""
        return self._bundle_config

    @property
    def target_triple(self) -> str:
        """Return the configured target triple or auto-detect the host target triple."""
        return self._bundle_config.target_arch or detect_host_target_triple()

    def resolve_pbs_url(self, target_triple: str | None = None) -> str:
        """Resolve the ``python-build-standalone`` archive URL for ``target_triple``.

        Explicit ``pbs_urls`` overrides win; otherwise the URL is derived from
        ``python_version`` and ``pbs_release`` via :data:`PBS_URL_TEMPLATE`.

        Raises:
            BundleConfigurationError: If the triple is unsupported or the
                ``python_version``/``pbs_release`` pair has no known full version.
        """
        triple = target_triple or self.target_triple
        if triple in self._bundle_config.pbs_urls:
            return self._bundle_config.pbs_urls[triple]
        if triple not in DEFAULT_TARGET_TRIPLES:
            msg = f"Unsupported target triple {triple!r}. Configure pbs_urls[{triple!r}] in BundleConfig."
            raise BundleConfigurationError(msg)
        url = default_pbs_url(triple, self._bundle_config.python_version, self._bundle_config.pbs_release)
        if url is None:
            msg = (
                f"No known python-build-standalone artifact for Python {self._bundle_config.python_version} "
                f"in release {self._bundle_config.pbs_release!r}. Configure pbs_urls[{triple!r}] in BundleConfig."
            )
            raise BundleConfigurationError(msg)
        return url

    def resolve_pip_platform(self, target_triple: str | None = None) -> str:
        """Resolve the ``uv pip install --python-platform`` tag for ``target_triple``."""
        triple = target_triple or self.target_triple
        if triple in self._bundle_config.platform_map:
            return self._bundle_config.platform_map[triple]
        if triple in DEFAULT_PLATFORMS:
            return DEFAULT_PLATFORMS[triple]
        msg = f"Unsupported target triple {triple!r}. Configure platform_map[{triple!r}] in BundleConfig."
        raise BundleConfigurationError(msg)

    def build_pip_install_command(
        self, site_packages: Path, wheels: Sequence[Path], target_triple: str | None = None
    ) -> list[str]:
        """Build the ``uv pip install --target`` command for staging wheels into ``site_packages``."""
        platform_tag = self.resolve_pip_platform(target_triple)
        return [
            "uv",
            "pip",
            "install",
            "--target",
            str(site_packages),
            "--python-version",
            self._bundle_config.python_version,
            "--python-platform",
            platform_tag,
            *self._bundle_config.extra_pip_args,
            *(str(w) for w in wheels),
            *(str(w) for w in self._bundle_config.extra_wheels),
        ]

    def build_ssr_compile_command(self, ssr_entry: Path, output_binary: Path) -> list[str]:
        """Build the command to compile ``ssr_entry`` into a native ``litestar-ssr-worker`` binary."""
        mode = self._bundle_config.compile_ssr_worker
        if mode == "bun":
            cmd = ["bun", "build", "--compile"]
            if self._bundle_config.ssr_bytecode:
                cmd.append("--bytecode")
            cmd.extend([str(ssr_entry), "--outfile", str(output_binary)])
            return cmd
        if mode == "deno":
            return ["deno", "compile", "--allow-read", "--allow-env", "--output", str(output_binary), str(ssr_entry)]
        msg = f"SSR binary compilation is only supported for 'bun' or 'deno', got {mode!r}."
        raise BundleConfigurationError(msg)

    def strip_staged_distribution(self, python_root: Path) -> None:
        """Remove bytecode caches, stdlib test suites, static libs, and C headers from a staged distribution.

        Only the standard library's own ``test`` and ``idle_test`` packages are
        removed; ``site-packages`` content is left intact apart from
        ``__pycache__`` directories so that installed projects shipping a
        ``tests`` package keep working.
        """
        include_dir = python_root / "include"
        if include_dir.is_dir():
            shutil.rmtree(include_dir)

        for stdlib_dir in self._iter_stdlib_dirs(python_root):
            for name in ("test", "idlelib/idle_test", "lib2to3/tests", "tkinter/test", "unittest/test"):
                candidate = stdlib_dir / name
                if candidate.is_dir():
                    shutil.rmtree(candidate, ignore_errors=True)

        for root_str, dirnames, filenames in os.walk(python_root, topdown=True):
            current_dir = Path(root_str)
            if "__pycache__" in dirnames:
                shutil.rmtree(current_dir / "__pycache__", ignore_errors=True)
                dirnames.remove("__pycache__")
            for fname in filenames:
                if fname.endswith((".pyc", ".pyo")):
                    (current_dir / fname).unlink(missing_ok=True)

        for lib_dir in (python_root / "lib", python_root / "libs"):
            if not lib_dir.is_dir():
                continue
            for archive in lib_dir.rglob("*.a"):
                if "site-packages" not in archive.parts:
                    archive.unlink(missing_ok=True)

    @staticmethod
    def _iter_stdlib_dirs(python_root: Path) -> list[Path]:
        """Return stdlib root directories for POSIX (``lib/pythonX.Y``) and Windows (``Lib``) layouts."""
        candidates: list[Path] = []
        lib_dir = python_root / "lib"
        if lib_dir.is_dir():
            candidates.extend(p for p in lib_dir.glob("python3*") if p.is_dir())
        win_lib = python_root / "Lib"
        if win_lib.is_dir():
            candidates.append(win_lib)
        return candidates

    def _resolve_site_packages_dir(self, python_root: Path, target_triple: str) -> Path:
        """Locate or construct the ``site-packages`` directory inside ``python_root``."""
        if "windows" in target_triple:
            site_pkgs = python_root / "Lib" / "site-packages"
        else:
            site_pkgs = python_root / "lib" / f"python{self._bundle_config.python_version}" / "site-packages"
        site_pkgs.mkdir(parents=True, exist_ok=True)
        return site_pkgs

    def _resolve_ssr_worker_binary_path(self, python_root: Path, target_triple: str) -> Path:
        """Return the destination path for ``litestar-ssr-worker`` inside ``python_root``.

        The worker is placed next to the interpreter so that
        :func:`litestar_vite.executor.find_bundled_ssr_worker` can locate it via
        ``Path(sys.executable).parent``: ``python/bin/`` on POSIX and the
        ``python/`` root on Windows (where ``python.exe`` lives at the top level).
        """
        if "windows" in target_triple:
            return python_root / "litestar-ssr-worker.exe"
        return python_root / "bin" / "litestar-ssr-worker"

    def build_project_wheel(self, work_dir: Path) -> list[Path]:
        """Build the current project's wheel into ``work_dir / 'wheels'`` using ``uv build``."""
        wheel_dir = work_dir / "wheels"
        wheel_dir.mkdir(parents=True, exist_ok=True)
        self._runner(["uv", "build", "--wheel", "--out-dir", str(wheel_dir)], cwd=self._config.root_dir)
        return sorted(wheel_dir.glob("*.whl"))

    def prepare_pyapp_source(self, work_dir: Path, pyapp_source: Path | None = None) -> Path:
        """Stage a writable PyApp source checkout under ``work_dir / 'pyapp'``."""
        dest = work_dir / "pyapp"
        if dest.exists():
            shutil.rmtree(dest)
        if pyapp_source is not None:
            shutil.copytree(pyapp_source, dest, ignore=shutil.ignore_patterns("target", ".git"))
            return dest
        work_dir.mkdir(parents=True, exist_ok=True)
        self._runner(
            [
                "git",
                "clone",
                "--depth",
                "1",
                "--branch",
                self._bundle_config.pyapp_version,
                PYAPP_REPOSITORY_URL,
                str(dest),
            ],
            cwd=work_dir,
        )
        return dest

    def stage_distribution(
        self,
        work_dir: Path,
        wheels: Sequence[Path] | None = None,
        *,
        archive_path: Path | None = None,
        ssr_entry: Path | None = None,
        target_triple: str | None = None,
    ) -> Path:
        """Stage a ``python-build-standalone`` distribution, install wheels, and repack ``python-dist.tar.gz``."""
        triple = target_triple or self.target_triple
        work_dir.mkdir(parents=True, exist_ok=True)

        pbs_archive = archive_path or (work_dir / "pbs-install-only-stripped.tar.gz")
        if not pbs_archive.is_file():
            url = self.resolve_pbs_url(triple)
            if not url.startswith("https://"):
                msg = f"Unsupported PBS URL scheme for {url!r}; expected https://"
                raise BundleConfigurationError(msg)
            self._runner(["curl", "-fSL", "--retry", "3", "-o", str(pbs_archive), url], cwd=work_dir)

        extract_root = work_dir / "extracted"
        if extract_root.exists():
            shutil.rmtree(extract_root)
        extract_root.mkdir(parents=True, exist_ok=True)

        with tarfile.open(pbs_archive, "r:gz") as tar:
            _safe_extract_tar(tar, extract_root)

        python_root = extract_root / "python"
        if not python_root.is_dir():
            msg = f"Expected 'python/' directory inside {pbs_archive}, not found."
            raise BundleConfigurationError(msg)

        resolved_wheels = list(wheels) if wheels is not None else []
        if resolved_wheels or self._bundle_config.extra_wheels:
            site_packages = self._resolve_site_packages_dir(python_root, triple)
            pip_cmd = self.build_pip_install_command(site_packages, resolved_wheels, triple)
            self._runner(pip_cmd, cwd=self._config.root_dir)

        if self._bundle_config.compile_ssr_worker in {"bun", "deno"}:
            resolved_ssr = ssr_entry or resolve_ssr_bundle_path(self._config.paths)
            ssr_out = self._resolve_ssr_worker_binary_path(python_root, triple)
            ssr_out.parent.mkdir(parents=True, exist_ok=True)
            ssr_cmd = self.build_ssr_compile_command(resolved_ssr, ssr_out)
            self._runner(ssr_cmd, cwd=self._config.root_dir)

        if self._bundle_config.strip_dist:
            self.strip_staged_distribution(python_root)

        out_dir = self._resolve_output_dir()
        out_dir.mkdir(parents=True, exist_ok=True)
        staged_archive = out_dir / "python-dist.tar.gz"
        with tarfile.open(staged_archive, "w:gz") as tar:
            tar.add(python_root, arcname="python")

        return staged_archive

    def build_pyapp_env(self, dist_archive: Path, target_triple: str | None = None) -> dict[str, str]:
        """Construct the ``PYAPP_*`` environment variables for compiling the PyApp binary."""
        triple = target_triple or self.target_triple
        is_windows = "windows" in triple
        python_rel = r"python\python.exe" if is_windows else "python/bin/python3"

        project_name = self._bundle_config.binary_name or self._config.root_dir.name
        env: dict[str, str] = {
            **os.environ,
            "PYAPP_PROJECT_NAME": project_name,
            "PYAPP_PROJECT_VERSION": self._bundle_config.project_version or "0.0.0",
            "PYAPP_DISTRIBUTION_PATH": str(dist_archive.resolve()),
            "PYAPP_DISTRIBUTION_EMBED": "true",
            "PYAPP_DISTRIBUTION_PYTHON_PATH": python_rel,
            "PYAPP_SKIP_INSTALL": "true" if self._bundle_config.skip_install else "false",
            "PYAPP_FULL_ISOLATION": "true" if self._bundle_config.full_isolation else "false",
            "PYAPP_PASS_LOCATION": "true" if self._bundle_config.pass_location else "false",
        }
        if self._bundle_config.exec_spec:
            env["PYAPP_EXEC_SPEC"] = self._bundle_config.exec_spec
        elif self._bundle_config.exec_module:
            env["PYAPP_EXEC_MODULE"] = self._bundle_config.exec_module
        else:
            env["PYAPP_EXEC_MODULE"] = project_name.replace("-", "_")

        if self._bundle_config.strip_symbols:
            env["CARGO_PROFILE_RELEASE_STRIP"] = "symbols"

        return env

    def build_cargo_command(self, target_triple: str | None = None) -> list[str]:
        """Construct the ``cargo build`` or ``cargo zigbuild`` command for compiling PyApp."""
        triple = target_triple or self.target_triple
        if self._bundle_config.use_zigbuild:
            target_arg = (
                f"{triple}.{self._bundle_config.glibc_version}"
                if "linux-gnu" in triple and self._bundle_config.glibc_version
                else triple
            )
            return ["cargo", "zigbuild", "--release", "--target", target_arg]
        return ["cargo", "build", "--release", "--target", triple]

    def _resolve_output_dir(self) -> Path:
        """Resolve ``bundle_config.output_dir`` relative to ``config.root_dir``."""
        out = self._bundle_config.output_dir
        return out if out.is_absolute() else (self._config.root_dir / out)

    def compile_binary(
        self, dist_archive: Path, pyapp_dir: Path, *, output_path: Path | None = None, target_triple: str | None = None
    ) -> Path:
        """Patch the PyApp source tree, invoke Cargo, and copy the compiled binary to ``output_dir``."""
        triple = target_triple or self.target_triple
        if self._bundle_config.install_root:
            patch_pyapp_install_dir(pyapp_dir, self._bundle_config.install_root)

        env = self.build_pyapp_env(dist_archive, triple)
        if self._bundle_config.static_compression_libs:
            env.update(patch_pyapp_static_bzip2(pyapp_dir))

        cargo_cmd = self.build_cargo_command(triple)
        self._runner(cargo_cmd, cwd=pyapp_dir, env=env)

        is_windows = "windows" in triple
        built_name = "pyapp.exe" if is_windows else "pyapp"
        candidates = [
            pyapp_dir / "target" / triple / "release" / built_name,
            pyapp_dir / "target" / "release" / built_name,
        ]
        built_binary = next((c for c in candidates if c.is_file()), None)
        if built_binary is None:
            msg = f"Compiled PyApp binary not found at {candidates[0]}"
            raise BundleConfigurationError(msg)

        if output_path is not None:
            dest = output_path
        else:
            out_dir = self._resolve_output_dir()
            binary_name = self._bundle_config.binary_name or self._config.root_dir.name
            if is_windows and not binary_name.endswith(".exe"):
                binary_name = f"{binary_name}.exe"
            dest = out_dir / binary_name

        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(built_binary, dest)
        return dest
