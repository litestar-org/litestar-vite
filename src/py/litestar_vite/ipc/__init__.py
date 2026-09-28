"""Inter-Process Communication (IPC) transports and resilience utilities for SSR and Fragments."""

from litestar_vite.ipc._base import (
    BaseIPCTransport,
    CircuitBreakerOpenError,
    IPCError,
    IPCRequest,
    IPCResponse,
    IPCTimeoutError,
    IPCWorkerCrashError,
)
from litestar_vite.ipc._circuit_breaker import CircuitState, SSRCircuitBreaker
from litestar_vite.ipc._stdio import StdioIPCTransport
from litestar_vite.ipc._tcp import TCPStreamIPCTransport

__all__ = (
    "BaseIPCTransport",
    "CircuitBreakerOpenError",
    "CircuitState",
    "IPCError",
    "IPCRequest",
    "IPCResponse",
    "IPCTimeoutError",
    "IPCWorkerCrashError",
    "SSRCircuitBreaker",
    "StdioIPCTransport",
    "TCPStreamIPCTransport",
)
