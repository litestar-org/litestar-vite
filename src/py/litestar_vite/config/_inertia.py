"""Inertia.js configuration classes."""

import os
import warnings
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

from litestar_vite.config._constants import empty_dict_factory, empty_set_factory

__all__ = ("InertiaConfig", "InertiaSSRConfig", "InertiaTypeGenConfig")


@dataclass
class InertiaSSRConfig:
    """Server-side rendering settings for Inertia.js.

    Inertia SSR runs a separate Node or worker process that renders the initial HTML for an
    Inertia page object. Litestar sends the page payload to the SSR worker
    and injects the returned head tags and body markup into the HTML response.

    When ``command`` is set, the plugin spawns the Node /render server in the
    server lifespan (mirroring Vite process management) and tears it down on
    shutdown. This makes SSR examples self-contained — no second terminal needed.

    Notes:
        - This is *not* Litestar-Vite's framework proxy mode (``mode="framework"``; aliases: ``mode="ssr"`` / ``mode="ssg"``).
        - When enabled, failures to contact the SSR server can fall back to client hydration when fallback_to_client is True.
    """

    enabled: bool = True
    transport: Literal["stdio", "uds", "tcp"] = "stdio"
    socket_path: Path | str | None = None
    url: str | None = "http://127.0.0.1:13714/render"
    timeout: float = 2.0
    target_selector: str = "#app"
    """CSS selector for the element whose outer HTML is replaced by the SSR-rendered body.

    Used by ``_render_template`` (template mode) to locate the mount point in the
    rendered Jinja HTML. Defaults to ``#app`` to match Inertia's convention.

    For ``mode="hybrid"``, ``SPAConfig.app_selector`` is the source of truth and
    this field is ignored — SPA config already governs the SPA shell selector.
    """

    command: list[str] | None = None
    """Command to start the Node /render server, e.g. ``["npm", "run", "start:ssr"]``.

    When set, the plugin spawns the command as a subprocess in the server lifespan
    and stops it on shutdown. Set to ``None`` to disable auto-start (run the SSR
    server manually in a separate terminal).
    """

    cwd: Path | None = None
    """Working directory for the SSR command. Defaults to ``ViteConfig.root_dir`` when None."""

    auto_start: bool = True
    """When True and ``command`` is set, the plugin starts the Node SSR process in lifespan.

    Set to False to keep the command around for documentation but skip auto-start
    (useful when running under an external process manager).
    """

    health_check: bool = False
    """When True, poll the SSR ``url`` until it responds before completing app startup.

    Default is False so the SSR process starts in the background and Litestar can serve
    requests immediately. Set to True if you want startup to block until /render is ready
    (catches misconfigured commands early at the cost of slower boot).
    """

    health_check_timeout: float = 10.0
    """Seconds to wait for the SSR endpoint to become reachable during startup.

    Only consulted when ``health_check`` is True. On timeout the plugin logs a warning
    and continues — startup is not aborted.
    """

    fallback_to_client: bool = True
    """Whether to fall back gracefully to client-side hydration if SSR rendering fails."""

    circuit_breaker_enabled: bool = True
    """Whether to enable the in-memory circuit breaker protecting the SSR rendering pipeline."""

    circuit_breaker_failure_threshold: int = 3
    """Number of consecutive failures before the circuit breaker trips to OPEN state."""

    circuit_breaker_reset_timeout: float = 30.0
    """Cooldown seconds to wait before probing SSR worker health after tripping."""

    max_consecutive_failures: int | None = None
    """Alias for circuit_breaker_failure_threshold."""

    circuit_breaker_cooldown_seconds: float | None = None
    """Alias for circuit_breaker_reset_timeout."""

    def __post_init__(self) -> None:
        """Validate and normalize SSR configuration options.

        Ensures transport parameters and timeouts satisfy runtime invariants
        across POSIX and Windows platforms.
        """
        if self.max_consecutive_failures is not None:
            self.circuit_breaker_failure_threshold = self.max_consecutive_failures
        else:
            self.max_consecutive_failures = self.circuit_breaker_failure_threshold

        if self.circuit_breaker_cooldown_seconds is not None:
            self.circuit_breaker_reset_timeout = self.circuit_breaker_cooldown_seconds
        else:
            self.circuit_breaker_cooldown_seconds = self.circuit_breaker_reset_timeout

        if self.url is not None and self.url != "http://127.0.0.1:13714/render" and self.transport == "stdio":
            warnings.warn(
                "Configuring 'url' in InertiaSSRConfig is deprecated in favor of 'transport=\"stdio\"' "
                "or 'transport=\"uds\"'. Defaulting transport to 'tcp' for backward compatibility.",
                DeprecationWarning,
                stacklevel=2,
            )
            self.transport = "tcp"

        if self.transport == "tcp" and self.url is None:
            self.url = "http://127.0.0.1:13714/render"

        if self.transport == "uds":
            if os.name == "nt":
                msg = (
                    "Unix domain socket transport ('uds') is not supported on Windows. "
                    "Use 'stdio' (default) or 'tcp' transport instead."
                )
                raise ValueError(msg)
            if self.socket_path is None:
                msg = "InertiaSSRConfig with transport='uds' requires 'socket_path'."
                raise ValueError(msg)
            if isinstance(self.socket_path, str):
                self.socket_path = Path(self.socket_path)


@dataclass
class InertiaConfig:
    """Configuration for InertiaJS support.

    This is the canonical configuration class for Inertia.js integration.
    Presence of an InertiaConfig instance indicates Inertia is enabled.

    Note:
        SPA mode (HTML transformation vs Jinja2 templates) is controlled by
        ViteConfig.mode='hybrid'. The app_selector for data-page injection
        is configured via SPAConfig.app_selector.

    Attributes:
        root_template: Name of the root template to use.
        component_opt_keys: Identifiers for getting inertia component from route opts.
        redirect_unauthorized_to: Path for unauthorized request redirects.
        redirect_404: Path for 404 request redirects.
        extra_static_page_props: Static props added to every page response.
        extra_session_page_props: Session keys to include in page props.
        transport: Default IPC transport mode ("stdio", "uds", "tcp").
        socket_path: Unix domain socket path for "uds" transport.
        ssr_url: Deprecated URL for TCP-based SSR render endpoint.
    """

    root_template: str = "index.html"
    """Name of the root template to use.

    This must be a path that is found by the Vite Plugin template config
    """
    component_opt_keys: tuple[str, ...] = ("component", "page")
    """Identifiers to use on routes to get the inertia component to render.

    The first key found in the route handler opts will be used. This allows
    semantic flexibility - use "component" or "page" depending on preference.
    """
    redirect_unauthorized_to: str | None = None
    """Optionally supply a path where unauthorized requests should redirect."""
    redirect_404: str | None = None
    """Optionally supply a path where 404 requests should redirect."""
    extra_static_page_props: dict[str, Any] = field(default_factory=empty_dict_factory)
    """A dictionary of values to automatically add in to page props on every response."""
    extra_session_page_props: set[str] | dict[str, type] = field(default_factory=empty_set_factory)
    """Session props to include in page responses.

    Keys are copied when the current request exposes a Litestar session. They are
    omitted from sessionless responses. Use ``CookieBackendConfig`` for encrypted,
    server-store-free persistence, or ``ServerSideSessionConfig`` with a Litestar
    store.

    Can be either:
    - A set of session key names (types will be 'unknown')
    - A dict mapping session keys to Python types (auto-registered with OpenAPI)
    """
    shared_page_prop_types: dict[str, Any] | None = None
    """Python types for props pushed at request time with ``share()``.

    This declares *types only* and never carries values, unlike
    ``extra_static_page_props``. It exists because ``share()`` calls in guards and
    middleware have no naming site the type generator can read, so without a
    declaration those props fall back to a synthesized default type.

    Declared annotations are registered against the same OpenAPI schema registry
    used for route props, so nested models resolve to the identical generated
    TypeScript type rather than a duplicate.

    Values are annotations, so containers and unions are accepted alongside plain
    models. Anything the schema generator cannot resolve falls back to the
    configured fallback type.

    Leave as ``None`` to keep the generated defaults.
    """
    encrypt_history: bool = False
    """Enable browser history encryption globally (v2 feature).

    When True, all Inertia responses will include `encryptHistory: true`
    in the page object. The Inertia client will encrypt history state
    using browser's crypto API before pushing to history.

    This prevents sensitive data from being visible in browser history
    after a user logs out. Individual responses can override this setting.

    Note: Encryption happens client-side; requires HTTPS in production.
    See: https://inertiajs.com/history-encryption
    """
    type_gen: "InertiaTypeGenConfig | None" = None
    """Type generation options for Inertia page props.

    Controls default types in generated page-props.ts. Set to InertiaTypeGenConfig()
    or leave as None for defaults. Use InertiaTypeGenConfig(include_default_auth=False)
    to disable default User/AuthData interfaces for non-standard user models.
    """

    ssr: InertiaSSRConfig | bool | None = None
    """Enable server-side rendering (SSR) for Inertia responses.

    When enabled, full-page HTML responses will be pre-rendered by a Node SSR server
    and injected into the SPA HTML before returning to the client.

    Supports:
        - True: enable with defaults -> ``InertiaSSRConfig()``
        - False/None: disabled -> ``None``
        - InertiaSSRConfig: use as-is
    """

    use_script_element: bool = True
    """Use a script element instead of data-page attribute for page data.

    When True, embeds page data in a ``<script type="application/json" id="app_page" data-page="app">``
    element instead of a ``data-page`` attribute on the app element.

    Benefits:
        - ~37% payload reduction for large pages (no HTML entity escaping)
        - Better performance for pages with complex props

    Requirements:
        - Inertia v3 clients use this transport by default; no extra client ``defaults`` block is required.
        - Inertia v2 clients must also enable:
          ``createInertiaApp({ defaults: { future: { useScriptElementForInitialPage: true } } })``
        - If SSR is enabled for an Inertia v2 client, keep the same
          ``defaults.future.useScriptElementForInitialPage`` option in both the browser entry
          and the SSR entry.
        - The script element must include the target app element ID in its ``data-page`` attribute so
          Inertia can locate the payload element.
        - Supported with Inertia v2.3+ and Inertia v3.

    Enabled by default for the current Inertia contract. Set to ``False`` to
    keep the legacy ``data-page`` attribute bootstrap, which can be useful when
    staying on an Inertia v2 client without the ``future`` opt-in.
    """

    precognition: bool = False
    """Enable Precognition support for real-time form validation.

    When True, registers an exception handler that converts validation errors
    to Laravel's Precognition format when the Precognition header is present.
    This enables real-time validation without executing handler side effects.

    See: https://laravel.com/docs/precognition
    """

    transport: Literal["stdio", "uds", "tcp"] = "stdio"
    """Default transport mode for SSR communication ('stdio', 'uds', 'tcp')."""

    socket_path: Path | str | None = None
    """Unix domain socket path when using transport='uds'."""

    ssr_url: str | None = None
    """Deprecated: use transport='stdio' or 'uds'. When provided, transport defaults to 'tcp'."""

    def __post_init__(self) -> None:
        """Normalize optional sub-configs."""
        if self.ssr_url is not None and self.transport == "stdio":
            warnings.warn(
                "Configuring 'ssr_url' in InertiaConfig is deprecated in favor of 'transport=\"stdio\"' "
                "or 'transport=\"uds\"'. Defaulting transport to 'tcp' for backward compatibility.",
                DeprecationWarning,
                stacklevel=2,
            )
            self.transport = "tcp"

        if self.ssr is True:
            self.ssr = InertiaSSRConfig(transport=self.transport, socket_path=self.socket_path, url=self.ssr_url)
        elif isinstance(self.ssr, InertiaSSRConfig):
            if self.ssr_url is not None and self.ssr.url is None:
                self.ssr.url = self.ssr_url
                self.ssr.transport = "tcp"
        elif self.ssr is False:
            self.ssr = None

    @property
    def ssr_config(self) -> InertiaSSRConfig | None:
        """Return the SSR config when enabled, otherwise None.

        Returns:
            The resolved SSR config when enabled, otherwise None.
        """
        if isinstance(self.ssr, InertiaSSRConfig) and self.ssr.enabled:
            return self.ssr
        return None


@dataclass
class InertiaTypeGenConfig:
    """Type generation options for Inertia page props.

    Controls which default types are included in the generated page-props.ts file.
    This follows Laravel Jetstream patterns - sensible defaults for common auth patterns.

    Attributes:
        include_default_auth: Include default User and AuthData interfaces.
            Default User has: id, email, name. Users extend via module augmentation.
            Set to False if your User model doesn't have these fields (uses uuid, username, etc.)
        include_default_flash: Include default FlashMessages interface.
            Uses { [category: string]: string[] } pattern for flash messages.
    """

    include_default_auth: bool = True
    """Include default User and AuthData interfaces.

    When True, generates:
    - User: { id: string, email: string, name?: string | null }
    - AuthData: { isAuthenticated: boolean, user?: User }

    Users extend via TypeScript module augmentation.
    Set to False if your User model has different required fields.
    """

    include_default_flash: bool = True
    """Include default FlashMessages interface.

    When True, generates:
    - FlashMessages: { [category: string]: string[] }

    Standard flash message pattern used by most web frameworks.
    """
