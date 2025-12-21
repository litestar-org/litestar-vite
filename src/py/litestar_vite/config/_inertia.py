"""Inertia.js configuration classes."""

from dataclasses import dataclass, field
from typing import Any

from litestar_vite.config._constants import empty_dict_factory, empty_set_factory

__all__ = ("InertiaConfig", "InertiaSSRConfig", "InertiaTypeGenConfig")


@dataclass
class InertiaSSRConfig:
    """Server-side rendering settings for Inertia.js.

    Inertia SSR runs a separate Node server that renders the initial HTML for an
    Inertia page object. Litestar sends the page payload to the SSR server (by
    default at ``http://127.0.0.1:13714/render``) and injects the returned head
    tags and body markup into the HTML response.

    Notes:
        - This is *not* Litestar-Vite's framework proxy mode (``mode="framework"``; aliases: ``mode="ssr"`` / ``mode="ssg"``).
        - When enabled, failures to contact the SSR server are treated as errors (no silent fallback).
    """

    enabled: bool = True
    url: str = "http://127.0.0.1:13714/render"
    timeout: float = 2.0


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
    """

    root_template: str = "index.html"
    """Name of the root template to use.

    This must be a path that is found by the Vite Plugin template config
    """
    component_opt_keys: "tuple[str, ...]" = ("component", "page")
    """Identifiers to use on routes to get the inertia component to render.

    The first key found in the route handler opts will be used. This allows
    semantic flexibility - use "component" or "page" depending on preference.

    Example:
        # All equivalent:
        @get("/", component="Home")
        @get("/", page="Home")

        # Custom keys:
        InertiaConfig(component_opt_keys=("view", "component", "page"))
    """
    redirect_unauthorized_to: "str | None" = None
    """Optionally supply a path where unauthorized requests should redirect."""
    redirect_404: "str | None" = None
    """Optionally supply a path where 404 requests should redirect."""
    extra_static_page_props: "dict[str, Any]" = field(default_factory=empty_dict_factory)
    """A dictionary of values to automatically add in to page props on every response."""
    extra_session_page_props: "set[str] | dict[str, type]" = field(default_factory=empty_set_factory)
    """Session props to include in page responses.

    Can be either:
    - A set of session key names (types will be 'unknown')
    - A dict mapping session keys to Python types (auto-registered with OpenAPI)

    Example with types (recommended):
        extra_session_page_props={"currentTeam": TeamDetail}

    Example without types (legacy):
        extra_session_page_props={"currentTeam"}
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

    ssr: "InertiaSSRConfig | bool | None" = None
    """Enable server-side rendering (SSR) for Inertia responses.

    When enabled, full-page HTML responses will be pre-rendered by a Node SSR server
    and injected into the SPA HTML before returning to the client.

    Supports:
        - True: enable with defaults -> ``InertiaSSRConfig()``
        - False/None: disabled -> ``None``
        - InertiaSSRConfig: use as-is
    """

    use_script_element: bool = False
    """Use a script element instead of data-page attribute for page data.

    When True, embeds page data in a ``<script type="application/json" id="app_page">``
    element instead of a ``data-page`` attribute on the app element.

    Benefits:
        - ~37% payload reduction for large pages (no HTML entity escaping)
        - Better performance for pages with complex props

    Requirements:
        - Client must also enable: ``createInertiaApp({ useScriptElementForInitialPage: true })``
        - Requires Inertia.js v2.3+

    Disabled by default for compatibility with existing Inertia clients.
    """

    precognition: bool = False
    """Enable Precognition support for real-time form validation.

    When True, registers an exception handler that converts validation errors
    to Laravel's Precognition format when the Precognition header is present.
    This enables real-time validation without executing handler side effects.

    Usage:
        1. Enable in config: InertiaConfig(precognition=True)
        2. Use @precognition decorator on form handlers
        3. Use laravel-precognition-vue/react on the frontend

    Note on Rate Limiting:
        Real-time validation can generate many requests. Consider:
        - Frontend debouncing (built into laravel-precognition libraries)
        - Server-side throttling for Precognition requests
        - Laravel has no official rate limiting solution for Precognition

    See: https://laravel.com/docs/precognition
    """

    def __post_init__(self) -> None:
        """Normalize optional sub-configs."""
        if self.ssr is True:
            self.ssr = InertiaSSRConfig()
        elif self.ssr is False:
            self.ssr = None

    @property
    def ssr_config(self) -> "InertiaSSRConfig | None":
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

    Example:
        Standard auth (95% of users) - just extend defaults::

            # Python: use defaults
            ViteConfig(inertia=InertiaConfig())

            # TypeScript: extend User interface
            declare module 'litestar-vite-plugin/inertia' {
                interface User {
                    avatarUrl?: string
                    roles: Role[]
                }
            }

        Custom auth (5% of users) - define from scratch::

            # Python: disable defaults
            ViteConfig(inertia=InertiaConfig(
                type_gen=InertiaTypeGenConfig(include_default_auth=False)
            ))

            # TypeScript: define your custom User
            declare module 'litestar-vite-plugin/inertia' {
                interface User {
                    uuid: string  // No id!
                    username: string  // No email!
                }
            }
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
