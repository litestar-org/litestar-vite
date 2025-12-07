from __future__ import annotations

from typing import TYPE_CHECKING

from tools.sphinx_ext import changelog, missing_references
from tools.sphinx_ext.svelte_lexer import SvelteLexer

if TYPE_CHECKING:
    from collections.abc import Mapping

    from sphinx.application import Sphinx


def setup(app: Sphinx) -> Mapping[str, bool]:
    ext_config: Mapping[str, bool] = {}
    ext_config.update(missing_references.setup(app))  # type: ignore[attr-defined]
    ext_config.update(*changelog.setup(app))  # type: ignore[attr-defined]

    # Register the Svelte lexer for syntax highlighting
    app.add_lexer("svelte", SvelteLexer)

    return ext_config
