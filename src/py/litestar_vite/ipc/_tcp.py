"""HTTP transport for communicating with Vite's development SSR middleware."""

from typing import Any, cast

import anyio
import httpx2

from litestar_vite.ipc._base import BaseIPCTransport, IPCError, IPCTimeoutError

__all__ = ("TCPStreamIPCTransport",)


class TCPStreamIPCTransport(BaseIPCTransport):
    """Send development SSR RPC requests through a pooled HTTP client."""

    __slots__ = ("_client", "_host", "_path", "_port", "_scheme", "_url")

    def __init__(
        self, host: str = "127.0.0.1", port: int = 5173, path: str = "/__litestar_ssr__", *, scheme: str = "http"
    ) -> None:
        """Configure the Vite SSR endpoint, including HTTPS when enabled."""
        if scheme not in {"http", "https"}:
            msg = "SSR transport scheme must be http or https"
            raise ValueError(msg)
        self._host = host
        self._port = port
        self._path = path if path.startswith("/") else f"/{path}"
        self._scheme = scheme
        self._url = httpx2.URL(scheme=scheme, host=host.strip("[]"), port=port, path=self._path)
        self._client: httpx2.AsyncClient | None = None

    @property
    def host(self) -> str:
        """Return the target hostname or IP address."""
        return self._host

    @property
    def port(self) -> int:
        """Return the target TCP port."""
        return self._port

    @property
    def path(self) -> str:
        """Return the configured HTTP endpoint path."""
        return self._path

    @property
    def scheme(self) -> str:
        """Return the endpoint protocol."""
        return self._scheme

    @property
    def is_running(self) -> bool:
        """Return True because connections are established lazily on the next request."""
        return True

    async def start(self) -> None:
        """Initialize the client connection pool if needed."""
        if self._client is None or self._client.is_closed:
            self._client = httpx2.AsyncClient(trust_env=False)

    async def close(self) -> None:
        """Release pooled connections."""
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    async def send_request(self, payload: dict[str, Any], timeout: float = 10.0) -> dict[str, Any]:
        """Send an RPC request within a total deadline and validate its response.

        Raises:
            IPCTimeoutError: The request exceeded its total deadline.
            IPCError: The connection failed or the server returned an invalid response.
        """
        try:
            with anyio.fail_after(timeout):
                await self.start()
                client = cast("httpx2.AsyncClient", self._client)
                response = await client.post(self._url, json=payload, timeout=timeout)
                if response.status_code != 200:
                    msg = f"Upstream SSR server returned HTTP {response.status_code}: {response.text}"
                    raise IPCError(msg)
                try:
                    result = response.json()
                except ValueError as exc:
                    msg = "SSR server returned invalid JSON"
                    raise IPCError(msg) from exc
                if not isinstance(result, dict) or ("result" not in result and "error" not in result):
                    msg = "SSR server response must be an object containing result or error"
                    raise IPCError(msg)
                return cast("dict[str, Any]", result)
        except (TimeoutError, httpx2.TimeoutException) as exc:
            msg = f"TCP request to {self._host}:{self._port} timed out after {timeout} seconds"
            raise IPCTimeoutError(msg) from exc
        except httpx2.HTTPError as exc:
            msg = f"TCP connection error to {self._host}:{self._port}: {exc}"
            raise IPCError(msg) from exc
