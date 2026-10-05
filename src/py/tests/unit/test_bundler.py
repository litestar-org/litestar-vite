"""Unit tests for BundleConfig and PyAppBundler."""

import tarfile
from pathlib import Path

import pytest

from litestar_vite.bundler import (
    DEFAULT_PLATFORMS,
    DEFAULT_TARGET_TRIPLES,
    PBS_URL_TEMPLATE,
    PYAPP_REPOSITORY_URL,
    BundleConfigurationError,
    PyAppBundler,
    default_pbs_url,
    detect_host_target_triple,
    patch_pyapp_install_dir,
    patch_pyapp_static_bzip2,
)
from litestar_vite.config import BundleConfig, PathConfig, ViteConfig


def test_default_pbs_urls_and_platforms_cover_five_standard_targets() -> None:
    """Verify default_pbs_url and DEFAULT_PLATFORMS cover all 5 standard target triples."""
    expected_targets = {
        "x86_64-unknown-linux-gnu",
        "aarch64-unknown-linux-gnu",
        "x86_64-apple-darwin",
        "aarch64-apple-darwin",
        "x86_64-pc-windows-msvc",
    }
    assert set(DEFAULT_TARGET_TRIPLES) == expected_targets
    assert set(DEFAULT_PLATFORMS.keys()) == expected_targets
    assert DEFAULT_PLATFORMS["x86_64-unknown-linux-gnu"] == "manylinux_2_28_x86_64"
    assert DEFAULT_PLATFORMS["aarch64-unknown-linux-gnu"] == "manylinux_2_28_aarch64"
    defaults = BundleConfig()
    for triple in DEFAULT_TARGET_TRIPLES:
        url = default_pbs_url(triple, defaults.python_version, defaults.pbs_release)
        assert url is not None
        assert "install_only_stripped" in url
        assert triple in url


_PYAPP_V0_29_0_INITIALIZE = """\
pub fn initialize() -> Result<()> {
    let platform_directories = ProjectDirs::from("", "", "pyapp")
        .with_context(|| "unable to find platform directories")?;
    PLATFORM_DIRS
        .set(platform_directories)
        .expect("could not set platform directories");

    let install_dir_override = env::var(format!(
        "PYAPP_INSTALL_DIR_{}",
        project_name().to_uppercase()
    ))
    .unwrap_or_default();
    let installation_directory = if !install_dir_override.is_empty() {
        PathBuf::from(install_dir_override)
    } else {
        platform_dirs()
            .data_local_dir()
            .join(project_name())
            .join(distribution_id())
            .join(project_version())
    };
    INSTALLATION_DIRECTORY
        .set(installation_directory)
        .expect("could not set installation directory");

    Ok(())
}
"""

_PRESERVED_INSTALL_SUFFIX = """
            .join(project_name())
            .join(distribution_id())
            .join(project_version())"""


def test_patch_pyapp_install_dir_home_relative_and_absolute(tmp_path: Path) -> None:
    """Verify patch_pyapp_install_dir rewrites the real PyApp v0.29.0 install_dir base for ~/ and absolute paths."""
    src_dir = tmp_path / "src"
    src_dir.mkdir(parents=True)
    app_rs = src_dir / "app.rs"
    app_rs.write_text(_PYAPP_V0_29_0_INITIALIZE, encoding="utf-8")

    patch_pyapp_install_dir(tmp_path, "~/.my-app/runtime")
    patched_home = app_rs.read_text(encoding="utf-8")
    home_expr = (
        'directories::BaseDirs::new().expect("could not find base directories").home_dir().join(".my-app/runtime")'
    )
    assert f"{home_expr}{_PRESERVED_INSTALL_SUFFIX}" in patched_home
    assert "platform_dirs()\n            .data_local_dir()" not in patched_home
    assert 'env::var(format!(\n        "PYAPP_INSTALL_DIR_{}"' in patched_home

    app_rs.write_text(_PYAPP_V0_29_0_INITIALIZE, encoding="utf-8")
    patch_pyapp_install_dir(tmp_path, "/opt/my-app/runtime")
    patched_abs = app_rs.read_text(encoding="utf-8")
    assert f'std::path::PathBuf::from("/opt/my-app/runtime"){_PRESERVED_INSTALL_SUFFIX}' in patched_abs

    app_rs.write_text("pub fn unrelated() {}\n", encoding="utf-8")
    with pytest.raises(BundleConfigurationError, match="install_dir"):
        patch_pyapp_install_dir(tmp_path, "~/.my-app/runtime")


@pytest.mark.parametrize(
    ("original", "expected"),
    [
        ('bzip2 = "0.6.0"\n', 'bzip2 = { version = "0.6.0", features = ["static"] }\n'),
        ('bzip2 = { version = "0.6.0" }\n', 'bzip2 = { version = "0.6.0", features = ["static"] }\n'),
        (
            'bzip2 = { version = "0.6.0", features = ["bzip2-sys"] }\n',
            'bzip2 = { version = "0.6.0", features = ["static", "bzip2-sys"] }\n',
        ),
        (
            'bzip2 = { version = "0.6.0", features = ["static"] }\n',
            'bzip2 = { version = "0.6.0", features = ["static"] }\n',
        ),
    ],
)
def test_patch_pyapp_static_bzip2_updates_cargo_toml_and_env(tmp_path: Path, original: str, expected: str) -> None:
    """Verify patch_pyapp_static_bzip2 rewrites simple and inline-table bzip2 dependencies and returns static env vars."""
    cargo_toml = tmp_path / "Cargo.toml"
    cargo_toml.write_text(f'[package]\nname = "pyapp"\n\n[dependencies]\n{original}', encoding="utf-8")

    env_flags = patch_pyapp_static_bzip2(tmp_path)

    assert env_flags == {"BZIP2_SYS_STATIC": "1", "LZMA_API_STATIC": "1"}
    assert cargo_toml.read_text(encoding="utf-8") == f'[package]\nname = "pyapp"\n\n[dependencies]\n{expected}'


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
    (pyapp_src / "src" / "app.rs").write_text(_PYAPP_V0_29_0_INITIALIZE, encoding="utf-8")
    (pyapp_src / "Cargo.toml").write_text(
        '[package]\nname = "pyapp"\n[dependencies]\nbzip2 = "0.6.0"\n', encoding="utf-8"
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


def test_pyapp_bundler_build_project_wheel_and_prepare_source(tmp_path: Path) -> None:
    """Verify build_project_wheel invokes uv build and prepare_pyapp_source copies or clones PyApp."""
    recorded_cmds: list[list[str]] = []

    def fake_runner(cmd: list[str], *, cwd: Path | None = None, env: dict[str, str] | None = None) -> None:
        del cwd, env
        recorded_cmds.append(list(cmd))
        if cmd[:3] == ["uv", "build", "--wheel"]:
            out_dir = Path(cmd[cmd.index("--out-dir") + 1])
            (out_dir / "demo_app-0.1.0-py3-none-any.whl").write_bytes(b"wheel")
        elif cmd[:2] == ["git", "clone"]:
            dest_dir = Path(cmd[-1])
            dest_dir.mkdir(parents=True, exist_ok=True)
            (dest_dir / "Cargo.toml").write_text('[package]\nname = "pyapp"\n', encoding="utf-8")

    vite_cfg = ViteConfig(mode="template", paths=PathConfig(root=tmp_path), bundle=True)
    bundler = PyAppBundler(config=vite_cfg, runner=fake_runner)

    work_dir = tmp_path / "work"
    wheels = bundler.build_project_wheel(work_dir)
    assert len(wheels) == 1
    assert wheels[0].name == "demo_app-0.1.0-py3-none-any.whl"

    local_pyapp = tmp_path / "local-pyapp"
    local_pyapp.mkdir(parents=True)
    (local_pyapp / "Cargo.toml").write_text('[package]\nname = "pyapp-local"\n', encoding="utf-8")

    staged_local = bundler.prepare_pyapp_source(work_dir, pyapp_source=local_pyapp)
    assert (staged_local / "Cargo.toml").read_text(encoding="utf-8") == '[package]\nname = "pyapp-local"\n'

    staged_cloned = bundler.prepare_pyapp_source(work_dir, pyapp_source=None)
    assert (staged_cloned / "Cargo.toml").read_text(encoding="utf-8") == '[package]\nname = "pyapp"\n'
    assert any(cmd[:2] == ["git", "clone"] for cmd in recorded_cmds)


def test_resolve_pbs_url_derives_from_python_version_and_release(tmp_path: Path) -> None:
    """Default PBS URLs follow python_version/pbs_release and fail fast for unknown pairs."""
    cfg_311 = BundleConfig(enabled=True, python_version="3.11", target_arch="aarch64-apple-darwin")
    bundler_311 = PyAppBundler(config=ViteConfig(mode="template", paths=PathConfig(root=tmp_path), bundle=cfg_311))
    url = bundler_311.resolve_pbs_url()
    assert url == default_pbs_url("aarch64-apple-darwin", "3.11", "20241016")
    assert "cpython-3.11.10%2B20241016-aarch64-apple-darwin-install_only_stripped.tar.gz" in url
    assert url.startswith(PBS_URL_TEMPLATE.split("{release}", 1)[0])

    cfg_unknown = BundleConfig(enabled=True, python_version="3.14", target_arch="x86_64-unknown-linux-gnu")
    bundler_unknown = PyAppBundler(
        config=ViteConfig(mode="template", paths=PathConfig(root=tmp_path), bundle=cfg_unknown)
    )
    with pytest.raises(BundleConfigurationError, match="No known python-build-standalone artifact"):
        bundler_unknown.resolve_pbs_url()

    cfg_bad_triple = BundleConfig(enabled=True, target_arch="riscv64gc-unknown-linux-gnu")
    bundler_bad = PyAppBundler(
        config=ViteConfig(mode="template", paths=PathConfig(root=tmp_path), bundle=cfg_bad_triple)
    )
    with pytest.raises(BundleConfigurationError, match="Unsupported target triple"):
        bundler_bad.resolve_pbs_url()


def test_build_pyapp_env_uses_project_version_and_pins_pyapp_clone(tmp_path: Path) -> None:
    """PYAPP_PROJECT_VERSION comes from BundleConfig.project_version and git clone targets pyapp_version."""
    recorded_cmds: list[list[str]] = []

    def fake_runner(cmd: list[str], *, cwd: Path | None = None, env: dict[str, str] | None = None) -> None:
        del cwd, env
        recorded_cmds.append(list(cmd))
        if cmd[:2] == ["git", "clone"]:
            Path(cmd[-1]).mkdir(parents=True, exist_ok=True)

    cfg = BundleConfig(enabled=True, binary_name="svc", project_version="4.5.6", pyapp_version="v0.27.0")
    bundler = PyAppBundler(
        config=ViteConfig(mode="template", paths=PathConfig(root=tmp_path), bundle=cfg), runner=fake_runner
    )
    env = bundler.build_pyapp_env(tmp_path / "python-dist.tar.gz", "x86_64-unknown-linux-gnu")
    assert env["PYAPP_PROJECT_VERSION"] == "4.5.6"
    assert env["PYAPP_PROJECT_NAME"] == "svc"

    default_env = PyAppBundler(
        config=ViteConfig(mode="template", paths=PathConfig(root=tmp_path), bundle=BundleConfig(enabled=True)),
        runner=fake_runner,
    ).build_pyapp_env(tmp_path / "python-dist.tar.gz", "x86_64-unknown-linux-gnu")
    assert default_env["PYAPP_PROJECT_VERSION"] == "0.0.0"

    bundler.prepare_pyapp_source(tmp_path / "work")
    clone_cmd = next(cmd for cmd in recorded_cmds if cmd[:2] == ["git", "clone"])
    assert clone_cmd[clone_cmd.index("--branch") + 1] == "v0.27.0"
    assert PYAPP_REPOSITORY_URL in clone_cmd


def test_prepare_pyapp_source_copy_ignores_target_and_git(tmp_path: Path) -> None:
    """Local PyApp checkouts are copied without build artifacts or VCS metadata."""
    source = tmp_path / "pyapp-local"
    (source / "src").mkdir(parents=True)
    (source / "target" / "release").mkdir(parents=True)
    (source / ".git").mkdir()
    (source / "Cargo.toml").write_text('[package]\nname = "pyapp"\n', encoding="utf-8")
    (source / "target" / "release" / "pyapp").write_bytes(b"stale")
    (source / ".git" / "HEAD").write_text("ref: refs/heads/main\n", encoding="utf-8")

    bundler = PyAppBundler(config=ViteConfig(mode="template", paths=PathConfig(root=tmp_path), bundle=True))
    staged = bundler.prepare_pyapp_source(tmp_path / "work", pyapp_source=source)
    assert (staged / "Cargo.toml").is_file()
    assert not (staged / "target").exists()
    assert not (staged / ".git").exists()


@pytest.mark.parametrize(
    ("member_name", "kind", "linkname"),
    [
        ("../escape.txt", tarfile.REGTYPE, ""),
        ("python/bin/evil", tarfile.SYMTYPE, "../../../etc/passwd"),
        ("python/bin/hard", tarfile.LNKTYPE, "../../outside"),
        ("python/dev/null", tarfile.CHRTYPE, ""),
    ],
)
def test_stage_distribution_rejects_unsafe_tar_members(
    tmp_path: Path, member_name: str, kind: bytes, linkname: str
) -> None:
    """Archives containing traversal paths, escaping links, or device nodes are rejected before extraction."""
    archive = tmp_path / "evil.tar.gz"
    with tarfile.open(archive, "w:gz") as tar:
        root = tarfile.TarInfo("python")
        root.type = tarfile.DIRTYPE
        tar.addfile(root)
        info = tarfile.TarInfo(member_name)
        info.type = kind
        info.linkname = linkname
        tar.addfile(info)

    bundler = PyAppBundler(
        config=ViteConfig(mode="template", paths=PathConfig(root=tmp_path), bundle=True), runner=lambda *_a, **_k: None
    )
    with pytest.raises(BundleConfigurationError, match=r"Unsafe tar|Unsupported tar"):
        bundler.stage_distribution(tmp_path / "work", archive_path=archive, target_triple="x86_64-unknown-linux-gnu")
    assert not (tmp_path / "escape.txt").exists()


def test_stage_distribution_rejects_non_https_pbs_url(tmp_path: Path) -> None:
    """Only https:// distribution URLs are downloaded."""
    cfg = BundleConfig(
        enabled=True,
        target_arch="x86_64-unknown-linux-gnu",
        pbs_urls={"x86_64-unknown-linux-gnu": "http://mirror.internal/python.tar.gz"},
    )
    bundler = PyAppBundler(
        config=ViteConfig(mode="template", paths=PathConfig(root=tmp_path), bundle=cfg), runner=lambda *_a, **_k: None
    )
    with pytest.raises(BundleConfigurationError, match="expected https://"):
        bundler.stage_distribution(tmp_path / "work")


def test_strip_staged_distribution_keeps_site_packages_tests(tmp_path: Path) -> None:
    """Stripping removes stdlib test suites and caches but leaves installed packages' tests directories."""
    python_root = tmp_path / "python"
    stdlib = python_root / "lib" / "python3.12"
    (stdlib / "test").mkdir(parents=True)
    (stdlib / "idlelib" / "idle_test").mkdir(parents=True)
    (stdlib / "json").mkdir(parents=True)
    (stdlib / "json" / "__pycache__").mkdir()
    (stdlib / "json" / "__pycache__" / "x.pyc").write_bytes(b"pyc")
    site = stdlib / "site-packages" / "pkg"
    (site / "tests").mkdir(parents=True)
    (site / "tests" / "test_pkg.py").write_text("assert True\n", encoding="utf-8")
    (python_root / "include").mkdir()
    (python_root / "lib" / "libpython3.12.a").write_bytes(b"ar")

    bundler = PyAppBundler(config=ViteConfig(mode="template", paths=PathConfig(root=tmp_path), bundle=True))
    bundler.strip_staged_distribution(python_root)

    assert not (stdlib / "test").exists()
    assert not (stdlib / "idlelib" / "idle_test").exists()
    assert not (stdlib / "json" / "__pycache__").exists()
    assert not (python_root / "include").exists()
    assert not (python_root / "lib" / "libpython3.12.a").exists()
    assert (site / "tests" / "test_pkg.py").is_file()


def test_ssr_worker_binary_placed_next_to_interpreter_per_platform(tmp_path: Path) -> None:
    """The compiled SSR worker lands in python/bin on POSIX and the python/ root on Windows."""
    bundler = PyAppBundler(config=ViteConfig(mode="template", paths=PathConfig(root=tmp_path), bundle=True))
    python_root = tmp_path / "python"
    assert bundler._resolve_ssr_worker_binary_path(python_root, "x86_64-unknown-linux-gnu") == (
        python_root / "bin" / "litestar-ssr-worker"
    )
    assert bundler._resolve_ssr_worker_binary_path(python_root, "x86_64-pc-windows-msvc") == (
        python_root / "litestar-ssr-worker.exe"
    )
