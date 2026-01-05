"""HTTP/WebSocket proxy middleware and HMR handlers."""

from contextlib import suppress
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

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

_PROXY_ALLOW_PREFIXES: tuple[str, ...] = (
    "/@vite",
    "/@id/",
    "/@fs/",
    "/@react-refresh",
    "/@vite/client",
    "/@vite/env",
    "/vite-hmr",
    "/__vite_ping",
    "/node_modules/.vite/",
    "/@analogjs/",
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


def _extract_proxy_response(upstream_resp: "httpx.Response") -> tuple[int, list[tuple[bytes, bytes]], bytes]:
    """Extract status, headers, and body from an httpx response for proxying.

    Returns:
        A tuple of (status_code, headers, body).
    """
    headers = [
        (k.encode(), v.encode()) for k, v in upstream_resp.headers.items() if k.lower() not in _HOP_BY_HOP_HEADERS
    ]
    return upstream_resp.status_code, headers, upstream_resp.content


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

    def _should_proxy(self, path: str, scope: "Scope") -> bool:
        try:
            from urllib.parse import unquote
        except ImportError:  # pragma: no cover
            decoded = path
            matches_prefix = path.startswith(self._proxy_allow_prefixes)
        else:
            decoded = unquote(path)
            matches_prefix = decoded.startswith(self._proxy_allow_prefixes) or path.startswith(
                self._proxy_allow_prefixes
            )

        if not matches_prefix:
            return False

        app = scope.get("app")  # pyright: ignore[reportUnknownMemberType]
        return not (app and is_litestar_route(path, app))

    async def _proxy_http(self, scope: dict[str, Any], receive: Any, send: Any) -> None:
        """Proxy a single HTTP request to the Vite dev server.

        The upstream response is buffered inside the httpx client context manager and only sent
        after the context exits. This avoids ASGI errors when httpx raises during cleanup after the
        response has started.
        """
        target_base_url = self._get_target_base_url()
        if target_base_url is None:
            await send({"type": "http.response.start", "status": 503, "headers": [(b"content-type", b"text/plain")]})
            await send({"type": "http.response.body", "body": b"Vite server not running", "more_body": False})
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

        headers = [(k.decode(), v.decode()) for k, v in scope.get("headers", [])]
        body = b""
        more_body = True
        while more_body:
            event = await receive()
            if event["type"] != "http.request":
                continue
            body += event.get("body", b"")
            more_body = event.get("more_body", False)

        response_status = 502
        response_headers: list[tuple[bytes, bytes]] = [(b"content-type", b"text/plain")]
        response_body = b"Bad gateway"
        got_full_body = False

        # Use shared client from plugin when available (connection pooling)
        client = self._plugin.proxy_client if self._plugin is not None else None

        try:
            if client is not None:
                # Use shared client (connection pooling, HTTP/2 multiplexing)
                upstream_resp = await client.request(method, url, headers=headers, content=body, timeout=10.0)
                response_status, response_headers, response_body = _extract_proxy_response(upstream_resp)
                got_full_body = True
            else:
                # Fallback: per-request client (graceful degradation)
                http2_enabled = check_http2_support(self.http2)
                async with httpx.AsyncClient(http2=http2_enabled) as fallback_client:
                    upstream_resp = await fallback_client.request(
                        method, url, headers=headers, content=body, timeout=10.0
                    )
                    response_status, response_headers, response_body = _extract_proxy_response(upstream_resp)
                    got_full_body = True
        except Exception as exc:  # noqa: BLE001  # pragma: no cover - catch all cleanup errors
            if not got_full_body:
                response_body = f"Upstream error: {exc}".encode()

        await send({"type": "http.response.start", "status": response_status, "headers": response_headers})
        await send({"type": "http.response.body", "body": response_body, "more_body": False})


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
    skip_headers = (
        b"host",
        b"upgrade",
        b"connection",
        b"sec-websocket-key",
        b"sec-websocket-version",
        b"sec-websocket-protocol",
        b"sec-websocket-extensions",
    )
    return [(k.decode(), v.decode()) for k, v in scope.get("headers", []) if k.lower() not in skip_headers]


def extract_subprotocols(scope: dict[str, Any]) -> list[str]:
    """Extract WebSocket subprotocols from the request headers.

    Returns:
        A list of subprotocol strings.
    """
    for key, value in scope.get("headers", []):
        if key.lower() == b"sec-websocket-protocol":
            return [p.strip() for p in value.decode().split(",")]
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
        """Proxy WebSocket messages between browser and Vite dev server.

        Raises:
            BaseException: Re-raises unexpected exceptions to allow the ASGI server to log them.
        """
        scope_dict = dict(socket.scope)
        target = build_hmr_target_url(hotfile_path, scope_dict, hmr_path, asset_url)
        if target is None:
            console.print("[yellow][vite-hmr] Vite server not running[/]")
            await socket.close(code=1011, reason="Vite server not running")
            return

        headers = extract_forward_headers(scope_dict)
        subprotocols = extract_subprotocols(scope_dict)
        typed_subprotocols: list[Subprotocol] = [cast("Subprotocol", p) for p in subprotocols]
        await socket.accept(subprotocols=typed_subprotocols[0] if typed_subprotocols else None)

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
        async def http_proxy(self, request: "Request[Any, Any, Any]") -> "Response[bytes]":
            """Proxy all HTTP requests to the SSR framework dev server.

            Returns:
                A Response with the proxied content from the SSR server.
            """
            target_url = get_target_url()
            if target_url is None:
                return Response(content=b"SSR server not running", status_code=503, media_type="text/plain")

            req_path: str = request.url.path
            url = build_proxy_url(target_url, req_path, request.url.query or "")

            if is_proxy_debug():
                console.print(f"[dim][ssr-proxy] {request.method} {req_path} → {url}[/]")

            headers_to_forward = [
                (k, v) for k, v in request.headers.items() if k.lower() not in {"host", "connection", "keep-alive"}
            ]
            body = await request.body()

            # Use shared client from plugin when available (connection pooling)
            client = plugin.proxy_client if plugin is not None else None

            try:
                if client is not None:
                    # Use shared client (connection pooling, HTTP/2 multiplexing)
                    upstream_resp = await client.request(
                        request.method,
                        url,
                        headers=headers_to_forward,
                        content=body,
                        follow_redirects=False,
                        timeout=30.0,
                    )
                else:
                    # Fallback: per-request client (graceful degradation)
                    http2_enabled = check_http2_support(http2)
                    async with httpx.AsyncClient(http2=http2_enabled, timeout=30.0) as fallback_client:
                        upstream_resp = await fallback_client.request(
                            request.method, url, headers=headers_to_forward, content=body, follow_redirects=False
                        )
            except httpx.ConnectError:
                return Response(
                    content=f"SSR server not running at {target_url}".encode(), status_code=503, media_type="text/plain"
                )
            except httpx.HTTPError as exc:
                return Response(content=str(exc).encode(), status_code=502, media_type="text/plain")

            return Response(
                content=upstream_resp.content,
                status_code=upstream_resp.status_code,
                headers=dict(upstream_resp.headers.items()),
                media_type=upstream_resp.headers.get("content-type"),
            )

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

            await socket.accept(subprotocols=typed_subprotocols[0] if typed_subprotocols else None)
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
