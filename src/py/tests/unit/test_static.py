"""Unit tests for static asset immutable Cache-Control headers, metadata blocking, and Granian placement."""

from pathlib import Path

import pytest
from litestar import Litestar
from litestar.testing import create_test_client

from litestar_vite.config import PathConfig, RuntimeConfig, ViteConfig
from litestar_vite.plugin import StaticFilesConfig, StaticPlacement, VitePlugin


def test_static_serving_immutable_cache_headers_and_unhashed_passthrough(tmp_path: Path) -> None:
    """Verify hashed assets receive immutable Cache-Control while unhashed files do not."""
    bundle_dir = tmp_path / "public"
    assets_dir = bundle_dir / "assets"
    assets_dir.mkdir(parents=True)

    (bundle_dir / "manifest.json").write_text(
        '{"src/main.ts": {"file": "assets/index-D8x9kL2p.js", "isEntry": true}}',
        encoding="utf-8",
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
    bundle_dir.mkdir(parents=True)
    (bundle_dir / "manifest.json").write_text('{"src/main.ts": {"file": "assets/main-12345678.js"}}', encoding="utf-8")

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
