"""Component fragment rendering engine for Litestar Vite."""

from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal, cast
from urllib.parse import urljoin

from litestar.exceptions import ImproperlyConfiguredException

if TYPE_CHECKING:
    from litestar_vite.config import ViteConfig
    from litestar_vite.ipc import BaseIPCTransport
    from litestar_vite.loader import ViteAssetLoader

__all__ = ("FragmentEngine",)


class FragmentEngine:
    """Orchestrates rendering UI component fragments over IPC transports."""

    __slots__ = ("_asset_loader", "_config", "_transport")

    def __init__(
        self, config: "ViteConfig", asset_loader: "ViteAssetLoader", transport: "BaseIPCTransport | None" = None
    ) -> None:
        """Initialize the fragment engine with configuration and asset loader.

        Args:
            config: Active ViteConfig instance.
            asset_loader: Active ViteAssetLoader for manifest CSS resolution.
            transport: Optional pre-configured BaseIPCTransport instance.
        """
        self._config = config
        self._asset_loader = asset_loader
        self._transport = transport

    def _get_transport(self) -> Any:
        """Resolve or lazily initialize the IPC transport for the active runtime mode.

        Returns:
            The resolved BaseIPCTransport instance.
        """
        if self._transport is None:
            from litestar_vite.ipc import StdioIPCTransport, TCPStreamIPCTransport

            if getattr(self._config, "is_dev_mode", False):
                host = getattr(self._config, "host", "127.0.0.1")
                port = getattr(self._config, "port", 5173)
                if host in {"::", "[::]", "localhost"} or host.startswith("0.0.0."):
                    host = "127.0.0.1"
                self._transport = TCPStreamIPCTransport(host=host, port=port, path="/__litestar_ssr__")
            else:
                self._transport = StdioIPCTransport(cwd=getattr(self._config, "root_dir", None))
        return self._transport

    def get_component_css_urls(self, component: str) -> list[str]:
        """Extract all CSS file URLs for a component from manifest or dev server.

        In production mode, looks up the component in the parsed manifest.json,
        collects its direct 'css' array, and recursively traverses 'imports'
        chunks to collect imported CSS dependencies with cycle detection.
        Normalizes paths using POSIX formatting to support Windows environments.

        In development mode, returns the direct component CSS URL or Vite dev
        server URL only for dedicated stylesheet files, omitting component entries
        such as .vue and .tsx to prevent browser MIME type rejections.

        Args:
            component: Relative path to the component, e.g. 'components/UserProfile.vue'.

        Returns:
            List of resolved CSS URLs.
        """
        loader: Any = self._asset_loader
        if hasattr(loader, "get_component_css_urls"):
            return list(cast("list[str]", loader.get_component_css_urls(component)))

        if getattr(loader, "_is_hot_dev", False):
            if component.endswith((".css", ".scss", ".sass", ".less", ".styl")):
                vite_url_fn = getattr(loader, "_vite_server_url", None)
                url = (
                    str(vite_url_fn(component)) if callable(vite_url_fn) else urljoin(self._config.asset_url, component)
                )
                return [url]
            return []

        manifest: dict[str, Any] = getattr(self._asset_loader, "_manifest", {}) or getattr(
            self._asset_loader, "manifest", {}
        )
        if not manifest:
            return []

        normalized_key = Path(component.replace("\\", "/")).as_posix().lstrip("/")
        manifest_entry = manifest.get(normalized_key)
        if manifest_entry is None and hasattr(self._config, "resource_dir"):
            resource_prefix = Path(str(self._config.resource_dir).replace("\\", "/")).as_posix().strip("/") + "/"
            if not normalized_key.startswith(resource_prefix):
                manifest_entry = manifest.get(f"{resource_prefix}{normalized_key}")

        if manifest_entry is None:
            return []

        collected_css: list[str] = []
        visited_chunks: set[str] = set()
        asset_base = self._config.asset_url

        def _collect_from_entry(entry: dict[str, Any]) -> None:
            for css_file in entry.get("css", []):
                url = urljoin(asset_base, css_file)
                if url not in collected_css:
                    collected_css.append(url)
            for import_chunk in entry.get("imports", []):
                if import_chunk not in visited_chunks and import_chunk in manifest:
                    visited_chunks.add(import_chunk)
                    _collect_from_entry(manifest[import_chunk])

        _collect_from_entry(manifest_entry)
        return collected_css

    def generate_component_css_tags(self, component: str, newline: str = "\n") -> str:
        """Generate HTML link tags for a component's scoped styles.

        Args:
            component: Relative path to the component entrypoint.
            newline: Line ending character to join multiple tags.

        Returns:
            String of HTML link tags, or empty string if no CSS is associated.
        """
        loader: Any = self._asset_loader
        if hasattr(loader, "generate_component_css_tags"):
            return str(loader.generate_component_css_tags(component))

        css_urls = self.get_component_css_urls(component)
        if not css_urls:
            return ""
        return newline.join(f'<link rel="stylesheet" href="{url}" />' for url in css_urls)

    async def render_fragment(
        self, component: str, props: dict[str, Any] | None = None, mode: Literal["static", "island"] = "static"
    ) -> str:
        """Render a UI component fragment to HTML asynchronously.

        Sends render request to the background IPC worker, retrieves the rendered
        markup, and prepends scoped CSS link tags resolved from manifest.json.

        Args:
            component: Path to the component entrypoint, e.g. 'components/Counter.vue'.
            props: Optional dictionary of component props.
            mode: Rendering mode, either 'static' (zero JS) or 'island' (interactive).

        Returns:
            Rendered HTML string with scoped CSS links prepended.

        Raises:
            ImproperlyConfiguredException: If the IPC worker reports a render error.
        """
        transport: Any = self._get_transport()
        payload: dict[str, Any] = {
            "method": "render_fragment",
            "params": {"component": component, "props": props or {}, "mode": mode},
        }

        try:
            response: Any = await transport.send_request(payload)
        except Exception as exc:
            msg = f"Failed to render component fragment {component!r}: {exc}"
            raise ImproperlyConfiguredException(msg) from exc

        resp_dict: dict[str, Any] = cast("dict[str, Any]", response) if isinstance(response, dict) else {}
        if isinstance(response, dict) and "error" in response:
            error_message = str(resp_dict.get("error", "Unknown IPC worker error"))
            msg = f"Failed to render component fragment {component!r}: {error_message}"
            raise ImproperlyConfiguredException(msg)

        res_obj = resp_dict.get("result", response)
        res_dict: dict[str, Any] = cast("dict[str, Any]", res_obj) if isinstance(res_obj, dict) else {}
        html_body: str = str(res_dict.get("html", res_obj))

        newline = "\r\n" if "\r\n" in html_body else "\n"
        css_tags = self.generate_component_css_tags(component, newline=newline)

        if css_tags:
            return f"{css_tags}{newline}{html_body}"
        return html_body

    def render_fragment_sync(
        self, component: str, props: dict[str, Any] | None = None, mode: Literal["static", "island"] = "static"
    ) -> str:
        """Render a UI component fragment synchronously for template engines.

        Executes the async render_fragment method on the worker loop using anyio.
        Falls back to anyio.run when no event loop is active on the current thread.

        Args:
            component: Path to the component entrypoint.
            props: Optional dictionary of component props.
            mode: Rendering mode.

        Returns:
            Rendered HTML string with scoped CSS links prepended.
        """
        try:
            import anyio.from_thread

            return anyio.from_thread.run(self.render_fragment, component, props, mode)
        except RuntimeError:
            import anyio

            return anyio.run(self.render_fragment, component, props, mode)
