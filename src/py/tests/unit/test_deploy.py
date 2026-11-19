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
    assert config.delete_orphaned is False
    assert config.include_manifest is False
    assert config.include_sourcemaps is False


@pytest.mark.parametrize(
    ("env_value", "expected_delete"), [(None, False), ("false", False), ("0", False), ("true", True), ("1", True)]
)
def test_deploy_config_safe_defaults_and_overrides(
    monkeypatch: pytest.MonkeyPatch, env_value: str | None, expected_delete: bool
) -> None:
    if env_value is None:
        monkeypatch.delenv("VITE_DEPLOY_DELETE", raising=False)
    else:
        monkeypatch.setenv("VITE_DEPLOY_DELETE", env_value)

    config = DeployConfig()

    assert config.delete_orphaned is expected_delete
    assert config.include_manifest is False
    assert config.include_sourcemaps is False

    with_maps = config.with_overrides(include_sourcemaps=True)
    assert with_maps.include_sourcemaps is True
    assert config.include_sourcemaps is False
    assert with_maps.with_overrides().include_sourcemaps is True
    assert with_maps.with_overrides(include_sourcemaps=False).include_sourcemaps is False


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
    (bundle / "assets" / "ignore.txt").write_text("ignore me")
    manifest = bundle / "manifest.json"
    manifest.write_text('{"entry":{"file":"assets/main.js","css":["assets/style.css"]}}')

    default_deployer = ViteDeployer(
        bundle_dir=bundle,
        manifest_name="manifest.json",
        deploy_config=DeployConfig(enabled=True, storage_backend="memory://deploy"),
    )
    opt_in_deployer = ViteDeployer(
        bundle_dir=bundle,
        manifest_name="manifest.json",
        deploy_config=DeployConfig(enabled=True, storage_backend="memory://deploy", include_manifest=True),
    )

    assert set(default_deployer.collect_local_files()) == {"assets/main.js", "assets/style.css"}
    assert set(opt_in_deployer.collect_local_files()) == {"assets/main.js", "assets/style.css", "manifest.json"}


def test_collect_local_files_respects_manifest_in_vite_dir(tmp_path: Path) -> None:
    bundle = tmp_path / "dist"
    bundle.mkdir()
    (bundle / "assets").mkdir()
    (bundle / "assets" / "main.js").write_text("console.log('hi')")
    (bundle / "assets" / "style.css").write_text("body{}")
    (bundle / "assets" / "ignore.txt").write_text("ignore me")
    (bundle / ".vite").mkdir()
    manifest = bundle / ".vite" / "manifest.json"
    manifest.write_text('{"entry":{"file":"assets/main.js","css":["assets/style.css"]}}')

    default_deployer = ViteDeployer(
        bundle_dir=bundle,
        manifest_name="manifest.json",
        deploy_config=DeployConfig(enabled=True, storage_backend="memory://deploy"),
    )
    opt_in_deployer = ViteDeployer(
        bundle_dir=bundle,
        manifest_name="manifest.json",
        deploy_config=DeployConfig(enabled=True, storage_backend="memory://deploy", include_manifest=True),
    )

    assert set(default_deployer.collect_local_files()) == {"assets/main.js", "assets/style.css"}
    assert set(opt_in_deployer.collect_local_files()) == {"assets/main.js", "assets/style.css", ".vite/manifest.json"}


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
        deploy_config=DeployConfig(enabled=True, storage_backend="memory://deploy", delete_orphaned=True),
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


def test_sync_default_preserves_remote_orphans(tmp_path: Path) -> None:
    bundle = tmp_path / "dist"
    bundle.mkdir()
    (bundle / "assets").mkdir()
    (bundle / "assets" / "main.js").write_text("new")
    (bundle / "manifest.json").write_text('{"entry":{"file":"assets/main.js"}}')

    fs = MemoryFileSystem()
    fs.pipe_file("deploy-preserve/unrelated.txt", b"keep")

    deployer = ViteDeployer(
        bundle_dir=bundle,
        manifest_name="manifest.json",
        deploy_config=DeployConfig(enabled=True, storage_backend="memory://deploy-preserve"),
        fs=fs,
        remote_path="deploy-preserve",
    )

    result = deployer.sync()

    assert result.deleted == []
    assert fs.exists("deploy-preserve/unrelated.txt")
    assert fs.exists("deploy-preserve/assets/main.js")
    assert not fs.exists("deploy-preserve/manifest.json")


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
        deploy_config=DeployConfig(enabled=True, storage_backend="memory://deploy", delete_orphaned=True),
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
        {
            "name": "deploy/file2.js",
            "size": "100",
            "LastModified": datetime(2026, 1, 2, tzinfo=timezone.utc),
            "type": "file",
        },
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
            enabled=True, storage_backend="s3://bucket/assets", content_types={".js": "application/javascript"}
        ),
        fs=fs,
        remote_path="deploy",
    )
    with patch.object(fs, "put") as mock_put:
        deployer.sync()
        mock_put.assert_called_once()
        _, kwargs = mock_put.call_args
        assert kwargs.get("ContentType") == "application/javascript"
        assert "content_type" not in kwargs


@pytest.mark.parametrize("storage_backend", ["s3://bucket/prefix", "s3a://bucket/prefix"])
def test_s3_upload_sends_only_contenttype(tmp_path: Path, storage_backend: str) -> None:
    """S3 and S3A uploads forward ContentType only, never lowercase content_type."""
    bundle = tmp_path / "dist"
    bundle.mkdir()
    (bundle / "app.js").write_text("console.log('hi')")
    fs = MemoryFileSystem()
    deployer = ViteDeployer(
        bundle_dir=bundle,
        manifest_name="manifest.json",
        deploy_config=DeployConfig(
            enabled=True, storage_backend=storage_backend, content_types={".js": "application/javascript"}
        ),
        fs=fs,
        remote_path="deploy",
    )
    with patch.object(fs, "put") as mock_put:
        deployer.sync()
        mock_put.assert_called_once()
        _, kwargs = mock_put.call_args
        assert kwargs.get("ContentType") == "application/javascript"
        assert "content_type" not in kwargs


def test_gcs_upload_sends_only_lowercase_content_type(tmp_path: Path) -> None:
    """Non-S3 uploads forward lowercase content_type only, never ContentType."""
    bundle = tmp_path / "dist"
    bundle.mkdir()
    (bundle / "app.js").write_text("console.log('hi')")
    fs = MemoryFileSystem()
    deployer = ViteDeployer(
        bundle_dir=bundle,
        manifest_name="manifest.json",
        deploy_config=DeployConfig(
            enabled=True, storage_backend="gs://bucket/prefix", content_types={".js": "application/javascript"}
        ),
        fs=fs,
        remote_path="deploy",
    )
    with patch.object(fs, "put") as mock_put:
        deployer.sync()
        mock_put.assert_called_once()
        _, kwargs = mock_put.call_args
        assert kwargs.get("content_type") == "application/javascript"
        assert "ContentType" not in kwargs


def test_upload_without_known_content_type_sends_no_kwargs(tmp_path: Path) -> None:
    """Uploads with unconfigured suffix forward neither content type keyword."""
    bundle = tmp_path / "dist"
    bundle.mkdir()
    (bundle / "unknown.xyz").write_text("data")
    fs = MemoryFileSystem()
    deployer = ViteDeployer(
        bundle_dir=bundle,
        manifest_name="manifest.json",
        deploy_config=DeployConfig(
            enabled=True, storage_backend="s3://bucket/prefix", content_types={".js": "application/javascript"}
        ),
        fs=fs,
        remote_path="deploy",
    )
    with patch.object(fs, "put") as mock_put:
        deployer.sync()
        mock_put.assert_called_once()
        _, kwargs = mock_put.call_args
        assert "ContentType" not in kwargs
        assert "content_type" not in kwargs


def test_collect_local_files_includes_sourcemaps(tmp_path: Path) -> None:
    """Sourcemap files are excluded by default and included when include_sourcemaps is True."""
    bundle = tmp_path / "dist"
    bundle.mkdir()
    (bundle / "assets").mkdir()
    (bundle / "assets" / "main.js").write_text("console.log('hi')")
    (bundle / "assets" / "main.js.map").write_text("{}")
    manifest = bundle / "manifest.json"
    manifest.write_text('{"entry":{"file":"assets/main.js"}}')

    default_deployer = ViteDeployer(
        bundle_dir=bundle,
        manifest_name="manifest.json",
        deploy_config=DeployConfig(enabled=True, storage_backend="memory://deploy"),
    )
    opt_in_deployer = ViteDeployer(
        bundle_dir=bundle,
        manifest_name="manifest.json",
        deploy_config=DeployConfig(enabled=True, storage_backend="memory://deploy", include_sourcemaps=True),
    )

    default_files = default_deployer.collect_local_files()
    opt_in_files = opt_in_deployer.collect_local_files()

    assert "assets/main.js" in default_files
    assert "assets/main.js.map" not in default_files
    assert "assets/main.js" in opt_in_files
    assert "assets/main.js.map" in opt_in_files


@pytest.mark.parametrize("manifest_location", ["manifest.json", ".vite/manifest.json", None])
def test_collect_local_files_excludes_metadata_dotfiles_and_sourcemaps_by_default(
    tmp_path: Path, manifest_location: str | None
) -> None:
    """Default deploy file collection excludes dotfiles, metadata files, manifests, and sourcemaps."""
    bundle = tmp_path / "dist"
    bundle.mkdir()
    (bundle / "assets").mkdir()
    (bundle / "assets" / "main.js").write_text("console.log('hi')")
    (bundle / "assets" / "main.js.map").write_text("{}")
    (bundle / "public.js.map").write_text("{}")
    (bundle / "favicon.ico").write_text("ico")
    (bundle / ".env").write_text("SECRET=test-token-placeholder")
    (bundle / ".env.local").write_text("LOCAL=test-token-placeholder")
    (bundle / ".litestar.json").write_text("{}")
    (bundle / "hot").write_text("http://127.0.0.1:5173")
    (bundle / "ssr-manifest.json").write_text("{}")
    (bundle / ".vite").mkdir()
    (bundle / ".vite" / "manifest.json").write_text("{}")

    if manifest_location == "manifest.json":
        (bundle / "manifest.json").write_text('{"entry":{"file":"assets/main.js"}}')
    elif manifest_location == ".vite/manifest.json":
        (bundle / ".vite" / "manifest.json").write_text('{"entry":{"file":"assets/main.js"}}')
    else:
        (bundle / "manifest.json").write_text("{}")

    deployer = ViteDeployer(
        bundle_dir=bundle,
        manifest_name="manifest.json",
        deploy_config=DeployConfig(enabled=True, storage_backend="memory://deploy"),
    )

    assert set(deployer.collect_local_files()) == {"assets/main.js", "favicon.ico"}


@pytest.mark.parametrize(
    ("include_sourcemaps", "include_manifest", "expected_files"),
    [
        (True, False, {"assets/main.js", "assets/main.js.map", "public.js.map", "favicon.ico"}),
        (False, True, {"assets/main.js", "favicon.ico", ".vite/manifest.json"}),
        (True, True, {"assets/main.js", "assets/main.js.map", "public.js.map", "favicon.ico", ".vite/manifest.json"}),
    ],
)
def test_collect_local_files_opt_in_sourcemaps_and_manifest(
    tmp_path: Path, include_sourcemaps: bool, include_manifest: bool, expected_files: set[str]
) -> None:
    """Opt-in flags include sourcemaps and manifest while keeping dotfiles and metadata excluded."""
    bundle = tmp_path / "dist"
    bundle.mkdir()
    (bundle / "assets").mkdir()
    (bundle / "assets" / "main.js").write_text("console.log('hi')")
    (bundle / "assets" / "main.js.map").write_text("{}")
    (bundle / "public.js.map").write_text("{}")
    (bundle / ".hidden.js.map").write_text("{}")
    (bundle / "favicon.ico").write_text("ico")
    (bundle / ".env").write_text("SECRET=test-token-placeholder")
    (bundle / ".litestar.json").write_text("{}")
    (bundle / "hot").write_text("http://127.0.0.1:5173")
    (bundle / "ssr-manifest.json").write_text("{}")
    (bundle / ".vite").mkdir()
    (bundle / ".vite" / "manifest.json").write_text('{"entry":{"file":"assets/main.js"}}')

    deployer = ViteDeployer(
        bundle_dir=bundle,
        manifest_name="manifest.json",
        deploy_config=DeployConfig(
            enabled=True,
            storage_backend="memory://deploy",
            include_sourcemaps=include_sourcemaps,
            include_manifest=include_manifest,
        ),
    )

    assert set(deployer.collect_local_files()) == expected_files


def test_collect_local_files_manifestless_opt_in_sourcemaps(tmp_path: Path) -> None:
    """Manifest-less bundles include sourcemaps on opt-in while excluding dotfiles and metadata."""
    bundle = tmp_path / "dist"
    bundle.mkdir()
    (bundle / "assets").mkdir()
    (bundle / "assets" / "main.js").write_text("console.log('hi')")
    (bundle / "assets" / "main.js.map").write_text("{}")
    (bundle / "public.js.map").write_text("{}")
    (bundle / ".hidden.js.map").write_text("{}")
    (bundle / ".env").write_text("SECRET=test-token-placeholder")
    (bundle / "hot").write_text("http://127.0.0.1:5173")

    deployer = ViteDeployer(
        bundle_dir=bundle,
        manifest_name="manifest.json",
        deploy_config=DeployConfig(enabled=True, storage_backend="memory://deploy", include_sourcemaps=True),
    )

    assert set(deployer.collect_local_files()) == {"assets/main.js", "assets/main.js.map", "public.js.map"}


@pytest.mark.parametrize(
    "bad_entry",
    [
        "../outside.txt",
        "assets/../../outside.txt",
        "\\etc\\passwd",
        "//etc/passwd",
        "/../outside.txt",
        "assets//main.js",
        "",
    ],
)
def test_collect_local_files_rejects_manifest_traversal_entries(tmp_path: Path, bad_entry: str) -> None:
    """Manifest entries containing traversal markers or invalid roots raise ValueError."""
    (tmp_path / "outside.txt").write_text("outside")
    bundle = tmp_path / "dist"
    bundle.mkdir()
    (bundle / "assets").mkdir()
    (bundle / "assets" / "main.js").write_text("console.log('hi')")
    manifest = bundle / "manifest.json"
    escaped_entry = bad_entry.replace("\\", "\\\\")
    manifest.write_text(f'{{"entry":{{"file":"{escaped_entry}"}}}}')

    deployer = ViteDeployer(
        bundle_dir=bundle,
        manifest_name="manifest.json",
        deploy_config=DeployConfig(enabled=True, storage_backend="memory://deploy"),
    )

    with pytest.raises(ValueError, match="resolves outside bundle directory") as exc_info:
        deployer.collect_local_files()

    assert repr(bad_entry) in str(exc_info.value)


def test_collect_local_files_rejects_escaping_manifest_symlink(tmp_path: Path) -> None:
    """Manifest entry resolving via symlink outside bundle_dir raises ValueError."""
    outside = tmp_path / "outside.txt"
    outside.write_text("outside")
    bundle = tmp_path / "dist"
    bundle.mkdir()
    (bundle / "assets").mkdir()
    (bundle / "assets" / "escaped.js").symlink_to(outside)
    (bundle / "manifest.json").write_text('{"entry":{"file":"assets/escaped.js"}}')

    deployer = ViteDeployer(
        bundle_dir=bundle,
        manifest_name="manifest.json",
        deploy_config=DeployConfig(enabled=True, storage_backend="memory://deploy"),
    )

    with pytest.raises(ValueError, match=r"assets/escaped\.js"):
        deployer.collect_local_files()


def test_collect_local_files_rejects_escaping_manifest_file_symlink(tmp_path: Path) -> None:
    """Explicit include_manifest=True rejects a manifest file symlink resolving outside bundle_dir."""
    outside = tmp_path / "outside-manifest.json"
    outside.write_text("{}")
    bundle = tmp_path / "dist"
    bundle.mkdir()
    (bundle / "app.js").write_text("console.log('hi')")
    (bundle / "manifest.json").symlink_to(outside)

    deployer = ViteDeployer(
        bundle_dir=bundle,
        manifest_name="manifest.json",
        deploy_config=DeployConfig(enabled=True, storage_backend="memory://deploy", include_manifest=True),
    )

    with pytest.raises(ValueError, match=r"manifest\.json"):
        deployer.collect_local_files()


def test_collect_local_files_excludes_custom_manifest_by_default(tmp_path: Path) -> None:
    """Custom manifest filenames are excluded by default and included when include_manifest is True."""
    bundle = tmp_path / "dist"
    bundle.mkdir()
    (bundle / "app.js").write_text("console.log('hi')")
    (bundle / "custom-manifest.json").write_text("{}")

    default_deployer = ViteDeployer(
        bundle_dir=bundle,
        manifest_name="custom-manifest.json",
        deploy_config=DeployConfig(enabled=True, storage_backend="memory://deploy"),
    )
    opt_in_deployer = ViteDeployer(
        bundle_dir=bundle,
        manifest_name="custom-manifest.json",
        deploy_config=DeployConfig(enabled=True, storage_backend="memory://deploy", include_manifest=True),
    )

    assert set(default_deployer.collect_local_files()) == {"app.js"}
    assert set(opt_in_deployer.collect_local_files()) == {"app.js", "custom-manifest.json"}


def test_collect_local_files_rejects_escaping_sourcemap_symlink(tmp_path: Path) -> None:
    """Sourcemap symlink resolving outside bundle_dir raises ValueError when include_sourcemaps is True."""
    outside = tmp_path / "outside.map"
    outside.write_text("{}")
    bundle = tmp_path / "dist"
    bundle.mkdir()
    (bundle / "assets").mkdir()
    (bundle / "assets" / "main.js").write_text("console.log('hi')")
    (bundle / "assets" / "main.js.map").symlink_to(outside)
    (bundle / "manifest.json").write_text('{"entry":{"file":"assets/main.js"}}')

    deployer = ViteDeployer(
        bundle_dir=bundle,
        manifest_name="manifest.json",
        deploy_config=DeployConfig(enabled=True, storage_backend="memory://deploy", include_sourcemaps=True),
    )

    with pytest.raises(ValueError, match=r"assets/main\.js\.map"):
        deployer.collect_local_files()


@pytest.mark.parametrize("with_manifest", [True, False])
def test_collect_local_files_excludes_unsafe_unmanaged_symlinks(tmp_path: Path, with_manifest: bool) -> None:
    """Unmanaged symlinks escaping bundle_dir or targeting blocked dotfiles are excluded."""
    outside = tmp_path / "outside.txt"
    outside.write_text("outside")
    bundle = tmp_path / "dist"
    bundle.mkdir()
    (bundle / "assets").mkdir()
    (bundle / "assets" / "main.js").write_text("console.log('hi')")
    (bundle / "favicon.ico").write_text("ico")
    (bundle / ".env").write_text("SECRET=test-token-placeholder")
    (bundle / "outside-link.txt").symlink_to(outside)
    (bundle / "public-link.txt").symlink_to(bundle / ".env")
    (bundle / "broken-link.txt").symlink_to(tmp_path / "nonexistent.txt")
    if with_manifest:
        (bundle / "manifest.json").write_text('{"entry":{"file":"assets/main.js"}}')

    deployer = ViteDeployer(
        bundle_dir=bundle,
        manifest_name="manifest.json",
        deploy_config=DeployConfig(enabled=True, storage_backend="memory://deploy"),
    )

    assert set(deployer.collect_local_files()) == {"assets/main.js", "favicon.ico"}


def test_collect_local_files_includes_public_assets(tmp_path: Path) -> None:
    """Public passthrough assets are indexed while stale manifest-dir files are excluded."""
    bundle = tmp_path / "dist"
    bundle.mkdir()
    (bundle / "assets").mkdir()
    (bundle / "assets" / "app-abc123.js").write_text("console.log('hi')")
    (bundle / "assets" / "app-old999.js").write_text("console.log('old')")
    (bundle / "images").mkdir()
    (bundle / "images" / "logo.png").write_text("png")
    (bundle / "favicon.ico").write_text("ico")
    (bundle / "robots.txt").write_text("User-agent: *")
    (bundle / ".vite").mkdir()
    manifest = bundle / ".vite" / "manifest.json"
    manifest.write_text('{"entry":{"file":"assets/app-abc123.js"}}')

    deployer = ViteDeployer(
        bundle_dir=bundle,
        manifest_name="manifest.json",
        deploy_config=DeployConfig(enabled=True, storage_backend="memory://deploy"),
    )
    files = set(deployer.collect_local_files())

    assert "assets/app-abc123.js" in files
    assert "favicon.ico" in files
    assert "robots.txt" in files
    assert "images/logo.png" in files
    assert "assets/app-old999.js" not in files


def test_sync_does_not_delete_public_assets(tmp_path: Path) -> None:
    """Deploy sync with delete_orphaned=True does not delete remote public assets."""
    bundle = tmp_path / "dist"
    bundle.mkdir()
    (bundle / "assets").mkdir()
    (bundle / "assets" / "app-abc123.js").write_text("console.log('hi')")
    (bundle / "favicon.ico").write_text("ico")
    (bundle / ".vite").mkdir()
    manifest = bundle / ".vite" / "manifest.json"
    manifest.write_text('{"entry":{"file":"assets/app-abc123.js"}}')

    fs = MemoryFileSystem()
    fs.pipe_file("deploy/favicon.ico", b"old_ico")
    deployer = ViteDeployer(
        bundle_dir=bundle,
        manifest_name="manifest.json",
        deploy_config=DeployConfig(enabled=True, storage_backend="memory://deploy", delete_orphaned=True),
        fs=fs,
        remote_path="deploy",
    )
    res = deployer.sync(dry_run=True)
    assert "favicon.ico" not in res.deleted
    assert "favicon.ico" in res.uploaded


def test_stale_hashed_assets_are_still_pruned(tmp_path: Path) -> None:
    """Stale hashed assets in manifest-managed dirs remain scheduled for deletion."""
    bundle = tmp_path / "dist"
    bundle.mkdir()
    (bundle / "assets").mkdir()
    (bundle / "assets" / "app-abc123.js").write_text("console.log('hi')")
    (bundle / ".vite").mkdir()
    manifest = bundle / ".vite" / "manifest.json"
    manifest.write_text('{"entry":{"file":"assets/app-abc123.js"}}')

    fs = MemoryFileSystem()
    fs.pipe_file("deploy/assets/app-old999.js", b"old")
    deployer = ViteDeployer(
        bundle_dir=bundle,
        manifest_name="manifest.json",
        deploy_config=DeployConfig(enabled=True, storage_backend="memory://deploy", delete_orphaned=True),
        fs=fs,
        remote_path="deploy",
    )
    res = deployer.sync(dry_run=True)
    assert "assets/app-old999.js" in res.deleted
