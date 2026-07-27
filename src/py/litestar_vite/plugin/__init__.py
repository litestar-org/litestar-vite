"""Vite Plugin for Litestar.

This module provides the VitePlugin class for integrating Vite with Litestar.
The plugin handles:

- Static file serving configuration
- Jinja2 template callable registration
- Vite dev server process management
- Async asset loader initialization
- Development proxies for Vite HTTP and HMR WebSockets (with hop-by-hop header filtering)

Example::

    from litestar import Litestar
    from litestar_vite import VitePlugin, ViteConfig

    app = Litestar(
        plugins=[VitePlugin(config=ViteConfig(dev_mode=True))],
    )
"""

from litestar_vite.plugin._core import VitePlugin
from litestar_vite.plugin._process import ViteProcess
from litestar_vite.plugin._proxy import (
    SSRProxyMiddleware,
    ViteProxyMiddleware,
    create_disabled_vite_hmr_handlers,
    create_ssr_http_proxy_handler,
    create_ssr_ws_proxy_handler,
    create_vite_hmr_handler,
)
from litestar_vite.plugin._proxy_headers import ProxyHeadersMiddleware, TrustedHosts
from litestar_vite.plugin._static import StaticFilesConfig, StaticPlacement, StaticServerConfig, StaticServerMount
from litestar_vite.plugin._utils import (
    get_litestar_route_prefixes,
    is_litestar_route,
    resolve_litestar_version,
    set_app_environment,
    set_environment,
)

__all__ = (
    "ProxyHeadersMiddleware",
    "SSRProxyMiddleware",
    "StaticFilesConfig",
    "StaticPlacement",
    "StaticServerConfig",
    "StaticServerMount",
    "TrustedHosts",
    "VitePlugin",
    "ViteProcess",
    "ViteProxyMiddleware",
    "create_disabled_vite_hmr_handlers",
    "create_ssr_http_proxy_handler",
    "create_ssr_ws_proxy_handler",
    "create_vite_hmr_handler",
    "get_litestar_route_prefixes",
    "is_litestar_route",
    "resolve_litestar_version",
    "set_app_environment",
    "set_environment",
)
