"""HTML transformation and injection utilities.

This module provides utilities for transforming HTML documents to inject
scripts, metadata, and attributes. It's used for SPA mode to inject:
- Route metadata (window.__LITESTAR_ROUTES__)
- Inertia.js page props (window.__INERTIA_PAGE__)
- Data attributes on elements

The implementation uses regex-based transformations for performance.
"""

import json
import re
from functools import lru_cache
from typing import Any

# Compiled regex patterns for HTML transformations (case-insensitive)
# These are compiled once at module load for better performance
_HEAD_END_PATTERN = re.compile(r"</head\s*>", re.IGNORECASE)
_BODY_END_PATTERN = re.compile(r"</body\s*>", re.IGNORECASE)
_BODY_START_PATTERN = re.compile(r"<body[^>]*>", re.IGNORECASE)
_HTML_END_PATTERN = re.compile(r"</html\s*>", re.IGNORECASE)


@lru_cache(maxsize=128)
def _get_id_selector_pattern(element_id: str) -> re.Pattern[str]:
    """Get compiled regex pattern for ID selector (cached)."""
    return re.compile(
        rf'(<[a-zA-Z][a-zA-Z0-9]*\s+[^>]*id\s*=\s*["\']?{re.escape(element_id)}["\']?[^>]*)(>)',
        re.IGNORECASE,
    )


@lru_cache(maxsize=128)
def _get_element_selector_pattern(element_name: str) -> re.Pattern[str]:
    """Get compiled regex pattern for element selector (cached)."""
    return re.compile(rf"(<{re.escape(element_name)}[^>]*)(>)", re.IGNORECASE)


@lru_cache(maxsize=128)
def _get_attr_pattern(attr: str) -> re.Pattern[str]:
    """Get compiled regex pattern for attribute matching (cached)."""
    return re.compile(rf'{re.escape(attr)}\s*=\s*["\'][^"\']*["\']', re.IGNORECASE)


def _escape_script(script: str) -> str:
    """Escape script content to prevent breaking out of script tags.

    Args:
        script: The script content.

    Returns:
        The escaped script content.
    """
    # Replace </script> with <\/script> to prevent breaking out
    return script.replace("</script>", r"<\/script>")


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
        script = _escape_script(script)

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


def set_data_attribute(html: str, selector: str, attr: str, value: str) -> str:
    """Set a data attribute on an element matching the selector.

    This function supports simple ID selectors (#id) and element selectors (div).
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
    escaped_value = _escape_attr(value)
    attr_pattern = _get_attr_pattern(attr)

    def make_replacer(attr_name: str, escaped_val: str) -> Any:
        """Create a replacer function for regex substitution."""

        def replacer(match: re.Match[str]) -> str:
            opening = match.group(1)
            closing = match.group(2)
            # Check if attribute already exists
            if attr_pattern.search(opening):
                # Replace existing attribute
                opening = attr_pattern.sub(f'{attr_name}="{escaped_val}"', opening)
            else:
                # Add new attribute
                opening = opening.rstrip() + f' {attr_name}="{escaped_val}"'
            return opening + closing

        return replacer

    # Handle ID selector (#id)
    if selector.startswith("#"):
        element_id = selector[1:]
        pattern = _get_id_selector_pattern(element_id)
        return pattern.sub(make_replacer(attr, escaped_value), html, count=1)

    # Handle element selector (e.g., "div")
    element_name = selector.lower()
    pattern = _get_element_selector_pattern(element_name)
    return pattern.sub(make_replacer(attr, escaped_value), html, count=1)


def inject_json_script(html: str, var_name: str, data: dict[str, Any]) -> str:
    """Inject a script that sets a global JavaScript variable to JSON data.

    This is a convenience function for injecting structured data into the page.

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
    return inject_head_script(html, script, escape=False)


# Backward compatibility: HtmlTransformer class wrapping module functions
class HtmlTransformer:
    """HTML transformer for injecting scripts and attributes.

    This class provides static methods for safely injecting content into HTML documents.
    It uses regex-based matching for performance.

    Note:
        This class is provided for backward compatibility. The underlying functions
        are also available as module-level functions (e.g., `inject_head_script`).

    Example:
        html = HtmlTransformer.inject_head_script(html, "console.log('injected');")
        html = HtmlTransformer.set_data_attribute(html, "#app", "data-page", '{"foo":"bar"}')
    """

    inject_head_script = staticmethod(inject_head_script)
    inject_body_content = staticmethod(inject_body_content)
    set_data_attribute = staticmethod(set_data_attribute)
    inject_json_script = staticmethod(inject_json_script)
    _escape_script = staticmethod(_escape_script)
    _escape_attr = staticmethod(_escape_attr)
