"""Runtime execution settings."""

import os
from dataclasses import dataclass, field
from typing import Literal

from litestar_vite.config._constants import TRUE_VALUES

__all__ = ("ExternalDevServer", "RuntimeConfig", "resolve_trusted_proxies")


def resolve_trusted_proxies() -> "list[str] | str | None":
    """Resolve trusted_proxies from environment variable.

    Reads LITESTAR_TRUSTED_PROXIES env var. Examples:
        - "*" -> Trust all proxies (for container environments)
        - "127.0.0.1" -> Trust localhost only
        - "10.0.0.0/8,172.16.0.0/12" -> Trust private networks

    Returns:
        The trusted proxies configuration, or None if not set.
    """
    env_value = os.getenv("LITESTAR_TRUSTED_PROXIES")
    if env_value is None:
        return None
    env_value = env_value.strip()
    if env_value == "*":
        return "*"
    if not env_value:
        return None
    return [h.strip() for h in env_value.split(",") if h.strip()]


def resolve_proxy_mode() -> "Literal['vite', 'direct', 'proxy'] | None":
    """Resolve proxy_mode from environment variable.

    Reads VITE_PROXY_MODE env var. Valid values:
    - "vite" (default): Proxy to internal Vite server (allow list - assets only)
    - "direct": Expose Vite port directly (no proxy)
    - "proxy": Proxy everything except Litestar routes (deny list)
    - "none": Disable proxy (for production)

    Raises:
        ValueError: If an invalid value is provided.

    Returns:
        The resolved proxy mode, or None if disabled.
    """
    env_value = os.getenv("VITE_PROXY_MODE")
    match env_value.strip().lower() if env_value is not None else None:
        case None:
            return "vite"
        case "none":
            return None
        case "direct":
            return "direct"
        case "proxy":
            return "proxy"
        case "vite":
            return "vite"
        case _:
            msg = f"Invalid VITE_PROXY_MODE: {env_value!r}. Expected one of: vite, direct, proxy, none"
            raise ValueError(msg)


@dataclass
class ExternalDevServer:
    """Configuration for external (non-Vite) dev servers.

    Use this when your frontend uses a framework with its own dev server
    (Angular CLI, Next.js, Create React App, etc.) instead of Vite.

    For SSR frameworks (Astro, Nuxt, SvelteKit) using Vite internally, leave
    target as None - the proxy will read the dynamic port from the hotfile.

    Attributes:
        target: The URL of the external dev server (e.g., "http://localhost:4200").
            If None, the proxy reads the target URL from the Vite hotfile.
        command: Custom command to start the dev server (e.g., ["ng", "serve"]).
            If None and start_dev_server=True, uses executor's default start command.
        build_command: Custom command to build for production (e.g., ["ng", "build"]).
            If None, uses executor's default build command (e.g., "npm run build").
        http2: Enable HTTP/2 for proxy connections.
        enabled: Whether the external proxy is enabled.
    """

    target: "str | None" = None
    command: "list[str] | None" = None
    build_command: "list[str] | None" = None
    http2: bool = False
    enabled: bool = True


@dataclass
class RuntimeConfig:
    """Runtime execution settings.

    Attributes:
        dev_mode: Enable development mode with HMR/watch.
        proxy_mode: Proxy handling mode:
            - "vite" (default): Proxy Vite assets only (allow list - SPA mode)
            - "direct": Expose Vite port directly (no proxy)
            - "proxy": Proxy everything except Litestar routes (deny list - framework mode)
            - None: No proxy (production mode)
        external_dev_server: Configuration for external dev server (used with proxy_mode="proxy").
        host: Vite dev server host.
        port: Vite dev server port.
        protocol: Protocol for dev server (http/https).
        executor: JavaScript runtime executor (node, bun, deno).
        run_command: Custom command to run Vite dev server (auto-detect if None).
        build_command: Custom command to build with Vite (auto-detect if None).
        build_watch_command: Custom command for watch mode build.
        serve_command: Custom command to run production server (for SSR frameworks).
        install_command: Custom command to install dependencies.
        is_react: Enable React Fast Refresh support.
        health_check: Enable health check for dev server startup.
        detect_nodeenv: Detect and use nodeenv in virtualenv (opt-in).
        set_environment: Set Vite environment variables from config.
        set_static_folders: Automatically configure static file serving.
        csp_nonce: Content Security Policy nonce for inline scripts.
        spa_handler: Auto-register catch-all SPA route when mode="spa".
        http2: Enable HTTP/2 for proxy HTTP requests (better multiplexing).
            WebSocket traffic (HMR) uses a separate connection and is unaffected.
    """

    dev_mode: bool = field(default_factory=lambda: os.getenv("VITE_DEV_MODE", "False") in TRUE_VALUES)
    proxy_mode: "Literal['vite', 'direct', 'proxy'] | None" = field(default_factory=resolve_proxy_mode)
    external_dev_server: "ExternalDevServer | str | None" = None
    host: str = field(default_factory=lambda: os.getenv("VITE_HOST", "127.0.0.1"))
    port: int = field(default_factory=lambda: int(os.getenv("VITE_PORT", "5173")))
    protocol: Literal["http", "https"] = "http"
    executor: "Literal['node', 'bun', 'deno', 'yarn', 'pnpm'] | None" = None
    run_command: "list[str] | None" = None
    build_command: "list[str] | None" = None
    build_watch_command: "list[str] | None" = None
    serve_command: "list[str] | None" = None
    install_command: "list[str] | None" = None
    is_react: bool = False
    health_check: bool = field(default_factory=lambda: os.getenv("VITE_HEALTH_CHECK", "False") in TRUE_VALUES)
    detect_nodeenv: bool = False
    set_environment: bool = True
    set_static_folders: bool = True
    csp_nonce: "str | None" = None
    spa_handler: bool = True
    http2: bool = True
    start_dev_server: bool = True
    trusted_proxies: "list[str] | str | None" = field(default_factory=resolve_trusted_proxies)
    """Trusted proxy hosts for X-Forwarded-* header processing.

    When set, the ProxyHeadersMiddleware will read and apply X-Forwarded-Proto,
    X-Forwarded-For, and X-Forwarded-Host headers only from requests originating
    from these hosts.

    Accepted values:
        - None (default): Disabled - do not trust any proxy headers
        - "*": Trust all proxies (use in controlled environments like Docker/Railway)
        - List of IP addresses: ["127.0.0.1", "10.0.0.0/8"]
        - Comma-separated string: "127.0.0.1, 10.0.0.0/8"

    Supports:
        - IPv4 addresses: "192.168.1.1"
        - IPv6 addresses: "::1"
        - CIDR notation: "10.0.0.0/8", "fd00::/8"
        - Unix socket literals (for advanced setups)

    Security Note:
        Only enable this when your application is behind a trusted reverse proxy.
        Never enable in environments where clients can directly connect to the app.
        Using "*" should only be done in controlled environments where direct client
        connections are blocked by network configuration.

    Environment Variable: LITESTAR_TRUSTED_PROXIES
    """

    def __post_init__(self) -> None:
        """Normalize runtime settings and apply derived defaults."""
        if isinstance(self.external_dev_server, str):
            self.external_dev_server = ExternalDevServer(target=self.external_dev_server)

        if self.external_dev_server is not None and self.proxy_mode in {None, "vite"}:
            self.proxy_mode = "proxy"

        if self.executor is None:
            self.executor = "node"

        executor_commands = {
            "node": {
                "run": ["npm", "run", "dev"],
                "build": ["npm", "run", "build"],
                "build_watch": ["npm", "run", "watch"],
                "serve": ["npm", "run", "serve"],
                "install": ["npm", "install"],
            },
            "bun": {
                "run": ["bun", "run", "dev"],
                "build": ["bun", "run", "build"],
                "build_watch": ["bun", "run", "watch"],
                "serve": ["bun", "run", "serve"],
                "install": ["bun", "install"],
            },
            "deno": {
                "run": ["deno", "task", "dev"],
                "build": ["deno", "task", "build"],
                "build_watch": ["deno", "task", "watch"],
                "serve": ["deno", "task", "serve"],
                "install": ["deno", "install"],
            },
            "yarn": {
                "run": ["yarn", "dev"],
                "build": ["yarn", "build"],
                "build_watch": ["yarn", "watch"],
                "serve": ["yarn", "serve"],
                "install": ["yarn", "install"],
            },
            "pnpm": {
                "run": ["pnpm", "dev"],
                "build": ["pnpm", "build"],
                "build_watch": ["pnpm", "watch"],
                "serve": ["pnpm", "serve"],
                "install": ["pnpm", "install"],
            },
        }

        if self.executor in executor_commands:
            cmds = executor_commands[self.executor]
            if self.run_command is None:
                self.run_command = cmds["run"]
            if self.build_command is None:
                self.build_command = cmds["build"]
            if self.build_watch_command is None:
                self.build_watch_command = cmds["build_watch"]
            if self.serve_command is None:
                self.serve_command = cmds["serve"]
            if self.install_command is None:
                self.install_command = cmds["install"]
