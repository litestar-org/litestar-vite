"""Inertia.js v2 deferred props, partial reloads, once caching, and infinite scroll."""

from __future__ import annotations

from typing import Any

from litestar import Litestar, get

from litestar_vite import InertiaConfig, RuntimeConfig, ViteConfig, VitePlugin
from litestar_vite.inertia import always, defer, lazy, merge, once, optional, scroll_props


def _load_slow_analytics() -> dict[str, int]:
    """Simulate an expensive analytics query deferred until after initial render."""
    return {"weeklyActive": 1420, "conversionRateBps": 385}


def _load_audit_log() -> list[str]:
    """Simulate an on-demand audit trail loaded only when requested."""
    return ["user.login", "invoice.exported"]


@get("/analytics", component="Analytics/Dashboard", sync_to_thread=False)
def analytics_dashboard() -> dict[str, Any]:
    """Combine eager, deferred, once-cached, optional, and merged props."""
    return {
        "permissions": always("permissions", {"canExport": True}),
        "summary": {"totalRevenue": 94200},
        "metrics": defer("metrics", _load_slow_analytics, group="charts"),
        "featureCatalog": once("featureCatalog", lambda: ["sso", "audit_stream"]),
        "auditLog": optional("auditLog", _load_audit_log),
        "legacySummary": lazy("legacySummary", lambda: {"archived": 12}),
        "events": merge(
            "events",
            [{"id": 1, "title": "Deployment succeeded"}, {"id": 2, "title": "Backup completed"}],
            strategy="append",
            match_on="id",
        ),
        "scroll": scroll_props(page_name="page", current_page=1, next_page=2),
    }


def create_app() -> Litestar:
    """Create a Litestar app demonstrating Inertia v2 prop wrappers."""
    vite_config = ViteConfig(
        mode="hybrid",
        dev_mode=True,
        inertia=InertiaConfig(root_template="index.html"),
        runtime=RuntimeConfig(start_dev_server=False),
    )
    return Litestar(route_handlers=[analytics_dashboard], plugins=[VitePlugin(config=vite_config)])


def main() -> None:
    """Verify Inertia v2 prop wrapper construction."""
    app = create_app()
    assert app is not None
    deferred = defer("metrics", _load_slow_analytics, group="charts")
    merged = merge("events", [{"id": 1}], strategy="append", match_on="id")
    assert deferred.group == "charts"
    assert merged.strategy == "append"
    assert merged.match_on == ["id"]


__all__ = ("analytics_dashboard", "create_app", "main")
