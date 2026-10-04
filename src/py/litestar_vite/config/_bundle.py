"""PyApp single-file executable bundle configuration."""

from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any, Literal, cast

import msgspec

__all__ = ("BundleConfig", "SSRWorkerCompileTarget")

SSRWorkerCompileTarget = Literal["none", "bun", "deno", "node", "wasm"]
_VALID_SSR_COMPILE_TARGETS: frozenset[str] = frozenset({"none", "bun", "deno", "node", "wasm"})


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
    """Configuration for staging and compiling PyApp single-file executables."""

    enabled: bool = False
    binary_name: str | None = None
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

        self.extra_wheels = [Path(w) if isinstance(w, str) else w for w in self.extra_wheels]
        self.extra_pip_args = [str(arg) for arg in self.extra_pip_args]

    @classmethod
    def from_pyproject(cls, pyproject_path: Path) -> "BundleConfig":
        """Load ``BundleConfig`` from ``[tool.litestar.bundle]`` in ``pyproject.toml``.

        Defaults ``binary_name`` to ``[project].name`` when not explicitly set in
        ``[tool.litestar.bundle]``.

        Args:
            pyproject_path: Path to the ``pyproject.toml`` file.

        Returns:
            Populated ``BundleConfig`` instance.
        """
        if not pyproject_path.is_file():
            return cls(enabled=False)

        raw_data = msgspec.toml.decode(pyproject_path.read_bytes())
        if not isinstance(raw_data, dict):
            return cls(enabled=False)

        data = cast("dict[str, Any]", raw_data)
        project_any = data.get("project")
        project_table = cast("dict[str, Any]", project_any) if isinstance(project_any, dict) else {}
        default_binary_name = project_table.get("name")
        binary_name_default = str(default_binary_name) if isinstance(default_binary_name, str) else None

        tool_any = data.get("tool")
        tool_table = cast("dict[str, Any]", tool_any) if isinstance(tool_any, dict) else {}
        litestar_any = tool_table.get("litestar")
        litestar_table = cast("dict[str, Any]", litestar_any) if isinstance(litestar_any, dict) else {}
        bundle_any = litestar_table.get("bundle")
        if not isinstance(bundle_any, dict):
            return cls(enabled=False, binary_name=binary_name_name_or_none(binary_name_default))

        bundle_table = cast("dict[str, Any]", bundle_any)
        kwargs: dict[str, Any] = {
            "enabled": bool(bundle_table.get("enabled", True)),
            "binary_name": bundle_table.get("binary_name", binary_name_default),
        }
        allowed_keys = {
            "exec_module",
            "exec_spec",
            "python_version",
            "pbs_release",
            "pbs_urls",
            "platform_map",
            "target_arch",
            "install_root",
            "full_isolation",
            "pass_location",
            "skip_install",
            "compile_ssr_worker",
            "ssr_bytecode",
            "strip_dist",
            "strip_symbols",
            "static_compression_libs",
            "use_zigbuild",
            "glibc_version",
            "extra_wheels",
            "extra_pip_args",
            "output_dir",
        }
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


def binary_name_name_or_none(value: str | None) -> str | None:
    """Return a trimmed binary name or None."""
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None
