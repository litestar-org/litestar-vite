"""HTML transformation and injection utilities for SPA output.

Regex patterns are compiled once at import time for performance.
"""

import re
from functools import lru_cache, partial
from html.parser import HTMLParser
from typing import Any, cast

__all__ = (
    "inject_head_html",
    "inject_head_script",
    "inject_inertia_ssr_tags",
    "inject_page_script",
    "inject_vite_dev_scripts",
    "replace_element_outer_html",
    "set_data_attribute",
    "transform_asset_urls",
)

_VALID_SELECTOR_RE = re.compile(r"^#?[a-zA-Z][a-zA-Z0-9_-]*$")
_VALID_ATTR_RE = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_-]*$")

_HEAD_END_PATTERN = re.compile(r"</head\s*>", re.IGNORECASE)
_BODY_END_PATTERN = re.compile(r"</body\s*>", re.IGNORECASE)
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


def _replace_outer_html_replacer(match: re.Match[str], *, content: str) -> str:
    """Replace an entire element match with raw HTML content."""
    return content


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

    if not _VALID_SELECTOR_RE.match(selector):
        msg = f"Invalid selector: {selector!r}. Must be an alphanumeric ID (#id) or element name."
        raise ValueError(msg)
    if not _VALID_ATTR_RE.match(attr):
        msg = f"Invalid attribute name: {attr!r}. Must be an alphanumeric attribute name."
        raise ValueError(msg)

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


def replace_element_outer_html(html: str, selector: str, content: str) -> str:
    """Replace the outer HTML of an element matching the selector.

    Supports only simple ID selectors (``#app``). This is used by the stable
    Inertia SSR path because the upstream SSR response already includes the
    root app wrapper and, in script-element mode, the page-data script.
    """
    if not selector or not selector.startswith("#"):
        return html

    element_id = selector[1:]
    pattern = _get_id_element_with_content_pattern(element_id)
    replacer = partial(_replace_outer_html_replacer, content=content)
    return pattern.sub(replacer, html, count=1)


class _InertiaSlots(HTMLParser):
    """Locate shell slots without interpreting script data or HTML attributes."""

    def __init__(self, html: str) -> None:
        super().__init__(convert_charrefs=False)
        self.slots: dict[str, tuple[int, int]] = {}
        self._offsets = [0, *(match.end() for match in re.finditer("\\n", html))]
        self._container: str | None = None
        self._raw_text_tag: str | None = None
        self.feed(html)

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"head", "body"}:
            self._container = tag
        elif tag in {"script", "style", "textarea", "title", "xmp", "iframe", "noembed", "noframes", "plaintext"}:
            self._raw_text_tag = tag

    def handle_endtag(self, tag: str) -> None:
        if tag == self._container:
            self._container = None
        if tag == self._raw_text_tag:
            self._raw_text_tag = None

    def handle_comment(self, data: str) -> None:
        kind = {"inertia-head": "head", "inertia-body": "body", "inertia": "body"}.get(data.strip())
        if kind is not None and self._raw_text_tag is None:
            self._record(kind, 0, len(data) + 7)

    def handle_data(self, data: str) -> None:
        kind = {"@inertiaHead": "head", "@inertia": "body"}.get(data.strip())
        if kind is not None and kind == self._container and self._raw_text_tag is None:
            leading = len(data) - len(data.lstrip())
            self._record(kind, leading, leading + len(data.strip()))

    def _record(self, kind: str, start: int, end: int) -> None:
        line, column = self.getpos()
        offset = self._offsets[line - 1] + column
        self.slots.setdefault(kind, (offset + start, offset + end))


def inject_inertia_ssr_tags(html: str, *, head: list[str] | str, body: str, selector: str = "#app") -> str:
    """Inject Inertia SSR head and body content into an HTML document.

    Checks first for token/slot-based replacement tags. If no tokens are present,
    falls back to backward-compatible selector outer HTML replacement and head injection.

    Args:
        html: The template or SPA HTML shell string.
        head: List of head HTML tags or a pre-joined head string.
        body: Rendered SSR body markup.
        selector: Fallback CSS ID selector for outer HTML replacement.

    Returns:
        Transformed HTML document containing head and body markup.
    """
    newline = "\r\n" if "\r\n" in html else "\n"
    head_content = newline.join(head) if isinstance(head, list) else head

    slots = _InertiaSlots(html).slots
    replacements = {"head": head_content, "body": body}
    for kind, (start, end) in sorted(slots.items(), key=lambda item: item[1][0], reverse=True):
        html = html[:start] + replacements[kind] + html[end:]

    if "body" not in slots:
        html = replace_element_outer_html(html, selector, body)
    if "head" not in slots and head_content:
        html = inject_head_html(html, head_content)

    return html


def inject_page_script(
    html: str, json_data: str, *, app_id: str = "app", nonce: str | None = None, script_id: str = "app_page"
) -> str:
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
        app_id: The app element ID used by the client bootstrap.
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

    escaped_json = json_data.replace("</", r"<\/")

    nonce_attr = f' nonce="{_escape_attr(nonce)}"' if nonce else ""
    script_tag = (
        f'<script type="application/json" id="{script_id}" data-page="{_escape_attr(app_id)}"{nonce_attr}>'
        f"{escaped_json}</script>\n"
    )

    body_end_match = _BODY_END_PATTERN.search(html)
    if body_end_match:
        pos = body_end_match.start()
        return html[:pos] + script_tag + html[pos:]

    return html + "\n" + script_tag


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

    Scripts are injected as relative URLs using the ``asset_url`` prefix so they
    are routed through the Litestar reverse proxy.

    When ``resource_dir`` is provided, entry point script URLs are also transformed
    to include the asset URL prefix.

    Args:
        html: The HTML document.
        vite_url: The Vite dev server URL.
        asset_url: The asset URL prefix (e.g., "/static/").
        is_react: Whether to inject the React Fast Refresh preamble.
        csp_nonce: Optional CSP nonce to add to injected ``<script>`` tags.
        resource_dir: Optional resource directory name (e.g., "resources", "src").

    Returns:
        The HTML with Vite dev scripts injected. Scripts are inserted before
        ``</head>`` when present, otherwise before ``</html>`` or at the end.

    Example:
        html = inject_vite_dev_scripts(html, "http://localhost:5173", asset_url="/static/", is_react=True)
    """
    _ = vite_url
    base = asset_url.rstrip("/")
    nonce_attr = f' nonce="{_escape_attr(csp_nonce)}"' if csp_nonce else ""

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


def _find_manifest_integrity_for_file(manifest: dict[str, Any], file_path: str) -> str | None:
    """Return the SRI integrity attribute for a built file path in the manifest, if present."""
    for raw_val in manifest.values():
        if isinstance(raw_val, dict):
            item = cast("dict[str, Any]", raw_val)
            if item.get("file") == file_path:
                integrity = item.get("integrity")
                if isinstance(integrity, str) and integrity:
                    return integrity
    return None


def _inject_tag_attributes(tag_suffix: str, extra_attrs: str) -> str:
    """Insert ``extra_attrs`` before the closing ``>`` or ``/>`` of an HTML opening tag suffix."""
    if not extra_attrs:
        return tag_suffix
    if tag_suffix.endswith("/>"):
        return f"{tag_suffix[:-2].rstrip()}{extra_attrs} />"
    if tag_suffix.endswith(">"):
        return f"{tag_suffix[:-1]}{extra_attrs}>"
    return f"{tag_suffix}{extra_attrs}"


def _format_companion_link_tags(
    css_items: list[dict[str, Any]], import_items: list[dict[str, Any]], build_url: Any, nonce_attr: str
) -> str:
    """Render companion ``<link rel="stylesheet">`` and ``<link rel="modulepreload">`` tags."""
    tags: list[str] = []
    for css_item in css_items:
        css_url = build_url(css_item["file"])
        css_integrity = css_item.get("integrity")
        sri_attr = (
            f' integrity="{_escape_attr(css_integrity)}" crossorigin="anonymous"'
            if isinstance(css_integrity, str) and css_integrity
            else ""
        )
        tags.append(f'<link rel="stylesheet"{sri_attr}{nonce_attr} href="{_escape_attr(css_url)}" />')
    for imp_item in import_items:
        imp_url = build_url(imp_item["file"])
        imp_integrity = imp_item.get("integrity")
        if isinstance(imp_integrity, str) and imp_integrity:
            preload_attrs = f'crossorigin="anonymous" integrity="{_escape_attr(imp_integrity)}"{nonce_attr}'
        else:
            preload_attrs = f"crossorigin{nonce_attr}"
        tags.append(f'<link rel="modulepreload" {preload_attrs} href="{_escape_attr(imp_url)}" />')
    return "".join(tags)


def _collect_manifest_entry_assets(
    manifest: dict[str, Any], entry_key: str, emitted_css: set[str], emitted_preloads: set[str]
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Collect CSS descriptors and imported chunk descriptors recursively for a manifest entry.

    Args:
        manifest: The parsed Vite manifest dictionary.
        entry_key: Normalized manifest entry key.
        emitted_css: Set of already emitted CSS paths across the HTML document.
        emitted_preloads: Set of already emitted modulepreload file paths across the HTML document.

    Returns:
        A tuple of ``(css_items, import_items)``.
    """
    visited: set[str] = {entry_key}
    css_items: list[dict[str, Any]] = []
    import_items: list[dict[str, Any]] = []

    def _append_css_from(manifest_item: dict[str, Any]) -> None:
        for css_file in manifest_item.get("css", []):
            if isinstance(css_file, str) and css_file not in emitted_css:
                emitted_css.add(css_file)
                css_items.append({"file": css_file, "integrity": _find_manifest_integrity_for_file(manifest, css_file)})

    def _walk(keys: list[str]) -> None:
        for key in keys:
            if key in visited or key not in manifest:
                continue
            visited.add(key)
            raw_imp = manifest[key]
            if not isinstance(raw_imp, dict):
                continue
            imp_item = cast("dict[str, Any]", raw_imp)
            _append_css_from(imp_item)
            imp_file = imp_item.get("file")
            if (
                isinstance(imp_file, str)
                and imp_file
                and not imp_file.endswith(".css")
                and imp_file not in emitted_preloads
            ):
                emitted_preloads.add(imp_file)
                import_items.append(imp_item)
            raw_nested = imp_item.get("imports", [])
            if isinstance(raw_nested, list):
                nested = cast("list[Any]", raw_nested)
                _walk([str(k) for k in nested])

    raw_root = manifest.get(entry_key)
    if isinstance(raw_root, dict):
        root_entry = cast("dict[str, Any]", raw_root)
        _append_css_from(root_entry)
        raw_direct = root_entry.get("imports", [])
        if isinstance(raw_direct, list):
            direct_imports = cast("list[Any]", raw_direct)
            _walk([str(k) for k in direct_imports])

    return css_items, import_items


def transform_asset_urls(
    html: str,
    manifest: dict[str, Any],
    asset_url: str = "/static/",
    base_url: str | None = None,
    *,
    csp_nonce: str | None = None,
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
        csp_nonce: Optional Content Security Policy nonce to attach to transformed
            and injected ``<script>`` and ``<link>`` tags.

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
    """
    if not manifest:
        return html

    url_base = base_url or asset_url
    emitted_css: set[str] = set()
    emitted_preloads: set[str] = set()
    nonce_attr = f' nonce="{_escape_attr(csp_nonce)}"' if csp_nonce else ""

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
        """Replace script src with manifest lookup and prepend recursive CSS and modulepreload links.

        Returns:
            The transformed script tag with updated src and companion link tags, or original if not found.
        """
        prefix = match.group(1)
        src = match.group(2)
        suffix = match.group(3)

        normalized = _normalize_path(src)
        if normalized in manifest:
            raw_entry = manifest[normalized]
            entry = cast("dict[str, Any]", raw_entry) if isinstance(raw_entry, dict) else {}
            new_src = _build_url(str(entry.get("file", src)))
            css_items, import_items = _collect_manifest_entry_assets(
                manifest, normalized, emitted_css, emitted_preloads
            )
            companion = _format_companion_link_tags(css_items, import_items, _build_url, nonce_attr)
            extra_attrs = ""
            integrity = entry.get("integrity")
            if isinstance(integrity, str) and integrity and "integrity=" not in prefix and "integrity=" not in suffix:
                extra_attrs += f' integrity="{_escape_attr(integrity)}" crossorigin="anonymous"'
            if nonce_attr and "nonce=" not in prefix and "nonce=" not in suffix:
                extra_attrs += nonce_attr
            return companion + prefix + new_src + _inject_tag_attributes(suffix, extra_attrs)
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
            raw_entry = manifest[normalized]
            entry = cast("dict[str, Any]", raw_entry) if isinstance(raw_entry, dict) else {}
            new_href = _build_url(str(entry.get("file", href)))
            extra_attrs = ""
            integrity = entry.get("integrity")
            if isinstance(integrity, str) and integrity and "integrity=" not in prefix and "integrity=" not in suffix:
                extra_attrs += f' integrity="{_escape_attr(integrity)}" crossorigin="anonymous"'
            if nonce_attr and "nonce=" not in prefix and "nonce=" not in suffix:
                extra_attrs += nonce_attr
            return prefix + new_href + _inject_tag_attributes(suffix, extra_attrs)
        return match.group(0)

    html = _SCRIPT_SRC_PATTERN.sub(replace_script_src, html)

    return _LINK_HREF_PATTERN.sub(replace_link_href, html)
