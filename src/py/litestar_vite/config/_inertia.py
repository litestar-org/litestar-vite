"""Inertia.js configuration classes."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from litestar_vite.config._constants import empty_dict_factory, empty_set_factory

__all__ = ("InertiaConfig", "InertiaSSRConfig", "InertiaTypeGenConfig")


@dataclass
class InertiaSSRConfig:
    """Server-side rendering (SSR) and circuit breaker settings for Inertia.js."""

    enabled: bool = True
    """Whether server-side rendering is active for Inertia full-page HTML responses."""
    timeout: float = 2.0
    """Maximum time in seconds to wait for an SSR render call before timing out."""
    target_selector: str = "#app"
    """CSS selector of the element replaced by SSR HTML in `mode='template'` (`SPAConfig.app_selector` is used in `mode='hybrid'`)."""
    command: list[str] | None = None
    """Command argv to launch the production stdio SSR worker (`node <ssr_output_dir>/ssr.js` when `None`)."""
    cwd: Path | None = None
    """Working directory for the production SSR subprocess (`ViteConfig.root_dir` when `None`)."""
    fallback_to_client: bool = True
    """Fall back gracefully to client-side rendering when SSR fails or times out."""
    circuit_breaker_enabled: bool = True
    """Enable the in-memory `SSRCircuitBreaker` protecting the SSR IPC pipeline."""
    circuit_breaker_failure_threshold: int = 3
    """Consecutive SSR failures required before the circuit breaker trips to `OPEN`."""
    circuit_breaker_reset_timeout: float = 30.0
    """Cooldown window in seconds before a tripped circuit breaker transitions to `HALF_OPEN`."""


@dataclass
class InertiaConfig:
    """Configuration for Inertia.js v2 protocol handling, shared props, SSR, and Precognition."""

    root_template: str = "index.html"
    """Root HTML or Jinja template filename used for initial Inertia page responses."""
    component_opt_keys: tuple[str, ...] = ("component", "page")
    """Route handler `opt` keys inspected to resolve the Inertia component name."""
    redirect_unauthorized_to: str | None = None
    """Optional URL path to redirect unauthenticated (`401`/`403`) Inertia requests."""
    redirect_404: str | None = None
    """Optional URL path to redirect `404 Not Found` Inertia requests."""
    extra_static_page_props: dict[str, Any] = field(default_factory=empty_dict_factory)
    """Static key-value props automatically merged into every Inertia page response."""
    extra_session_page_props: set[str] | dict[str, type] = field(default_factory=empty_set_factory)
    """Session key names (or mapping of session keys to Python types) copied into page props when a session exists."""
    shared_page_prop_types: dict[str, Any] | None = None
    """Type-only mapping of `share()` prop keys to Python type annotations for OpenAPI/TypeScript generation."""
    encrypt_history: bool = False
    """Set `encryptHistory: true` globally on Inertia page responses so the client encrypts browser history state."""
    type_gen: "InertiaTypeGenConfig | None" = None
    """Type generation options controlling default `User`, `AuthData`, and `FlashMessages` interfaces in `page-props.ts`."""
    ssr: InertiaSSRConfig | bool | None = None
    """Enable Inertia SSR (`True` for default `InertiaSSRConfig()`, `False`/`None` to disable, or a custom `InertiaSSRConfig`)."""
    use_script_element: bool = True
    """Embed initial page JSON in `<script type="application/json" data-page="app">` instead of an HTML-escaped `data-page` attribute."""
    precognition: bool = False
    """Register the Laravel Precognition validation exception handler for `Precognition: true` requests."""

    def __post_init__(self) -> None:
        """Normalize optional sub-configs."""
        if self.ssr is True:
            self.ssr = InertiaSSRConfig()
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
    """Type generation options for default Inertia interfaces in `page-props.ts`."""

    include_default_auth: bool = True
    """Emit default `User` and `AuthData` TypeScript interfaces in `page-props.ts`."""
    include_default_flash: bool = True
    """Emit the default `FlashMessages` (`Record<string, string[]>`) interface in `page-props.ts`."""
