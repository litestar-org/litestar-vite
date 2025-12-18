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
        value
        .replace("&", "&amp;")
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


def inject_head_script(html: str, script: str, *, escape: bool = True, nonce: str | None = None) -> str:
    """Inject a script tag before the closing </head> tag.

    Args:
        html: The HTML document.
        script: The JavaScript code to inject (without <script> tags).
        escape: Whether to escape the script content. Default True.
        nonce: Optional CSP nonce to add to the injected ``<script>`` tag.

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

    nonce_attr = f' nonce="{_escape_attr(nonce)}"' if nonce else ""
    script_tag = f"<script{nonce_attr}>{script}</script>\n"

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


def inject_page_script(html: str, json_data: str, *, nonce: str | None = None, script_id: str = "app_page") -> str:
    r"""Inject page data as a JSON script element before ``</body>``.

    This is an Inertia.js v2.3+ optimization that embeds page data in a
    ``<script type="application/json">`` element instead of a ``data-page`` attribute.
    This provides ~37% payload reduction for large pages by avoiding HTML entity escaping.

    The script element is inserted before ``</body>`` with:
    - ``type="application/json"`` (non-executable, just data)
    - ``id="app_page"`` (Inertia's expected ID for useScriptElementForInitialPage)
    - Optional ``nonce`` for CSP compliance

    Args:
        html: The HTML document.
        json_data: Pre-serialized JSON string (page props).
        nonce: Optional CSP nonce to add to the script element.
        script_id: The script element ID (default "app_page" per Inertia protocol).

    Returns:
        The HTML with the script element injected before ``</body>``.
        Falls back to appending at the end if no ``</body>`` tag is found.

    Note:
        The JSON content is escaped to prevent XSS via ``</script>`` injection.
        Sequences like ``</`` are replaced with ``<\\/`` (escaped forward slash)
        which is valid JSON and prevents HTML parser issues.

    Example:
        html = inject_page_script(html, '{"component":"Home","props":{}}')
    """
    if not json_data:
        return html

    # Escape sequences that could break out of script element
    # Replace </ with <\/ to prevent premature tag closure (XSS prevention)
    escaped_json = json_data.replace("</", r"<\/")

    nonce_attr = f' nonce="{_escape_attr(nonce)}"' if nonce else ""
    script_tag = f'<script type="application/json" id="{script_id}"{nonce_attr}>{escaped_json}</script>\n'

    body_end_match = _BODY_END_PATTERN.search(html)
    if body_end_match:
        pos = body_end_match.start()
        return html[:pos] + script_tag + html[pos:]

    return html + "\n" + script_tag


def inject_json_script(html: str, var_name: str, data: dict[str, Any], *, nonce: str | None = None) -> str:
    """Inject a script that sets a global JavaScript variable to JSON data.

    This is a convenience function for injecting structured data into the page.
    The data is serialized with compact JSON (no extra whitespace) and non-ASCII
    characters are preserved.

    Args:
        html: The HTML document.
        var_name: The global variable name (e.g., "__LITESTAR_ROUTES__").
        data: The data to serialize as JSON.
        nonce: Optional CSP nonce to add to the injected ``<script>`` tag.

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
    return inject_head_script(html, script, escape=False, nonce=nonce)


def inject_vite_dev_scripts(
    html: str,
    vite_url: str,
    *,
    asset_url: str = "/static/",
    is_react: bool = False,
    csp_nonce: str | None = None,
    resource_dir: str | None = None,
) -> str:
    """Inject Vite dev server scripts for HMR support.

    This function injects the necessary scripts for Vite's Hot Module Replacement
    (HMR) to work when serving HTML from the backend (e.g., in hybrid/Inertia mode).
    The scripts are injected into the ``<head>`` section.

    For React apps, a preamble script is injected before the Vite client to
    enable React Fast Refresh.

    Scripts are injected as relative URLs using the ``asset_url`` prefix. This
    routes them through Litestar's proxy middleware, which forwards to Vite
    with the correct base path handling.

    When ``resource_dir`` is provided, entry point script URLs are also transformed
    to include the asset URL prefix (e.g., ``/resources/main.tsx`` becomes
    ``/static/resources/main.tsx``).

    Args:
        html: The HTML document.
        vite_url: The Vite dev server URL (kept for backward compatibility, unused).
        asset_url: The asset URL prefix (e.g., "/static/"). Scripts are served
            at ``{asset_url}@vite/client`` etc.
        is_react: Whether to inject the React Fast Refresh preamble.
        csp_nonce: Optional CSP nonce to add to injected ``<script>`` tags.
        resource_dir: Optional resource directory name (e.g., "resources", "src").
            When provided, script sources starting with ``/{resource_dir}/`` are
            prefixed with ``asset_url``.

    Returns:
        The HTML with Vite dev scripts injected. Scripts are inserted before
        ``</head>`` when present, otherwise before ``</html>`` or at the end.

    Example:
        html = inject_vite_dev_scripts(html, "", asset_url="/static/", is_react=True)
    """
    # Use relative URLs with asset_url prefix so requests go through Litestar's proxy
    # This ensures proper base path handling (Vite expects /static/@vite/client, not /@vite/client)
    base = asset_url.rstrip("/")
    nonce_attr = f' nonce="{_escape_attr(csp_nonce)}"' if csp_nonce else ""

    # Transform entry point script URLs to include the asset URL prefix
    # This ensures /resources/main.tsx becomes /static/resources/main.tsx
    if resource_dir:
        resource_prefix = f"/{resource_dir.strip('/')}/"

        def transform_entry_script(match: re.Match[str]) -> str:
            prefix = match.group(1)
            src = match.group(2)
            suffix = match.group(3)
            if src.startswith(resource_prefix) and not src.startswith(base):
                return prefix + base + src + suffix
            return match.group(0)

        html = _SCRIPT_SRC_PATTERN.sub(transform_entry_script, html)

    scripts: list[str] = []

    if is_react:
        react_preamble = f"""import RefreshRuntime from '{base}/@react-refresh'
RefreshRuntime.injectIntoGlobalHook(window)
window.$RefreshReg$ = () => {{}}
window.$RefreshSig$ = () => (type) => type
window.__vite_plugin_react_preamble_installed__ = true"""
        scripts.append(f'<script type="module"{nonce_attr}>{react_preamble}</script>')

    scripts.append(f'<script type="module" src="{base}/@vite/client"{nonce_attr}></script>')

    script_content = "\n".join(scripts) + "\n"

    head_end_match = _HEAD_END_PATTERN.search(html)
    if head_end_match:
        pos = head_end_match.start()
        return html[:pos] + script_content + html[pos:]

    html_end_match = _HTML_END_PATTERN.search(html)
    if html_end_match:
        pos = html_end_match.start()
        return html[:pos] + script_content + html[pos:]

    return html + "\n" + script_content


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
