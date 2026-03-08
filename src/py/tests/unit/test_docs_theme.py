import runpy
from pathlib import Path
from typing import cast

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

    html_theme_options = cast(dict[str, object], conf["html_theme_options"])
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
