"""Unit tests for transform_asset_urls Vite manifest compliance, CSP nonces, and SRI."""

from litestar_vite.html_transform import transform_asset_urls


def test_transform_asset_urls_injects_recursive_css_and_modulepreload() -> None:
    """Verify transform_asset_urls injects transitive CSS and modulepreload links for script entries."""
    manifest = {
        "resources/main.tsx": {
            "file": "assets/main-abc123.js",
            "src": "resources/main.tsx",
            "isEntry": True,
            "css": ["assets/main-def456.css"],
            "imports": ["_vendor-111.js"],
        },
        "_vendor-111.js": {
            "file": "assets/vendor-111.js",
            "css": ["assets/vendor-111.css"],
            "imports": ["_vendor-222.js"],
        },
        "_vendor-222.js": {"file": "assets/vendor-222.js", "imports": ["_vendor-111.js"]},
    }
    html = '<html><head></head><body><script type="module" src="/resources/main.tsx"></script></body></html>'

    result = transform_asset_urls(html, manifest, asset_url="/static/")

    assert '<link rel="stylesheet" href="/static/assets/main-def456.css" />' in result
    assert '<link rel="stylesheet" href="/static/assets/vendor-111.css" />' in result
    assert '<link rel="modulepreload" crossorigin href="/static/assets/vendor-111.js" />' in result
    assert '<link rel="modulepreload" crossorigin href="/static/assets/vendor-222.js" />' in result
    assert '<script type="module" src="/static/assets/main-abc123.js"></script>' in result


def test_transform_asset_urls_preserves_simple_entry_without_extra_tags() -> None:
    """Verify simple manifest entry without css or imports only rewrites script src."""
    manifest = {"resources/main.tsx": {"file": "assets/main-abc123.js"}}
    html = '<script type="module" src="/resources/main.tsx"></script>'

    result = transform_asset_urls(html, manifest, asset_url="/static/")

    assert result == '<script type="module" src="/static/assets/main-abc123.js"></script>'
