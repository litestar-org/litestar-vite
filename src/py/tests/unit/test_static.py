"""Unit tests for static asset immutable Cache-Control headers, metadata blocking, and Granian placement."""

from pathlib import Path

import pytest
from litestar import Litestar
from litestar.testing import create_test_client

from litestar_vite.config import PathConfig, RuntimeConfig, ViteConfig
from litestar_vite.plugin import StaticFilesConfig, StaticPlacement, VitePlugin
from litestar_vite.plugin._static import is_blocked_static_metadata_path, is_hashed_asset_path


def test_static_serving_immutable_cache_headers_and_unhashed_passthrough(tmp_path: Path) -> None:
    """Verify hashed assets receive immutable Cache-Control while unhashed files do not."""
    bundle_dir = tmp_path / "public"
    assets_dir = bundle_dir / "assets"
    assets_dir.mkdir(parents=True)

    (bundle_dir / "manifest.json").write_text(
        '{"src/main.ts": {"file": "assets/index-D8x9kL2p.js", "isEntry": true}}', encoding="utf-8"
    )
    (assets_dir / "index-D8x9kL2p.js").write_text("console.log('hashed');", encoding="utf-8")
    (bundle_dir / "favicon.ico").write_text("icon-bytes", encoding="utf-8")

    plugin = VitePlugin(
        config=ViteConfig(
            mode="template",
            paths=PathConfig(root=tmp_path, bundle_dir=bundle_dir, asset_url="/static/"),
            runtime=RuntimeConfig(dev_mode=False, immutable_cache_headers=True),
        )
    )

    with create_test_client(route_handlers=[], plugins=[plugin]) as client:
        hashed_resp = client.get("/static/assets/index-D8x9kL2p.js")
        assert hashed_resp.status_code == 200
        assert hashed_resp.headers.get("cache-control") == "public, max-age=31536000, immutable"

        unhashed_resp = client.get("/static/favicon.ico")
        assert unhashed_resp.status_code == 200
        assert "immutable" not in (unhashed_resp.headers.get("cache-control") or "")


def test_static_serving_can_disable_immutable_cache_headers(tmp_path: Path) -> None:
    """Verify immutable_cache_headers=False disables automatic immutable Cache-Control header."""
    bundle_dir = tmp_path / "public"
    assets_dir = bundle_dir / "assets"
    assets_dir.mkdir(parents=True)
    (bundle_dir / "manifest.json").write_text("{}", encoding="utf-8")
    (assets_dir / "index-D8x9kL2p.js").write_text("console.log('hashed');", encoding="utf-8")

    plugin = VitePlugin(
        config=ViteConfig(
            mode="template",
            paths=PathConfig(root=tmp_path, bundle_dir=bundle_dir, asset_url="/static/"),
            runtime=RuntimeConfig(dev_mode=False, immutable_cache_headers=False),
        )
    )

    with create_test_client(route_handlers=[], plugins=[plugin]) as client:
        hashed_resp = client.get("/static/assets/index-D8x9kL2p.js")
        assert hashed_resp.status_code == 200
        assert "immutable" not in (hashed_resp.headers.get("cache-control") or "")


@pytest.mark.parametrize(
    "blocked_path",
    [
        "/static/manifest.json",
        "/static/.vite/manifest.json",
        "/static/ssr-manifest.json",
        "/static/.vite/ssr-manifest.json",
        "/static/.litestar.json",
        "/static/hot",
    ],
)
def test_static_serving_blocks_internal_metadata_files(tmp_path: Path, blocked_path: str) -> None:
    """Verify internal build metadata files under bundle_dir return 404 Not Found over HTTP."""
    bundle_dir = tmp_path / "public"
    vite_dir = bundle_dir / ".vite"
    vite_dir.mkdir(parents=True)

    (bundle_dir / "manifest.json").write_text("{}", encoding="utf-8")
    (vite_dir / "manifest.json").write_text("{}", encoding="utf-8")
    (bundle_dir / "ssr-manifest.json").write_text("{}", encoding="utf-8")
    (vite_dir / "ssr-manifest.json").write_text("{}", encoding="utf-8")
    (bundle_dir / ".litestar.json").write_text("{}", encoding="utf-8")
    (bundle_dir / "hot").write_text("http://127.0.0.1:5173", encoding="utf-8")

    plugin = VitePlugin(
        config=ViteConfig(
            mode="template",
            paths=PathConfig(root=tmp_path, bundle_dir=bundle_dir, asset_url="/static/"),
            runtime=RuntimeConfig(dev_mode=False),
        )
    )

    with create_test_client(route_handlers=[], plugins=[plugin]) as client:
        response = client.get(blocked_path)
        assert response.status_code == 404


def test_static_placement_native_preserved_without_user_asgi_overrides(tmp_path: Path) -> None:
    """Verify StaticPlacement.NATIVE is preserved on StaticServerConfig even after app init."""
    bundle_dir = tmp_path / "public"
    assets_dir = bundle_dir / "assets"
    assets_dir.mkdir(parents=True)
    (bundle_dir / "manifest.json").write_text('{"src/main.ts": {"file": "assets/main-12345678.js"}}', encoding="utf-8")
    (assets_dir / "main-12345678.js").write_text("console.log('ok');", encoding="utf-8")

    static_cfg = StaticFilesConfig(tags=["assets"])
    plugin = VitePlugin(
        config=ViteConfig(
            mode="template",
            paths=PathConfig(root=tmp_path, bundle_dir=bundle_dir, asset_url="/static/"),
            runtime=RuntimeConfig(dev_mode=False),
        ),
        static_files_config=static_cfg,
    )
    _ = Litestar(route_handlers=[], plugins=[plugin])

    assert static_cfg.has_asgi_overrides() is False
    server_cfg = plugin.get_static_server_config()
    assert server_cfg.placement is StaticPlacement.NATIVE
    assert len(server_cfg.mounts) == 1
    assert server_cfg.mounts[0].route == "/static/assets"
    assert server_cfg.mounts[0].directory == assets_dir.resolve()


@pytest.mark.parametrize(
    ("file_path", "expected"),
    [
        ("/srv/public/assets/index-D8x9kL2p.js", True),
        ("/srv/public/assets/index-D8x9kL2p.js.map", True),
        ("/srv/public/assets/vendor.Bq1X9zKf.css", True),
        ("/srv/public/assets/chunk-a1b2c3d4e5f6a7b8.js", True),
        ("/srv/public/assets/nested/logo-CkXp9Q2z.svg", True),
        ("/srv/public/icon-192x192.png", False),
        ("/srv/public/assets/icon-192x192.png", False),
        ("/srv/public/vendor.ReactDOM.js", False),
        ("/srv/public/favicon.ico", False),
        ("/srv/public/assets/index.js", False),
        ("/srv/public/robots.txt", False),
    ],
)
def test_is_hashed_asset_path_requires_assets_dir_and_hash_segment(file_path: str, expected: bool) -> None:
    """Only Rollup-hashed files under the Vite assets directory are treated as immutable."""
    assert is_hashed_asset_path(file_path) is expected


def test_is_blocked_static_metadata_path_is_case_insensitive() -> None:
    """Metadata blocking matches regardless of path casing or separators."""
    assert is_blocked_static_metadata_path("Manifest.JSON") is True
    assert is_blocked_static_metadata_path(".VITE\\manifest.json") is True
    assert is_blocked_static_metadata_path("nested/.Vite/manifest.json") is True
    assert is_blocked_static_metadata_path("assets/app-D8x9kL2p.js") is False


@pytest.mark.parametrize(
    ("probe_path", "extra_blocked"),
    [
        (".env", ()),
        (".env.local", ()),
        (".git/config", ()),
        (".vite/other.json", ()),
        ("sub/.hidden", ()),
        ("sub/.secret", ()),
        ("%2eenv", ()),
        ("%252eenv", ()),
        ("%2evite/manifest.json", ()),
        (".vite/%6danifest.json", ()),
        ("assets/../manifest.json", ()),
        ("./manifest.json", ()),
        ("assets/..%2fmanifest.json", ()),
        ("nested\\.vite\\manifest.json", ()),
        ("../outside", ()),
        ("..", ()),
        ("custom-manifest.json", ("custom-manifest.json",)),
        ("./custom-manifest.json", ("custom-manifest.json",)),
        ("%63ustom-manifest.json", ("custom-manifest.json",)),
        ("vite.hot", ("vite.hot",)),
        ("assets/../vite.hot", ("vite.hot",)),
    ],
)
def test_is_blocked_static_metadata_path_blocks_encoded_normalized_and_dotfiles(
    probe_path: str, extra_blocked: tuple[str, ...]
) -> None:
    """Encoded, normalized, dotfile, traversal, and custom metadata paths are blocked."""
    assert is_blocked_static_metadata_path(probe_path, extra_blocked) is True


@pytest.mark.parametrize(
    "allowed_path",
    [
        "assets/index-D8x9kL2p.js",
        "favicon.ico",
        "images/logo.v2.png",
        "fonts/inter.v2.woff2",
        "nested/assets/chunk.css",
        "",
        "/",
        ".",
    ],
)
def test_is_blocked_static_metadata_path_allows_normal_assets(allowed_path: str) -> None:
    """Normal production asset paths remain allowed."""
    assert is_blocked_static_metadata_path(allowed_path) is False


@pytest.mark.parametrize(
    "blocked_url",
    [
        "/static/.env",
        "/static/.env.local",
        "/static/.git/config",
        "/static/.vite/other.json",
        "/static/sub/.secret",
        "/static/%2eenv",
        "/static/%252eenv",
        "/static/%2evite/manifest.json",
        "/static/.vite/%6danifest.json",
        "/static/assets/../manifest.json",
        "/static/./manifest.json",
        "/static/assets/..%2fmanifest.json",
        "/static/nested%5c.vite%5cmanifest.json",
        "/static/custom-manifest.json",
        "/static/vite.hot",
    ],
)
def test_static_serving_blocks_encoded_normalized_and_dotfile_http_requests(tmp_path: Path, blocked_url: str) -> None:
    """Encoded, normalized, dotfile, and custom metadata HTTP requests return 404."""
    bundle_dir = tmp_path / "public"
    (bundle_dir / ".vite").mkdir(parents=True)
    (bundle_dir / ".git").mkdir(parents=True)
    (bundle_dir / "sub").mkdir(parents=True)
    (bundle_dir / "assets").mkdir(parents=True)
    (bundle_dir / "nested" / ".vite").mkdir(parents=True)

    (bundle_dir / ".env").write_text("SECRET=1", encoding="utf-8")
    (bundle_dir / ".env.local").write_text("SECRET=2", encoding="utf-8")
    (bundle_dir / ".git" / "config").write_text("[core]", encoding="utf-8")
    (bundle_dir / ".vite" / "manifest.json").write_text("{}", encoding="utf-8")
    (bundle_dir / ".vite" / "other.json").write_text("{}", encoding="utf-8")
    (bundle_dir / "sub" / ".secret").write_text("hidden", encoding="utf-8")
    (bundle_dir / "manifest.json").write_text("{}", encoding="utf-8")
    (bundle_dir / "custom-manifest.json").write_text("{}", encoding="utf-8")
    (bundle_dir / "vite.hot").write_text("http://127.0.0.1:5173", encoding="utf-8")
    (bundle_dir / "nested" / ".vite" / "manifest.json").write_text("{}", encoding="utf-8")
    (bundle_dir / "assets" / "index-D8x9kL2p.js").write_text("console.log('ok');", encoding="utf-8")

    plugin = VitePlugin(
        config=ViteConfig(
            mode="template",
            paths=PathConfig(
                root=tmp_path,
                bundle_dir=bundle_dir,
                asset_url="/static/",
                manifest_name="custom-manifest.json",
                hot_file="vite.hot",
            ),
            runtime=RuntimeConfig(dev_mode=False),
        )
    )

    with create_test_client(route_handlers=[], plugins=[plugin]) as client:
        response = client.get(blocked_url)
        assert response.status_code == 404


@pytest.mark.parametrize(
    ("rel_path", "body"),
    [
        ("assets/index-D8x9kL2p.js", "console.log('ok');"),
        ("favicon.ico", "icon-bytes"),
        ("images/logo.v2.png", "png-bytes"),
        ("fonts/inter.v2.woff2", "font-bytes"),
        ("nested/assets/chunk.css", "body{}"),
    ],
)
def test_static_serving_allows_normal_asset_http_requests(tmp_path: Path, rel_path: str, body: str) -> None:
    """Normal production asset HTTP requests return 200."""
    bundle_dir = tmp_path / "public"
    target = bundle_dir / rel_path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(body, encoding="utf-8")

    plugin = VitePlugin(
        config=ViteConfig(
            mode="template",
            paths=PathConfig(root=tmp_path, bundle_dir=bundle_dir, asset_url="/static/"),
            runtime=RuntimeConfig(dev_mode=False),
        )
    )

    with create_test_client(route_handlers=[], plugins=[plugin]) as client:
        response = client.get(f"/static/{rel_path}")
        assert response.status_code == 200
        assert response.text == body


def test_static_placement_native_clean_bundle_mounts_bundle_dir(tmp_path: Path) -> None:
    """Manifest-less clean builds without dotfiles mount bundle_dir natively."""
    bundle_dir = tmp_path / "public"
    bundle_dir.mkdir(parents=True)
    (bundle_dir / "index.html").write_text("<!doctype html>", encoding="utf-8")
    (bundle_dir / "app.js").write_text("console.log('clean');", encoding="utf-8")

    plugin = VitePlugin(
        config=ViteConfig(
            mode="template",
            paths=PathConfig(root=tmp_path, bundle_dir=bundle_dir, asset_url="/static/"),
            runtime=RuntimeConfig(dev_mode=False),
        )
    )

    server_cfg = plugin.get_static_server_config()
    assert server_cfg.placement is StaticPlacement.NATIVE
    assert server_cfg.reason is None
    assert len(server_cfg.mounts) == 1
    assert server_cfg.mounts[0].route == "/static"
    assert server_cfg.mounts[0].directory == bundle_dir.resolve()


@pytest.mark.parametrize("manifest_rel", ["manifest.json", ".vite/manifest.json"])
def test_static_placement_native_submounts_clean_assets_dir(tmp_path: Path, manifest_rel: str) -> None:
    """Standard Vite builds with metadata mount the clean assets subdirectory natively."""
    bundle_dir = tmp_path / "public"
    manifest_file = bundle_dir / manifest_rel
    manifest_file.parent.mkdir(parents=True, exist_ok=True)
    manifest_file.write_text('{"src/main.ts": {"file": "assets/main-12345678.js"}}', encoding="utf-8")
    assets_dir = bundle_dir / "assets"
    assets_dir.mkdir(parents=True, exist_ok=True)
    (assets_dir / "main-12345678.js").write_text("console.log('submount');", encoding="utf-8")
    (bundle_dir / "favicon.ico").write_text("icon", encoding="utf-8")

    plugin = VitePlugin(
        config=ViteConfig(
            mode="template",
            paths=PathConfig(root=tmp_path, bundle_dir=bundle_dir, asset_url="/static/"),
            runtime=RuntimeConfig(dev_mode=False),
        )
    )

    server_cfg = plugin.get_static_server_config()
    assert server_cfg.placement is StaticPlacement.NATIVE
    assert server_cfg.reason is None
    assert len(server_cfg.mounts) == 1
    assert server_cfg.mounts[0].route == "/static/assets"
    assert server_cfg.mounts[0].directory == assets_dir.resolve()


@pytest.mark.parametrize(
    "scenario",
    [
        "manifest_no_assets",
        "manifest_empty_assets",
        "assets_dotfile",
        "assets_nested_manifest",
        "assets_symlink_to_dotfile",
        "assets_symlink_outside",
        "assets_dir_symlink_outside",
        "assets_symlinked_subdir_with_dotfile",
        "index_with_dotfile",
    ],
)
def test_static_placement_falls_back_to_asgi_for_unsafe_or_missing_assets(tmp_path: Path, scenario: str) -> None:
    """Bundles with metadata/dotfiles and no clean non-empty assets/ fall back to ASGI."""
    bundle_dir = tmp_path / "public"
    bundle_dir.mkdir(parents=True)
    manifest_name = "manifest.json"

    if scenario == "manifest_no_assets":
        (bundle_dir / "manifest.json").write_text("{}", encoding="utf-8")
    elif scenario == "manifest_empty_assets":
        (bundle_dir / "manifest.json").write_text("{}", encoding="utf-8")
        (bundle_dir / "assets").mkdir()
    elif scenario == "assets_dotfile":
        (bundle_dir / "manifest.json").write_text("{}", encoding="utf-8")
        assets_dir = bundle_dir / "assets"
        assets_dir.mkdir()
        (assets_dir / "main-12345678.js").write_text("console.log('ok');", encoding="utf-8")
        (assets_dir / ".env").write_text("SECRET=1", encoding="utf-8")
    elif scenario == "assets_nested_manifest":
        manifest_name = "assets/custom-manifest.json"
        assets_dir = bundle_dir / "assets"
        assets_dir.mkdir()
        (assets_dir / "custom-manifest.json").write_text("{}", encoding="utf-8")
        (assets_dir / "main-12345678.js").write_text("console.log('ok');", encoding="utf-8")
    elif scenario == "assets_symlink_to_dotfile":
        (bundle_dir / "manifest.json").write_text("{}", encoding="utf-8")
        secret_file = bundle_dir / ".env"
        secret_file.write_text("SECRET=1", encoding="utf-8")
        assets_dir = bundle_dir / "assets"
        assets_dir.mkdir()
        (assets_dir / "main-12345678.js").write_text("console.log('ok');", encoding="utf-8")
        (assets_dir / "leak.txt").symlink_to(secret_file)
    elif scenario == "assets_symlink_outside":
        (bundle_dir / "manifest.json").write_text("{}", encoding="utf-8")
        outside_file = tmp_path / "outside.js"
        outside_file.write_text("console.log('outside');", encoding="utf-8")
        assets_dir = bundle_dir / "assets"
        assets_dir.mkdir()
        (assets_dir / "main-12345678.js").write_text("console.log('ok');", encoding="utf-8")
        (assets_dir / "escape.js").symlink_to(outside_file)
    elif scenario == "assets_dir_symlink_outside":
        (bundle_dir / "manifest.json").write_text("{}", encoding="utf-8")
        outside_dir = tmp_path / "outside_assets"
        outside_dir.mkdir()
        (outside_dir / "main-12345678.js").write_text("console.log('outside');", encoding="utf-8")
        (bundle_dir / "assets").symlink_to(outside_dir)
    elif scenario == "assets_symlinked_subdir_with_dotfile":
        (bundle_dir / "manifest.json").write_text("{}", encoding="utf-8")
        sub_dir = bundle_dir / "sub"
        sub_dir.mkdir()
        (sub_dir / ".env").write_text("SECRET=1", encoding="utf-8")
        assets_dir = bundle_dir / "assets"
        assets_dir.mkdir()
        (assets_dir / "main-12345678.js").write_text("console.log('ok');", encoding="utf-8")
        (assets_dir / "link").symlink_to(sub_dir, target_is_directory=True)
    elif scenario == "index_with_dotfile":
        (bundle_dir / "index.html").write_text("<!doctype html>", encoding="utf-8")
        (bundle_dir / ".env").write_text("SECRET=1", encoding="utf-8")

    plugin = VitePlugin(
        config=ViteConfig(
            mode="template",
            paths=PathConfig(root=tmp_path, bundle_dir=bundle_dir, asset_url="/static/", manifest_name=manifest_name),
            runtime=RuntimeConfig(dev_mode=False),
        )
    )

    server_cfg = plugin.get_static_server_config()
    assert server_cfg.placement is StaticPlacement.ASGI
    assert server_cfg.mounts == ()
    assert server_cfg.reason is not None
    assert server_cfg.reason.strip() != ""
