"""HTML transformation and injection utilities for SPA output.

Regex patterns are compiled once at import time for performance.
"""

import re
from functools import lru_cache, partial
from typing import Any

from litestar.serialization import encode_json

_HEAD_END_PATTERN = re.compile(r"</head\s*>", re.IGNORECASE)
_BODY_END_PATTERN = re.compile(r"</body\s*>", re.IGNORECASE)
_BODY_START_PATTERN = re.compile(r"<body[^>]*>", re.IGNORECASE)
_HTML_END_PATTERN = re.compile(r"</html\s*>", re.IGNORECASE)
_SCRIPT_SRC_PATTERN = re.compile(r'(<script[^>]*\s+src\s*=\s*["\'])([^"\']+)(["\'][^>]*>)', re.IGNORECASE)
_LINK_HREF_PATTERN = re.compile(r'(<link[^>]*\s+href\s*=\s*["\'])([^"\']+)(["\'][^>]*>)', re.IGNORECASE)


@lru_cache(maxsize=128)
def _get_id_selector_pattern(element_id: str) -> re.Pattern[str]:
    """Return a compiled regex pattern for an ID selector.

    Returns:
        Pattern matching an element with the given ID.
    """
    return re.compile(
        rf'(<[a-zA-Z][a-zA-Z0-9]*\s+[^>]*id\s*=\s*["\']?{re.escape(element_id)}["\']?[^>]*)(>)', re.IGNORECASE
    )


@lru_cache(maxsize=128)
def _get_element_selector_pattern(element_name: str) -> re.Pattern[str]:
    """Return a compiled regex pattern for an element selector.

    Returns:
        Pattern matching elements with the given tag name.
    """
    return re.compile(rf"(<{re.escape(element_name)}[^>]*)(>)", re.IGNORECASE)


@lru_cache(maxsize=128)
def _get_attr_pattern(attr: str) -> re.Pattern[str]:
    """Return a compiled regex pattern for an attribute.

    Returns:
        Pattern matching the attribute with its value.
    """
    return re.compile(rf'{re.escape(attr)}\s*=\s*["\'][^"\']*["\']', re.IGNORECASE)


@lru_cache(maxsize=128)
def _get_id_element_with_content_pattern(element_id: str) -> re.Pattern[str]:
    """Return a compiled regex pattern to match an element by ID and capture its inner HTML.

    The pattern matches: <tag ... id="element_id" ...> ... </tag>
    and captures the opening tag, the inner content, and the closing tag.

    Returns:
        Pattern matching an element with the given ID, capturing its inner HTML.
    """
    return re.compile(
        rf"(<(?P<tag>[a-zA-Z0-9]+)(?P<attrs>[^>]*\bid=[\"']{re.escape(element_id)}[\"'][^>]*)>)(?P<inner>.*?)(</(?P=tag)\s*>)",
        flags=re.IGNORECASE | re.DOTALL,
    )


def _escape_script(script: str) -> str:
    r"""Escape script content to prevent breaking out of script tags.

    Replaces ``</script>`` with ``<\/script>`` to prevent premature tag closure.

    Args:
        script: The script content to escape.

    Returns:
        The escaped script content safe for embedding in ``<script>`` tags.
    """
    return script.replace("</script>", r"<\/script>")


def _escape_attr(value: str) -> str:
    """Escape attribute value for safe HTML embedding.

    Escapes special HTML characters: ``&``, ``"``, ``'``, ``<``, ``>``.

    Args:
        value: The attribute value to escape.

    Returns:
        The escaped value safe for use in HTML attribute values.
    """
    return (
        value.replace("&", "&amp;")
        .replace('"', "&quot;")
        .replace("'", "&#39;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def _set_attribute_replacer(
    match: re.Match[str], *, attr_pattern: re.Pattern[str], attr_name: str, escaped_val: str
) -> str:
    """Replace or add an attribute on an opening tag match.

    Args:
        match: Regex match capturing the opening portion and closing delimiter.
        attr_pattern: Compiled pattern that matches the attribute assignment.
        attr_name: Attribute name to set.
        escaped_val: Escaped attribute value.

    Returns:
        Updated tag string with ``attr_name`` set to ``escaped_val``.
    """
    opening = match.group(1)
    closing = match.group(2)
    if attr_pattern.search(opening):
        opening = attr_pattern.sub(f'{attr_name}="{escaped_val}"', opening)
    else:
        opening = opening.rstrip() + f' {attr_name}="{escaped_val}"'
    return opening + closing


def _set_inner_html_replacer(match: re.Match[str], *, content: str) -> str:
    """Replace inner HTML for an ID-targeted element match.

    Args:
        match: Regex match from ``_get_id_element_with_content_pattern``.
        content: Raw HTML to inject as the element's inner HTML.

    Returns:
        Updated HTML fragment with replaced inner content.
    """
    return match.group(1) + content + match.group(5)


def inject_head_script(html: str, script: str, *, escape: bool = True) -> str:
    """Inject a script tag before the closing </head> tag.

    Args:
        html: The HTML document.
        script: The JavaScript code to inject (without <script> tags).
        escape: Whether to escape the script content. Default True.

    Returns:
        The HTML with the injected script. If ``</head>`` is not found,
        falls back to injecting before ``</html>``. If neither is found,
        appends the script at the end. Returns the original HTML unchanged
        if ``script`` is empty.

    Example:
        html = inject_head_script(html, "window.__DATA__ = {foo: 1};")
    """
    if not script:
        return html

    if escape:
        script = _escape_script(script)

    script_tag = f"<script>{script}</script>\n"

    head_end_match = _HEAD_END_PATTERN.search(html)
    if head_end_match:
        pos = head_end_match.start()
        return html[:pos] + script_tag + html[pos:]

    html_end_match = _HTML_END_PATTERN.search(html)
    if html_end_match:
        pos = html_end_match.start()
        return html[:pos] + script_tag + html[pos:]

    return html + "\n" + script_tag


def inject_head_html(html: str, content: str) -> str:
    """Inject raw HTML into the ``<head>`` section.

    This is used for Inertia SSR, where the SSR server returns an array of HTML strings
    (typically ``<title>``, ``<meta>``, etc.) that must be placed in the final HTML response.

    Args:
        html: The HTML document.
        content: Raw HTML to inject. This is inserted as-is.

    Returns:
        The HTML with the content injected before ``</head>`` when present.
        Falls back to injecting before ``</html>`` or appending at the end.
    """
    if not content:
        return html

    head_end_match = _HEAD_END_PATTERN.search(html)
    if head_end_match:
        pos = head_end_match.start()
        return html[:pos] + content + "\n" + html[pos:]

    html_end_match = _HTML_END_PATTERN.search(html)
    if html_end_match:
        pos = html_end_match.start()
        return html[:pos] + content + "\n" + html[pos:]

    return html + "\n" + content


def inject_body_content(html: str, content: str, *, position: str = "end") -> str:
    """Inject content into the body element.

    Args:
        html: The HTML document.
        content: The content to inject (can include HTML tags).
        position: Where to inject - "start" (after <body>) or "end" (before </body>).

    Returns:
        The HTML with the injected content. Returns the original HTML unchanged
        if ``content`` is empty or if no ``<body>`` tag is found.

    Example:
        html = inject_body_content(html, '<div id="portal"></div>', position="end")
    """
    if not content:
        return html

    if position == "end":
        body_end_match = _BODY_END_PATTERN.search(html)
        if body_end_match:
            pos = body_end_match.start()
            return html[:pos] + content + "\n" + html[pos:]

    elif position == "start":
        body_start_match = _BODY_START_PATTERN.search(html)
        if body_start_match:
            pos = body_start_match.end()
            return html[:pos] + "\n" + content + html[pos:]

    return html


def set_data_attribute(html: str, selector: str, attr: str, value: str) -> str:
    """Set a data attribute on an element matching the selector.

    This function supports simple ID selectors (#id) and element selectors (div).
    For complex selectors, consider using a proper HTML parser.

    Args:
        html: The HTML document.
        selector: CSS-like selector (currently supports #id and element names).
        attr: The attribute name (e.g., "data-page").
        value: The attribute value (will be HTML-escaped automatically).

    Returns:
        The HTML with the attribute set. If the attribute already exists, it is
        replaced. Returns the original HTML unchanged if ``selector`` or ``attr``
        is empty, or if no matching element is found.

    Note:
        Only the first matching element is modified. The value is automatically
        escaped to prevent XSS vulnerabilities.

    Example:
        html = set_data_attribute(html, "#app", "data-page", '{"component":"Home"}')
    """
    if not selector or not attr:
        return html

    escaped_value = _escape_attr(value)
    attr_pattern = _get_attr_pattern(attr)
    replacer = partial(_set_attribute_replacer, attr_pattern=attr_pattern, attr_name=attr, escaped_val=escaped_value)

    if selector.startswith("#"):
        element_id = selector[1:]
        pattern = _get_id_selector_pattern(element_id)
        return pattern.sub(replacer, html, count=1)

    element_name = selector.lower()
    pattern = _get_element_selector_pattern(element_name)
    return pattern.sub(replacer, html, count=1)


def set_element_inner_html(html: str, selector: str, content: str) -> str:
    """Replace the inner HTML of an element matching the selector.

    Supports only simple ID selectors (``#app``). This is intentionally limited to avoid
    the overhead and edge cases of a full HTML parser.

    Args:
        html: The HTML document.
        selector: The selector (only ``#id`` supported).
        content: The raw HTML to set as the element's innerHTML.

    Returns:
        Updated HTML. If no matching element is found, returns the original HTML.
    """
    if not selector or not selector.startswith("#"):
        return html

    element_id = selector[1:]
    pattern = _get_id_element_with_content_pattern(element_id)
    replacer = partial(_set_inner_html_replacer, content=content)
    return pattern.sub(replacer, html, count=1)


def inject_json_script(html: str, var_name: str, data: dict[str, Any]) -> str:
    """Inject a script that sets a global JavaScript variable to JSON data.

    This is a convenience function for injecting structured data into the page.
    The data is serialized with compact JSON (no extra whitespace) and non-ASCII
    characters are preserved.

    Args:
        html: The HTML document.
        var_name: The global variable name (e.g., "__LITESTAR_ROUTES__").
        data: The data to serialize as JSON.

    Returns:
        The HTML with the injected script in the ``<head>`` section. Falls back
        to injecting before ``</html>`` or at the end if no ``</head>`` is found.

    Note:
        The script content is NOT escaped to preserve valid JSON. Ensure that
        ``data`` does not contain user-controlled content that could include
        malicious ``</script>`` sequences.

    Example:
        html = inject_json_script(html, "__ROUTES__", {"home": "/", "about": "/about"})
    """
    json_data = encode_json(data).decode("utf-8")
    script = f"window.{var_name} = {json_data};"
    return inject_head_script(html, script, escape=False)


def transform_asset_urls(
    html: str, manifest: dict[str, Any], asset_url: str = "/static/", base_url: str | None = None
) -> str:
    """Transform asset URLs in HTML based on Vite manifest.

    This function replaces source asset paths (e.g., /resources/main.tsx)
    with their hashed production equivalents from the Vite manifest
    (e.g., /static/assets/main-C-_c4FS5.js).

    This is essential for production mode when using Vite's library mode
    (input: ["resources/main.tsx"]) where Vite doesn't transform index.html.

    Args:
        html: The HTML document to transform.
        manifest: The Vite manifest dictionary mapping source paths to output.
            Each entry should have a ``file`` key with the hashed output path.
        asset_url: Base URL for assets (default "/static/").
        base_url: Optional CDN base URL override for production assets. When
            provided, takes precedence over ``asset_url``.

    Returns:
        The HTML with transformed asset URLs. Returns the original HTML unchanged
        if ``manifest`` is empty. Asset paths not found in the manifest are left
        unchanged (no error is raised).

    Note:
        This function transforms ``<script src="...">`` and ``<link href="...">``
        attributes. Leading slashes in source paths are normalized for manifest
        lookup (e.g., "/resources/main.tsx" matches "resources/main.tsx" in manifest).

    Example:
        manifest = {"resources/main.tsx": {"file": "assets/main-abc123.js"}}
        html = '<script type="module" src="/resources/main.tsx"></script>'
        result = transform_asset_urls(html, manifest)
        # Result: '<script type="module" src="/static/assets/main-abc123.js"></script>'
    """
    if not manifest:
        return html

    url_base = base_url or asset_url

    def _normalize_path(path: str) -> str:
        """Normalize a path for manifest lookup by removing leading slash.

        Returns:
            The normalized path without leading slash.
        """
        return path.lstrip("/")

    def _build_url(file_path: str) -> str:
        """Build the full URL for an asset file.

        Returns:
            The full URL combining base and file path.
        """
        base = url_base if url_base.endswith("/") else url_base + "/"
        return base + file_path

    def replace_script_src(match: re.Match[str]) -> str:
        """Replace script src with manifest lookup.

        Returns:
            The transformed script tag with updated src, or original if not found.
        """
        prefix = match.group(1)
        src = match.group(2)
        suffix = match.group(3)

        normalized = _normalize_path(src)
        if normalized in manifest:
            entry = manifest[normalized]
            new_src = _build_url(entry.get("file", src))
            return prefix + new_src + suffix
        return match.group(0)

    def replace_link_href(match: re.Match[str]) -> str:
        """Replace link href with manifest lookup.

        Returns:
            The transformed link tag with updated href, or original if not found.
        """
        prefix = match.group(1)
        href = match.group(2)
        suffix = match.group(3)

        normalized = _normalize_path(href)
        if normalized in manifest:
            entry = manifest[normalized]
            new_href = _build_url(entry.get("file", href))
            return prefix + new_href + suffix
        return match.group(0)

    html = _SCRIPT_SRC_PATTERN.sub(replace_script_src, html)

    return _LINK_HREF_PATTERN.sub(replace_link_href, html)
