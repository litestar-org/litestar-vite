"""Islands architecture and HTMX server-rendered component fragments."""

from __future__ import annotations

from litestar import Litestar, get

from litestar_vite import ComponentResponse, FragmentEngine, RuntimeConfig, ViteConfig, VitePlugin


@get("/fragments/revenue-chart", sync_to_thread=False)
def revenue_chart_fragment() -> ComponentResponse:
    """Render a standalone UI component fragment for HTMX partial swaps."""
    return ComponentResponse(
        component="islands/RevenueChart.tsx",
        props={"period": "30d", "series": [120, 145, 190, 210]},
        headers={"HX-Trigger": "chartRendered"},
    )


def create_app() -> Litestar:
    """Create a Litestar app with fragment rendering enabled."""
    vite_config = ViteConfig(mode="template", dev_mode=True, runtime=RuntimeConfig(start_dev_server=False))
    return Litestar(route_handlers=[revenue_chart_fragment], plugins=[VitePlugin(config=vite_config)])


def main() -> None:
    """Verify ``ComponentResponse`` and ``FragmentEngine`` wiring."""
    app = create_app()
    assert app is not None
    response = ComponentResponse(
        component="islands/RevenueChart.tsx", props={"period": "90d", "series": [120, 145, 190, 210]}
    )
    assert response.component == "islands/RevenueChart.tsx"
    assert response.props["period"] == "90d"
    assert FragmentEngine is not None


__all__ = ("create_app", "main", "revenue_chart_fragment")
