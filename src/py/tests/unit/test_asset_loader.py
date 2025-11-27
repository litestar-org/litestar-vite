from pathlib import Path

import pytest
from litestar.exceptions import ImproperlyConfiguredException

from litestar_vite.config import ViteConfig
from litestar_vite.exceptions import AssetNotFoundError
from litestar_vite.loader import ViteAssetLoader


@pytest.fixture(autouse=True)
def reset_singleton() -> None:
    from litestar_vite.loader import SingletonMeta

    SingletonMeta._instances.clear()
    yield
    SingletonMeta._instances.clear()


def test_parse_manifest_when_file_exists(tmp_path: Path) -> None:
    bundle_dir = tmp_path / "public"
    bundle_dir.mkdir()
    manifest = bundle_dir / "manifest.json"
    manifest.write_text('{"main.js": {"file": "assets/main.123456.js"}}')

    config = ViteConfig(bundle_dir=str(bundle_dir), hot_reload=False, dev_mode=False)
    loader = ViteAssetLoader.initialize_loader(config=config)

    assert loader._manifest == {"main.js": {"file": "assets/main.123456.js"}}


def test_parse_manifest_when_file_not_exists(tmp_path: Path) -> None:
    bundle_dir = tmp_path / "public"
    # Do not create directory or file

    config = ViteConfig(bundle_dir=str(bundle_dir), hot_reload=False, dev_mode=False)

    # Should not raise
    loader = ViteAssetLoader.initialize_loader(config=config)
    assert loader._manifest == {}


def test_parse_manifest_hot_reload_mode(tmp_path: Path) -> None:
    bundle_dir = tmp_path / "public"
    bundle_dir.mkdir()
    hot_file = bundle_dir / "hot"
    hot_file.write_text("http://localhost:3000")

    config = ViteConfig(bundle_dir=str(bundle_dir), hot_reload=True, dev_mode=True)
    loader = ViteAssetLoader.initialize_loader(config=config)

    assert loader._vite_base_path == "http://localhost:3000"


def test_generate_asset_tags_prod_mode() -> None:
    config = ViteConfig(hot_reload=False, dev_mode=False, asset_url="/static/")
    loader = ViteAssetLoader(config)
    loader._manifest = {
        "main.js": {"file": "assets/main.js", "css": ["assets/main.css"]},
        "vendor.js": {"file": "assets/vendor.js"},
    }

    tags = loader.generate_asset_tags("main.js")
    assert '<link rel="stylesheet" href="/static/assets/main.css" />' in tags
    assert '<script type="module" async="" defer="" src="/static/assets/main.js"></script>' in tags


def test_generate_asset_tags_dev_mode() -> None:
    config = ViteConfig(hot_reload=True, dev_mode=True)
    loader = ViteAssetLoader(config)

    tags = loader.generate_asset_tags("main.js")
    # Should point to vite server
    assert 'src="http://localhost:5173/static/main.js"' in tags


def test_generate_asset_tags_missing_entry() -> None:
    config = ViteConfig(hot_reload=False, dev_mode=False)
    loader = ViteAssetLoader(config)
    loader._manifest = {}

    with pytest.raises(ImproperlyConfiguredException):
        loader.generate_asset_tags("missing.js")


def test_get_static_asset_dev_mode() -> None:
    config = ViteConfig(dev_mode=True, hot_reload=True)
    loader = ViteAssetLoader(config)
    assert loader.get_static_asset("test.png") == "http://localhost:5173/static/test.png"


def test_get_static_asset_prod_mode_found() -> None:
    config = ViteConfig(dev_mode=False, hot_reload=False, bundle_dir="tests/fixtures", asset_url="/static/")
    loader = ViteAssetLoader(config)
    # Mock manifest
    loader._manifest = {"test.png": {"file": "assets/test.hash.png"}}
    assert loader.get_static_asset("test.png") == "/static/assets/test.hash.png"


def test_get_static_asset_prod_mode_not_found() -> None:
    config = ViteConfig(dev_mode=False)
    loader = ViteAssetLoader(config)
    loader._manifest = {}
    with pytest.raises(AssetNotFoundError):
        loader.get_static_asset("missing.png")


def test_get_static_asset_with_base_url() -> None:
    config = ViteConfig(dev_mode=False, hot_reload=False, base_url="https://cdn.example.com/", asset_url="/static/")
    loader = ViteAssetLoader(config)
    loader._manifest = {"test.png": {"file": "assets/test.hash.png"}}
    # base_url overrides asset_url for the base part
    assert loader.get_static_asset("test.png") == "https://cdn.example.com/assets/test.hash.png"
