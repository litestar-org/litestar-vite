"""Tests for ProxyHeadersMiddleware and TrustedHosts."""

from typing import TYPE_CHECKING, Any

import pytest

from litestar_vite.plugin._proxy_headers import ProxyHeadersMiddleware, TrustedHosts

if TYPE_CHECKING:
    from litestar.types import Receive, Scope, Send


# =============================================================================
# TrustedHosts Tests
# =============================================================================


def test_trusted_hosts_wildcard() -> None:
    """Test that '*' trusts all hosts."""
    hosts = TrustedHosts("*")
    assert "192.168.1.1" in hosts
    assert "10.0.0.1" in hosts
    assert "::1" in hosts
    assert "any.host.example.com" in hosts
    assert None not in hosts  # None should never be trusted


def test_trusted_hosts_wildcard_list() -> None:
    """Test that ['*'] trusts all hosts."""
    hosts = TrustedHosts(["*"])
    assert "192.168.1.1" in hosts
    assert "10.0.0.1" in hosts


def test_trusted_hosts_specific_ip() -> None:
    """Test trusting specific IP addresses."""
    hosts = TrustedHosts(["127.0.0.1", "192.168.1.1"])
    assert "127.0.0.1" in hosts
    assert "192.168.1.1" in hosts
    assert "10.0.0.1" not in hosts
    assert "192.168.1.2" not in hosts


def test_trusted_hosts_string_single() -> None:
    """Test trusting a single IP address as string."""
    hosts = TrustedHosts("127.0.0.1")
    assert "127.0.0.1" in hosts
    assert "192.168.1.1" not in hosts


def test_trusted_hosts_string_comma_separated() -> None:
    """Test trusting comma-separated IP addresses."""
    hosts = TrustedHosts("127.0.0.1, 10.0.0.1, 192.168.1.1")
    assert "127.0.0.1" in hosts
    assert "10.0.0.1" in hosts
    assert "192.168.1.1" in hosts
    assert "172.16.0.1" not in hosts


def test_trusted_hosts_cidr_network_ipv4() -> None:
    """Test trusting CIDR networks for IPv4."""
    hosts = TrustedHosts("10.0.0.0/8")
    assert "10.0.0.1" in hosts
    assert "10.255.255.255" in hosts
    assert "10.1.2.3" in hosts
    assert "192.168.1.1" not in hosts
    assert "11.0.0.1" not in hosts


def test_trusted_hosts_cidr_network_class_b() -> None:
    """Test trusting Class B CIDR network."""
    hosts = TrustedHosts("172.16.0.0/12")
    assert "172.16.0.1" in hosts
    assert "172.31.255.255" in hosts
    assert "172.32.0.1" not in hosts


def test_trusted_hosts_cidr_network_class_c() -> None:
    """Test trusting Class C CIDR network."""
    hosts = TrustedHosts("192.168.1.0/24")
    assert "192.168.1.1" in hosts
    assert "192.168.1.254" in hosts
    assert "192.168.2.1" not in hosts


def test_trusted_hosts_ipv6() -> None:
    """Test IPv6 address support."""
    hosts = TrustedHosts(["::1"])
    assert "::1" in hosts
    assert "::2" not in hosts


def test_trusted_hosts_ipv6_network() -> None:
    """Test IPv6 CIDR network support."""
    hosts = TrustedHosts("fd00::/8")
    assert "fd00::1" in hosts
    assert "fd12:3456::1" in hosts
    assert "fe80::1" not in hosts


def test_trusted_hosts_mixed_ipv4_ipv6() -> None:
    """Test mixed IPv4 and IPv6 addresses."""
    hosts = TrustedHosts(["127.0.0.1", "::1", "10.0.0.0/8"])
    assert "127.0.0.1" in hosts
    assert "::1" in hosts
    assert "10.1.2.3" in hosts
    assert "192.168.1.1" not in hosts


def test_trusted_hosts_literal() -> None:
    """Test literal host names (non-IP)."""
    hosts = TrustedHosts(["unix:/var/run/proxy.sock"])
    assert "unix:/var/run/proxy.sock" in hosts
    assert "127.0.0.1" not in hosts


def test_trusted_hosts_empty_string() -> None:
    """Test empty string input."""
    hosts = TrustedHosts("")
    assert "127.0.0.1" not in hosts
    assert "" not in hosts


def test_trusted_hosts_none_input() -> None:
    """Test that None is never in trusted hosts."""
    hosts = TrustedHosts("127.0.0.1")
    assert None not in hosts


def test_trusted_hosts_empty_host() -> None:
    """Test that empty string is never trusted."""
    hosts = TrustedHosts("*")
    assert "" not in hosts


def test_get_trusted_client_host_single() -> None:
    """Test extracting client from single-hop X-Forwarded-For."""
    hosts = TrustedHosts("*")
    assert hosts.get_trusted_client_host("1.2.3.4") == "1.2.3.4"


def test_get_trusted_client_host_chain_trust_all() -> None:
    """Test extracting client from multi-hop X-Forwarded-For when trusting all."""
    hosts = TrustedHosts("*")
    # When trusting all, return the leftmost (original client)
    result = hosts.get_trusted_client_host("1.2.3.4, 5.6.7.8, 10.0.0.1")
    assert result == "1.2.3.4"


def test_get_trusted_client_host_chain_partial_trust() -> None:
    """Test extracting client from multi-hop X-Forwarded-For with partial trust."""
    hosts = TrustedHosts("10.0.0.1")
    # Client -> Untrusted Proxy (5.6.7.8) -> Trusted Proxy (10.0.0.1)
    # Should return first untrusted from right
    result = hosts.get_trusted_client_host("1.2.3.4, 5.6.7.8, 10.0.0.1")
    assert result == "5.6.7.8"


def test_get_trusted_client_host_all_trusted() -> None:
    """Test when all proxies in chain are trusted."""
    hosts = TrustedHosts(["10.0.0.1", "10.0.0.2", "10.0.0.3"])
    result = hosts.get_trusted_client_host("10.0.0.1, 10.0.0.2, 10.0.0.3")
    # All trusted - return original client (leftmost)
    assert result == "10.0.0.1"


def test_get_trusted_client_host_empty() -> None:
    """Test with empty X-Forwarded-For."""
    hosts = TrustedHosts("*")
    assert hosts.get_trusted_client_host("") == ""


def test_get_trusted_client_host_whitespace() -> None:
    """Test with whitespace in X-Forwarded-For."""
    hosts = TrustedHosts("*")
    result = hosts.get_trusted_client_host("  1.2.3.4  ,  5.6.7.8  ")
    assert result == "1.2.3.4"


# =============================================================================
# ProxyHeadersMiddleware Tests
# =============================================================================


class _ScopeRecorder:
    """Records scope passed to downstream app."""

    def __init__(self) -> None:
        self.scopes: list[dict[str, Any]] = []

    async def __call__(self, scope: "Scope", receive: "Receive", send: "Send") -> None:
        self.scopes.append(dict(scope))


@pytest.mark.anyio
async def test_middleware_ignores_untrusted_client() -> None:
    """Test that middleware ignores headers from untrusted clients."""
    recorder = _ScopeRecorder()

    middleware = ProxyHeadersMiddleware(recorder, trusted_hosts="10.0.0.1")

    scope = {
        "type": "http",
        "scheme": "http",
        "client": ("1.2.3.4", 12345),  # Untrusted client
        "headers": [(b"x-forwarded-proto", b"https")],
    }

    await middleware(scope, lambda: ..., lambda x: ...)  # type: ignore

    assert len(recorder.scopes) == 1
    assert recorder.scopes[0]["scheme"] == "http"  # NOT changed


@pytest.mark.anyio
async def test_middleware_applies_forwarded_proto() -> None:
    """Test that middleware applies X-Forwarded-Proto from trusted client."""
    recorder = _ScopeRecorder()

    middleware = ProxyHeadersMiddleware(recorder, trusted_hosts="127.0.0.1")

    scope = {
        "type": "http",
        "scheme": "http",
        "client": ("127.0.0.1", 12345),
        "headers": [(b"x-forwarded-proto", b"https")],
    }

    await middleware(scope, lambda: ..., lambda x: ...)  # type: ignore

    assert len(recorder.scopes) == 1
    assert recorder.scopes[0]["scheme"] == "https"


@pytest.mark.anyio
async def test_middleware_applies_http_scheme() -> None:
    """Test that middleware can set http scheme."""
    recorder = _ScopeRecorder()

    middleware = ProxyHeadersMiddleware(recorder, trusted_hosts="*")

    scope = {
        "type": "http",
        "scheme": "https",
        "client": ("127.0.0.1", 12345),
        "headers": [(b"x-forwarded-proto", b"http")],
    }

    await middleware(scope, lambda: ..., lambda x: ...)  # type: ignore

    assert recorder.scopes[0]["scheme"] == "http"


@pytest.mark.anyio
async def test_middleware_rejects_invalid_scheme() -> None:
    """Test that middleware rejects invalid X-Forwarded-Proto values."""
    recorder = _ScopeRecorder()

    middleware = ProxyHeadersMiddleware(recorder, trusted_hosts="*")

    scope = {
        "type": "http",
        "scheme": "http",
        "client": ("127.0.0.1", 12345),
        "headers": [(b"x-forwarded-proto", b"javascript")],  # Invalid!
    }

    await middleware(scope, lambda: ..., lambda x: ...)  # type: ignore

    assert recorder.scopes[0]["scheme"] == "http"  # NOT changed


@pytest.mark.anyio
async def test_middleware_rejects_empty_scheme() -> None:
    """Test that middleware ignores empty X-Forwarded-Proto."""
    recorder = _ScopeRecorder()

    middleware = ProxyHeadersMiddleware(recorder, trusted_hosts="*")

    scope = {"type": "http", "scheme": "http", "client": ("127.0.0.1", 12345), "headers": [(b"x-forwarded-proto", b"")]}

    await middleware(scope, lambda: ..., lambda x: ...)  # type: ignore

    assert recorder.scopes[0]["scheme"] == "http"


@pytest.mark.anyio
async def test_middleware_applies_forwarded_for() -> None:
    """Test that middleware applies X-Forwarded-For from trusted client."""
    recorder = _ScopeRecorder()

    middleware = ProxyHeadersMiddleware(recorder, trusted_hosts="*")

    scope = {
        "type": "http",
        "scheme": "http",
        "client": ("127.0.0.1", 12345),
        "headers": [(b"x-forwarded-for", b"1.2.3.4")],
    }

    await middleware(scope, lambda: ..., lambda x: ...)  # type: ignore

    assert recorder.scopes[0]["client"] == ("1.2.3.4", 0)


@pytest.mark.anyio
async def test_middleware_applies_forwarded_for_chain() -> None:
    """Test that middleware extracts correct client from X-Forwarded-For chain."""
    recorder = _ScopeRecorder()

    # Trust only the direct proxy
    middleware = ProxyHeadersMiddleware(recorder, trusted_hosts="127.0.0.1")

    scope = {
        "type": "http",
        "scheme": "http",
        "client": ("127.0.0.1", 12345),
        "headers": [(b"x-forwarded-for", b"1.2.3.4, 5.6.7.8")],
    }

    await middleware(scope, lambda: ..., lambda x: ...)  # type: ignore

    # Neither 1.2.3.4 nor 5.6.7.8 are trusted, so return rightmost untrusted
    assert recorder.scopes[0]["client"] == ("5.6.7.8", 0)


@pytest.mark.anyio
async def test_middleware_applies_forwarded_host() -> None:
    """Test that middleware applies X-Forwarded-Host."""
    recorder = _ScopeRecorder()

    middleware = ProxyHeadersMiddleware(recorder, trusted_hosts="*", handle_forwarded_host=True)

    scope = {
        "type": "http",
        "scheme": "http",
        "client": ("127.0.0.1", 12345),
        "headers": [(b"host", b"internal.local"), (b"x-forwarded-host", b"example.com")],
    }

    await middleware(scope, lambda: ..., lambda x: ...)  # type: ignore

    # Host should be replaced
    headers = dict(recorder.scopes[0]["headers"])
    assert headers[b"host"] == b"example.com"


@pytest.mark.anyio
async def test_middleware_skips_forwarded_host_when_disabled() -> None:
    """Test that X-Forwarded-Host is skipped when handle_forwarded_host=False."""
    recorder = _ScopeRecorder()

    middleware = ProxyHeadersMiddleware(recorder, trusted_hosts="*", handle_forwarded_host=False)

    scope = {
        "type": "http",
        "scheme": "http",
        "client": ("127.0.0.1", 12345),
        "headers": [(b"host", b"internal.local"), (b"x-forwarded-host", b"example.com")],
    }

    await middleware(scope, lambda: ..., lambda x: ...)  # type: ignore

    # Host should NOT be replaced
    headers = dict(recorder.scopes[0]["headers"])
    assert headers[b"host"] == b"internal.local"


@pytest.mark.anyio
async def test_middleware_adds_host_if_missing() -> None:
    """Test that X-Forwarded-Host adds Host header if not present."""
    recorder = _ScopeRecorder()

    middleware = ProxyHeadersMiddleware(recorder, trusted_hosts="*")

    scope = {
        "type": "http",
        "scheme": "http",
        "client": ("127.0.0.1", 12345),
        "headers": [(b"x-forwarded-host", b"example.com")],
    }

    await middleware(scope, lambda: ..., lambda x: ...)  # type: ignore

    headers = dict(recorder.scopes[0]["headers"])
    assert headers[b"host"] == b"example.com"


@pytest.mark.anyio
async def test_middleware_websocket_https_to_wss() -> None:
    """Test that middleware converts https to wss for WebSocket scope."""
    recorder = _ScopeRecorder()

    middleware = ProxyHeadersMiddleware(recorder, trusted_hosts="*")

    scope = {
        "type": "websocket",
        "scheme": "ws",
        "client": ("127.0.0.1", 12345),
        "headers": [(b"x-forwarded-proto", b"https")],
    }

    await middleware(scope, lambda: ..., lambda x: ...)  # type: ignore

    assert recorder.scopes[0]["scheme"] == "wss"


@pytest.mark.anyio
async def test_middleware_websocket_http_to_ws() -> None:
    """Test that middleware converts http to ws for WebSocket scope."""
    recorder = _ScopeRecorder()

    middleware = ProxyHeadersMiddleware(recorder, trusted_hosts="*")

    scope = {
        "type": "websocket",
        "scheme": "wss",
        "client": ("127.0.0.1", 12345),
        "headers": [(b"x-forwarded-proto", b"http")],
    }

    await middleware(scope, lambda: ..., lambda x: ...)  # type: ignore

    assert recorder.scopes[0]["scheme"] == "ws"


@pytest.mark.anyio
async def test_middleware_websocket_ws_unchanged() -> None:
    """Test that ws scheme is preserved for WebSocket."""
    recorder = _ScopeRecorder()

    middleware = ProxyHeadersMiddleware(recorder, trusted_hosts="*")

    scope = {
        "type": "websocket",
        "scheme": "wss",
        "client": ("127.0.0.1", 12345),
        "headers": [(b"x-forwarded-proto", b"ws")],
    }

    await middleware(scope, lambda: ..., lambda x: ...)  # type: ignore

    assert recorder.scopes[0]["scheme"] == "ws"


@pytest.mark.anyio
async def test_middleware_websocket_wss_unchanged() -> None:
    """Test that wss scheme is preserved for WebSocket."""
    recorder = _ScopeRecorder()

    middleware = ProxyHeadersMiddleware(recorder, trusted_hosts="*")

    scope = {
        "type": "websocket",
        "scheme": "ws",
        "client": ("127.0.0.1", 12345),
        "headers": [(b"x-forwarded-proto", b"wss")],
    }

    await middleware(scope, lambda: ..., lambda x: ...)  # type: ignore

    assert recorder.scopes[0]["scheme"] == "wss"


@pytest.mark.anyio
async def test_middleware_no_client() -> None:
    """Test that middleware handles missing client gracefully."""
    recorder = _ScopeRecorder()

    middleware = ProxyHeadersMiddleware(recorder, trusted_hosts="*")

    scope = {
        "type": "http",
        "scheme": "http",
        "client": None,  # No client info
        "headers": [(b"x-forwarded-proto", b"https")],
    }

    await middleware(scope, lambda: ..., lambda x: ...)  # type: ignore

    # Should not apply because client is None (not in trusted hosts)
    assert recorder.scopes[0]["scheme"] == "http"


@pytest.mark.anyio
async def test_middleware_cidr_trust() -> None:
    """Test middleware with CIDR network trust."""
    recorder = _ScopeRecorder()

    middleware = ProxyHeadersMiddleware(recorder, trusted_hosts="10.0.0.0/8")

    scope = {
        "type": "http",
        "scheme": "http",
        "client": ("10.123.45.67", 12345),  # In 10.0.0.0/8
        "headers": [(b"x-forwarded-proto", b"https")],
    }

    await middleware(scope, lambda: ..., lambda x: ...)  # type: ignore

    assert recorder.scopes[0]["scheme"] == "https"


@pytest.mark.anyio
async def test_middleware_multiple_headers_first_wins() -> None:
    """Test that first occurrence of header is used."""
    recorder = _ScopeRecorder()

    middleware = ProxyHeadersMiddleware(recorder, trusted_hosts="*")

    scope = {
        "type": "http",
        "scheme": "http",
        "client": ("127.0.0.1", 12345),
        "headers": [
            (b"x-forwarded-proto", b"https"),
            (b"x-forwarded-proto", b"http"),  # Second occurrence should be ignored
        ],
    }

    await middleware(scope, lambda: ..., lambda x: ...)  # type: ignore

    assert recorder.scopes[0]["scheme"] == "https"


@pytest.mark.anyio
async def test_middleware_case_insensitive_scheme() -> None:
    """Test that scheme comparison is case-insensitive."""
    recorder = _ScopeRecorder()

    middleware = ProxyHeadersMiddleware(recorder, trusted_hosts="*")

    scope = {
        "type": "http",
        "scheme": "http",
        "client": ("127.0.0.1", 12345),
        "headers": [(b"x-forwarded-proto", b"HTTPS")],
    }

    await middleware(scope, lambda: ..., lambda x: ...)  # type: ignore

    assert recorder.scopes[0]["scheme"] == "https"


@pytest.mark.anyio
async def test_middleware_all_headers_combined() -> None:
    """Test that all X-Forwarded-* headers are applied together."""
    recorder = _ScopeRecorder()

    middleware = ProxyHeadersMiddleware(recorder, trusted_hosts="*")

    scope = {
        "type": "http",
        "scheme": "http",
        "client": ("127.0.0.1", 12345),
        "headers": [
            (b"host", b"internal.local"),
            (b"x-forwarded-proto", b"https"),
            (b"x-forwarded-for", b"1.2.3.4"),
            (b"x-forwarded-host", b"example.com"),
        ],
    }

    await middleware(scope, lambda: ..., lambda x: ...)  # type: ignore

    assert recorder.scopes[0]["scheme"] == "https"
    assert recorder.scopes[0]["client"] == ("1.2.3.4", 0)
    headers = dict(recorder.scopes[0]["headers"])
    assert headers[b"host"] == b"example.com"
