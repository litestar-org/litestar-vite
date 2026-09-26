"""Asynchronous HTTP/1.1 TCP stream transport for communicating with Vite's dev SSR middleware."""

from typing import Any

import anyio
from litestar.serialization import decode_json, encode_json

from litestar_vite.ipc._base import BaseIPCTransport, IPCError, IPCTimeoutError

__all__ = ("TCPStreamIPCTransport",)


def _decode_chunked_http_body(body_buffer: bytearray) -> bytes:
    """Decode an HTTP/1.1 chunked transfer-encoded byte buffer.

    Args:
        body_buffer: Mutable bytearray containing raw chunked body bytes.

    Returns:
        Concatenated unchunked payload bytes.
    """
    decoded_chunks: list[bytes] = []
    while body_buffer:
        crlf_pos = body_buffer.find(b"\r\n")
        if crlf_pos == -1:
            break
        hex_len_bytes = bytes(body_buffer[:crlf_pos]).split(b";", 1)[0].strip()
        del body_buffer[: crlf_pos + 2]
        if not hex_len_bytes:
            continue
        try:
            chunk_len = int(hex_len_bytes, 16)
        except ValueError:
            break

        if chunk_len == 0:
            break

        chunk_data = bytes(body_buffer[:chunk_len])
        del body_buffer[:chunk_len]
        decoded_chunks.append(chunk_data)

        if body_buffer.startswith(b"\r\n"):
            del body_buffer[:2]

    return b"".join(decoded_chunks)


def _parse_http_response(raw_response: bytearray) -> dict[str, Any]:
    """Parse raw HTTP/1.1 response bytes into a dictionary.

    Args:
        raw_response: Mutable bytearray of received HTTP/1.1 response bytes.

    Returns:
        Decoded payload dictionary.

    Raises:
        IPCError: If response is incomplete or reports an upstream error status.
    """
    header_end = raw_response.find(b"\r\n\r\n")
    if header_end == -1:
        msg = "Incomplete HTTP response from SSR server"
        raise IPCError(msg)

    header_part = bytes(raw_response[:header_end])
    body_part = bytearray(raw_response[header_end + 4 :])

    status_line = header_part.split(b"\r\n", 1)[0].decode("latin-1")
    status_parts = status_line.split(" ", 2)
    status_code = int(status_parts[1]) if len(status_parts) > 1 else 200

    is_chunked = False
    for line in header_part.split(b"\r\n")[1:]:
        if b":" in line:
            k, v = line.split(b":", 1)
            if k.strip().lower() == b"transfer-encoding" and b"chunked" in v.lower():
                is_chunked = True
                break

    decoded_body = _decode_chunked_http_body(body_part) if is_chunked else bytes(body_part)

    if status_code != 200:
        err_msg = decoded_body.decode("utf-8", errors="replace")
        msg = f"Upstream SSR server returned HTTP {status_code}: {err_msg}"
        raise IPCError(msg)

    result: dict[str, Any] = decode_json(decoded_body)
    return result


class TCPStreamIPCTransport(BaseIPCTransport):
    """Asynchronous HTTP/1.1 POST transport over AnyIO TCP socket streams for Vite dev SSR."""

    __slots__ = ("_host", "_path", "_port")

    def __init__(self, host: str = "127.0.0.1", port: int = 5173, path: str = "/__litestar_ssr__") -> None:
        """Initialize the TCP stream transport.

        Args:
            host: Target hostname or IP address.
            port: Target TCP port number.
            path: HTTP endpoint path on the Vite dev server.
        """
        self._host = host
        self._port = port
        self._path = path if path.startswith("/") else f"/{path}"

    @property
    def host(self) -> str:
        """Return the target host address.

        Returns:
            Hostname or IP address.
        """
        return self._host

    @property
    def port(self) -> int:
        """Return the target TCP port.

        Returns:
            Port number.
        """
        return self._port

    @property
    def path(self) -> str:
        """Return the configured HTTP endpoint path.

        Returns:
            Endpoint path string.
        """
        return self._path

    @property
    def is_running(self) -> bool:
        """Return True indicating the transport is ready to connect.

        Returns:
            Always True for stateless client socket connections.
        """
        return True

    async def start(self) -> None:
        """Initialize any client connection pools."""
        return

    async def close(self) -> None:
        """Release any persistent client socket connections."""
        return

    async def send_request(self, payload: dict[str, Any], timeout: float = 10.0) -> dict[str, Any]:
        """Send an HTTP/1.1 POST request over TCP and await the decoded JSON response.

        Args:
            payload: Request dictionary payload.
            timeout: Maximum duration in seconds to await response.

        Returns:
            Decoded worker response dictionary.

        Raises:
            IPCTimeoutError: When request exceeds timeout threshold.
            IPCError: When socket communication fails or server returns an error.
        """
        try:
            with anyio.fail_after(timeout):
                async with await anyio.connect_tcp(self._host, self._port) as stream:
                    body = encode_json(payload)
                    req = (
                        f"POST {self._path} HTTP/1.1\r\n"
                        f"Host: {self._host}:{self._port}\r\n"
                        "Content-Type: application/json\r\n"
                        f"Content-Length: {len(body)}\r\n"
                        "Connection: close\r\n\r\n"
                    ).encode("latin-1") + body

                    await stream.send(req)

                    raw_response = bytearray()
                    while True:
                        try:
                            chunk = await stream.receive()
                        except anyio.EndOfStream:
                            break
                        raw_response.extend(chunk)

                    if not raw_response:
                        msg = "TCP server closed connection before sending response"
                        raise IPCError(msg)

                    return _parse_http_response(raw_response)

        except TimeoutError as exc:
            msg = f"TCP request to {self._host}:{self._port} timed out after {timeout} seconds"
            raise IPCTimeoutError(msg) from exc
        except (OSError, anyio.ClosedResourceError) as exc:
            msg = f"TCP connection error to {self._host}:{self._port}: {exc}"
            raise IPCError(msg) from exc
