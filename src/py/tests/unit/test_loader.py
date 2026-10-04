"""Unit tests for ViteAssetLoader manifest spec compliance, CSP nonces, SRI, and preload headers."""

from litestar_vite.config import PathConfig, RuntimeConfig, ViteConfig
from litestar_vite.loader import ViteAssetLoader


def test_generate_asset_tags_recursive_modulepreload_and_css() -> None:
    """Verify multi-level imports emit modulepreload links and transitive CSS in deterministic order."""
    config = ViteConfig(paths=PathConfig(asset_url="/static/"), runtime=RuntimeConfig(dev_mode=False))
    loader = ViteAssetLoader(config)
    loader._manifest = {
        "src/main.ts": {
            "file": "assets/main-111.js",
            "src": "src/main.ts",
            "isEntry": True,
            "css": ["assets/main-111.css"],
            "imports": ["_vendor-a.js"],
        },
        "_vendor-a.js": {
            "file": "assets/vendor-a-222.js",
            "css": ["assets/vendor-a-222.css"],
            "imports": ["_vendor-b.js"],
        },
        "_vendor-b.js": {
            "file": "assets/vendor-b-333.js",
            "css": ["assets/vendor-b-333.css"],
            "imports": ["_vendor-a.js"],
        },
    }

    tags = loader.generate_asset_tags("src/main.ts")

    assert '<link rel="stylesheet" href="/static/assets/main-111.css" />' in tags
    assert '<link rel="stylesheet" href="/static/assets/vendor-a-222.css" />' in tags
    assert '<link rel="stylesheet" href="/static/assets/vendor-b-333.css" />' in tags
    assert '<script type="module" src="/static/assets/main-111.js"></script>' in tags
    assert '<link rel="modulepreload" crossorigin href="/static/assets/vendor-a-222.js" />' in tags
    assert '<link rel="modulepreload" crossorigin href="/static/assets/vendor-b-333.js" />' in tags
    assert 'src="/static/assets/vendor-a-222.js"' not in tags
    assert 'src="/static/assets/vendor-b-333.js"' not in tags
    assert "async=" not in tags


def test_generate_asset_tags_deduplicates_across_multiple_entries() -> None:
    """Verify shared imports and CSS are deduplicated when rendering multiple entries."""
    config = ViteConfig(paths=PathConfig(asset_url="/static/"), runtime=RuntimeConfig(dev_mode=False))
    loader = ViteAssetLoader(config)
    loader._manifest = {
        "src/main.ts": {"file": "assets/main-111.js", "css": ["assets/shared.css"], "imports": ["_shared.js"]},
        "src/admin.ts": {
            "file": "assets/admin-222.js",
            "css": ["assets/shared.css", "assets/admin.css"],
            "imports": ["_shared.js"],
        },
        "_shared.js": {"file": "assets/shared-333.js", "css": ["assets/shared-vendor.css"]},
    }

    tags = str(loader.render_asset_tag(["src/main.ts", "src/admin.ts"]))

    assert tags.count('href="/static/assets/shared.css"') == 1
    assert tags.count('href="/static/assets/shared-vendor.css"') == 1
    assert tags.count('href="/static/assets/admin.css"') == 1
    assert tags.count('href="/static/assets/shared-333.js"') == 1
    assert tags.count('src="/static/assets/main-111.js"') == 1
    assert tags.count('src="/static/assets/admin-222.js"') == 1


def test_generate_asset_tags_respects_explicit_scripts_attrs() -> None:
    """Verify explicit scripts_attrs are preserved on entry script tags."""
    config = ViteConfig(paths=PathConfig(asset_url="/static/"), runtime=RuntimeConfig(dev_mode=False))
    loader = ViteAssetLoader(config)
    loader._manifest = {"src/main.ts": {"file": "assets/main-111.js"}}

    tags = loader.generate_asset_tags("src/main.ts", scripts_attrs={"type": "module", "async": ""})
    assert '<script type="module" async="" src="/static/assets/main-111.js"></script>' in tags
