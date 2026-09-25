"""Unified IPC transport manager and platform-aware auto-selection engine."""

import os
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from litestar_vite.ipc._base import BaseIPCTransport, CircuitBreakerOpenError, UnsupportedPlatformError
from litestar_vite.ipc._circuit_breaker import SSRCircuitBreaker
from litestar_vite.ipc._stdio import StdioIPCTransport
from litestar_vite.ipc._tcp import TCPStreamIPCTransport
from litestar_vite.ipc._uds import UnixSocketIPCTransport

__all__ = ("IPCTransportManager",)


class IPCTransportManager:
    """Manages IPC transport lifecycle, platform auto-selection, and fault-tolerant fallbacks."""

    __slots__ = ("_circuit_breaker", "_fallback_transport", "_transport")

    def __init__(
        self,
        transport: BaseIPCTransport,
        circuit_breaker: SSRCircuitBreaker | None = None,
        fallback_transport: BaseIPCTransport | None = None,
    ) -> None:
        """Initialize the IPC transport manager with an active transport and optional resilience mechanisms.

        Args:
            transport: Primary active IPC transport.
            circuit_breaker: Optional circuit breaker guarding outbound requests.
            fallback_transport: Optional secondary transport to try when primary transport trips or fails.
        """
        self._transport = transport
        self._circuit_breaker = circuit_breaker
        self._fallback_transport = fallback_transport

    @property
    def transport(self) -> BaseIPCTransport:
        """Return the primary active transport.

        Returns:
            Configured BaseIPCTransport instance.
        """
        return self._transport

    @property
    def fallback_transport(self) -> BaseIPCTransport | None:
        """Return the fallback transport if configured.

        Returns:
            Secondary BaseIPCTransport instance or None.
        """
        return self._fallback_transport

    @property
    def circuit_breaker(self) -> SSRCircuitBreaker | None:
        """Return the configured circuit breaker or None.

        Returns:
            Active SSRCircuitBreaker instance or None.
        """
        return self._circuit_breaker

    @property
    def is_running(self) -> bool:
        """Return True if the underlying transport is active.

        Returns:
            Boolean indicating ready status.
        """
        return self._transport.is_running

    async def start(self) -> None:
        """Initialize both primary and optional fallback transports."""
        await self._transport.start()
        if self._fallback_transport is not None:
            await self._fallback_transport.start()

    async def close(self) -> None:
        """Shut down both primary and optional fallback transports."""
        await self._transport.close()
        if self._fallback_transport is not None:
            await self._fallback_transport.close()

    async def send_request(self, payload: dict[str, Any], timeout: float = 10.0) -> dict[str, Any]:
        """Send an IPC request with circuit breaker protection and fallback execution.

        Args:
            payload: Request dictionary payload.
            timeout: Maximum time in seconds to await response.

        Returns:
            Worker response dictionary.

        Raises:
            CircuitBreakerOpenError: When circuit is open and no fallback transport is available.
            IPCError: When both primary and fallback transports fail.
        """
        if self._circuit_breaker is not None:
            try:
                async with self._circuit_breaker:
                    return await self._transport.send_request(payload, timeout=timeout)
            except CircuitBreakerOpenError:
                if self._fallback_transport is not None:
                    return await self._fallback_transport.send_request(payload, timeout=timeout)
                raise
            except Exception:
                if self._fallback_transport is not None:
                    return await self._fallback_transport.send_request(payload, timeout=timeout)
                raise

        try:
            return await self._transport.send_request(payload, timeout=timeout)
        except Exception:
            if self._fallback_transport is not None:
                return await self._fallback_transport.send_request(payload, timeout=timeout)
            raise

    @classmethod
    def create_transport(
        cls,
        *,
        mode: str = "auto",
        command: list[str] | None = None,
        socket_path: str | Path | None = None,
        url: str | None = None,
        cwd: Path | str | None = None,
    ) -> BaseIPCTransport:
        """Resolve and instantiate the optimal IPC transport based on configuration and host OS.

        Args:
            mode: Resolution mode ("auto", "stdio", "uds", "tcp").
            command: Subprocess execution array for stdio transport.
            socket_path: Path to Unix domain socket for UDS transport.
            url: HTTP/TCP URL for TCP stream transport.
            cwd: Working directory for spawned worker subprocesses.

        Returns:
            Configured BaseIPCTransport instance matching parameters.

        Raises:
            UnsupportedPlatformError: If Unix domain socket is requested on Windows.
        """
        resolved_mode = mode
        if resolved_mode == "auto":
            if socket_path:
                resolved_mode = "uds"
            elif command:
                resolved_mode = "stdio"
            elif url:
                resolved_mode = "tcp"
            else:
                resolved_mode = "stdio"

        if resolved_mode == "uds":
            if os.name == "nt":
                msg = "Unix domain sockets are not supported on Windows. Configure a stdio command or TCP URL instead."
                raise UnsupportedPlatformError(msg)
            if socket_path is None:
                msg = "Unix domain socket transport requires 'socket_path'."
                raise ValueError(msg)
            return UnixSocketIPCTransport(socket_path=socket_path)

        if resolved_mode == "tcp":
            parsed = urlparse(url or "http://127.0.0.1:13714/render")
            port = parsed.port or (443 if parsed.scheme == "https" else 13714)
            return TCPStreamIPCTransport(host=parsed.hostname or "127.0.0.1", port=port, path=parsed.path or "/render")

        return StdioIPCTransport(command=command or ["node", "ssr.js"], cwd=cwd)
