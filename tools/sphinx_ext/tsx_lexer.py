"""TSX (TypeScript JSX) syntax highlighting lexer for Pygments.

A custom Pygments lexer for TSX files (.tsx) which combine TypeScript with JSX syntax.
This extends the battle-tested jsx-lexer package for proper JSX support.
"""

from __future__ import annotations

from jsx.lexer import JsxLexer

__all__ = ["TsxLexer"]


class TsxLexer(JsxLexer):
    """Pygments lexer for TSX (TypeScript JSX) files.

    Extends JsxLexer from the jsx-lexer package which provides proper JSX
    syntax highlighting including fragments, nested expressions, and attributes.

    The lexer handles:
    - Standard JavaScript/TypeScript syntax
    - JSX elements and fragments
    - JSX attributes with string or expression values
    - Nested JSX expressions

    Note:
        This lexer inherits from jsx-lexer (pip install jsx-lexer) which
        provides comprehensive JSX parsing support.
    """

    name = "TSX"
    aliases = ["tsx", "typescriptreact"]
    filenames = ["*.tsx"]
    mimetypes = ["text/typescript-jsx", "application/typescript-jsx"]
