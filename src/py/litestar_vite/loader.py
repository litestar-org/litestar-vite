"""Vite Asset Loader.

This module provides the ViteAssetLoader class for loading and rendering
Vite-managed assets. The loader handles both development mode (with HMR)
and production mode (with manifest-based asset resolution).

Key features:
- Async initialization for non-blocking I/O during app startup
- Manifest parsing for production asset resolution
- HMR client script generation for development
- React Fast Refresh support
"""

import hashlib
import json
from functools import cached_property
from pathlib import Path
from textwrap import dedent
from typing import TYPE_CHECKING, Any, Optional, Union
from urllib.parse import urljoin

import anyio
import markupsafe

from litestar_vite.exceptions import AssetNotFoundError, ManifestNotFoundError

if TYPE_CHECKING:
    from collections.abc import Mapping

    from litestar.connection import Request

    from litestar_vite.config import ViteConfig
    from litestar_vite.plugin import VitePlugin


def _get_request_from_context(
    context: "Mapping[str, Any]",
) -> "Request[Any, Any, Any]":
    """Get the request from the template context.

    Args:
        context: The template context.

    Returns:
        The request object.
    """
    from litestar.connection import Request

    request = context.get("request")
    if request is None:
        msg = "Request not found in template context. Ensure 'request' is passed to the template."
        raise ValueError(msg)
    if not isinstance(request, Request):  # pyright: ignore[reportUnknownVariableType]
        msg = f"Expected Request object, got {type(request)}"
        raise TypeError(msg)
    return request  # pyright: ignore[reportReturnType,reportUnknownVariableType]


def _get_vite_plugin(context: "Mapping[str, Any]") -> "Optional[VitePlugin]":
    """Get the VitePlugin from the template context.

    Args:
        context: The template context.

    Returns:
        The VitePlugin instance or None if not found.
    """
    request = _get_request_from_context(context)
    return request.app.plugins.get("VitePlugin")


def render_hmr_client(context: "Mapping[str, Any]", /) -> "markupsafe.Markup":
    """Render the HMR client script tag.

    This is a Jinja2 template callable that renders the Vite HMR client
    script tag for development mode.

    Args:
        context: The template context containing the request.

    Returns:
        HTML markup for the HMR client script.
    """
    vite_plugin = _get_vite_plugin(context)
    if vite_plugin is None:
        return markupsafe.Markup("")
    return vite_plugin.asset_loader.render_hmr_client()


def render_asset_tag(
    context: "Mapping[str, Any]",
    /,
    path: "Union[str, list[str]]",
    scripts_attrs: "Optional[dict[str, str]]" = None,
) -> "markupsafe.Markup":
    """Render asset tags for the specified path(s).

    This is a Jinja2 template callable that renders script/link tags
    for Vite-managed assets. Also works for HTMX partial responses.

    Args:
        context: The template context containing the request.
        path: Single path or list of paths to assets.
        scripts_attrs: Optional attributes for script tags.

    Returns:
        HTML markup for the asset tags.

    Example:
        In a Jinja2 template:
        {{ vite_asset("src/main.ts") }}
        {{ vite_asset("src/components/UserProfile.tsx") }}  # For partials
    """
    vite_plugin = _get_vite_plugin(context)
    if vite_plugin is None:
        return markupsafe.Markup("")
    return vite_plugin.asset_loader.render_asset_tag(path, scripts_attrs)


def render_static_asset(context: "Mapping[str, Any]", /, path: str) -> str:
    """Render a static asset URL.

    This is a Jinja2 template callable that returns the URL for a static asset.

    Args:
        context: The template context containing the request.
        path: Path to the static asset.

    Returns:
        The full URL to the static asset.
    """
    vite_plugin = _get_vite_plugin(context)
    if vite_plugin is None:
        return ""
    return vite_plugin.asset_loader.get_static_asset(path)


# Backward compatibility alias for render_asset_tag
# Previously render_partial_asset_tag was a separate function with identical implementation
render_partial_asset_tag = render_asset_tag


class ViteAssetLoader:
    """Vite asset loader for managing frontend assets.

    This class handles loading and rendering of Vite-managed assets.
    It supports both development mode (with HMR) and production mode
    (with manifest-based asset resolution).

    The loader is designed to be instantiated per-app (not a singleton)
    and supports async initialization for non-blocking file I/O.

    Attributes:
        config: The Vite configuration.

    Example:
        loader = ViteAssetLoader(config)
        await loader.initialize()
        html = loader.render_asset_tag("src/main.ts")
    """

    def __init__(self, config: "ViteConfig") -> None:
        """Initialize the asset loader.

        Args:
            config: The Vite configuration.
        """
        self._config = config
        self._manifest: dict[str, Any] = {}
        self._manifest_content: str = ""
        self._vite_base_path: "Optional[str]" = None
        self._initialized: bool = False

    @classmethod
    def initialize_loader(cls, config: "ViteConfig") -> "ViteAssetLoader":
        """Synchronously initialize a loader instance.

        This is a convenience method for synchronous initialization.
        For async contexts, prefer using `initialize()` after construction.

        Args:
            config: The Vite configuration.

        Returns:
            An initialized ViteAssetLoader instance.
        """
        loader = cls(config=config)
        loader.parse_manifest()
        return loader

    async def initialize(self) -> None:
        """Asynchronously initialize the loader.

        This method performs async file I/O to load the manifest or hot file.
        Call this during app startup in an async context.
        """
        if self._initialized:
            return

        if self._config.hot_reload and self._config.is_dev_mode:
            await self._load_hot_file_async()
        else:
            await self._load_manifest_async()

        self._initialized = True

    def parse_manifest(self) -> None:
        """Synchronously parse the Vite manifest file.

        This method reads the manifest.json file in production mode
        or the hot file in development mode.

        Note: For async contexts, use `initialize()` instead.
        """
        if self._config.hot_reload and self._config.is_dev_mode:
            self._load_hot_file_sync()
        else:
            self._load_manifest_sync()

    # --- Internal file loading methods (consolidated sync/async) ---

    def _get_manifest_path(self) -> Path:
        """Get the path to the manifest file."""
        return self._config.bundle_dir / self._config.manifest_name

    def _get_hot_file_path(self) -> Path:
        """Get the path to the hot file."""
        return self._config.bundle_dir / self._config.hot_file

    async def _load_manifest_async(self) -> None:
        """Asynchronously load and parse the Vite manifest file."""
        manifest_path = anyio.Path(self._get_manifest_path())
        try:
            if await manifest_path.exists():
                content = await manifest_path.read_text()
                self._manifest_content = content
                self._manifest = json.loads(content)
            else:
                self._manifest = {}
        except Exception as exc:
            raise ManifestNotFoundError(str(manifest_path)) from exc

    def _load_manifest_sync(self) -> None:
        """Synchronously load and parse the Vite manifest file."""
        manifest_path = self._get_manifest_path()
        try:
            if manifest_path.exists():
                self._manifest_content = manifest_path.read_text()
                self._manifest = json.loads(self._manifest_content)
            else:
                self._manifest = {}
        except Exception as exc:
            raise ManifestNotFoundError(str(manifest_path)) from exc

    async def _load_hot_file_async(self) -> None:
        """Asynchronously read the hot file for dev server URL."""
        hot_file_path = anyio.Path(self._get_hot_file_path())
        if await hot_file_path.exists():
            self._vite_base_path = await hot_file_path.read_text()

    def _load_hot_file_sync(self) -> None:
        """Synchronously read the hot file for dev server URL."""
        hot_file_path = self._get_hot_file_path()
        if hot_file_path.exists():
            self._vite_base_path = hot_file_path.read_text()

    # --- Deprecated async methods (kept for backward compatibility) ---

    async def _parse_manifest_async(self) -> None:
        """Asynchronously parse the Vite manifest file.

        Deprecated: Use _load_manifest_async instead.
        """
        await self._load_manifest_async()

    async def _read_hot_file(self) -> None:
        """Asynchronously read the hot file for dev server URL.

        Deprecated: Use _load_hot_file_async instead.
        """
        await self._load_hot_file_async()

    # --- Properties ---

    @property
    def manifest_content(self) -> str:
        """Get the raw manifest content."""
        return self._manifest_content

    @manifest_content.setter
    def manifest_content(self, value: str) -> None:
        """Set the manifest content."""
        self._manifest_content = value

    @cached_property
    def version_id(self) -> str:
        """Get the version ID of the manifest.

        The version ID is used for cache busting and Inertia.js asset versioning.

        Returns:
            A hash of the manifest content, or "1.0" if no manifest.
        """
        if self._manifest_content:
            return hashlib.sha256(self._manifest_content.encode("utf-8")).hexdigest()
        return "1.0"

    # --- HTML generation methods ---

    def render_hmr_client(self) -> "markupsafe.Markup":
        """Render the HMR client script tags.

        Returns:
            HTML markup containing React HMR and Vite client script tags.
        """
        return markupsafe.Markup(f"{self.generate_react_hmr_tags()}{self.generate_ws_client_tags()}")

    def render_asset_tag(
        self,
        path: "Union[str, list[str]]",
        scripts_attrs: "Optional[dict[str, str]]" = None,
    ) -> "markupsafe.Markup":
        """Render asset tags for the specified path(s).

        Args:
            path: Single path or list of paths to assets.
            scripts_attrs: Optional attributes for script tags.

        Returns:
            HTML markup for script and link tags.
        """
        paths = [str(p) for p in path] if isinstance(path, list) else [str(path)]
        return markupsafe.Markup("".join(self.generate_asset_tags(p, scripts_attrs=scripts_attrs) for p in paths))

    def get_static_asset(self, path: str) -> str:
        """Get the URL for a static asset.

        Args:
            path: The path to the asset.

        Returns:
            The full URL to the asset.

        Raises:
            AssetNotFoundError: If the asset is not in the manifest.
        """
        if self._config.hot_reload and self._config.is_dev_mode:
            return self._vite_server_url(path)

        if path not in self._manifest:
            raise AssetNotFoundError(path, str(self._get_manifest_path()))

        return urljoin(
            self._config.base_url or self._config.asset_url,
            self._manifest[path]["file"],
        )

    def generate_ws_client_tags(self) -> str:
        """Generate the Vite HMR client script tag.

        Only generates output in development mode with hot reload enabled.

        Returns:
            Script tag HTML or empty string in production.
        """
        if self._config.hot_reload and self._config.is_dev_mode:
            return self._script_tag(
                self._vite_server_url("@vite/client"),
                {"type": "module"},
            )
        return ""

    def generate_react_hmr_tags(self) -> str:
        """Generate React Fast Refresh preamble script.

        Only generates output when React mode is enabled in development.

        Returns:
            React refresh script HTML or empty string.
        """
        if self._config.is_react and self._config.hot_reload and self._config.is_dev_mode:
            return dedent(f"""
                <script type="module">
                import RefreshRuntime from '{self._vite_server_url()}@react-refresh'
                RefreshRuntime.injectIntoGlobalHook(window)
                window.$RefreshReg$ = () => {{}}
                window.$RefreshSig$ = () => (type) => type
                window.__vite_plugin_react_preamble_installed__=true
                </script>
                """)
        return ""

    def generate_asset_tags(
        self,
        path: "Union[str, list[str]]",
        scripts_attrs: "Optional[dict[str, str]]" = None,
    ) -> str:
        """Generate all asset tags for the specified file(s).

        Args:
            path: Path or list of paths to assets.
            scripts_attrs: Optional attributes for script tags.

        Returns:
            HTML string with all necessary script and link tags.

        Raises:
            ImproperlyConfiguredException: If asset not found in manifest.
        """
        from litestar.exceptions import ImproperlyConfiguredException

        if isinstance(path, str):
            path = [path]

        # Development mode - serve from Vite dev server
        if self._config.hot_reload and self._config.is_dev_mode:
            return "".join(
                self._style_tag(self._vite_server_url(p))
                if p.endswith(".css")
                else self._script_tag(
                    self._vite_server_url(p),
                    {"type": "module", "async": "", "defer": ""},
                )
                for p in path
            )

        # Production mode - use manifest
        missing = [p for p in path if p not in self._manifest]
        if missing:
            msg = "Cannot find %s in Vite manifest at %s. Did you forget to build your assets after an update?"
            raise ImproperlyConfiguredException(msg, missing, self._get_manifest_path())

        tags: list[str] = []
        manifest_entries = {p: self._manifest[p] for p in path if p}

        if not scripts_attrs:
            scripts_attrs = {"type": "module", "async": "", "defer": ""}

        asset_url_base = self._config.base_url or self._config.asset_url

        for manifest in manifest_entries.values():
            # Add CSS files
            if "css" in manifest:
                tags.extend(self._style_tag(urljoin(asset_url_base, css_path)) for css_path in manifest.get("css", []))

            # Add imported dependencies
            if "imports" in manifest:
                tags.extend(
                    self.generate_asset_tags(vendor_path, scripts_attrs=scripts_attrs)
                    for vendor_path in manifest.get("imports", [])
                )

            # Add the main file
            file_path = manifest.get("file", "")
            if file_path.endswith(".css"):
                tags.append(self._style_tag(urljoin(asset_url_base, file_path)))
            else:
                tags.append(
                    self._script_tag(
                        urljoin(asset_url_base, file_path),
                        attrs=scripts_attrs,
                    )
                )

        return "".join(tags)

    def _vite_server_url(self, path: "Optional[str]" = None) -> str:
        """Generate a URL to an asset on the Vite development server.

        Args:
            path: Optional path to append to the base URL.

        Returns:
            Full URL to the asset on the dev server.
        """
        base_path = self._vite_base_path or f"{self._config.protocol}://{self._config.host}:{self._config.port}"
        return urljoin(
            base_path,
            urljoin(self._config.asset_url, path if path is not None else ""),
        )

    @staticmethod
    def _script_tag(src: str, attrs: "Optional[dict[str, str]]" = None) -> str:
        """Generate an HTML script tag.

        Args:
            src: The source URL for the script.
            attrs: Optional attributes for the script tag.

        Returns:
            HTML script tag string.
        """
        if attrs is None:
            attrs = {}
        attrs_str = " ".join(f'{key}="{value}"' for key, value in attrs.items())
        return f'<script {attrs_str} src="{src}"></script>'

    @staticmethod
    def _style_tag(href: str) -> str:
        """Generate an HTML link tag for CSS.

        Args:
            href: The URL to the CSS file.

        Returns:
            HTML link tag string.
        """
        return f'<link rel="stylesheet" href="{href}" />'
