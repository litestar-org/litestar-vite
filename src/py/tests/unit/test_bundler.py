"""Unit tests for BundleConfig and PyAppBundler."""

import tarfile
from pathlib import Path

import pytest

from litestar_vite.bundler import (
    DEFAULT_PLATFORMS,
    DEFAULT_URLS,
    BundleConfigurationError,
    PyAppBundler,
    detect_host_target_triple,
    patch_pyapp_install_dir,
    patch_pyapp_static_bzip2,
)
from litestar_vite.config import BundleConfig, PathConfig, ViteConfig


def test_default_urls_and_platforms_cover_five_standard_targets() -> None:
    """Verify DEFAULT_URLS and DEFAULT_PLATFORMS cover all 5 standard target triples."""
    expected_targets = {
        "x86_64-unknown-linux-gnu",
        "aarch64-unknown-linux-gnu",
        "x86_64-apple-darwin",
        "aarch64-apple-darwin",
        "x86_64-pc-windows-msvc",
    }
    assert set(DEFAULT_URLS.keys()) == expected_targets
    assert set(DEFAULT_PLATFORMS.keys()) == expected_targets
    assert DEFAULT_PLATFORMS["x86_64-unknown-linux-gnu"] == "manylinux_2_28_x86_64"
    assert DEFAULT_PLATFORMS["aarch64-unknown-linux-gnu"] == "manylinux_2_28_aarch64"
    for url in DEFAULT_URLS.values():
        assert "install_only_stripped" in url


def test_patch_pyapp_install_dir_home_relative_and_absolute(tmp_path: Path) -> None:
    """Verify patch_pyapp_install_dir patches src/app.rs for both ~/ and absolute paths."""
    src_dir = tmp_path / "src"
    src_dir.mkdir(parents=True)
    app_rs = src_dir / "app.rs"
    original_source = 'pub fn storage_dir() -> PathBuf {\n    project_dirs().data_local_dir().join("pyapp")\n}\n'
    app_rs.write_text(original_source, encoding="utf-8")

    patch_pyapp_install_dir(tmp_path, "~/.my-app/runtime")
    patched_home = app_rs.read_text(encoding="utf-8")
    assert (
        'directories::BaseDirs::new().expect("could not find base directories").home_dir().join(".my-app/runtime")'
        in patched_home
    )

    app_rs.write_text(original_source, encoding="utf-8")
    patch_pyapp_install_dir(tmp_path, "/opt/my-app/runtime")
    patched_abs = app_rs.read_text(encoding="utf-8")
    assert 'std::path::PathBuf::from("/opt/my-app/runtime")' in patched_abs

    app_rs.write_text("pub fn unrelated() {}\n", encoding="utf-8")
    with pytest.raises(BundleConfigurationError, match="storage_dir"):
        patch_pyapp_install_dir(tmp_path, "~/.my-app/runtime")


def test_patch_pyapp_static_bzip2_updates_cargo_toml_and_env(tmp_path: Path) -> None:
    """Verify patch_pyapp_static_bzip2 adds static feature to bzip2 in Cargo.toml and returns static env vars."""
    cargo_toml = tmp_path / "Cargo.toml"
    cargo_toml.write_text('[package]\nname = "pyapp"\n\n[dependencies]\nbzip2 = "0.4.4"\n', encoding="utf-8")

    env_flags = patch_pyapp_static_bzip2(tmp_path)
    updated = cargo_toml.read_text(encoding="utf-8")

    assert env_flags == {"BZIP2_SYS_STATIC": "1", "LZMA_API_STATIC": "1"}
    assert "static" in updated
    assert "bzip2" in updated


def test_pyapp_bundler_commands_and_overrides(tmp_path: Path) -> None:
    """Verify PyAppBundler resolves PBS URLs, pip target commands, SSR compile commands, and cargo zigbuild args."""
    custom_url = "https://mirror.internal/python-3.12-linux.tar.gz"
    bundle_cfg = BundleConfig(
        enabled=True,
        binary_name="acme-portal",
        exec_module="acme.cli",
        python_version="3.12",
        target_arch="x86_64-unknown-linux-gnu",
        pbs_urls={"x86_64-unknown-linux-gnu": custom_url},
        platform_map={"x86_64-unknown-linux-gnu": "manylinux_2_28_x86_64"},
        compile_ssr_worker="bun",
        ssr_bytecode=True,
        use_zigbuild=True,
        glibc_version="2.28",
        extra_pip_args=["--no-compile"],
    )
    vite_cfg = ViteConfig(mode="template", paths=PathConfig(root=tmp_path), bundle=bundle_cfg)
    bundler = PyAppBundler(config=vite_cfg)

    assert bundler.resolve_pbs_url() == custom_url
    assert bundler.resolve_pip_platform() == "manylinux_2_28_x86_64"

    wheel_path = tmp_path / "dist" / "acme-1.0.0-py3-none-any.whl"
    site_packages = tmp_path / "stage" / "python" / "lib" / "python3.12" / "site-packages"
    pip_cmd = bundler.build_pip_install_command(site_packages, [wheel_path])
    assert pip_cmd[:4] == ["uv", "pip", "install", "--target"]
    assert str(site_packages) in pip_cmd
    assert "--python-version" in pip_cmd
    assert "3.12" in pip_cmd
    assert "--python-platform" in pip_cmd
    assert "manylinux_2_28_x86_64" in pip_cmd
    assert "--no-compile" in pip_cmd
    assert str(wheel_path) in pip_cmd

    ssr_entry = tmp_path / "dist" / "ssr" / "ssr.js"
    ssr_bin = tmp_path / "stage" / "python" / "bin" / "litestar-ssr-worker"
    bun_cmd = bundler.build_ssr_compile_command(ssr_entry, ssr_bin)
    assert bun_cmd == ["bun", "build", "--compile", "--bytecode", str(ssr_entry), "--outfile", str(ssr_bin)]

    cargo_cmd = bundler.build_cargo_command()
    assert cargo_cmd == ["cargo", "zigbuild", "--release", "--target", "x86_64-unknown-linux-gnu.2.28"]


def test_pyapp_bundler_stage_and_compile_lifecycle(tmp_path: Path) -> None:
    """Verify PyAppBundler.stage_distribution strips bloat, packs python-dist.tar.gz, and compile_binary invokes cargo."""
    recorded_calls: list[tuple[list[str], dict[str, str] | None]] = []

    def fake_runner(cmd: list[str], *, cwd: Path | None = None, env: dict[str, str] | None = None) -> None:
        del cwd
        recorded_calls.append((list(cmd), dict(env) if env is not None else None))
        if cmd[:2] == ["bun", "build"] and "--outfile" in cmd:
            outfile = Path(cmd[cmd.index("--outfile") + 1])
            outfile.parent.mkdir(parents=True, exist_ok=True)
            outfile.write_text("#!/bin/sh\n", encoding="utf-8")
            outfile.chmod(0o755)
        if cmd[0] == "cargo":
            assert env is not None
            pyapp_root = tmp_path / "pyapp-src"
            target_triple = "x86_64-unknown-linux-gnu"
            built_bin = pyapp_root / "target" / target_triple / "release" / "pyapp"
            built_bin.parent.mkdir(parents=True, exist_ok=True)
            built_bin.write_bytes(b"ELF-BINARY")

    pbs_archive = tmp_path / "pbs.tar.gz"
    pbs_src = tmp_path / "pbs-tree" / "python"
    site_pkgs = pbs_src / "lib" / "python3.12" / "site-packages"
    pycache_dir = site_pkgs / "demo" / "__pycache__"
    tests_dir = site_pkgs / "demo" / "tests"
    include_dir = pbs_src / "include" / "python3.12"
    bin_dir = pbs_src / "bin"
    for d in (pycache_dir, tests_dir, include_dir, bin_dir):
        d.mkdir(parents=True, exist_ok=True)
    (bin_dir / "python3").write_text("#!/bin/sh\n", encoding="utf-8")
    (pycache_dir / "mod.cpython-312.pyc").write_bytes(b"pyc")
    (tests_dir / "test_mod.py").write_text("assert True\n", encoding="utf-8")
    (include_dir / "Python.h").write_text("/* header */\n", encoding="utf-8")
    (site_pkgs / "demo" / "__init__.py").write_text("__version__ = '1.0'\n", encoding="utf-8")

    with tarfile.open(pbs_archive, "w:gz") as tar:
        tar.add(pbs_src, arcname="python")

    ssr_entry = tmp_path / "ssr.js"
    ssr_entry.write_text("globalThis.__litestar_ssr_dispatch__ = () => {};", encoding="utf-8")
    wheel_file = tmp_path / "demo-1.0.0-py3-none-any.whl"
    wheel_file.write_bytes(b"wheel")

    bundle_cfg = BundleConfig(
        enabled=True,
        binary_name="demo-app",
        exec_spec="demo.app:run",
        target_arch="x86_64-unknown-linux-gnu",
        install_root="~/.demo-app/runtime",
        compile_ssr_worker="bun",
        strip_dist=True,
        static_compression_libs=True,
        output_dir=tmp_path / "dist" / "bundle",
    )
    vite_cfg = ViteConfig(mode="template", paths=PathConfig(root=tmp_path), bundle=bundle_cfg)
    bundler = PyAppBundler(config=vite_cfg, runner=fake_runner)

    staged_tar = bundler.stage_distribution(
        work_dir=tmp_path / "work", wheels=[wheel_file], archive_path=pbs_archive, ssr_entry=ssr_entry
    )
    assert staged_tar.is_file()

    with tarfile.open(staged_tar, "r:gz") as tar:
        names = set(tar.getnames())
    assert "python/bin/litestar-ssr-worker" in names
    assert "python/lib/python3.12/site-packages/demo/__init__.py" in names
    assert not any("__pycache__" in n for n in names)
    assert not any(n.endswith(".pyc") for n in names)

    pyapp_src = tmp_path / "pyapp-src"
    (pyapp_src / "src").mkdir(parents=True)
    (pyapp_src / "src" / "app.rs").write_text(
        'pub fn storage_dir() -> PathBuf { project_dirs().data_local_dir().join("pyapp") }\n', encoding="utf-8"
    )
    (pyapp_src / "Cargo.toml").write_text(
        '[package]\nname = "pyapp"\n[dependencies]\nbzip2 = "0.4.4"\n', encoding="utf-8"
    )

    out_bin = bundler.compile_binary(staged_tar, pyapp_src)
    assert out_bin == tmp_path / "dist" / "bundle" / "demo-app"
    assert out_bin.is_file()

    cargo_calls = [(cmd, env) for cmd, env in recorded_calls if cmd[0] == "cargo"]
    assert len(cargo_calls) == 1
    _, cargo_env = cargo_calls[0]
    assert cargo_env is not None
    assert cargo_env["PYAPP_DISTRIBUTION_PATH"] == str(staged_tar)
    assert cargo_env["PYAPP_DISTRIBUTION_EMBED"] == "true"
    assert cargo_env["PYAPP_SKIP_INSTALL"] == "true"
    assert cargo_env["PYAPP_FULL_ISOLATION"] == "true"
    assert cargo_env["PYAPP_PASS_LOCATION"] == "true"
    assert cargo_env["PYAPP_EXEC_SPEC"] == "demo.app:run"
    assert cargo_env["BZIP2_SYS_STATIC"] == "1"
    assert cargo_env["LZMA_API_STATIC"] == "1"
    assert isinstance(detect_host_target_triple(), str)
