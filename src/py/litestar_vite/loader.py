import json
from functools import cached_property
from pathlib import Path
from textwrap import dedent
from typing import TYPE_CHECKING, Any, Optional, Union, cast
from urllib.parse import urljoin

import markupsafe
from litestar.exceptions import ImproperlyConfiguredException

if TYPE_CHECKING:
    from collections.abc import Mapping

    from litestar.connection import Request

    from litestar_vite.config import ViteConfig
    from litestar_vite.plugin import VitePlugin


def _get_request_from_context(context: "Mapping[str, Any]") -> "Request[Any, Any, Any]":
    """Get the request from the template context.

    Args:
        context: The template context.

    Returns:
        The request object.
    """
    return cast("Request[Any, Any, Any]", context["request"])


def render_hmr_client(context: "Mapping[str, Any]", /) -> "markupsafe.Markup":
    """Render the HMR client.

    Args:
        context: The template context.

    Returns:
        The HMR client.
    """
    return cast(
        "VitePlugin", _get_request_from_context(context).app.plugins.get("VitePlugin")
    ).asset_loader.render_hmr_client()


def render_asset_tag(
    context: "Mapping[str, Any]", /, path: "Union[str, list[str]]", scripts_attrs: "Optional[dict[str, str]]" = None
) -> "markupsafe.Markup":
    """Render an asset tag.

    Args:
        context: The template context.
        path: The path to the asset.
        scripts_attrs: The attributes for the script tag.

    Returns:
        The asset tag.
    """
    return cast(
        "VitePlugin", _get_request_from_context(context).app.plugins.get("VitePlugin")
    ).asset_loader.render_asset_tag(path, scripts_attrs)


class SingletonMeta(type):
    """Singleton metaclass."""

    _instances: "dict[type, Any]" = {}

    def __call__(cls, *args: "Any", **kwargs: "Any") -> "Any":
        if cls not in cls._instances:  # pyright: ignore[reportUnnecessaryContains]
            cls._instances[cls] = super().__call__(*args, **kwargs)
        return cls._instances[cls]


class ViteAssetLoader(metaclass=SingletonMeta):
    """Vite  manifest loader.

    Please see: https://vitejs.dev/guide/backend-integration.html
    """

    _config: "ViteConfig"
    _manifest: "dict[str, Any]"
    _manifest_content: "str"
    _vite_base_path: "Optional[str]"

    def __init__(self, config: "ViteConfig") -> None:
        """Initialize the manifest loader.

        Args:
            config: The Vite configuration.
        """
        self._config = config
        self._manifest: "dict[str, Any]" = {}
        self._manifest_content: "str" = ""
        self._vite_base_path: "Optional[str]" = None

    @classmethod
    def initialize_loader(cls, config: "ViteConfig") -> "ViteAssetLoader":
        """Initialize the manifest loader.

        Args:
            config: The Vite configuration.

        Returns:
            The manifest loader.
        """
        loader = cls(config=config)
        loader.parse_manifest()
        return loader

    @cached_property
    def version_id(self) -> str:
        """Get the version ID of the manifest.

        Returns:
            The version ID of the manifest.
        """
        if self._manifest_content:
            return str(hash(self.manifest_content))
        return "1.0"

    def render_hmr_client(self) -> "markupsafe.Markup":
        """Render the HMR client.

        Returns:
            The HMR client.
        """
        return markupsafe.Markup(
            f"{self.generate_react_hmr_tags()}{self.generate_ws_client_tags()}",
        )

    def render_asset_tag(
        self, path: "Union[str, list[str]]", scripts_attrs: "Optional[dict[str, str]]" = None
    ) -> "markupsafe.Markup":
        """Render an asset tag.

        Args:
            path: The path to the asset.
            scripts_attrs: The attributes for the script tag.

        Returns:
            The asset tag.
        """
        path = [str(p) for p in path] if isinstance(path, list) else [str(path)]
        return markupsafe.Markup(
            "".join([self.generate_asset_tags(p, scripts_attrs=scripts_attrs) for p in path]),
        )

    def parse_manifest(self) -> None:
        """Parse the Vite manifest file.

        The manifest file is a JSON file that maps source files to their corresponding output files.
        Example manifest file structure:

        .. code-block:: json

            {
                "main.js": {
                    "file": "assets/main.4889e940.js",
                    "src": "main.js",
                    "isEntry": true,
                    "dynamicImports": ["views/foo.js"],
                    "css": ["assets/main.b82dbe22.css"],
                    "assets": ["assets/asset.0ab0f9cd.png"]
                },
                "views/foo.js": {
                    "file": "assets/foo.869aea0d.js",
                    "src": "views/foo.js",
                    "isDynamicEntry": true,
                    "imports": ["_shared.83069a53.js"]
                },
                "_shared.83069a53.js": {
                    "file": "assets/shared.83069a53.js"
                }
            }

        The manifest is parsed and stored in memory for asset resolution during template rendering.

        Raises:
            RuntimeError: If the manifest file is not found or cannot be read.
        """
        if self._config.hot_reload and self._config.dev_mode:
            hot_file_path = Path(
                f"{self._config.bundle_dir}/{self._config.hot_file}",
            )
            if hot_file_path.exists():
                with hot_file_path.open() as hot_file:
                    self._vite_base_path = hot_file.read()

        else:
            manifest_path = Path(f"{self._config.bundle_dir}/{self._config.manifest_name}")
            try:
                if manifest_path.exists():
                    with manifest_path.open() as manifest_file:
                        self.manifest_content = manifest_file.read()
                        self._manifest = json.loads(self.manifest_content)
                else:
                    self._manifest = {}
            except Exception as exc:
                msg = "There was an issue reading the Vite manifest file at  %s. Did you forget to build your assets?"
                raise RuntimeError(
                    msg,
                    manifest_path,
                ) from exc

    def generate_ws_client_tags(self) -> str:
        """Generate the script tag for the Vite WS client for HMR.

        Only used when hot module reloading is enabled, in production this method returns an empty string.

        Returns:
            str: The script tag or an empty string.
        """
        if self._config.hot_reload and self._config.dev_mode:
            return self._script_tag(
                self._vite_server_url("@vite/client"),
                {"type": "module"},
            )
        return ""

    def generate_react_hmr_tags(self) -> str:
        """Generate the script tag for the Vite WS client for HMR.

        Only used when hot module reloading is enabled, in production this method returns an empty string.

        Returns:
            str: The script tag or an empty string.
        """
        if self._config.is_react and self._config.hot_reload and self._config.dev_mode:
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
        self, path: "Union[str, list[str]]", scripts_attrs: "Optional[dict[str, str]]" = None
    ) -> str:
        """Generate all assets include tags for the file in argument.

        Args:
            path: The path to the asset.
            scripts_attrs: The attributes for the script tag.

        Raises:
            ImproperlyConfiguredException: If the manifest file is not found or cannot be read.

        Returns:
            str: All tags to import this asset in your HTML page.
        """
        if isinstance(path, str):
            path = [path]
        if self._config.hot_reload and self._config.dev_mode:
            return "".join(
                [
                    self._style_tag(self._vite_server_url(p))
                    if p.endswith(".css")
                    else self._script_tag(
                        self._vite_server_url(p),
                        {"type": "module", "async": "", "defer": ""},
                    )
                    for p in path
                ],
            )

        if any(p for p in path if p not in self._manifest):
            msg = "Cannot find %s in Vite manifest at %s.  Did you forget to build your assets after an update?"
            raise ImproperlyConfiguredException(
                msg,
                path,
                Path(f"{self._config.bundle_dir}/{self._config.manifest_name}"),
            )

        tags: list[str] = []
        manifest_entry: dict[str, Any] = {}
        manifest_entry.update({p: self._manifest[p] for p in path if p})
        if not scripts_attrs:
            scripts_attrs = {"type": "module", "async": "", "defer": ""}
        for manifest in manifest_entry.values():
            if "css" in manifest:
                tags.extend(
                    self._style_tag(urljoin(self._config.asset_url, css_path)) for css_path in manifest.get("css", {})
                )
            # Add dependent "vendor"
            if "imports" in manifest:
                tags.extend(
                    self.generate_asset_tags(vendor_path, scripts_attrs=scripts_attrs)
                    for vendor_path in manifest.get("imports", {})
                )
            # Add the script by itself
            if manifest.get("file").endswith(".css"):
                tags.append(
                    self._style_tag(urljoin(self._config.asset_url, manifest["file"])),
                )
            else:
                tags.append(
                    self._script_tag(
                        urljoin(self._config.asset_url, manifest["file"]),
                        attrs=scripts_attrs,
                    ),
                )
        return "".join(tags)

    def _vite_server_url(self, path: "Optional[str]" = None) -> str:
        """Generate an URL to and asset served by the Vite development server.

        Keyword Arguments:
            path: Path to the asset. (default: {None})

        Returns:
            str: Full URL to the asset.
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
            src: The source of the script.
            attrs: The attributes for the script tag.

        Returns:
            str: The script tag.
        """
        if attrs is None:
            attrs = {}
        attrs_str = " ".join([f'{key}="{value}"' for key, value in attrs.items()])
        return f'<script {attrs_str} src="{src}"></script>'

    @staticmethod
    def _style_tag(href: str) -> str:
        """Generate and HTML <link> stylesheet tag for CSS.

        Args:
            href: CSS file URL.

        Returns:
            str: CSS link tag.
        """
        return f'<link rel="stylesheet" href="{href}" />'
