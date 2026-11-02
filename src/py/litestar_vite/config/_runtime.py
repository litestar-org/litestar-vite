"""Runtime execution settings."""

import os
import warnings
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Literal

from litestar_vite.config._constants import TRUE_VALUES

__all__ = ("ExternalDevServer", "RuntimeConfig", "resolve_trusted_proxies")

_EXECUTOR_COMMANDS: dict[str, dict[str, tuple[str, ...]]] = {
    "node": {
        "run": ("npm", "run", "dev"),
        "build": ("npm", "run", "build"),
        "build_watch": ("npm", "run", "watch"),
        "serve": ("npm", "run", "serve"),
        "install": ("npm", "install"),
    },
    "bun": {
        "run": ("bun", "run", "dev"),
        "build": ("bun", "run", "build"),
        "build_watch": ("bun", "run", "watch"),
        "serve": ("bun", "run", "serve"),
        "install": ("bun", "install"),
        "serve_ssr": ("bun", "run", "resources/ssr.tsx"),
    },
    "deno": {
        "run": ("deno", "task", "dev"),
        "build": ("deno", "task", "build"),
        "build_watch": ("deno", "task", "watch"),
        "serve": ("deno", "task", "serve"),
        "install": ("deno", "install"),
    },
    "yarn": {
        "run": ("yarn", "dev"),
        "build": ("yarn", "build"),
        "build_watch": ("yarn", "watch"),
        "serve": ("yarn", "serve"),
        "install": ("yarn", "install"),
    },
    "pnpm": {
        "run": ("pnpm", "dev"),
        "build": ("pnpm", "build"),
        "build_watch": ("pnpm", "watch"),
        "serve": ("pnpm", "serve"),
        "install": ("pnpm", "install"),
    },
}


@lru_cache(maxsize=32)
def _cached_resolve_trusted_proxies(env_value: str | None) -> "tuple[str, ...] | Literal['*'] | None":
    """Resolve trusted proxies from env input with caching.

    Returns a tuple for cached list values to preserve immutability across cache entries.
    """
    if env_value is None:
        return None

    env_value = env_value.strip()
    if env_value == "*":
        return ("*",)
    if not env_value:
        return None

    return tuple(h.strip() for h in env_value.split(",") if h.strip())


@lru_cache(maxsize=16)
def _cached_resolve_proxy_mode(env_value: str | None) -> "Literal['vite', 'proxy', '__none__'] | None":
    """Resolve proxy mode from env input with caching.

    "__none__" preserves an explicit "none" value while still allowing ``None``
    for missing values. ``None`` (unset) defers to ``ViteConfig._apply_proxy_mode_defaults``
    which auto-derives from ``mode``.
    """
    match env_value.strip().lower() if env_value is not None else None:
        case None:
            return None
        case "none":
            return "__none__"
        case "direct":
            warnings.warn(
                "VITE_PROXY_MODE='direct' is deprecated and now coerced to 'vite'. "
                "Two-port dev mode (browser hits Vite directly) violates the single-port-via-ASGI "
                "contract and is no longer supported.",
                DeprecationWarning,
                stacklevel=4,
            )
            return "vite"
        case "proxy":
            return "proxy"
        case "vite":
            return "vite"
        case _:
            msg = f"Invalid VITE_PROXY_MODE: {env_value!r}. Expected one of: vite, proxy, none"
            raise ValueError(msg)


def resolve_trusted_proxies() -> "list[str] | str | None":
    """Resolve trusted_proxies from environment variable.

    Reads LITESTAR_TRUSTED_PROXIES env var. Examples:
        - "*" -> Trust all proxies (for container environments)
        - "127.0.0.1" -> Trust localhost only
        - "10.0.0.0/8,172.16.0.0/12" -> Trust private networks

    Returns:
        The trusted proxies configuration, or None if not set.
    """
    cached_value = _cached_resolve_trusted_proxies(os.getenv("LITESTAR_TRUSTED_PROXIES"))

    if cached_value is None:
        return None
    if cached_value == ("*",):
        return "*"
    return list(cached_value)


def resolve_proxy_mode() -> "Literal['vite', 'proxy'] | None":
    """Resolve proxy_mode from environment variable.

    Reads ``VITE_PROXY_MODE`` env var. Valid values:

    - unset (default): auto-derive from ``ViteConfig.mode``
    - ``"vite"``: Proxy to internal Vite server (allow list - assets only)
    - ``"proxy"``: Proxy everything except Litestar routes (deny list); requires ``mode='framework'``
    - ``"none"``: Disable proxy (for production)
    - ``"direct"``: DEPRECATED. Auto-coerced to ``"vite"`` with ``DeprecationWarning``.

    Raises:
        ValueError: If an invalid value is provided.

    Returns:
        The resolved proxy mode, or None if disabled or unset (let ViteConfig auto-derive).
    """
    cached_mode = _cached_resolve_proxy_mode(os.getenv("VITE_PROXY_MODE"))
    if cached_mode == "__none__":
        return None
    return cached_mode


@dataclass
class ExternalDevServer:
    """Configuration for proxying to an external (non-Vite) development server."""

    target: "str | None" = None
    """Target URL of the external dev server (for example, `'http://localhost:4200'`), or `None` to read the Vite hotfile."""
    command: "list[str] | None" = None
    """Custom command argv used to start the external dev server."""
    build_command: "list[str] | None" = None
    """Custom command argv used to build production assets for the external framework."""
    http2: bool = False
    """Enable HTTP/2 for proxy connections to the external dev server."""
    enabled: bool = True
    """Whether the external dev server proxy is enabled."""


@dataclass
class RuntimeConfig:
    """Runtime process management, dev proxy, and JavaScript executor settings."""

    dev_mode: bool = field(default_factory=lambda: os.getenv("VITE_DEV_MODE", "False") in TRUE_VALUES)
    """Enable development mode with Vite HMR and watch processes."""
    proxy_mode: "Literal['vite', 'proxy'] | None" = field(default_factory=resolve_proxy_mode)
    """Dev proxy routing mode (`'vite'` allowlist, `'proxy'` denylist for framework mode, or `None` in production)."""
    external_dev_server: "ExternalDevServer | str | None" = None
    """External dev server configuration or target URL string used when `proxy_mode='proxy'`."""
    host: str = field(default_factory=lambda: os.getenv("VITE_HOST", "127.0.0.1"))
    """Hostname or IP address where the Vite dev server binds."""
    port: int = field(default_factory=lambda: int(os.getenv("VITE_PORT", "5173")))
    """TCP port where the Vite dev server listens."""
    protocol: Literal["http", "https"] = "http"
    """Protocol (`'http'` or `'https'`) used by the Vite dev server."""
    executor: "Literal['node', 'bun', 'deno', 'yarn', 'pnpm'] | None" = None
    """JavaScript runtime/package manager used to execute Vite commands (`'node'` when `None`)."""
    run_command: "list[str] | None" = None
    """Custom command argv to start the Vite dev server (auto-derived from `executor` when `None`)."""
    build_command: "list[str] | None" = None
    """Custom command argv to run a production Vite build (auto-derived from `executor` when `None`)."""
    build_watch_command: "list[str] | None" = None
    """Custom command argv to run Vite in watch-build mode (auto-derived from `executor` when `None`)."""
    serve_command: "list[str] | None" = None
    """Custom command argv to run the production SSR server (auto-derived from `executor` when `None`)."""
    install_command: "list[str] | None" = None
    """Custom command argv to install frontend dependencies (auto-derived from `executor` when `None`)."""
    is_react: bool = False
    """Inject the `@vitejs/plugin-react` Fast Refresh preamble in development HTML."""
    health_check: bool = field(default_factory=lambda: os.getenv("VITE_HEALTH_CHECK", "False") in TRUE_VALUES)
    """Poll the Vite dev server for readiness before completing startup."""
    detect_nodeenv: bool = False
    """Detect and run `nodeenv` inside the active Python virtual environment."""
    set_environment: bool = True
    """Export resolved Vite settings (`VITE_PORT`, `VITE_HOST`, `ASSET_URL`) into process environment variables."""
    set_static_folders: bool = True
    """Automatically mount static asset directories on the Litestar router."""
    csp_nonce: "str | None" = None
    """Content Security Policy nonce applied to injected inline `<script>` and `<style>` tags."""
    spa_handler: bool = True
    """Automatically register the `AppHandler` catch-all SPA route when `mode='spa'`."""
    http2: bool = True
    """Enable HTTP/2 multiplexing for proxy HTTP requests."""
    start_dev_server: bool = True
    """Automatically spawn and manage the Vite dev server subprocess during Litestar lifespan."""
    trusted_proxies: "list[str] | str | None" = field(default_factory=resolve_trusted_proxies)
    """Trusted proxy hosts/CIDRs (`'*'` or IP list) for `X-Forwarded-*` header processing (`LITESTAR_TRUSTED_PROXIES`)."""
    extra_route_prefixes: tuple[str, ...] = ()
    """Additional backend route prefixes excluded from dev proxy forwarding and SPA catch-all routing."""

    def __post_init__(self) -> None:
        """Normalize runtime settings and apply derived defaults."""
        if isinstance(self.extra_route_prefixes, str):
            self.extra_route_prefixes = (self.extra_route_prefixes,)
        else:
            self.extra_route_prefixes = tuple(self.extra_route_prefixes)

        if isinstance(self.external_dev_server, str):
            self.external_dev_server = ExternalDevServer(target=self.external_dev_server)

        if self.external_dev_server is not None and self.proxy_mode in {None, "vite"}:
            self.proxy_mode = "proxy"

        if self.executor is None:
            self.executor = "node"

        if self.executor in _EXECUTOR_COMMANDS:
            cmds = _EXECUTOR_COMMANDS[self.executor]
            if self.run_command is None:
                self.run_command = list(cmds["run"])
            if self.build_command is None:
                self.build_command = list(cmds["build"])
            if self.build_watch_command is None:
                self.build_watch_command = list(cmds["build_watch"])
            if self.serve_command is None:
                self.serve_command = list(cmds["serve"])
            if self.install_command is None:
                self.install_command = list(cmds["install"])
