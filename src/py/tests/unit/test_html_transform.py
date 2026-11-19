"""Unit tests for HTML transformation helpers, JSON escaping, and asset URL rewriting."""

import json

import pytest

from litestar_vite import html_transform
from litestar_vite.html_transform import escape_json_for_html, transform_asset_urls


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


def test_transform_asset_urls_propagates_csp_nonce_and_sri_integrity() -> None:
    """Verify transform_asset_urls injects CSP nonce and SRI integrity attributes."""
    manifest = {
        "resources/main.tsx": {
            "file": "assets/main-abc123.js",
            "css": ["assets/main-def456.css"],
            "imports": ["_vendor-111.js"],
            "integrity": "sha384-entryhash",
        },
        "_vendor-111.js": {"file": "assets/vendor-111.js", "integrity": "sha384-vendorhash"},
        "resources/extra.css": {"file": "assets/extra-999.css", "integrity": "sha384-csshash"},
    }
    html = (
        '<html><head><link rel="stylesheet" href="/resources/extra.css"></head>'
        '<body><script type="module" src="/resources/main.tsx"></script></body></html>'
    )

    result = transform_asset_urls(html, manifest, asset_url="/static/", csp_nonce='req-"nonce"')

    assert '<link rel="stylesheet" nonce="req-&quot;nonce&quot;" href="/static/assets/main-def456.css" />' in result
    assert (
        '<link rel="modulepreload" crossorigin="anonymous" '
        'integrity="sha384-vendorhash" nonce="req-&quot;nonce&quot;" '
        'href="/static/assets/vendor-111.js" />'
    ) in result
    assert 'integrity="sha384-entryhash"' in result
    assert 'integrity="sha384-csshash"' in result
    assert result.count('nonce="req-&quot;nonce&quot;"') == 4


def test_escape_json_for_html_empty_and_exported() -> None:
    """Verify escape_json_for_html is exported in __all__ and preserves empty input."""
    assert "escape_json_for_html" in html_transform.__all__
    assert escape_json_for_html("") == ""


@pytest.mark.parametrize(
    ("raw_value", "forbidden", "expected_escape"),
    [
        ("</script>", "</script>", r"\u003c/script\u003e"),
        ("<!--<script>", "<!--<script>", r"\u003c!--\u003cscript\u003e"),
        ("a & b", "&", r"\u0026"),
        ("it's", "'", r"\u0027"),
        ("line1\u2028line2", "\u2028", r"\u2028"),
        ("para1\u2029para2", "\u2029", r"\u2029"),
    ],
)
def test_escape_json_for_html_special_characters(raw_value: str, forbidden: str, expected_escape: str) -> None:
    """Verify escape_json_for_html encodes HTML-significant characters and preserves JSON round-trip."""
    payload = json.dumps({"value": raw_value}, ensure_ascii=False)
    escaped = escape_json_for_html(payload)

    assert forbidden not in escaped
    assert expected_escape in escaped
    assert json.loads(escaped) == json.loads(payload)


def test_escape_json_for_html_combined_payload() -> None:
    """Verify escape_json_for_html removes all six unsafe characters in a combined payload."""
    payload = json.dumps({"value": "<!--<script></script> & ' \u2028 \u2029"}, ensure_ascii=False)
    escaped = escape_json_for_html(payload)

    assert "<" not in escaped
    assert ">" not in escaped
    assert "&" not in escaped
    assert "'" not in escaped
    assert "\u2028" not in escaped
    assert "\u2029" not in escaped
    assert r"\u003c!--\u003cscript\u003e\u003c/script\u003e" in escaped
    assert r"\u0026" in escaped
    assert r"\u0027" in escaped
    assert r"\u2028" in escaped
    assert r"\u2029" in escaped
    assert json.loads(escaped) == json.loads(payload)
