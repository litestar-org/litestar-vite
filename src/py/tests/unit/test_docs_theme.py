import runpy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]


def _load_docs_conf() -> dict[str, object]:
    return runpy.run_path(str(ROOT / "docs" / "conf.py"))


# ===== Theme Foundation =====


def test_docs_theme_conf_uses_shibuya_foundation() -> None:
    conf = _load_docs_conf()

    assert conf["html_theme"] == "shibuya"
    assert conf["templates_path"] == ["_templates"]
    assert conf["html_sidebars"] == {"**": []}
    assert conf["html_css_files"] == ["theme.css", "layout.css", "code.css"]
    assert conf["html_js_files"] == ["theme.js"]

    html_theme_options = conf["html_theme_options"]
    assert html_theme_options["accent_color"] == "amber"
    assert html_theme_options["light_logo"] == "_static/logo-light.svg"
    assert html_theme_options["dark_logo"] == "_static/logo-dark.svg"
    assert html_theme_options["logo_target"] == "/litestar-vite/latest/"


def test_docs_theme_foundation_files_exist() -> None:
    assert (ROOT / "docs" / "_templates" / "components" / "copy-page-button.html").exists()
    assert (ROOT / "docs" / "_static" / "theme.css").exists()
    assert (ROOT / "docs" / "_static" / "layout.css").exists()
    assert (ROOT / "docs" / "_static" / "code.css").exists()
    assert (ROOT / "docs" / "_static" / "theme.js").exists()


def test_docs_dependencies_use_shibuya_theme() -> None:
    pyproject = (ROOT / "pyproject.toml").read_text()

    assert '"shibuya"' in pyproject
    assert "litestar-sphinx-theme" not in pyproject


def test_docs_theme_layout_hubs_keep_demo_discovery_visible() -> None:
    index = (ROOT / "docs" / "index.rst").read_text()
    demos = (ROOT / "docs" / "demos.rst").read_text()
    conf = _load_docs_conf()

    assert "landing-badges" in index
    assert ":link: demos" in index
    assert "Featured Demos" in index

    for asset in ("scaffolding.gif", "hmr.gif", "type-generation.gif", "assets-cli.gif", "production-build.gif"):
        assert asset in demos

    docs_group = next(group for group in conf["html_theme_options"]["nav_links"] if group["title"] == "Docs")
    assert any(child["title"] == "Demos" and child["url"] == "demos" for child in docs_group["children"])


def test_docs_theme_code_surface_uses_playground_palette_and_actions() -> None:
    code_css = (ROOT / "docs" / "_static" / "code.css").read_text()
    layout_css = (ROOT / "docs" / "_static" / "layout.css").read_text()
    theme_js = (ROOT / "docs" / "_static" / "theme.js").read_text()
    template = (ROOT / "docs" / "_templates" / "components" / "copy-page-button.html").read_text()

    for needle in (
        "--lv-code-keyword",
        "--lv-code-string",
        "--lv-code-number",
        "--lv-code-comment",
        "--lv-code-definition",
        "#0369a1",
        "#2E7D32",
        "#7dd3fc",
        "#A5D6A7",
    ):
        assert needle in code_css

    for needle in (".admonition", ".copybtn", ".copy-page-wrapper", ".demo-frame"):
        assert needle in layout_css

    for needle in ("div.highlight", "copybtn", "data-language", "lv-code-block"):
        assert needle in theme_js

    for needle in (
        "View Source",
        "Open in ChatGPT",
        "Open in Claude",
        "Open in Gemini",
        "Open in Perplexity",
        "raw.githubusercontent.com",
    ):
        assert needle in template
