from pathlib import Path

import pytest
from litestar.exceptions import ImproperlyConfiguredException

from litestar_vite.config import PathConfig, RuntimeConfig, ViteConfig
from litestar_vite.exceptions import AssetNotFoundError
from litestar_vite.loader import ViteAssetLoader


def test_parse_manifest_when_file_exists(tmp_path: Path) -> None:
    bundle_dir = tmp_path / "public"
    bundle_dir.mkdir()
    manifest = bundle_dir / "manifest.json"
    manifest.write_text('{"main.js": {"file": "assets/main.123456.js"}}')

    config = ViteConfig(paths=PathConfig(bundle_dir=bundle_dir), runtime=RuntimeConfig(dev_mode=False))
    loader = ViteAssetLoader.initialize_loader(config=config)

    assert loader._manifest == {"main.js": {"file": "assets/main.123456.js"}}


def test_parse_manifest_when_file_exists_in_vite_dir(tmp_path: Path) -> None:
    bundle_dir = tmp_path / "public"
    (bundle_dir / ".vite").mkdir(parents=True)
    manifest = bundle_dir / ".vite" / "manifest.json"
    manifest.write_text('{"main.js": {"file": "assets/main.123456.js"}}')

    config = ViteConfig(paths=PathConfig(bundle_dir=bundle_dir), runtime=RuntimeConfig(dev_mode=False))
    loader = ViteAssetLoader.initialize_loader(config=config)

    assert loader._manifest == {"main.js": {"file": "assets/main.123456.js"}}


def test_parse_manifest_when_file_not_exists(tmp_path: Path) -> None:
    bundle_dir = tmp_path / "public"
    # Do not create directory or file

    config = ViteConfig(paths=PathConfig(bundle_dir=bundle_dir), runtime=RuntimeConfig(dev_mode=False))

    # Should not raise
    loader = ViteAssetLoader.initialize_loader(config=config)
    assert loader._manifest == {}


def test_parse_manifest_hot_reload_mode(tmp_path: Path) -> None:
    bundle_dir = tmp_path / "public"
    bundle_dir.mkdir()
    hot_file = bundle_dir / "hot"
    hot_file.write_text("http://localhost:3000")

    config = ViteConfig(paths=PathConfig(bundle_dir=bundle_dir), runtime=RuntimeConfig(dev_mode=True))
    loader = ViteAssetLoader.initialize_loader(config=config)

    assert loader._vite_base_path == "http://localhost:3000"


def test_generate_asset_tags_prod_mode() -> None:
    config = ViteConfig(paths=PathConfig(asset_url="/static/"), runtime=RuntimeConfig(dev_mode=False))
    loader = ViteAssetLoader(config)
    loader._manifest = {
        "main.js": {"file": "assets/main.js", "css": ["assets/main.css"]},
        "vendor.js": {"file": "assets/vendor.js"},
    }

    tags = loader.generate_asset_tags("main.js")
    assert '<link rel="stylesheet" href="/static/assets/main.css" />' in tags
    assert '<script type="module" async="" defer="" src="/static/assets/main.js"></script>' in tags


def test_generate_asset_tags_dev_mode() -> None:
    config = ViteConfig(runtime=RuntimeConfig(dev_mode=True))
    loader = ViteAssetLoader(config)

    tags = loader.generate_asset_tags("main.js")
    # Should point to vite server
    assert 'src="http://127.0.0.1:5173/static/main.js"' in tags


def test_generate_asset_tags_missing_entry() -> None:
    config = ViteConfig(runtime=RuntimeConfig(dev_mode=False))
    loader = ViteAssetLoader(config)
    loader._manifest = {}

    with pytest.raises(ImproperlyConfiguredException):
        loader.generate_asset_tags("missing.js")


def test_get_static_asset_dev_mode() -> None:
    config = ViteConfig(runtime=RuntimeConfig(dev_mode=True))
    loader = ViteAssetLoader(config)
    assert loader.get_static_asset("test.png") == "http://127.0.0.1:5173/static/test.png"


def test_react_hmr_preamble_includes_csp_nonce() -> None:
    config = ViteConfig(runtime=RuntimeConfig(dev_mode=True, is_react=True, csp_nonce="abc123"))
    loader = ViteAssetLoader(config)
    tags = loader.generate_react_hmr_tags()

    assert 'nonce="abc123"' in tags


def test_get_static_asset_prod_mode_found() -> None:
    config = ViteConfig(
        paths=PathConfig(bundle_dir=Path("tests/fixtures"), asset_url="/static/"), runtime=RuntimeConfig(dev_mode=False)
    )
    loader = ViteAssetLoader(config)
    # Mock manifest
    loader._manifest = {"test.png": {"file": "assets/test.hash.png"}}
    assert loader.get_static_asset("test.png") == "/static/assets/test.hash.png"


def test_get_static_asset_prod_mode_not_found() -> None:
    config = ViteConfig(runtime=RuntimeConfig(dev_mode=False))
    loader = ViteAssetLoader(config)
    loader._manifest = {}
    with pytest.raises(AssetNotFoundError):
        loader.get_static_asset("missing.png")


def test_get_static_asset_with_absolute_asset_url() -> None:
    config = ViteConfig(
        paths=PathConfig(asset_url="https://cdn.example.com/"),
        runtime=RuntimeConfig(dev_mode=False),
        base_url="https://app.example.com/",
    )
    loader = ViteAssetLoader(config)
    loader._manifest = {"test.png": {"file": "assets/test.hash.png"}}
    # Production assets are resolved from asset_url
    assert loader.get_static_asset("test.png") == "https://cdn.example.com/assets/test.hash.png"


@pytest.mark.anyio
async def test_async_initialization(tmp_path: Path) -> None:
    """Test async initialization of the asset loader."""
    bundle_dir = tmp_path / "public"
    bundle_dir.mkdir()
    manifest = bundle_dir / "manifest.json"
    manifest.write_text('{"main.js": {"file": "assets/main.123456.js"}}')

    config = ViteConfig(paths=PathConfig(bundle_dir=bundle_dir), runtime=RuntimeConfig(dev_mode=False))
    loader = ViteAssetLoader(config)
    await loader.initialize()

    assert loader._manifest == {"main.js": {"file": "assets/main.123456.js"}}
    assert loader._initialized is True


@pytest.mark.anyio
async def test_async_initialization_manifest_in_vite_dir(tmp_path: Path) -> None:
    """Async initialization should resolve bundle_dir/.vite/manifest.json."""
    bundle_dir = tmp_path / "public"
    (bundle_dir / ".vite").mkdir(parents=True)
    manifest = bundle_dir / ".vite" / "manifest.json"
    manifest.write_text('{"main.js": {"file": "assets/main.123456.js"}}')

    config = ViteConfig(paths=PathConfig(bundle_dir=bundle_dir), runtime=RuntimeConfig(dev_mode=False))
    loader = ViteAssetLoader(config)
    await loader.initialize()

    assert loader._manifest == {"main.js": {"file": "assets/main.123456.js"}}
    assert loader._initialized is True


@pytest.mark.anyio
async def test_async_initialization_dev_mode(tmp_path: Path) -> None:
    """Test async initialization in dev mode reads hot file."""
    bundle_dir = tmp_path / "public"
    bundle_dir.mkdir()
    hot_file = bundle_dir / "hot"
    hot_file.write_text("http://localhost:3000")

    config = ViteConfig(paths=PathConfig(bundle_dir=bundle_dir), runtime=RuntimeConfig(dev_mode=True))
    loader = ViteAssetLoader(config)
    await loader.initialize()

    assert loader._vite_base_path == "http://localhost:3000"
    assert loader._initialized is True
