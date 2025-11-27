"""HTML transformation and injection utilities.

This module provides utilities for transforming HTML documents to inject
scripts, metadata, and attributes. It's used for SPA mode to inject:
- Route metadata (window.__LITESTAR_ROUTES__)
- Inertia.js page props (window.__INERTIA_PAGE__)
- Data attributes on elements

The implementation uses regex-based transformations with fallback to
html.parser for edge cases.
"""

import json
import re
from html.parser import HTMLParser
from typing import Any, Optional

# Compiled regex patterns for HTML transformations (case-insensitive)
# These are compiled once at module load for better performance
_HEAD_END_PATTERN = re.compile(r"</head\s*>", re.IGNORECASE)
_BODY_END_PATTERN = re.compile(r"</body\s*>", re.IGNORECASE)
_BODY_START_PATTERN = re.compile(r"<body[^>]*>", re.IGNORECASE)
_HTML_END_PATTERN = re.compile(r"</html\s*>", re.IGNORECASE)


class HtmlTransformer:
    """HTML transformer for injecting scripts and attributes.

    This class provides methods for safely injecting content into HTML documents.
    It uses regex-based matching for performance, with fallback to html.parser
    for edge cases.

    Example:
        transformer = HtmlTransformer()
        html = transformer.inject_head_script(html, "console.log('injected');")
        html = transformer.set_data_attribute(html, "#app", "data-page", '{"foo":"bar"}')
    """

    @staticmethod
    def inject_head_script(html: str, script: str, *, escape: bool = True) -> str:
        """Inject a script tag before the closing </head> tag.

        Args:
            html: The HTML document.
            script: The JavaScript code to inject (without <script> tags).
            escape: Whether to escape the script content. Default True.

        Returns:
            The HTML with the injected script.

        Example:
            html = inject_head_script(html, "window.__DATA__ = {foo: 1};")
        """
        if not script:
            return html

        # Escape the script content if needed
        if escape:
            script = HtmlTransformer._escape_script(script)

        script_tag = f"<script>{script}</script>\n"

        # Try to find </head> tag (handles whitespace variations)
        head_end_match = _HEAD_END_PATTERN.search(html)
        if head_end_match:
            pos = head_end_match.start()
            return html[:pos] + script_tag + html[pos:]

        # Fallback: inject before </html>
        html_end_match = _HTML_END_PATTERN.search(html)
        if html_end_match:
            pos = html_end_match.start()
            return html[:pos] + script_tag + html[pos:]

        # No closing tags found - append at the end
        return html + "\n" + script_tag

    @staticmethod
    def inject_body_content(html: str, content: str, *, position: str = "end") -> str:
        """Inject content into the body element.

        Args:
            html: The HTML document.
            content: The content to inject (can include HTML tags).
            position: Where to inject - "start" (after <body>) or "end" (before </body>).

        Returns:
            The HTML with the injected content.

        Example:
            html = inject_body_content(html, '<div id="portal"></div>', position="end")
        """
        if not content:
            return html

        if position == "end":
            # Inject before closing </body> tag
            body_end_match = _BODY_END_PATTERN.search(html)
            if body_end_match:
                pos = body_end_match.start()
                return html[:pos] + content + "\n" + html[pos:]

        elif position == "start":
            # Inject after opening <body> tag
            body_start_match = _BODY_START_PATTERN.search(html)
            if body_start_match:
                pos = body_start_match.end()
                return html[:pos] + "\n" + content + html[pos:]

        # No body tag found - return as-is
        return html

    @staticmethod
    def set_data_attribute(html: str, selector: str, attr: str, value: str) -> str:
        """Set a data attribute on an element matching the selector.

        This method currently supports simple ID selectors (#id) and element selectors (div).
        For complex selectors, consider using a proper HTML parser.

        Args:
            html: The HTML document.
            selector: CSS-like selector (currently supports #id and element names).
            attr: The attribute name (e.g., "data-page").
            value: The attribute value.

        Returns:
            The HTML with the attribute set.

        Example:
            html = set_data_attribute(html, "#app", "data-page", '{"component":"Home"}')
        """
        if not selector or not attr:
            return html

        # Escape the value for HTML attribute
        escaped_value = HtmlTransformer._escape_attr(value)

        # Handle ID selector (#id)
        if selector.startswith("#"):
            element_id = selector[1:]
            # Match opening tag with this id
            pattern = re.compile(
                rf'(<[a-zA-Z][a-zA-Z0-9]*\s+[^>]*id\s*=\s*["\']?{re.escape(element_id)}["\']?[^>]*)(>)',
                re.IGNORECASE,
            )

            def replacer(match: re.Match[str]) -> str:
                opening = match.group(1)
                closing = match.group(2)
                # Check if attribute already exists
                attr_pattern = re.compile(rf'{re.escape(attr)}\s*=\s*["\'][^"\']*["\']', re.IGNORECASE)
                if attr_pattern.search(opening):
                    # Replace existing attribute
                    opening = attr_pattern.sub(f'{attr}="{escaped_value}"', opening)
                else:
                    # Add new attribute
                    opening = opening.rstrip() + f' {attr}="{escaped_value}"'
                return opening + closing

            return pattern.sub(replacer, html, count=1)

        # Handle element selector (e.g., "div")
        element_name = selector.lower()
        pattern = re.compile(rf"(<{re.escape(element_name)}[^>]*)(>)", re.IGNORECASE)

        def element_replacer(match: re.Match[str]) -> str:
            opening = match.group(1)
            closing = match.group(2)
            # Check if attribute already exists
            attr_pattern = re.compile(rf'{re.escape(attr)}\s*=\s*["\'][^"\']*["\']', re.IGNORECASE)
            if attr_pattern.search(opening):
                # Replace existing attribute
                opening = attr_pattern.sub(f'{attr}="{escaped_value}"', opening)
            else:
                # Add new attribute
                opening = opening.rstrip() + f' {attr}="{escaped_value}"'
            return opening + closing

        return pattern.sub(element_replacer, html, count=1)

    @staticmethod
    def inject_json_script(html: str, var_name: str, data: dict[str, Any]) -> str:
        """Inject a script that sets a global JavaScript variable to JSON data.

        This is a convenience method for injecting structured data into the page.

        Args:
            html: The HTML document.
            var_name: The global variable name (e.g., "__LITESTAR_ROUTES__").
            data: The data to serialize as JSON.

        Returns:
            The HTML with the injected script.

        Example:
            html = inject_json_script(html, "__ROUTES__", {"home": "/", "about": "/about"})
        """
        json_data = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
        script = f"window.{var_name} = {json_data};"
        return HtmlTransformer.inject_head_script(html, script, escape=False)

    @staticmethod
    def _escape_script(script: str) -> str:
        """Escape script content to prevent breaking out of script tags.

        Args:
            script: The script content.

        Returns:
            The escaped script content.
        """
        # Replace </script> with <\/script> to prevent breaking out
        return script.replace("</script>", r"<\/script>")

    @staticmethod
    def _escape_attr(value: str) -> str:
        """Escape attribute value for HTML.

        Args:
            value: The attribute value.

        Returns:
            The escaped value.
        """
        return (
            value.replace("&", "&amp;")
            .replace('"', "&quot;")
            .replace("'", "&#39;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
        )


class SafeHTMLParser(HTMLParser):
    """Safe HTML parser for finding tag positions.

    This parser is used as a fallback for complex HTML transformations
    when regex-based approaches fail.
    """

    def __init__(self) -> None:
        """Initialize the parser."""
        super().__init__()
        self.tag_positions: list[tuple[str, int, int]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, "Optional[str]"]]) -> None:
        """Record start tag position."""
        self.tag_positions.append((tag, self.getpos()[0], self.getpos()[1]))

    def handle_endtag(self, tag: str) -> None:
        """Record end tag position."""
        self.tag_positions.append((f"/{tag}", self.getpos()[0], self.getpos()[1]))
