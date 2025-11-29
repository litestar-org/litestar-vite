from dataclasses import dataclass, field
from typing import Any, Optional

__all__ = ("InertiaConfig",)


@dataclass
class InertiaConfig:
    """Configuration for InertiaJS support.

    Attributes:
        root_template: Name of the root template to use.
        component_opt_key: Identifier for getting inertia component from route opts.
        exclude_from_js_routes_key: Identifier to exclude route from generated routes.
        redirect_unauthorized_to: Path for unauthorized request redirects.
        redirect_404: Path for 404 request redirects.
        extra_static_page_props: Static props added to every page response.
        extra_session_page_props: Session keys to include in page props.
        spa_mode: Use SPA mode (HtmlTransformer) instead of Jinja2 templates.
        app_selector: CSS selector for the app root element in SPA mode.
    """

    root_template: str = "index.html"
    """Name of the root template to use.

    This must be a path that is found by the Vite Plugin template config
    """
    component_opt_key: str = "component"
    """An identifier to use on routes to get the inertia component to render."""
    exclude_from_js_routes_key: str = "exclude_from_routes"
    """An identifier to use on routes to exclude a route from the generated routes typescript file."""
    redirect_unauthorized_to: "Optional[str]" = None
    """Optionally supply a path where unauthorized requests should redirect."""
    redirect_404: "Optional[str]" = None
    """Optionally supply a path where 404 requests should redirect."""
    extra_static_page_props: "dict[str, Any]" = field(default_factory=dict)  # pyright: ignore
    """A dictionary of values to automatically add in to page props on every response."""
    extra_session_page_props: "set[str]" = field(default_factory=set)  # pyright: ignore
    """A set of session keys for which the value automatically be added (if it exists) to the response."""
    spa_mode: bool = False
    """Enable SPA mode to render without Jinja2 templates.

    When True, InertiaResponse uses ViteSPAHandler and HtmlTransformer
    to inject page data instead of rendering Jinja2 templates.
    This allows template-less Inertia applications.
    """
    app_selector: str = "#app"
    """CSS selector for the app root element.

    Used in SPA mode to locate the element where data-page attribute
    should be injected. Defaults to "#app".
    """
