"""HTTP/WebSocket proxy middleware and HMR handlers."""

import logging
from collections.abc import AsyncGenerator, Awaitable, Iterable
from contextlib import suppress
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast
from urllib.parse import unquote

import anyio
import httpx
import websockets
from litestar.enums import ScopeType
from litestar.exceptions import WebSocketDisconnect
from litestar.middleware import AbstractMiddleware

from litestar_vite.plugin._utils import console, is_litestar_route, is_proxy_debug, normalize_prefix
from litestar_vite.utils import read_hotfile_url

if TYPE_CHECKING:
    from collections.abc import Callable

    from litestar.connection import Request
    from litestar.types import ASGIApp, Receive, Scope, Send
    from websockets.typing import Subprotocol

    from litestar_vite.plugin import VitePlugin

_DISCONNECT_EXCEPTIONS = (WebSocketDisconnect, anyio.ClosedResourceError, websockets.ConnectionClosed)

_BODY_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE"})

_PROXY_ALLOW_PREFIXES: tuple[str, ...] = (
    "/@vite",
    "/@id/",
    "/@fs/",
    "/@react-refresh",
    "/@vite/client",
    "/@vite/env",
    "/vite-hmr",
    "/__vite_ping",
    "/node_modules/",
    "/@analogjs/",
)

_PROXY_ALLOW_SUFFIXES: tuple[str, ...] = (
    ".js",
    ".cjs",
    ".mjs",
    ".ts",
    ".cts",
    ".mts",
    ".jsx",
    ".tsx",
    ".vue",
    ".svelte",
    ".astro",
    ".css",
    ".scss",
    ".sass",
    ".less",
    ".html",
    ".json",
    ".xml",
    ".txt",
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".svg",
    ".avif",
    ".bmp",
    ".webp",
    ".map",
    ".ico",
    ".webmanifest",
    ".woff",
    ".woff2",
    ".ttf",
    ".eot",
    ".otf",
    ".wasm",
    ".mp4",
    ".webm",
    ".ogg",
    ".mp3",
    ".wav",
    ".flac",
    ".aac",
)

_HOP_BY_HOP_HEADERS = frozenset({
    "connection",
    "keep-alive",
    "proxy-authenticate",
    "proxy-authorization",
    "te",
    "trailers",
    "transfer-encoding",
    "upgrade",
    "content-length",
    "content-encoding",
})

_WS_REQUEST_SKIP_HEADERS = _HOP_BY_HOP_HEADERS | {
    "host",
    "upgrade",
    "sec-websocket-key",
    "sec-websocket-version",
    "sec-websocket-protocol",
    "sec-websocket-extensions",
}

_LOGGER = logging.getLogger(__name__)


def _normalize_header_key(raw_key: Any) -> str:
    """Normalize a raw header key to a lower-cased string."""
    if isinstance(raw_key, bytes):
        return raw_key.decode("latin-1").lower()
    return str(raw_key).lower()


def _normalize_header_value(raw_value: Any) -> str:
    """Normalize a raw header value to a string."""
    if isinstance(raw_value, bytes):
        return raw_value.decode("latin-1")
    return str(raw_value)


def _collect_connection_tokens(headers: Any) -> set[str]:
    """Collect header names listed in Connection headers."""
    tokens: set[str] = set()
    for key, value in headers:
        if _normalize_header_key(key) == "connection":
            tokens.update(token.strip().lower() for token in _normalize_header_value(value).split(",") if token.strip())
    return tokens


def _filter_hop_by_hop_headers(headers: Any) -> list[tuple[str, str]]:
    """Filter hop-by-hop headers while preserving case-sensitive duplicates and order."""
    return _extract_request_headers(headers)


def _extract_request_headers(
    headers: Any, extra_skip_headers: "Iterable[bytes | str] | None" = None
) -> list[tuple[str, str]]:
    """Extract request headers, excluding hop-by-hop and optional additional skip headers."""
    if not headers:
        return []

    skip = {_normalize_header_key(name) for name in _HOP_BY_HOP_HEADERS}
    if extra_skip_headers is not None:
        skip.update(_normalize_header_key(name) for name in extra_skip_headers)

    hop_by_hop = set(skip)
    hop_by_hop.update(_collect_connection_tokens(headers))

    filtered: list[tuple[str, str]] = []
    for key, value in headers:
        normalized_key = _normalize_header_key(key)
        if normalized_key in hop_by_hop:
            continue
        filtered.append((str(key) if isinstance(key, str) else key.decode("latin-1"), _normalize_header_value(value)))

    return filtered


def _extract_proxy_response(upstream_resp: "httpx.Response") -> tuple[int, list[tuple[bytes, bytes]], bytes]:  # pyright: ignore[reportUnusedFunction]
    """Extract status, headers, and body from an httpx response for proxying.

    Returns:
        A tuple of (status_code, headers, body).
    """
    headers = _extract_proxy_response_headers(upstream_resp.headers)
    return upstream_resp.status_code, headers, upstream_resp.content


def _extract_proxy_response_headers(headers: "httpx.Headers") -> list[tuple[bytes, bytes]]:
    """Extract response headers while preserving duplicates and filtering hop-by-hop headers.

    Uses the same hop-by-hop header set as request filtering, plus any headers
    dynamically listed in the Connection header (RFC 7230 §6.1).

    Returns:
        A list of (header_name, header_value) tuples.
    """
    hop_by_hop = set(_HOP_BY_HOP_HEADERS)
    # Collect dynamically-declared hop-by-hop headers from Connection header
    hop_by_hop.update(
        _collect_connection_tokens((key.decode("latin-1"), value.decode("latin-1")) for key, value in headers.raw)
    )

    extracted: list[tuple[bytes, bytes]] = []
    for key, value in headers.raw:
        lower_key = key.decode("latin-1").lower()
        if lower_key in hop_by_hop:
            continue
        extracted.append((key, value))

    return extracted


async def _stream_request_body(receive: "Callable[[], Awaitable[dict[str, Any]]]") -> AsyncGenerator[bytes, None]:
    """Stream request body chunks from ASGI receive events.

    Yields:
        An async generator of bytes.
    """
    while True:
        event = await receive()
        if event.get("type") != "http.request":
            continue
        body = event.get("body", b"")
        if body:
            yield cast("bytes", body)
        if not event.get("more_body", False):
            return


async def _stream_request_body_chunks(content: "AsyncGenerator[bytes, None]") -> AsyncGenerator[bytes, None]:
    """Proxy a request body-like async generator while dropping empty chunks."""
    async for chunk in content:
        if chunk:
            yield chunk


async def _stream_response_body(
    response: "httpx.Response", close_callback: "Callable[[], Awaitable[None]] | None" = None
) -> AsyncGenerator[bytes, None]:
    """Iterate response body chunks and close the upstream response."""
    try:
        async for chunk in response.aiter_bytes():
            if chunk:
                yield chunk
    finally:
        if close_callback is not None:
            await close_callback()
        else:
            await response.aclose()


async def _proxy_stream_response(
    response: "httpx.Response",
    send: "Callable[[dict[str, Any]], Any]",
    close_callback: "Callable[[], Awaitable[None]] | None" = None,
) -> None:
    """Stream upstream response to the client incrementally."""
    response_headers = _extract_proxy_response_headers(response.headers)
    await send({"type": "http.response.start", "status": response.status_code, "headers": response_headers})
    async for chunk in _stream_response_body(response, close_callback=close_callback):
        await send({"type": "http.response.body", "body": chunk, "more_body": True})

    await send({"type": "http.response.body", "body": b"", "more_body": False})


class ViteProxyMiddleware(AbstractMiddleware):
    """ASGI middleware to proxy Vite dev HTTP traffic to internal Vite server.

    HTTP requests use httpx.AsyncClient with optional HTTP/2 support for better
    connection multiplexing. WebSocket traffic (used by Vite HMR) is handled by
    a dedicated WebSocket route handler created by create_vite_hmr_handler().

    The middleware reads the Vite server URL from the hotfile dynamically,
    ensuring it always connects to the correct Vite server even if the port changes.
    """

    scopes = {ScopeType.HTTP}

    def __init__(
        self,
        app: "ASGIApp",
        hotfile_path: Path,
        asset_url: "str | None" = None,
        resource_dir: "Path | None" = None,
        bundle_dir: "Path | None" = None,
        root_dir: "Path | None" = None,
        http2: bool = True,
        plugin: "VitePlugin | None" = None,
    ) -> None:
        super().__init__(app)
        self.hotfile_path = hotfile_path
        self._cached_target: str | None = None
        self._cache_initialized = False
        self.asset_prefix = normalize_prefix(asset_url) if asset_url else "/"
        self.http2 = http2
        self._plugin = plugin
        self._proxy_allow_prefixes = normalize_proxy_prefixes(
            base_prefixes=_PROXY_ALLOW_PREFIXES,
            asset_url=asset_url,
            resource_dir=resource_dir,
            bundle_dir=bundle_dir,
            root_dir=root_dir,
        )

    def _get_target_base_url(self) -> str | None:
        """Read the Vite server URL from the hotfile with permanent caching.

        The hotfile is read once and cached for the lifetime of the server.
        Server restart refreshes the cache automatically.

        Returns:
            The Vite server URL or None if unavailable.
        """
        if self._cache_initialized:
            return self._cached_target.rstrip("/") if self._cached_target else None

        try:
            url = read_hotfile_url(self.hotfile_path)
            self._cached_target = url
            self._cache_initialized = True
            if is_proxy_debug():
                console.print(f"[dim][vite-proxy] Target: {url}[/]")
            return url.rstrip("/")
        except FileNotFoundError:
            self._cached_target = None
            self._cache_initialized = True
            return None

    async def __call__(self, scope: "Scope", receive: "Receive", send: "Send") -> None:
        scope_dict = cast("dict[str, Any]", scope)
        path = scope_dict.get("path", "")
        should = self._should_proxy(path, scope)
        if is_proxy_debug():
            console.print(f"[dim][vite-proxy] {path} → proxy={should}[/]")
        if should:
            await self._proxy_http(scope_dict, receive, send)
            return
        await self.app(scope, receive, send)

    @staticmethod
    def _has_path_traversal(path: str) -> bool:
        """Check if a path contains directory traversal sequences."""
        return ".." in path or "\\" in path

    def _should_proxy(self, path: str, scope: "Scope") -> bool:
        decoded = unquote(path) if "%" in path else path
        # Double-decode to catch double-encoded traversal (%252e%252e)
        double_decoded = unquote(decoded) if "%" in decoded else decoded

        if self._has_path_traversal(decoded) or self._has_path_traversal(double_decoded):
            return False

        path_lower = path.lower()
        decoded_lower = decoded.lower()

        matches_prefix = decoded.startswith(self._proxy_allow_prefixes) or path.startswith(self._proxy_allow_prefixes)
        matches_suffix = decoded_lower.endswith(_PROXY_ALLOW_SUFFIXES) or path_lower.endswith(_PROXY_ALLOW_SUFFIXES)

        if not (matches_prefix or matches_suffix):
            return False

        app = scope.get("app")  # pyright: ignore[reportUnknownMemberType]
        if not app:
            return True

        return not (is_litestar_route(path, app) or is_litestar_route(decoded, app))

    async def _proxy_http(self, scope: dict[str, Any], receive: Any, send: Any) -> None:
        """Proxy a single HTTP request to the Vite dev server.

        The upstream response is streamed directly from Vite to the client. When
        the Vite hot file is absent, the request falls through to the next ASGI
        app so static files can serve built assets when they exist.
        """
        target_base_url = self._get_target_base_url()
        if target_base_url is None:
            await self.app(cast("Scope", scope), receive, send)
            return

        method = scope.get("method", "GET")
        raw_path = scope.get("raw_path", b"").decode()
        query_string = scope.get("query_string", b"").decode()
        proxied_path = raw_path
        if self.asset_prefix != "/" and not raw_path.startswith(self.asset_prefix):
            proxied_path = f"{self.asset_prefix.rstrip('/')}{raw_path}"

        url = f"{target_base_url}{proxied_path}"
        if query_string:
            url = f"{url}?{query_string}"

        headers = _filter_hop_by_hop_headers(scope.get("headers", []))
        # Only stream request body for methods that carry a body.
        # Passing an async generator as content for GET/HEAD/OPTIONS causes httpx
        # to add Transfer-Encoding: chunked, which Vite dev server rejects with 400.
        # See: https://github.com/litestar-org/litestar-vite/issues/242
        request_body = _stream_request_body(receive) if method in _BODY_METHODS else None

        # Use shared client from plugin when available (connection pooling)
        client = self._plugin.proxy_client if self._plugin is not None else None

        try:
            if client is not None:
                # Use shared client (connection pooling, HTTP/2 multiplexing)
                async with client.stream(
                    method, url, headers=headers, content=request_body, timeout=10.0, follow_redirects=False
                ) as upstream_resp:
                    await _proxy_stream_response(upstream_resp, send)
            else:
                # Fallback: per-request client (graceful degradation)
                http2_enabled = check_http2_support(self.http2)
                async with (
                    httpx.AsyncClient(http2=http2_enabled) as fallback_client,
                    fallback_client.stream(
                        method, url, headers=headers, content=request_body, timeout=10.0, follow_redirects=False
                    ) as upstream_resp,
                ):
                    await _proxy_stream_response(upstream_resp, send)
        except Exception as exc:  # noqa: BLE001  # pragma: no cover - catch all cleanup errors
            await send({"type": "http.response.start", "status": 502, "headers": [(b"content-type", b"text/plain")]})
            await send({"type": "http.response.body", "body": f"Upstream error: {exc}".encode(), "more_body": False})


def build_hmr_target_url(hotfile_path: Path, scope: dict[str, Any], hmr_path: str, asset_url: str) -> "str | None":
    """Build the target WebSocket URL for Vite HMR proxy.

    Vite's HMR WebSocket listens at {base}{hmr.path}, so we preserve
    the full path including the asset prefix (e.g., /static/vite-hmr).

    Returns:
        The target WebSocket URL or None if the hotfile is not found.
    """
    try:
        vite_url = read_hotfile_url(hotfile_path)
    except FileNotFoundError:
        return None

    ws_url = vite_url.replace("http://", "ws://").replace("https://", "wss://")
    original_path = scope.get("path", hmr_path)
    query_string = scope.get("query_string", b"").decode()

    target = f"{ws_url}{original_path}"
    if query_string:
        target = f"{target}?{query_string}"

    if is_proxy_debug():
        console.print(f"[dim][vite-hmr] Connecting: {target}[/]")

    return target


def extract_forward_headers(scope: dict[str, Any]) -> list[tuple[str, str]]:
    """Extract headers to forward, excluding WebSocket handshake headers.

    Excludes protocol-specific headers that websockets library handles itself.
    The sec-websocket-protocol header is also excluded since we handle subprotocols separately.

    Returns:
        A list of (header_name, header_value) tuples.
    """
    return _extract_request_headers(scope.get("headers", []), extra_skip_headers=_WS_REQUEST_SKIP_HEADERS)


def extract_subprotocols(scope: dict[str, Any]) -> list[str]:
    """Extract WebSocket subprotocols from the request headers.

    Returns:
        A list of subprotocol strings.
    """
    for key, value in scope.get("headers", []):
        if _normalize_header_key(key) == "sec-websocket-protocol":
            return [p.strip() for p in _normalize_header_value(value).split(",") if p.strip()]
    return []


async def _run_websocket_proxy(socket: Any, upstream: Any) -> None:
    """Run bidirectional WebSocket proxy between client and upstream.

    Args:
        socket: The client WebSocket connection (Litestar WebSocket).
        upstream: The upstream WebSocket connection (websockets client).
    """

    async def client_to_upstream() -> None:
        """Forward messages from browser to Vite."""
        try:
            while True:
                data = await socket.receive_text()
                await upstream.send(data)
        except (WebSocketDisconnect, anyio.ClosedResourceError, websockets.ConnectionClosed):
            pass
        finally:
            with suppress(websockets.ConnectionClosed):
                await upstream.close()

    async def upstream_to_client() -> None:
        """Forward messages from Vite to browser."""
        try:
            async for msg in upstream:
                if isinstance(msg, str):
                    await socket.send_text(msg)
                else:
                    await socket.send_bytes(msg)
        except (WebSocketDisconnect, anyio.ClosedResourceError, websockets.ConnectionClosed):
            pass
        finally:
            with suppress(anyio.ClosedResourceError, WebSocketDisconnect):
                await socket.close()

    async with anyio.create_task_group() as tg:
        tg.start_soon(client_to_upstream)
        tg.start_soon(upstream_to_client)


def create_vite_hmr_handler(hotfile_path: Path, hmr_path: str = "/static/vite-hmr", asset_url: str = "/static/") -> Any:
    """Create a WebSocket route handler for Vite HMR proxy.

    This handler proxies WebSocket connections from the browser to the Vite
    dev server for Hot Module Replacement (HMR) functionality.

    Args:
        hotfile_path: Path to the hotfile written by the Vite plugin.
        hmr_path: The path to register the WebSocket handler at.
        asset_url: The asset URL prefix to strip when connecting to Vite.

    Returns:
        A WebsocketRouteHandler that proxies HMR connections.
    """
    from litestar import WebSocket, websocket

    @websocket(path=hmr_path, opt={"exclude_from_auth": True})
    async def vite_hmr_proxy(socket: "WebSocket[Any, Any, Any]") -> None:
        """Proxy WebSocket messages between browser and Vite dev server."""
        scope_dict = dict(socket.scope)
        target = build_hmr_target_url(hotfile_path, scope_dict, hmr_path, asset_url)
        if target is None:
            console.print("[yellow][vite-hmr] Vite server not running[/]")
            await socket.close(code=1011, reason="Vite server not running")
            return

        headers = extract_forward_headers(scope_dict)
        subprotocols = extract_subprotocols(scope_dict)
        accept_subprotocol: str | None = subprotocols[0] if subprotocols else None
        typed_subprotocols: list[Subprotocol] = [cast("Subprotocol", p) for p in subprotocols]
        await socket.accept(subprotocols=accept_subprotocol)

        try:
            async with websockets.connect(
                target, additional_headers=headers, open_timeout=10, subprotocols=typed_subprotocols or None
            ) as upstream:
                if is_proxy_debug():
                    console.print("[dim][vite-hmr] ✓ Connected[/]")
                await _run_websocket_proxy(socket, upstream)
        except TimeoutError:
            if is_proxy_debug():
                console.print("[yellow][vite-hmr] Connection timeout[/]")
            with suppress(anyio.ClosedResourceError, WebSocketDisconnect):
                await socket.close(code=1011, reason="Vite HMR connection timeout")
        except OSError as exc:
            if is_proxy_debug():
                console.print(f"[yellow][vite-hmr] Connection failed: {exc}[/]")
            with suppress(anyio.ClosedResourceError, WebSocketDisconnect):
                await socket.close(code=1011, reason="Vite HMR connection failed")
        except WebSocketDisconnect:
            pass
        except BaseException as exc:
            exceptions: list[BaseException] | tuple[BaseException, ...] | None
            try:
                exceptions = cast("list[BaseException] | tuple[BaseException, ...]", exc.exceptions)  # type: ignore[attr-defined]
            except AttributeError:
                exceptions = None

            if exceptions is not None:
                if any(not isinstance(err, _DISCONNECT_EXCEPTIONS) for err in exceptions):
                    raise
                return

            if not isinstance(exc, _DISCONNECT_EXCEPTIONS):
                raise

    return vite_hmr_proxy


def check_http2_support(enable: bool) -> bool:
    """Check if HTTP/2 support is available.

    Returns:
        True if HTTP/2 is enabled and the h2 package is installed, else False.
    """
    if not enable:
        return False
    try:
        import h2  # noqa: F401  # pyright: ignore[reportMissingImports,reportUnusedImport]
    except ImportError:
        return False
    else:
        return True


def build_proxy_url(target_url: str, path: str, query: str) -> str:
    """Build the full proxy URL from target, path, and query string.

    Returns:
        The full URL as a string.
    """
    url = f"{target_url}{path}"
    return f"{url}?{query}" if query else url


def create_target_url_getter(
    target: "str | None", hotfile_path: "Path | None", cached_target: list["str | None"]
) -> "Callable[[], str | None]":
    """Create a function that returns the current target URL with permanent caching.

    The hotfile is read once and cached for the lifetime of the server.
    Server restart refreshes the cache automatically.

    Returns:
        A callable that returns the target URL or None if unavailable.
    """
    cache_initialized: list[bool] = [False]

    def _get_target_url() -> str | None:
        if target is not None:
            return target.rstrip("/")
        if hotfile_path is None:
            return None

        if cache_initialized[0]:
            return cached_target[0].rstrip("/") if cached_target[0] else None

        try:
            url = read_hotfile_url(hotfile_path)
            cached_target[0] = url
            cache_initialized[0] = True
            if is_proxy_debug():
                console.print(f"[dim][ssr-proxy] Dynamic target: {url}[/]")
            return url.rstrip("/")
        except FileNotFoundError:
            cached_target[0] = None
            cache_initialized[0] = True
            return None

    return _get_target_url


def create_hmr_target_getter(
    hotfile_path: "Path | None", cached_hmr_target: list["str | None"]
) -> "Callable[[], str | None]":
    """Create a function that returns the HMR target URL from hotfile with permanent caching.

    The hotfile is read once and cached for the lifetime of the server.
    Server restart refreshes the cache automatically.

    The JS side writes HMR URLs to a sibling file at ``<hotfile>.hmr``.

    Returns:
        A callable that returns the HMR target URL or None if unavailable.
    """
    cache_initialized: list[bool] = [False]

    def _get_hmr_target_url() -> str | None:
        if hotfile_path is None:
            return None

        if cache_initialized[0]:
            return cached_hmr_target[0].rstrip("/") if cached_hmr_target[0] else None

        hmr_path = Path(f"{hotfile_path}.hmr")
        try:
            url = read_hotfile_url(hmr_path)
            cached_hmr_target[0] = url
            cache_initialized[0] = True
            if is_proxy_debug():
                console.print(f"[dim][ssr-proxy] HMR target: {url}[/]")
            return url.rstrip("/")
        except FileNotFoundError:
            cached_hmr_target[0] = None
            cache_initialized[0] = True
            return None

    return _get_hmr_target_url


async def _handle_ssr_websocket_proxy(
    socket: Any, ws_url: str, headers: list[tuple[str, str]], typed_subprotocols: "list[Subprotocol]"
) -> None:
    """Handle the WebSocket proxy connection to SSR framework.

    Args:
        socket: The client WebSocket connection.
        ws_url: The upstream WebSocket URL.
        headers: Headers to forward.
        typed_subprotocols: WebSocket subprotocols.
    """
    try:
        async with websockets.connect(
            ws_url, additional_headers=headers, open_timeout=10, subprotocols=typed_subprotocols or None
        ) as upstream:
            if is_proxy_debug():
                console.print("[dim][ssr-proxy-ws] ✓ Connected[/]")
            await _run_websocket_proxy(socket, upstream)
    except TimeoutError:
        if is_proxy_debug():
            console.print("[yellow][ssr-proxy-ws] Connection timeout[/]")
        with suppress(anyio.ClosedResourceError, WebSocketDisconnect):
            await socket.close(code=1011, reason="SSR HMR connection timeout")
    except OSError as exc:
        if is_proxy_debug():
            console.print(f"[yellow][ssr-proxy-ws] Connection failed: {exc}[/]")
        with suppress(anyio.ClosedResourceError, WebSocketDisconnect):
            await socket.close(code=1011, reason="SSR HMR connection failed")
    except (WebSocketDisconnect, websockets.ConnectionClosed, anyio.ClosedResourceError):
        pass


def create_ssr_proxy_controller(
    target: "str | None" = None,
    hotfile_path: "Path | None" = None,
    http2: bool = True,
    plugin: "VitePlugin | None" = None,
) -> type:
    """Create a Controller that proxies to an SSR framework dev server.

    This controller is used for SSR frameworks (Astro, Nuxt, SvelteKit) where all
    non-API requests should be proxied to the framework's dev server for rendering.

    Args:
        target: Static target URL to proxy to. If None, uses hotfile for dynamic discovery.
        hotfile_path: Path to the hotfile for dynamic target discovery.
        http2: Enable HTTP/2 for proxy connections.
        plugin: Optional VitePlugin reference for accessing shared proxy client.

    Returns:
        A Litestar Controller class with HTTP and WebSocket handlers for SSR proxy.
    """
    from litestar import Controller, HttpMethod, Response, WebSocket, route, websocket

    cached_target: list[str | None] = [target]
    get_target_url = create_target_url_getter(target, hotfile_path, cached_target)
    get_hmr_target_url = create_hmr_target_getter(hotfile_path, [None])

    class SSRProxyController(Controller):
        """Controller that proxies requests to an SSR framework dev server."""

        include_in_schema = False
        opt = {"exclude_from_auth": True}

        @route(
            path=["/", "/{path:path}"],
            http_method=[
                HttpMethod.GET,
                HttpMethod.POST,
                HttpMethod.PUT,
                HttpMethod.PATCH,
                HttpMethod.DELETE,
                HttpMethod.HEAD,
                HttpMethod.OPTIONS,
            ],
            name="ssr_proxy",
        )
        async def http_proxy(self, request: "Request[Any, Any, Any]") -> "ASGIApp":
            """Proxy all HTTP requests to the SSR framework dev server.

            Returns:
                A Response with the proxied content from the SSR server.
            """
            target_url = get_target_url()
            if target_url is None:
                return cast(
                    "ASGIApp", Response(content=b"SSR server not running", status_code=503, media_type="text/plain")
                )

            req_path: str = request.url.path
            url = build_proxy_url(target_url, req_path, request.url.query or "")

            if is_proxy_debug():
                console.print(f"[dim][ssr-proxy] {request.method} {req_path} → {url}[/]")

            headers_to_forward = _filter_hop_by_hop_headers(request.headers.items())
            # Only stream request body for methods that carry a body.
            # See: https://github.com/litestar-org/litestar-vite/issues/242
            request_body = _stream_request_body_chunks(request.stream()) if request.method in _BODY_METHODS else None

            # Use shared client from plugin when available (connection pooling)
            client = plugin.proxy_client if plugin is not None else None

            stream_context = None
            http_client: httpx.AsyncClient | None = None

            try:
                if client is not None:
                    # Use shared client (connection pooling, HTTP/2 multiplexing)
                    stream_context = client.stream(
                        request.method,
                        url,
                        headers=headers_to_forward,
                        content=request_body,
                        follow_redirects=False,
                        timeout=30.0,
                    )
                else:
                    # Fallback: per-request client (graceful degradation)
                    http2_enabled = check_http2_support(http2)
                    http_client = httpx.AsyncClient(http2=http2_enabled, timeout=30.0)
                    stream_context = http_client.stream(
                        request.method, url, headers=headers_to_forward, content=request_body, follow_redirects=False
                    )

                upstream_resp = await stream_context.__aenter__()
            except httpx.ConnectError:
                if http_client is not None:
                    await http_client.aclose()
                return cast(
                    "ASGIApp",
                    Response(
                        content=f"SSR server not running at {target_url}".encode(),
                        status_code=503,
                        media_type="text/plain",
                    ),
                )
            except httpx.HTTPError as exc:
                if http_client is not None:
                    await http_client.aclose()
                return cast("ASGIApp", Response(content=str(exc).encode(), status_code=502, media_type="text/plain"))

            async def _close_stream_context() -> None:
                try:
                    await stream_context.__aexit__(None, None, None)
                    if http_client is not None:
                        await http_client.aclose()
                except (RuntimeError, OSError, httpx.HTTPError) as exc:
                    _LOGGER.debug("Failed to close SSR proxy stream context cleanly: %s", exc)

            async def asgi_response_app(_scope: "Scope", _receive: "Receive", send: "Send") -> None:
                del _scope, _receive
                await _proxy_stream_response(
                    response=upstream_resp,
                    send=cast("Callable[[dict[str, Any]], Any]", send),
                    close_callback=_close_stream_context,
                )

            return asgi_response_app

        @websocket(path=["/", "/{path:path}"], name="ssr_proxy_ws")
        async def ws_proxy(self, socket: "WebSocket[Any, Any, Any]") -> None:
            """Proxy WebSocket connections to the SSR framework dev server (for HMR)."""
            target_url = get_hmr_target_url() or get_target_url()

            if target_url is None:
                await socket.close(code=1011, reason="SSR server not running")
                return

            ws_target = target_url.replace("http://", "ws://").replace("https://", "wss://")
            scope_dict = dict(socket.scope)
            ws_path = str(scope_dict.get("path", "/"))
            query_bytes = cast("bytes", scope_dict.get("query_string", b""))
            ws_url = build_proxy_url(ws_target, ws_path, query_bytes.decode("utf-8") if query_bytes else "")

            if is_proxy_debug():
                console.print(f"[dim][ssr-proxy-ws] {ws_path} → {ws_url}[/]")

            headers = extract_forward_headers(scope_dict)
            subprotocols = extract_subprotocols(scope_dict)
            typed_subprotocols: list[Subprotocol] = [cast("Subprotocol", p) for p in subprotocols]
            accept_subprotocol: str | None = subprotocols[0] if subprotocols else None
            await socket.accept(subprotocols=accept_subprotocol)
            await _handle_ssr_websocket_proxy(socket, ws_url, headers, typed_subprotocols)

    return SSRProxyController


def normalize_proxy_prefixes(
    base_prefixes: tuple[str, ...],
    asset_url: "str | None" = None,
    resource_dir: "Path | None" = None,
    bundle_dir: "Path | None" = None,
    root_dir: "Path | None" = None,
) -> tuple[str, ...]:
    prefixes: list[str] = list(base_prefixes)

    if asset_url:
        prefixes.append(normalize_prefix(asset_url))

    def _add_path(path: Path | str | None) -> None:
        if path is None:
            return
        p = Path(path)
        if root_dir and p.is_absolute():
            with suppress(ValueError):
                p = p.relative_to(root_dir)
        prefixes.append(normalize_prefix(str(p).replace("\\", "/")))

    _add_path(resource_dir)
    _add_path(bundle_dir)

    seen: set[str] = set()
    unique: list[str] = []
    for p in prefixes:
        if p not in seen:
            unique.append(p)
            seen.add(p)
    return tuple(unique)
