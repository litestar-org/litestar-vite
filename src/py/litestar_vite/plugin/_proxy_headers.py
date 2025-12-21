"""Proxy headers middleware for handling X-Forwarded-* headers securely.

This module provides middleware to handle X-Forwarded-* headers from reverse proxies
like Railway, Heroku, AWS ALB, nginx, etc.

Security: Headers are only trusted when the direct caller IP is in the configured
trusted_proxies list. This prevents header spoofing attacks.

Related: https://github.com/litestar-org/litestar-vite/issues/167
"""

import ipaddress
from typing import TYPE_CHECKING, Any, cast

from litestar.enums import ScopeType
from litestar.middleware import AbstractMiddleware

if TYPE_CHECKING:
    from litestar.types import ASGIApp, Receive, Scope, Send

__all__ = ("ProxyHeadersMiddleware", "TrustedHosts")


class TrustedHosts:
    """Container for trusted proxy hosts and networks.

    Provides efficient lookup for IP addresses and CIDR networks.
    Following Uvicorn's security model for proxy header validation.

    Supports:
        - Wildcard "*" to trust all hosts (for controlled environments)
        - IPv4 addresses: "192.168.1.1"
        - IPv6 addresses: "::1"
        - CIDR notation: "10.0.0.0/8", "fd00::/8"
        - Literals for non-IP hosts (e.g., Unix socket paths)
    """

    __slots__ = ("always_trust", "trusted_hosts", "trusted_literals", "trusted_networks")

    def __init__(self, trusted_hosts: "list[str] | str") -> None:
        """Initialize trusted hosts container.

        Args:
            trusted_hosts: A single host, comma-separated string, or list of hosts.
                Use "*" to trust all hosts (only in controlled environments).
        """
        self.always_trust: bool = trusted_hosts in ("*", ["*"])
        self.trusted_literals: set[str] = set()
        self.trusted_hosts: set[ipaddress.IPv4Address | ipaddress.IPv6Address] = set()
        self.trusted_networks: set[ipaddress.IPv4Network | ipaddress.IPv6Network] = set()

        if not self.always_trust:
            hosts_list: list[str]
            if isinstance(trusted_hosts, str):
                hosts_list = [h.strip() for h in trusted_hosts.split(",") if h.strip()]
            else:
                hosts_list = trusted_hosts

            for host in hosts_list:
                if "/" in host:
                    # CIDR notation
                    try:
                        self.trusted_networks.add(ipaddress.ip_network(host, strict=False))
                    except ValueError:
                        # Not a valid network, treat as literal
                        self.trusted_literals.add(host)
                else:
                    try:
                        self.trusted_hosts.add(ipaddress.ip_address(host))
                    except ValueError:
                        # Not a valid IP, treat as literal (e.g., Unix socket path)
                        self.trusted_literals.add(host)

    def __contains__(self, host: "str | None") -> bool:
        """Check if a host is trusted.

        Args:
            host: The host to check. Can be an IP address or literal.

        Returns:
            True if the host is trusted, False otherwise.
        """
        # None and empty string are never trusted
        if not host:
            return False
        if self.always_trust:
            return True

        try:
            ip = ipaddress.ip_address(host)
            if ip in self.trusted_hosts:
                return True
            return any(ip in net for net in self.trusted_networks)
        except ValueError:
            return host in self.trusted_literals

    def get_trusted_client_host(self, x_forwarded_for: str) -> str:
        """Extract the real client IP from X-Forwarded-For header.

        The X-Forwarded-For header contains a comma-separated list of IPs.
        Each proxy appends the client IP to the list. We find the first
        untrusted host (reading from right to left) which is the real client.

        Args:
            x_forwarded_for: The X-Forwarded-For header value.

        Returns:
            The first untrusted host in the chain, or the original client
            if all hosts are trusted.
        """
        hosts = [h.strip() for h in x_forwarded_for.split(",") if h.strip()]

        if not hosts:
            return ""

        if self.always_trust:
            # When trusting all, return the leftmost (original client)
            return hosts[0]

        # Each proxy appends to the list, so check in reverse
        # Find the first untrusted host from the right
        for host in reversed(hosts):
            if host not in self:
                return host

        # All hosts are trusted - return the original client
        return hosts[0]


class ProxyHeadersMiddleware(AbstractMiddleware):
    """ASGI middleware for secure proxy header handling.

    Only processes X-Forwarded-* headers when the direct caller (scope["client"])
    is in the trusted hosts list. This prevents header spoofing attacks.

    Handles:
        - X-Forwarded-Proto: Sets scope["scheme"] (http/https/ws/wss)
        - X-Forwarded-For: Sets scope["client"] to the real client IP
        - X-Forwarded-Host: Optionally sets the Host header

    Security:
        Never blindly trusts headers from any client. Validates caller IP
        against trusted hosts before reading headers. Validates scheme values
        to only allow http/https/ws/wss.

    Example::

        from litestar_vite import VitePlugin, ViteConfig
        from litestar_vite.config import RuntimeConfig

        # Trust all proxies (Railway, Heroku, container environments)
        app = Litestar(
            plugins=[VitePlugin(config=ViteConfig(
                runtime=RuntimeConfig(trusted_proxies="*")
            ))]
        )

        # Trust specific proxy IPs
        app = Litestar(
            plugins=[VitePlugin(config=ViteConfig(
                runtime=RuntimeConfig(trusted_proxies=["10.0.0.0/8", "172.16.0.0/12"])
            ))]
        )
    """

    scopes = {ScopeType.HTTP, ScopeType.WEBSOCKET}

    def __init__(
        self, app: "ASGIApp", trusted_hosts: "list[str] | str" = "127.0.0.1", handle_forwarded_host: bool = True
    ) -> None:
        """Initialize the proxy headers middleware.

        Args:
            app: The ASGI application to wrap.
            trusted_hosts: Hosts to trust for X-Forwarded-* headers.
                Defaults to "127.0.0.1" (localhost only).
            handle_forwarded_host: Whether to handle X-Forwarded-Host header
                for Host header rewriting. Defaults to True.
        """
        super().__init__(app)
        self.trusted_hosts = TrustedHosts(trusted_hosts)
        self.handle_forwarded_host = handle_forwarded_host

    async def __call__(self, scope: "Scope", receive: "Receive", send: "Send") -> None:
        """Process the request and apply proxy headers if trusted.

        Args:
            scope: The ASGI scope.
            receive: The receive callable.
            send: The send callable.
        """
        client_addr = scope.get("client")  # pyright: ignore[reportUnknownMemberType]
        client_host = client_addr[0] if client_addr else None

        if client_host in self.trusted_hosts:
            # Build a dict of headers for efficient lookup
            headers: dict[bytes, bytes] = {}
            for key, value in scope.get("headers", []):  # pyright: ignore[reportUnknownMemberType]
                # Use first occurrence only (as per HTTP spec)
                if key not in headers:
                    headers[key] = value

            scope_dict = cast("dict[str, Any]", scope)

            # X-Forwarded-Proto -> scope["scheme"]
            if b"x-forwarded-proto" in headers:
                proto = headers[b"x-forwarded-proto"].decode("latin-1").strip().lower()
                if proto in {"http", "https", "ws", "wss"}:
                    # For WebSocket, ensure ws/wss scheme
                    if scope["type"] == "websocket":
                        if proto == "https":
                            scope_dict["scheme"] = "wss"
                        elif proto == "http":
                            scope_dict["scheme"] = "ws"
                        else:
                            scope_dict["scheme"] = proto
                    else:
                        scope_dict["scheme"] = proto

            # X-Forwarded-For -> scope["client"]
            if b"x-forwarded-for" in headers:
                x_forwarded_for = headers[b"x-forwarded-for"].decode("latin-1")
                real_client = self.trusted_hosts.get_trusted_client_host(x_forwarded_for)
                if real_client:
                    scope_dict["client"] = (real_client, 0)

            # X-Forwarded-Host -> replace Host header
            if self.handle_forwarded_host and b"x-forwarded-host" in headers:
                forwarded_host = headers[b"x-forwarded-host"]
                # Rebuild headers list with replaced Host
                new_headers: list[tuple[bytes, bytes]] = []
                host_replaced = False
                for key, value in scope.get("headers", []):  # pyright: ignore[reportUnknownMemberType]
                    if key == b"host" and not host_replaced:
                        new_headers.append((b"host", forwarded_host))
                        host_replaced = True
                    else:
                        new_headers.append((key, value))
                # If no Host header existed, add it
                if not host_replaced:
                    new_headers.append((b"host", forwarded_host))
                scope_dict["headers"] = new_headers

        await self.app(scope, receive, send)
