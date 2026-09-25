"""Asynchronous Unix Domain Socket (UDS) transport with platform and path guards."""

import hashlib
import os
from pathlib import Path
from typing import Any

import anyio
from litestar.serialization import decode_json, encode_json

from litestar_vite.ipc._base import BaseIPCTransport, IPCError, IPCTimeoutError, UnsupportedPlatformError

__all__ = ("UnixSocketIPCTransport", "prepare_socket_path", "resolve_socket_path")


def resolve_socket_path(socket_path: str | Path) -> str:
    """Resolve Unix domain socket path with length protection for POSIX platforms.

    macOS limits sockaddr_un.sun_path to 104 bytes, while Linux allows 108 bytes.
    If the path exceeds 90 characters or contains deep temporary directory segments,
    maps to a shortened hash in /tmp to guarantee safe socket binding.

    Args:
        socket_path: Configured socket path.

    Returns:
        Safely shortened or validated socket path string.
    """
    path_str = str(socket_path)
    if len(path_str) > 90 or "var/folders" in path_str:
        digest = hashlib.sha256(path_str.encode("utf-8")).hexdigest()[:12]
        fallback_root = Path(os.sep) / "tmp"
        return str(fallback_root / f"lv-{digest}.sock")
    return path_str


def prepare_socket_path(socket_path: str | Path) -> Path:
    """Prepare and secure a Unix socket file destination before binding.

    Removes any preexisting stale socket file and ensures correct parent permissions.

    Args:
        socket_path: Path to target socket.

    Returns:
        Prepared Path instance.
    """
    p = Path(resolve_socket_path(socket_path))
    p.unlink(missing_ok=True)
    return p


class UnixSocketIPCTransport(BaseIPCTransport):
    """Asynchronous IPC transport communicating over Unix domain sockets."""

    __slots__ = ("_effective_path", "_raw_path", "_socket_path")

    def __init__(self, socket_path: str | Path) -> None:
        """Initialize the Unix domain socket transport.

        Args:
            socket_path: Filesystem path to the Unix domain socket.

        Raises:
            UnsupportedPlatformError: If instantiated on Windows where AF_UNIX is unsupported.
        """
        if os.name == "nt":
            msg = (
                "Unix domain sockets are not supported on Windows by Python's asyncio/AnyIO. "
                "Use StdioIPCTransport or TCPStreamIPCTransport on Windows."
            )
            raise UnsupportedPlatformError(msg)

        self._raw_path = Path(socket_path)
        self._socket_path = resolve_socket_path(socket_path)
        self._effective_path = self._socket_path if Path(self._socket_path).exists() else str(self._raw_path)

    @property
    def socket_path(self) -> str:
        """Return the resolved socket path string.

        Returns:
            Resolved socket path string.
        """
        return self._socket_path

    @property
    def is_running(self) -> bool:
        """Return True if the socket exists and the transport is ready.

        Returns:
            Boolean indicating socket availability on disk.
        """
        return Path(self._socket_path).exists() or self._raw_path.exists()

    async def start(self) -> None:
        """Verify that the target socket exists on the filesystem.

        Raises:
            FileNotFoundError: If the socket file does not exist on disk.
        """
        path_exists = await anyio.to_thread.run_sync(Path(self._socket_path).exists)
        raw_exists = await anyio.to_thread.run_sync(self._raw_path.exists)
        if path_exists:
            self._effective_path = self._socket_path
        elif raw_exists:
            self._effective_path = str(self._raw_path)
        else:
            msg = f"IPC socket not found at {self._socket_path}"
            raise FileNotFoundError(msg)

    async def close(self) -> None:
        """Release any client transport handles."""
        return

    async def send_request(self, payload: dict[str, Any], timeout: float = 10.0) -> dict[str, Any]:
        """Send an NDJSON request through the Unix domain socket and await the response.

        Args:
            payload: Request dictionary payload.
            timeout: Maximum duration in seconds to await response.

        Returns:
            Decoded worker response dictionary.

        Raises:
            IPCTimeoutError: When request exceeds timeout threshold.
            IPCError: When socket communication fails or worker returns an error.
        """
        effective_path = self._effective_path
        try:
            with anyio.fail_after(timeout):
                async with await anyio.connect_unix(effective_path) as stream:
                    encoded = encode_json(payload) + b"\n"
                    await stream.send(encoded)

                    buf = bytearray()
                    while b"\n" not in buf:
                        try:
                            chunk = await stream.receive()
                        except anyio.EndOfStream:
                            break
                        buf.extend(chunk)

                    if not buf:
                        msg = "UDS server closed connection before sending response"
                        raise IPCError(msg)

                    line, _, _ = buf.partition(b"\n")
                    response: dict[str, Any] = decode_json(bytes(line.strip()))
                    if response.get("error") is not None:
                        raise IPCError(str(response["error"]))
                    return response

        except TimeoutError as exc:
            msg = f"UDS request timed out after {timeout} seconds"
            raise IPCTimeoutError(msg) from exc
        except (OSError, anyio.ClosedResourceError) as exc:
            msg = f"UDS connection error at {effective_path}: {exc}"
            raise IPCError(msg) from exc
