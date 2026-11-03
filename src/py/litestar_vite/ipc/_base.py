"""Base contracts, protocols, data structures, and exceptions for IPC communication."""

from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable

__all__ = (
    "BaseIPCTransport",
    "CircuitBreakerOpenError",
    "IPCError",
    "IPCRequest",
    "IPCResponse",
    "IPCTimeoutError",
    "IPCWorkerCrashError",
)


class IPCError(Exception):
    """Base exception for all IPC errors."""


class IPCTimeoutError(IPCError):
    """Raised when an IPC request exceeds the configured timeout threshold."""


class IPCWorkerCrashError(IPCError):
    """Raised when an IPC child worker terminates unexpectedly."""


class CircuitBreakerOpenError(IPCError):
    """Raised when an IPC request is attempted while the circuit breaker is open."""


@dataclass(slots=True)
class IPCRequest:
    """Structured representation of an outbound JSON-RPC/NDJSON IPC request payload."""

    id: int
    """Monotonically increasing request correlation identifier."""
    method: str
    """RPC method name (`'ssr'`, `'fragment'`, `'ping'`, or `'shutdown'`)."""
    params: dict[str, Any] | None = None
    """Optional JSON-serializable parameters dictionary passed to the worker method."""

    def to_dict(self) -> dict[str, Any]:
        """Convert the request into a JSON-serializable dictionary.

        Returns:
            Dictionary payload adhering to the RPC framing contract.
        """
        payload: dict[str, Any] = {"id": self.id, "method": self.method}
        if self.params is not None:
            payload["params"] = self.params
        return payload


@dataclass(slots=True)
class IPCResponse:
    """Structured representation of an inbound JSON-RPC/NDJSON IPC response payload."""

    id: int
    """Correlation identifier matching the originating `IPCRequest.id`."""
    result: Any = None
    """Decoded response payload returned by the worker when successful."""
    error: str | None = None
    """Error message string returned by the worker when execution fails."""


@runtime_checkable
class BaseIPCTransport(Protocol):
    """Protocol defining the asynchronous IPC transport contract."""

    __slots__ = ()

    async def start(self) -> None:
        """Start or initialize the IPC transport."""
        ...

    async def close(self) -> None:
        """Gracefully shut down the IPC transport and release all resources."""
        ...

    async def send_request(self, payload: dict[str, Any], timeout: float = 10.0) -> dict[str, Any]:
        """Send a JSON payload and return the response.

        Args:
            payload: Request dictionary payload.
            timeout: Maximum duration in seconds to wait for a response.

        Returns:
            Decoded response payload dictionary from the worker.
        """
        ...

    @property
    def is_running(self) -> bool:
        """Return True if the transport is running and ready to handle requests."""
        ...
