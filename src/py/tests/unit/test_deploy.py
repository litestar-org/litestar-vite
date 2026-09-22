from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

import pytest

try:
    from fsspec.implementations.memory import MemoryFileSystem
except ImportError:  # pragma: no cover - optional dependency
    pytest.skip("fsspec not installed", allow_module_level=True)

from litestar_vite.config import DeployConfig, ViteConfig
from litestar_vite.deploy import FileInfo, ViteDeployer


def test_collect_local_files_caches_manifest_paths(tmp_path: Path) -> None:
    bundle = tmp_path / "dist"
    bundle.mkdir()
    (bundle / "assets").mkdir()
    (bundle / "assets" / "main.js").write_text("console.log('hi')")
    manifest = bundle / "manifest.json"
    manifest.write_text('{"entry":{"file":"assets/main.js"}}')

    deployer = ViteDeployer(
        bundle_dir=bundle,
        manifest_name="manifest.json",
        deploy_config=DeployConfig(enabled=True, storage_backend="memory://deploy"),
    )

    with patch("litestar_vite.deploy.decode_json") as mock_decode:
        mock_decode.return_value = {"entry": {"file": "assets/main.js"}}

        deployer.collect_local_files()
        deployer.collect_local_files()

    mock_decode.assert_called_once()


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


def test_sync_dry_run_detects_nested_remote_orphans(tmp_path: Path) -> None:
    bundle = tmp_path / "dist"
    bundle.mkdir()
    (bundle / "assets").mkdir()
    (bundle / "assets" / "main.js").write_text("new")
    manifest = bundle / "manifest.json"
    manifest.write_text('{"entry":{"file":"assets/main.js"}}')

    fs = MemoryFileSystem()
    fs.pipe_file("deploy/assets/main.js", b"new")
    fs.pipe_file("deploy/assets/nested/old.js", b"old")

    deployer = ViteDeployer(
        bundle_dir=bundle,
        manifest_name="manifest.json",
        deploy_config=DeployConfig(enabled=True, storage_backend="memory://deploy"),
        fs=fs,
        remote_path="deploy",
    )

    result = deployer.sync(dry_run=True)

    assert result.deleted == ["assets/nested/old.js"]


def test_deployer_raises_when_bundle_dir_missing(tmp_path: Path) -> None:
    """Deployer must raise FileNotFoundError if bundle directory does not exist."""
    missing_bundle = tmp_path / "nonexistent"
    with pytest.raises(FileNotFoundError, match=r"Bundle directory .* does not exist"):
        ViteDeployer(
            bundle_dir=missing_bundle,
            manifest_name="manifest.json",
            deploy_config=DeployConfig(enabled=True, storage_backend="memory://deploy"),
        )


def test_deployer_raises_when_bundle_dir_not_a_directory(tmp_path: Path) -> None:
    """Deployer must raise NotADirectoryError if bundle path is a regular file."""
    bundle_file = tmp_path / "file.txt"
    bundle_file.write_text("hello")
    with pytest.raises(NotADirectoryError, match=r"Bundle path .* is not a directory"):
        ViteDeployer(
            bundle_dir=bundle_file,
            manifest_name="manifest.json",
            deploy_config=DeployConfig(enabled=True, storage_backend="memory://deploy"),
        )


def test_sync_refuses_to_wipe_remote_on_empty_bundle(tmp_path: Path) -> None:
    """Sync must abort if local bundle directory has no files and remote files exist."""
    empty_bundle = tmp_path / "empty_dist"
    empty_bundle.mkdir()
    fs = MemoryFileSystem()
    fs.pipe_file("deploy/existing.js", b"console.log('keep me')")
    deployer = ViteDeployer(
        bundle_dir=empty_bundle,
        manifest_name="manifest.json",
        deploy_config=DeployConfig(enabled=True, storage_backend="memory://deploy", delete_orphaned=True),
        fs=fs,
        remote_path="deploy",
    )
    with pytest.raises(ValueError, match=r"Cannot sync bundle: local bundle directory .* produced 0 deployable files"):
        deployer.sync()
    assert fs.exists("deploy/existing.js")


def test_collect_remote_files_handles_none_size_and_datetime_mtime(tmp_path: Path) -> None:
    """Remote files parser must gracefully coerce None sizes and datetime modification times."""
    bundle = tmp_path / "dist"
    bundle.mkdir()
    fs = MemoryFileSystem()
    deployer = ViteDeployer(
        bundle_dir=bundle,
        manifest_name="manifest.json",
        deploy_config=DeployConfig(enabled=True, storage_backend="memory://deploy"),
        fs=fs,
        remote_path="deploy",
    )
    mock_entries = [
        {"name": "deploy/file1.js", "size": None, "mtime": datetime(2026, 1, 1, tzinfo=timezone.utc), "type": "file"},
        {"name": "deploy/file2.js", "size": "100", "LastModified": datetime(2026, 1, 2, tzinfo=timezone.utc), "type": "file"},
    ]
    with patch.object(deployer, "_iter_remote_entries", return_value=mock_entries):
        remote = deployer.collect_remote_files()
        assert remote["file1.js"].size == 0
        assert remote["file1.js"].mtime > 0
        assert remote["file2.js"].size == 100
        assert remote["file2.js"].mtime > 0


def test_sync_passes_content_type_for_s3(tmp_path: Path) -> None:
    """S3 backend uploads must supply capitalized ContentType parameter."""
    bundle = tmp_path / "dist"
    bundle.mkdir()
    (bundle / "app.js").write_text("console.log('hi')")
    fs = MemoryFileSystem()
    deployer = ViteDeployer(
        bundle_dir=bundle,
        manifest_name="manifest.json",
        deploy_config=DeployConfig(
            enabled=True,
            storage_backend="s3://bucket/assets",
            content_types={".js": "application/javascript"},
        ),
        fs=fs,
        remote_path="deploy",
    )
    with patch.object(fs, "put") as mock_put:
        deployer.sync()
        mock_put.assert_called_once()
        _, kwargs = mock_put.call_args
        assert kwargs.get("ContentType") == "application/javascript"


def test_collect_local_files_includes_sourcemaps(tmp_path: Path) -> None:
    """Sourcemap files corresponding to manifest assets must be included in local files."""
    bundle = tmp_path / "dist"
    bundle.mkdir()
    (bundle / "assets").mkdir()
    (bundle / "assets" / "main.js").write_text("console.log('hi')")
    (bundle / "assets" / "main.js.map").write_text("{}")
    manifest = bundle / "manifest.json"
    manifest.write_text('{"entry":{"file":"assets/main.js"}}')
    deployer = ViteDeployer(
        bundle_dir=bundle,
        manifest_name="manifest.json",
        deploy_config=DeployConfig(enabled=True, storage_backend="memory://deploy"),
    )
    files = deployer.collect_local_files()
    assert "assets/main.js" in files
    assert "assets/main.js.map" in files

