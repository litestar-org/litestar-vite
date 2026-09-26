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
    """Structured representation of an outbound IPC request payload."""

    id: int
    method: str
    params: dict[str, Any] | None = None

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
    """Structured representation of an inbound IPC response payload."""

    id: int
    result: Any = None
    error: str | None = None


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
