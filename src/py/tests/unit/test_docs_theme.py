import re
import runpy
from pathlib import Path
from typing import cast

from pygments.token import Comment, Keyword, Name, String, Token

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
    assert html_theme_options["light_logo"] == "_static/header-star-light.svg"
    assert html_theme_options["dark_logo"] == "_static/header-star-dark.svg"
    assert html_theme_options["logo_target"] == "/"


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


# ===== Code Surface: Custom Lexer Validation =====

# CSS classes the code.css palette maps to token families.
# If a lexer emits tokens in these families, the palette covers them.
_PALETTE_TOKEN_FAMILIES = {
    Keyword,  # .k, .kd, .kn, etc.  → --lv-code-keyword
    String,  # .s, .s1, .s2, etc.  → --lv-code-string
    Comment,  # .c, .c1, .cm, etc.  → --lv-code-comment
    Name.Tag,  # .nt                  → --lv-code-property
    Name.Attribute,  # .na                  → --lv-code-definition
    Name.Builtin,  # .nb                  → --lv-code-builtin
}


def _token_families_emitted(lexer_cls: type, source: str) -> set:
    """Return the set of top-level Pygments token families emitted by a lexer for the given source."""
    lexer = lexer_cls()
    families: set = set()
    for _index, token_type, _value in lexer.get_tokens_unprocessed(source):
        # Walk up to the second level (e.g. Token.Keyword.Declaration → Token.Keyword)
        parent = token_type
        while parent.parent and parent.parent not in (Token, None):
            parent = parent.parent
        families.add(parent)
    return families


def test_tsx_lexer_emits_palette_covered_tokens() -> None:
    """TSX lexer output maps to CSS classes defined in code.css."""
    from tools.sphinx_ext.tsx_lexer import TsxLexer

    source = 'import React from "react";\nconst App = () => <div className="app">Hello</div>;'
    families = _token_families_emitted(TsxLexer, source)

    assert families & {Keyword, String, Name.Attribute, Name.Tag}, (
        f"TSX lexer missing expected token families; got {families}"
    )


def test_astro_lexer_emits_palette_covered_tokens() -> None:
    """Astro lexer output maps to CSS classes defined in code.css."""
    from tools.sphinx_ext.astro_lexer import AstroLexer

    source = '---\nimport Layout from "./Layout.astro";\nconst title = "Hello";\n---\n<Layout title={title}>\n  <h1>{title}</h1>\n</Layout>'
    families = _token_families_emitted(AstroLexer, source)

    assert families & {Keyword, String, Name.Tag}, f"Astro lexer missing expected token families; got {families}"


def test_svelte_lexer_emits_palette_covered_tokens() -> None:
    """Svelte lexer output maps to CSS classes defined in code.css."""
    from tools.sphinx_ext.svelte_lexer import SvelteLexer

    source = "<script>\n  let count = 0;\n  function increment() { count += 1; }\n</script>\n<button on:click={increment}>{count}</button>"
    families = _token_families_emitted(SvelteLexer, source)

    assert families & {Keyword, Name.Tag}, f"Svelte lexer missing expected token families; got {families}"


def test_code_css_covers_all_pygments_short_classes() -> None:
    """code.css defines selectors for the core Pygments CSS short classes used by the palette."""
    code_css = (ROOT / "docs" / "_static" / "code.css").read_text()

    # Core short classes that MUST be styled for the palette to work
    required_classes = ["k", "s", "c", "m", "nb", "nf", "nt", "nv", "o"]
    for cls in required_classes:
        pattern = rf"\.highlight\s+\.{re.escape(cls)}\b"
        assert re.search(pattern, code_css), f"code.css missing selector for .highlight .{cls}"
