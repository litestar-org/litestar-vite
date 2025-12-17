from pathlib import Path

import pytest

try:
    from fsspec.implementations.memory import MemoryFileSystem
except ImportError:  # pragma: no cover - optional dependency
    pytest.skip("fsspec not installed", allow_module_level=True)

from litestar_vite.config import DeployConfig, ViteConfig
from litestar_vite.deploy import FileInfo, ViteDeployer


def test_deploy_config_env_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("VITE_DEPLOY_STORAGE", "gcs://bucket/assets")
    monkeypatch.setenv("VITE_DEPLOY_ASSET_URL", "https://cdn.example.com/assets")

    config = DeployConfig()

    assert config.storage_backend == "gcs://bucket/assets"
    assert config.asset_url == "https://cdn.example.com/assets/"
    assert config.delete_orphaned is True


def test_vite_config_deploy_bool_shortcut() -> None:
    config = ViteConfig(deploy=True)

    assert config.deploy_config is not None
    assert config.deploy_config.enabled is True


def test_collect_local_files_respects_manifest(tmp_path: Path) -> None:
    bundle = tmp_path / "dist"
    bundle.mkdir()
    (bundle / "assets").mkdir()
    (bundle / "assets" / "main.js").write_text("console.log('hi')")
    (bundle / "assets" / "style.css").write_text("body{}")
    (bundle / "ignore.txt").write_text("ignore me")
    manifest = bundle / "manifest.json"
    manifest.write_text('{"entry":{"file":"assets/main.js","css":["assets/style.css"]}}')

    deployer = ViteDeployer(
        bundle_dir=bundle,
        manifest_name="manifest.json",
        deploy_config=DeployConfig(enabled=True, storage_backend="memory://deploy"),
    )

    files = deployer.collect_local_files()

    assert set(files) == {"assets/main.js", "assets/style.css", "manifest.json"}


def test_collect_local_files_respects_manifest_in_vite_dir(tmp_path: Path) -> None:
    bundle = tmp_path / "dist"
    bundle.mkdir()
    (bundle / "assets").mkdir()
    (bundle / "assets" / "main.js").write_text("console.log('hi')")
    (bundle / "assets" / "style.css").write_text("body{}")
    (bundle / "ignore.txt").write_text("ignore me")
    (bundle / ".vite").mkdir()
    manifest = bundle / ".vite" / "manifest.json"
    manifest.write_text('{"entry":{"file":"assets/main.js","css":["assets/style.css"]}}')

    deployer = ViteDeployer(
        bundle_dir=bundle,
        manifest_name="manifest.json",
        deploy_config=DeployConfig(enabled=True, storage_backend="memory://deploy"),
    )

    files = deployer.collect_local_files()

    assert set(files) == {"assets/main.js", "assets/style.css", ".vite/manifest.json"}


def test_collect_local_files_without_manifest(tmp_path: Path) -> None:
    bundle = tmp_path / "dist"
    bundle.mkdir()
    (bundle / "app.js").write_text("console.log('ok')")
    (bundle / "index.html").write_text("<html></html>")

    deployer = ViteDeployer(
        bundle_dir=bundle,
        manifest_name="manifest.json",
        deploy_config=DeployConfig(enabled=True, storage_backend="memory://deploy"),
    )

    files = deployer.collect_local_files()

    assert "app.js" in files
    assert "index.html" in files


def test_compute_diff_detects_new_and_deleted() -> None:
    local = {"a.js": FileInfo(path="a.js", size=10, mtime=0.0), "b.js": FileInfo(path="b.js", size=20, mtime=0.0)}
    remote = {"b.js": FileInfo(path="b.js", size=10, mtime=0.0), "c.js": FileInfo(path="c.js", size=5, mtime=0.0)}

    plan = ViteDeployer.compute_diff(local, remote, delete_orphaned=True)

    assert set(plan.to_upload) == {"a.js", "b.js"}
    assert set(plan.to_delete) == {"c.js"}


def test_sync_memory_filesystem(tmp_path: Path) -> None:
    bundle = tmp_path / "dist"
    bundle.mkdir()
    (bundle / "assets").mkdir()
    (bundle / "assets" / "main.js").write_text("new")
    manifest = bundle / "manifest.json"
    manifest.write_text('{"entry":{"file":"assets/main.js"}}')

    fs = MemoryFileSystem()
    fs.pipe_file("deploy/old.js", b"old")

    deployer = ViteDeployer(
        bundle_dir=bundle,
        manifest_name="manifest.json",
        deploy_config=DeployConfig(enabled=True, storage_backend="memory://deploy"),
        fs=fs,
        remote_path="deploy",
    )

    actions: list[str] = []

    def _progress(action: str, path: str) -> None:
        actions.append(f"{action}:{path}")

    result = deployer.sync(on_progress=_progress)

    assert fs.exists("deploy/assets/main.js")
    assert not fs.exists("deploy/old.js")
    assert "upload:assets/main.js" in actions
    assert "delete:old.js" in actions
    assert result.dry_run is False
