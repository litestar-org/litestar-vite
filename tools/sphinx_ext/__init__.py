from __future__ import annotations

from typing import TYPE_CHECKING

from tools.sphinx_ext import changelog, missing_references
from tools.sphinx_ext.astro_lexer import AstroLexer
from tools.sphinx_ext.svelte_lexer import SvelteLexer
from tools.sphinx_ext.tsx_lexer import TsxLexer

if TYPE_CHECKING:
    from collections.abc import Mapping

    from sphinx.application import Sphinx


def setup(app: Sphinx) -> Mapping[str, bool]:
    ext_config: Mapping[str, bool] = {}
    ext_config.update(missing_references.setup(app))  # type: ignore[attr-defined]
    ext_config.update(*changelog.setup(app))  # type: ignore[attr-defined]

    # Register custom lexers for syntax highlighting
    app.add_lexer("svelte", SvelteLexer)
    app.add_lexer("astro", AstroLexer)
    app.add_lexer("tsx", TsxLexer)

    return ext_config
