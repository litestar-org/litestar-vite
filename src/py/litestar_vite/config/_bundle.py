"""PyApp single-file executable bundle configuration."""

from dataclasses import dataclass, field, fields, replace
from pathlib import Path
from typing import Any, Literal, cast

import msgspec

__all__ = ("DEFAULT_PBS_FULL_VERSIONS", "DEFAULT_PYAPP_VERSION", "BundleConfig", "SSRWorkerCompileTarget")

SSRWorkerCompileTarget = Literal["none", "bun", "deno"]
_VALID_SSR_COMPILE_TARGETS: frozenset[str] = frozenset({"none", "bun", "deno"})

DEFAULT_PYAPP_VERSION = "v0.29.0"
"""PyApp release tag cloned when no ``pyapp_version`` override is provided."""

DEFAULT_PBS_FULL_VERSIONS: dict[str, dict[str, str]] = {
    "20241016": {"3.10": "3.10.15", "3.11": "3.11.10", "3.12": "3.12.7", "3.13": "3.13.0"}
}
"""Known ``python-build-standalone`` release -> ``major.minor`` -> full patch version table.

Used to derive default distribution download URLs. Releases or Python versions
outside this table require an explicit ``pbs_urls`` override.
"""


def _empty_str_dict() -> dict[str, str]:
    """Return an empty string-to-string dictionary."""
    return {}


def _empty_path_list() -> list[Path]:
    """Return an empty list of Path objects."""
    return []


def _empty_str_list() -> list[str]:
    """Return an empty list of strings."""
    return []


def _default_output_dir() -> Path:
    """Return the default bundle output directory."""
    return Path("dist/bundle")


@dataclass(slots=True)
class BundleConfig:
    """Configuration for staging and compiling PyApp single-file executables.

    Attributes:
        enabled: Whether bundling is enabled for this project.
        binary_name: Output executable name. Defaults to ``[project].name``.
        project_version: Version reported to PyApp via ``PYAPP_PROJECT_VERSION``.
            Defaults to ``[project].version`` when loaded from ``pyproject.toml``.
        exec_module: Module executed via ``python -m`` at startup (mutually exclusive with ``exec_spec``).
        exec_spec: ``module:callable`` object reference executed at startup.
        python_version: ``major.minor`` CPython version to embed (e.g. ``"3.12"``).
        pbs_release: ``python-build-standalone`` release tag used to derive download URLs.
        pbs_urls: Explicit target-triple -> distribution URL overrides.
        platform_map: Target-triple -> pip platform tag overrides.
        target_arch: Default Rust target triple when not passed on the CLI.
        install_root: Base directory that replaces PyApp's platform data-local directory
            when resolving the extracted runtime location. PyApp still appends
            ``<project_name>/<distribution_id>/<project_version>`` beneath it, and the
            runtime ``PYAPP_INSTALL_DIR_<PROJECT_NAME>`` environment variable still wins.
        full_isolation: Set ``PYAPP_FULL_ISOLATION=1`` (required for bundled SSR worker discovery).
        pass_location: Set ``PYAPP_PASS_LOCATION=1``.
        skip_install: Set ``PYAPP_SKIP_INSTALL=1`` (project is pre-installed in the staged distribution).
        compile_ssr_worker: Compile ``ssr.js`` into a native worker binary with ``bun`` or ``deno``.
        ssr_bytecode: Pass ``--bytecode`` to ``bun build --compile``.
        strip_dist: Remove stdlib test suites and ``__pycache__`` from the staged distribution.
        strip_symbols: Strip debug symbols from the compiled PyApp binary.
        static_compression_libs: Enable the ``bzip2`` crate ``static`` feature and export
            ``BZIP2_SYS_STATIC``/``LZMA_API_STATIC`` for the cargo build. PyApp ``v0.28+`` uses
            the pure-Rust ``libbz2-rs-sys`` backend by default, so this only changes linking
            when a custom ``pyapp_version`` still depends on the C ``bzip2-sys`` backend.
        use_zigbuild: Use ``cargo zigbuild`` for cross-compilation.
        glibc_version: glibc floor appended to Linux targets when ``use_zigbuild`` is enabled.
        pyapp_version: PyApp git tag to clone when building from source.
        extra_wheels: Additional wheel files installed into the staged distribution.
        extra_pip_args: Additional arguments appended to the ``pip install`` command.
        output_dir: Directory receiving the compiled binary.
    """

    enabled: bool = False
    binary_name: str | None = None
    project_version: str | None = None
    exec_module: str | None = None
    exec_spec: str | None = None
    python_version: str = "3.12"
    pbs_release: str = "20241016"
    pbs_urls: dict[str, str] = field(default_factory=_empty_str_dict)
    platform_map: dict[str, str] = field(default_factory=_empty_str_dict)
    target_arch: str | None = None
    install_root: str | None = None
    full_isolation: bool = True
    pass_location: bool = True
    skip_install: bool = True
    compile_ssr_worker: SSRWorkerCompileTarget = "none"
    ssr_bytecode: bool = True
    strip_dist: bool = True
    strip_symbols: bool = True
    static_compression_libs: bool = True
    use_zigbuild: bool = False
    glibc_version: str = "2.17"
    pyapp_version: str = DEFAULT_PYAPP_VERSION
    extra_wheels: list[Path] = field(default_factory=_empty_path_list)
    extra_pip_args: list[str] = field(default_factory=_empty_str_list)
    output_dir: Path = field(default_factory=_default_output_dir)

    def __post_init__(self) -> None:
        """Validate and normalize bundle configuration fields."""
        if self.exec_module and self.exec_spec:
            msg = "Cannot specify both exec_module and exec_spec in BundleConfig."
            raise ValueError(msg)

        if self.compile_ssr_worker not in _VALID_SSR_COMPILE_TARGETS:
            msg = (
                f"Invalid compile_ssr_worker={self.compile_ssr_worker!r}. "
                f"Expected one of: {', '.join(sorted(_VALID_SSR_COMPILE_TARGETS))}"
            )
            raise ValueError(msg)

        if isinstance(self.output_dir, str):
            self.output_dir = Path(self.output_dir)

        self.binary_name = _normalize_binary_name(self.binary_name)
        self.project_version = _normalize_binary_name(self.project_version)
        self.extra_wheels = [Path(w) if isinstance(w, str) else w for w in self.extra_wheels]
        self.extra_pip_args = [str(arg) for arg in self.extra_pip_args]

    @classmethod
    def from_pyproject(cls, pyproject_path: Path) -> "BundleConfig":
        """Load ``BundleConfig`` from ``[tool.litestar.bundle]`` in ``pyproject.toml``.

        Defaults ``binary_name`` to ``[project].name`` and ``project_version`` to
        ``[project].version`` when not explicitly set in ``[tool.litestar.bundle]``.

        Parsing failures (unreadable file, malformed TOML, or a missing TOML
        backend on Python < 3.11) yield a disabled configuration instead of
        raising so that ``ViteConfig`` construction never depends on this file.

        Args:
            pyproject_path: Path to the ``pyproject.toml`` file.

        Returns:
            Populated ``BundleConfig`` instance.
        """
        if not pyproject_path.is_file():
            return cls(enabled=False)

        try:
            raw_data = msgspec.toml.decode(pyproject_path.read_bytes())
        except (ImportError, OSError, msgspec.DecodeError):
            return cls(enabled=False)
        if not isinstance(raw_data, dict):
            return cls(enabled=False)

        data = cast("dict[str, Any]", raw_data)
        project_any = data.get("project")
        project_table = cast("dict[str, Any]", project_any) if isinstance(project_any, dict) else {}
        default_binary_name = project_table.get("name")
        binary_name_default = str(default_binary_name) if isinstance(default_binary_name, str) else None
        default_version = project_table.get("version")
        version_default = str(default_version) if isinstance(default_version, str) else None

        tool_any = data.get("tool")
        tool_table = cast("dict[str, Any]", tool_any) if isinstance(tool_any, dict) else {}
        litestar_any = tool_table.get("litestar")
        litestar_table = cast("dict[str, Any]", litestar_any) if isinstance(litestar_any, dict) else {}
        bundle_any = litestar_table.get("bundle")
        if not isinstance(bundle_any, dict):
            return cls(enabled=False, binary_name=binary_name_default, project_version=version_default)

        bundle_table = cast("dict[str, Any]", bundle_any)
        kwargs: dict[str, Any] = {
            "enabled": bool(bundle_table.get("enabled", True)),
            "binary_name": bundle_table.get("binary_name", binary_name_default),
            "project_version": bundle_table.get("project_version", version_default),
        }
        allowed_keys = {f.name for f in fields(cls)} - set(kwargs)
        for key in allowed_keys:
            if key in bundle_table:
                kwargs[key] = bundle_table[key]

        return cls(**kwargs)

    def with_overrides(
        self,
        *,
        enabled: bool | None = None,
        binary_name: str | None = None,
        target_arch: str | None = None,
        output_dir: Path | None = None,
        compile_ssr_worker: SSRWorkerCompileTarget | None = None,
        install_root: str | None = None,
        use_zigbuild: bool | None = None,
        strip_dist: bool | None = None,
        strip_symbols: bool | None = None,
    ) -> "BundleConfig":
        """Return a copy of ``BundleConfig`` with non-None CLI overrides applied."""
        return replace(
            self,
            enabled=self.enabled if enabled is None else enabled,
            binary_name=self.binary_name if binary_name is None else binary_name,
            target_arch=self.target_arch if target_arch is None else target_arch,
            output_dir=self.output_dir if output_dir is None else output_dir,
            compile_ssr_worker=self.compile_ssr_worker if compile_ssr_worker is None else compile_ssr_worker,
            install_root=self.install_root if install_root is None else install_root,
            use_zigbuild=self.use_zigbuild if use_zigbuild is None else use_zigbuild,
            strip_dist=self.strip_dist if strip_dist is None else strip_dist,
            strip_symbols=self.strip_symbols if strip_symbols is None else strip_symbols,
        )


def _normalize_binary_name(value: str | None) -> str | None:
    """Return a trimmed non-empty string or None."""
    if value is None:
        return None
    stripped = str(value).strip()
    return stripped or None
