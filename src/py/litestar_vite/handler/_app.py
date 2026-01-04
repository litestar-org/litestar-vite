"""SPA mode handler for Vite integration.

This module provides :class:`~litestar_vite.handler.AppHandler` which manages serving
the Single Page Application (SPA) HTML in both development and production modes.

In dev mode, it proxies requests to the Vite dev server for HMR support.
In production, it serves the built index.html with async caching.
"""

import logging
from contextlib import suppress
from functools import lru_cache
from pathlib import Path
from typing import TYPE_CHECKING, Any, NoReturn

import anyio
import httpx
from litestar import get
from litestar.exceptions import ImproperlyConfiguredException, SerializationException
from litestar.serialization import decode_json, encode_json

from litestar_vite.config import InertiaConfig
from litestar_vite.handler._routing import spa_handler_dev, spa_handler_prod
from litestar_vite.html_transform import (
    inject_head_script,
    inject_page_script,
    inject_vite_dev_scripts,
    set_data_attribute,
    transform_asset_urls,
)
from litestar_vite.utils import get_static_resource_path, read_hotfile_url

if TYPE_CHECKING:
    from litestar.connection import Request
    from litestar.types import Guard  # pyright: ignore[reportUnknownVariableType]

    from litestar_vite.config import SPAConfig, ViteConfig

logger = logging.getLogger("litestar_vite")

_SERVER_STARTING_PATH = get_static_resource_path("server-starting.html")


@lru_cache(maxsize=1)
def _load_server_starting_template() -> str:
    """Load the server starting HTML template once."""
    try:
        return _SERVER_STARTING_PATH.read_text()
    except (FileNotFoundError, IsADirectoryError, OSError):
        # Fallback minimal HTML if the built file is missing
        logger.warning("Server starting page not found at %s", _SERVER_STARTING_PATH)
        return """<!DOCTYPE html>
<html><head><meta http-equiv="refresh" content="2"><title>Starting...</title></head>
<body style="background:#202235;color:#dcdfe4;font-family:system-ui;display:flex;align-items:center;justify-content:center;height:100vh;margin:0">
<div style="text-align:center"><h1>Server starting...</h1><p>Connecting to {{ vite_url }}</p></div>
</body></html>"""


def _get_server_starting_html(vite_url: str) -> str:
    """Load and format the server starting page.

    The HTML is loaded from a pre-built static file that ships with the package.
    Uses module-level caching to avoid repeated file I/O.

    Args:
        vite_url: The Vite dev server URL to display.

    Returns:
        Formatted HTML string with the vite_url substituted.
    """
    return _load_server_starting_template().replace("{{ vite_url }}", vite_url)


class AppHandler:
    """Handler for serving SPA HTML in both dev and production modes."""

    __slots__ = (
        "_cached_bytes",
        "_cached_html",
        "_cached_transformed_html",
        "_config",
        "_http_client",
        "_http_client_sync",
        "_initialized",
        "_manifest",
        "_spa_config",
        "_vite_url",
    )

    def __init__(self, config: "ViteConfig") -> None:
        """Initialize the SPA handler.

        Args:
            config: The Vite configuration.
        """
        self._config = config
        self._spa_config: "SPAConfig | None" = config.spa_config
        self._cached_html: "str | None" = None
        self._cached_bytes: "bytes | None" = None
        self._cached_transformed_html: "str | None" = None
        self._initialized = False
        self._http_client: "httpx.AsyncClient | None" = None
        self._http_client_sync: "httpx.Client | None" = None
        self._vite_url: "str | None" = None
        self._manifest: "dict[str, Any]" = {}

    @property
    def is_initialized(self) -> bool:
        """Whether the handler has been initialized.

        Returns:
            True when initialized, otherwise False.
        """
        return self._initialized

    async def initialize_async(self, vite_url: "str | None" = None) -> None:
        """Initialize the handler asynchronously.

        Args:
            vite_url: Optional Vite server URL to use for proxying.
        """
        if self._initialized:
            return

        if self._config.is_dev_mode and self._config.hot_reload:
            self._init_http_clients(vite_url)
        else:
            await self._load_production_assets_async()

        self._initialized = True

    def initialize_sync(self, vite_url: "str | None" = None) -> None:
        """Initialize the handler synchronously.

        Args:
            vite_url: Optional Vite server URL to use for proxying.
        """
        if self._initialized:
            return

        if self._config.is_dev_mode and self._config.hot_reload:
            self._init_http_clients(vite_url)
        else:
            self._load_production_assets_sync()

        self._initialized = True

    def _init_http_clients(self, vite_url: "str | None" = None) -> None:
        """Initialize HTTP clients for dev mode proxying."""
        self._vite_url = vite_url or self._resolve_vite_url()

        http2_enabled = self._config.http2
        if http2_enabled:
            try:
                import h2  # noqa: F401  # pyright: ignore[reportMissingImports,reportUnusedImport]
            except ImportError:
                http2_enabled = False

        self._http_client = httpx.AsyncClient(timeout=httpx.Timeout(5.0), http2=http2_enabled)
        self._http_client_sync = httpx.Client(timeout=httpx.Timeout(5.0))

    async def shutdown_async(self) -> None:
        """Shutdown the handler asynchronously."""
        if self._http_client is not None:
            with suppress(RuntimeError):
                await self._http_client.aclose()
            self._http_client = None
        if self._http_client_sync is not None:
            with suppress(RuntimeError):
                self._http_client_sync.close()
            self._http_client_sync = None

    def _load_production_assets_sync(self) -> None:
        """Load manifest and index.html synchronously in production modes."""
        if self._config.mode != "external":
            self._load_manifest_sync()
        self._load_index_html_sync()

    async def _load_production_assets_async(self) -> None:
        """Load manifest and index.html asynchronously in production modes."""
        if self._config.mode != "external":
            await self._load_manifest_async()
        await self._load_index_html_async()

    def _transform_html(
        self, html: str, page_data: "dict[str, Any] | None" = None, csrf_token: "str | None" = None
    ) -> str:
        """Transform HTML by injecting CSRF token and/or page data.

        Returns:
            The transformed HTML.
        """
        if self._spa_config is None:
            if page_data is not None:
                json_data = encode_json(page_data).decode("utf-8")
                html = set_data_attribute(html, "#app", "data-page", json_data)
            return html

        if self._spa_config.inject_csrf and csrf_token:
            script = f'window.{self._spa_config.csrf_var_name} = "{csrf_token}";'
            html = inject_head_script(html, script, escape=False, nonce=self._config.csp_nonce)

        if page_data is not None:
            json_data = encode_json(page_data).decode("utf-8")
            # Check InertiaConfig for use_script_element (Inertia-specific setting)
            inertia = self._config.inertia
            use_script_element = isinstance(inertia, InertiaConfig) and inertia.use_script_element
            if use_script_element:
                # v2.3+ Inertia protocol: Use script element for better performance (~37% smaller)
                html = inject_page_script(html, json_data, nonce=self._config.csp_nonce)
            else:
                # Legacy: Use data-page attribute
                html = set_data_attribute(html, self._spa_config.app_selector, "data-page", json_data)

        return html

    async def _load_index_html_async(self) -> None:
        """Load and cache index.html asynchronously."""
        resolved_path: Path | None = None
        for candidate in self._config.candidate_index_html_paths():
            candidate_path = anyio.Path(candidate)
            if await candidate_path.exists():
                resolved_path = candidate
                break

        if resolved_path is None:
            self._raise_index_not_found()

        raw_bytes = await anyio.Path(resolved_path).read_bytes()
        html = raw_bytes.decode("utf-8")
        html = self._transform_asset_urls_in_html(html)

        self._cached_html = html
        self._cached_bytes = html.encode("utf-8")

    def _load_index_html_sync(self) -> None:
        """Load and cache index.html synchronously."""
        resolved_path: Path | None = None
        for candidate in self._config.candidate_index_html_paths():
            candidate_path = Path(candidate)
            if candidate_path.exists():
                resolved_path = candidate_path
                break

        if resolved_path is None:
            self._raise_index_not_found()

        raw_bytes = resolved_path.read_bytes()
        html = raw_bytes.decode("utf-8")
        html = self._transform_asset_urls_in_html(html)

        self._cached_html = html
        self._cached_bytes = html.encode("utf-8")

    def _raise_index_not_found(self) -> NoReturn:
        """Raise an exception when index.html is not found.

        Raises:
            ImproperlyConfiguredException: Always raised.
        """
        joined_paths = ", ".join(str(path) for path in self._config.candidate_index_html_paths())
        msg = (
            "index.html not found. "
            f"Checked: {joined_paths}. "
            "SPA mode requires index.html in one of the expected locations. "
            "Did you forget to build your assets?"
        )
        raise ImproperlyConfiguredException(msg)

    def _get_manifest_path(self) -> Path:
        """Get the path to the Vite manifest file.

        Returns:
            Absolute path to the manifest file location.
        """
        bundle_dir = self._config.bundle_dir
        if not bundle_dir.is_absolute():
            bundle_dir = self._config.root_dir / bundle_dir
        return bundle_dir / self._config.manifest_name

    async def _load_manifest_async(self) -> None:
        """Asynchronously load the Vite manifest for asset URL transformation."""
        manifest_path = anyio.Path(self._get_manifest_path())
        try:
            if await manifest_path.exists():
                content = await manifest_path.read_bytes()
                self._manifest = decode_json(content)
            else:
                logger.warning(
                    "Vite manifest not found at %s. "
                    "Asset URLs in index.html will not be transformed. "
                    "Run 'litestar assets build' to generate the manifest.",
                    manifest_path,
                )
        except OSError as exc:
            logger.warning("Failed to read Vite manifest file: %s", exc)
        except SerializationException as exc:
            logger.warning("Failed to parse Vite manifest JSON: %s", exc)

    def _load_manifest_sync(self) -> None:
        """Synchronously load the Vite manifest for asset URL transformation."""
        manifest_path = self._get_manifest_path()
        try:
            if manifest_path.exists():
                content = manifest_path.read_bytes()
                self._manifest = decode_json(content)
            else:
                logger.warning(
                    "Vite manifest not found at %s. "
                    "Asset URLs in index.html will not be transformed. "
                    "Run 'litestar assets build' to generate the manifest.",
                    manifest_path,
                )
        except OSError as exc:
            logger.warning("Failed to read Vite manifest file: %s", exc)
        except SerializationException as exc:
            logger.warning("Failed to parse Vite manifest JSON: %s", exc)

    def _transform_asset_urls_in_html(self, html: str) -> str:
        """Transform source asset URLs to production hashed URLs using manifest.

        Args:
            html: The HTML to transform.

        Returns:
            The transformed HTML (or original HTML when no manifest is loaded).
        """
        if not self._manifest:
            return html
        return transform_asset_urls(html, self._manifest, asset_url=self._config.asset_url, base_url=None)

    def _inject_dev_scripts(self, html: str) -> str:
        """Inject Vite dev scripts for hybrid mode HTML served by Litestar.

        Returns:
            The HTML with Vite dev scripts injected.
        """
        resource_dir = self._config.resource_dir
        try:
            resource_dir_str = str(resource_dir.relative_to(self._config.root_dir))
        except ValueError:
            resource_dir_str = resource_dir.name
        return inject_vite_dev_scripts(
            html,
            "",
            asset_url=self._config.asset_url,
            is_react=self._config.is_react,
            csp_nonce=self._config.csp_nonce,
            resource_dir=resource_dir_str,
        )

    async def _transform_html_with_vite(self, html: str, url: str) -> str:
        """Transform HTML using the Vite dev server pipeline.

        Returns:
            The transformed HTML.
        """
        if self._http_client is None or self._vite_url is None:
            msg = "HTTP client not initialized. Ensure initialize_async() was called for dev mode."
            raise ImproperlyConfiguredException(msg)
        endpoint = f"{self._vite_url.rstrip('/')}/__litestar__/transform-index"
        response = await self._http_client.post(endpoint, json={"url": url, "html": html}, timeout=5.0)
        response.raise_for_status()
        return response.text

    def _transform_html_with_vite_sync(self, html: str, url: str) -> str:
        """Transform HTML using the Vite dev server pipeline (sync).

        Raises:
            ImproperlyConfiguredException: If the HTTP client is not initialized.

        Returns:
            The transformed HTML.
        """
        if self._http_client_sync is None or self._vite_url is None:
            msg = "HTTP client not initialized. Ensure initialize_sync() was called for dev mode."
            raise ImproperlyConfiguredException(msg)
        endpoint = f"{self._vite_url.rstrip('/')}/__litestar__/transform-index"
        response = self._http_client_sync.post(endpoint, json={"url": url, "html": html}, timeout=5.0)
        response.raise_for_status()
        return response.text

    async def _get_dev_html(self, request: "Request[Any, Any, Any]") -> str:
        """Resolve dev HTML for SPA or hybrid modes.

        Returns:
            The HTML to serve in development.
        """
        if self._config.mode == "hybrid":
            if self._cached_html is None:
                await self._load_index_html_async()
            base_html = self._cached_html or ""
            request_url = request.url.path or "/"
            try:
                return await self._transform_html_with_vite(base_html, request_url)
            except Exception as exc:  # noqa: BLE001
                logger.warning("Falling back to manual Vite script injection: %s", exc)
                return self._inject_dev_scripts(base_html)
        return await self._proxy_to_dev_server(request)

    def _get_dev_html_sync(self, page_url: str | None = None) -> str:
        """Resolve dev HTML synchronously for SPA or hybrid modes.

        Returns:
            The HTML to serve in development.
        """
        if self._config.mode == "hybrid":
            if self._cached_html is None:
                self._load_index_html_sync()
            base_html = self._cached_html or ""
            request_url = page_url or "/"
            try:
                return self._transform_html_with_vite_sync(base_html, request_url)
            except Exception as exc:  # noqa: BLE001
                logger.warning("Falling back to manual Vite script injection: %s", exc)
                return self._inject_dev_scripts(base_html)
        return self._proxy_to_dev_server_sync()

    def _get_csrf_token(self, request: "Request[Any, Any, Any]") -> "str | None":
        """Extract CSRF token from the request scope.

        Args:
            request: Incoming request.

        Returns:
            The CSRF token, or None if not present.
        """
        from litestar.utils.empty import value_or_default
        from litestar.utils.scope.state import ScopeState

        return value_or_default(ScopeState.from_scope(request.scope).csrf_token, None)

    async def get_html(self, request: "Request[Any, Any, Any]", *, page_data: "dict[str, Any] | None" = None) -> str:
        """Get the HTML for the SPA with optional transformations.

        Args:
            request: Incoming request.
            page_data: Optional page data to inject (e.g., Inertia page props).

        Returns:
            The rendered HTML.

        Raises:
            ImproperlyConfiguredException: If the handler is not initialized.
        """
        if not self._initialized:
            msg = "AppHandler not initialized. Call initialize() during app startup."
            raise ImproperlyConfiguredException(msg)

        needs_transform = self._spa_config is not None or page_data is not None
        needs_csrf = self._spa_config is not None and self._spa_config.inject_csrf
        csrf_token = self._get_csrf_token(request) if needs_csrf else None

        if self._config.is_dev_mode and self._config.hot_reload:
            html = await self._get_dev_html(request)
            if needs_transform:
                html = self._transform_html(html, page_data, csrf_token)
            return html

        if self._cached_html is None:
            await self._load_index_html_async()

        base_html = self._cached_html or ""

        if not needs_transform:
            return base_html

        if page_data is not None or csrf_token is not None:
            return self._transform_html(base_html, page_data, csrf_token)

        if self._spa_config is not None and self._spa_config.cache_transformed_html:
            if self._cached_transformed_html is not None:
                return self._cached_transformed_html
            self._cached_transformed_html = self._transform_html(base_html, None, None)
            return self._cached_transformed_html

        return self._transform_html(base_html, None, None)

    def get_html_sync(self, *, page_data: "dict[str, Any] | None" = None, csrf_token: "str | None" = None) -> str:
        """Get the HTML for the SPA synchronously.

        Args:
            page_data: Optional page data to inject (e.g., Inertia page props).
            csrf_token: Optional CSRF token to inject.

        Returns:
            The rendered HTML.
        """
        if not self._initialized:
            logger.warning(
                "AppHandler lazy init triggered - lifespan may not have run. "
                "Consider calling initialize_sync() explicitly during app startup."
            )
            self.initialize_sync()

        needs_transform = self._spa_config is not None or page_data is not None
        if not needs_transform:
            if self._config.is_dev_mode and self._config.hot_reload:
                return self._get_dev_html_sync()
            return self._cached_html or ""

        if self._config.is_dev_mode and self._config.hot_reload:
            page_url = None
            if page_data is not None:
                url_value = page_data.get("url")
                if isinstance(url_value, str) and url_value:
                    page_url = url_value
            html = self._get_dev_html_sync(page_url)
            return self._transform_html(html, page_data, csrf_token)

        base_html = self._cached_html or ""
        return self._transform_html(base_html, page_data, csrf_token)

    async def get_bytes(self) -> bytes:
        """Get cached index.html bytes (production).

        Returns:
            Cached HTML bytes. .
        """
        if not self._initialized:
            logger.warning(
                "AppHandler lazy init triggered - lifespan may not have run. "
                "Consider calling initialize_sync() explicitly during app startup."
            )
            await self.initialize_async()

        if self._cached_bytes is None:
            await self._load_index_html_async()

        return self._cached_bytes or b""

    async def _proxy_to_dev_server(self, request: "Request[Any, Any, Any]") -> str:
        """Proxy request to Vite dev server and return HTML.

        Args:
            request: Incoming request.

        Returns:
            HTML from the Vite dev server, or a friendly "server starting" page
            if the server is not yet ready.

        Raises:
            ImproperlyConfiguredException: If the HTTP client is not initialized.
        """
        if self._http_client is None:
            msg = "HTTP client not initialized. Ensure initialize_async() was called for dev mode."
            raise ImproperlyConfiguredException(msg)

        if self._vite_url is None:
            msg = "Vite URL not resolved. Ensure initialize_sync() or initialize_async() was called."
            raise ImproperlyConfiguredException(msg)

        target_url = f"{self._vite_url}/"

        try:
            response = await self._http_client.get(target_url, follow_redirects=True)
            response.raise_for_status()
        except httpx.HTTPError:
            # Return a friendly startup page instead of an error
            logger.debug("Vite server not ready at %s, showing startup page", target_url)
            return _get_server_starting_html(target_url)
        else:
            return response.text

    def _proxy_to_dev_server_sync(self) -> str:
        """Proxy request to Vite dev server synchronously.

        Returns:
            HTML from the Vite dev server, or a friendly "server starting" page
            if the server is not yet ready.

        Raises:
            ImproperlyConfiguredException: If the HTTP client is not initialized.
        """
        if self._http_client_sync is None:
            msg = "HTTP client not initialized. Ensure initialize_sync() was called for dev mode."
            raise ImproperlyConfiguredException(msg)

        if self._vite_url is None:
            msg = "Vite URL not resolved. Ensure initialize_sync() or initialize_async() was called."
            raise ImproperlyConfiguredException(msg)

        target_url = f"{self._vite_url}/"

        try:
            response = self._http_client_sync.get(target_url, follow_redirects=True)
            response.raise_for_status()
        except httpx.HTTPError:
            # Return a friendly startup page instead of an error
            logger.debug("Vite server not ready at %s, showing startup page", target_url)
            return _get_server_starting_html(target_url)
        else:
            return response.text

    def _resolve_vite_url(self) -> str:
        """Resolve the Vite server URL from hotfile or config.

        Returns:
            The base Vite URL without a trailing slash.
        """
        hotfile = self._config.bundle_dir / self._config.hot_file
        if not hotfile.is_absolute():
            hotfile = self._config.root_dir / hotfile

        if hotfile.exists():
            try:
                url = read_hotfile_url(hotfile)
                if url:
                    return url.rstrip("/")
            except OSError:
                pass

        return f"{self._config.protocol}://{self._config.host}:{self._config.port}"

    def create_route_handler(self) -> Any:
        """Create a Litestar route handler for the SPA.

        Returns:
            A Litestar route handler suitable for registering on an application.
        """
        is_dev = self._config.is_dev_mode and self._config.hot_reload

        opt: dict[str, Any] = {}
        if self._config.exclude_static_from_auth:
            opt["exclude_from_auth"] = True
        opt["_vite_spa_handler"] = self

        guards: "list[Guard] | None" = list(self._config.guards) if self._config.guards else None  # pyright: ignore[reportUnknownVariableType,reportUnknownMemberType,reportUnknownArgumentType]

        asset_url = self._config.asset_url
        spa_path = self._config.spa_path
        effective_spa_path = spa_path if spa_path is not None else "/"
        include_root = self._config.include_root_spa_paths

        if effective_spa_path and effective_spa_path != "/":
            base = effective_spa_path.rstrip("/")
            paths: list[str] = [f"{base}/", f"{base}/{{path:path}}"]
            if include_root:
                paths.extend(["/", "/{path:path}"])
        else:
            paths = ["/", "/{path:path}"]

        needs_exclusion = asset_url and asset_url != "/" and (effective_spa_path == "/" or include_root)
        asset_prefix = asset_url.rstrip("/") if needs_exclusion else None
        if asset_prefix:
            opt["_vite_asset_prefix"] = asset_prefix

        if is_dev:
            return get(path=paths, name="vite_spa", opt=opt, include_in_schema=False, guards=guards)(spa_handler_dev)

        return get(path=paths, name="vite_spa", opt=opt, include_in_schema=False, cache=3600, guards=guards)(
            spa_handler_prod
        )
