"""Astro syntax highlighting lexer for Pygments.

A custom Pygments lexer for Astro single-file components (.astro files).
Astro components have a frontmatter section (---) with JavaScript/TypeScript
followed by an HTML template section.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from pygments.lexer import DelegatingLexer
from pygments.lexers.html import HtmlLexer
from pygments.lexers.javascript import JavascriptLexer
from pygments.token import Comment, _TokenType

if TYPE_CHECKING:
    from collections.abc import Iterator

__all__ = ["AstroLexer"]


class AstroLexer(DelegatingLexer):
    """Pygments lexer for Astro single-file components.

    Astro files have two sections:
    1. Frontmatter (between --- delimiters) containing JavaScript/TypeScript
    2. Template section containing HTML with Astro expressions

    This lexer delegates to JavaScriptLexer for frontmatter and HtmlLexer
    for the template section, providing reasonable syntax highlighting
    for Astro components in documentation.
    """

    name = "Astro"
    aliases = ["astro"]
    filenames = ["*.astro"]
    mimetypes = ["text/x-astro", "application/x-astro"]

    def __init__(self, **options: object) -> None:
        super().__init__(HtmlLexer, JavascriptLexer, **options)

    def get_tokens_unprocessed(self, text: str) -> Iterator[tuple[int, _TokenType, str]]:
        """Tokenize Astro content with frontmatter support.

        Splits the content at frontmatter delimiters (---) and delegates
        to the appropriate lexer for each section.

        Args:
            text: The Astro source code to tokenize.

        Yields:
            Tuples of (index, token_type, value) for each token.
        """
        # Check for frontmatter (starts with ---)
        if text.lstrip().startswith("---"):
            # Find the frontmatter boundaries
            stripped = text.lstrip()
            first_delim = stripped.find("---")
            if first_delim != -1:
                # Find the closing ---
                second_delim = stripped.find("---", first_delim + 3)
                if second_delim != -1:
                    # Calculate actual positions in original text
                    leading_ws = len(text) - len(stripped)

                    # Opening delimiter
                    yield (leading_ws, Comment.Preproc, "---")

                    # Frontmatter content (JavaScript/TypeScript)
                    frontmatter_start = leading_ws + 3
                    frontmatter_end = leading_ws + second_delim
                    frontmatter = text[frontmatter_start:frontmatter_end]

                    # Use JavaScript lexer for frontmatter
                    js_lexer = JavascriptLexer()
                    for idx, token, value in js_lexer.get_tokens_unprocessed(frontmatter):
                        yield (frontmatter_start + idx, token, value)

                    # Closing delimiter
                    yield (frontmatter_end, Comment.Preproc, "---")

                    # Template content (HTML)
                    template_start = frontmatter_end + 3
                    template = text[template_start:]

                    # Use HTML lexer for template
                    html_lexer = HtmlLexer()
                    for idx, token, value in html_lexer.get_tokens_unprocessed(template):
                        yield (template_start + idx, token, value)
                    return

        # No frontmatter, treat as HTML
        yield from HtmlLexer().get_tokens_unprocessed(text)
