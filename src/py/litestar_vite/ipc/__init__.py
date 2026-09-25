"""Cross-platform Inter-Process Communication (IPC) transports and resilience utilities."""

from litestar_vite.ipc._base import (
    BaseIPCTransport,
    CircuitBreakerOpenError,
    IPCError,
    IPCRequest,
    IPCResponse,
    IPCTimeoutError,
    IPCWorkerCrashError,
    UnsupportedPlatformError,
)
from litestar_vite.ipc._circuit_breaker import CircuitState, SSRCircuitBreaker
from litestar_vite.ipc._manager import IPCTransportManager
from litestar_vite.ipc._stdio import StdioIPCTransport
from litestar_vite.ipc._tcp import TCPStreamIPCTransport
from litestar_vite.ipc._uds import UnixSocketIPCTransport, prepare_socket_path, resolve_socket_path

__all__ = (
    "BaseIPCTransport",
    "CircuitBreakerOpenError",
    "CircuitState",
    "IPCError",
    "IPCRequest",
    "IPCResponse",
    "IPCTimeoutError",
    "IPCTransportManager",
    "IPCWorkerCrashError",
    "SSRCircuitBreaker",
    "StdioIPCTransport",
    "TCPStreamIPCTransport",
    "UnixSocketIPCTransport",
    "UnsupportedPlatformError",
    "prepare_socket_path",
    "resolve_socket_path",
)
