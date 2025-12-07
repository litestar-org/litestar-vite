"""Svelte syntax highlighting lexer for Pygments.

A custom Pygments lexer for Svelte single-file components (.svelte files).
Svelte components combine HTML, CSS, and JavaScript/TypeScript in a single file
with special syntax for reactivity and templating.
"""

from __future__ import annotations

from pygments.lexers.html import HtmlLexer

__all__ = ["SvelteLexer"]


class SvelteLexer(HtmlLexer):
    """Pygments lexer for Svelte single-file components.

    Extends HtmlLexer to handle Svelte files. The HTML lexer already handles:
    - <script> tags with embedded JavaScript
    - <style> tags with embedded CSS
    - HTML template syntax

    This provides reasonable syntax highlighting for Svelte components
    in documentation without requiring a full Svelte parser.
    """

    name = "Svelte"
    aliases = ["svelte"]
    filenames = ["*.svelte"]
    mimetypes = ["text/x-svelte", "application/x-svelte"]
