"""Inertia.js v2 page components, InertiaResponse, and redirects."""

from __future__ import annotations

from typing import Any

from litestar import Litestar, Request, get, post
from msgspec import Struct

from litestar_vite import InertiaConfig, RuntimeConfig, ViteConfig, VitePlugin
from litestar_vite.inertia import InertiaExternalRedirect, InertiaRedirect, InertiaResponse


class InvoiceSummary(Struct, frozen=True, gc=False):
    """Typed invoice item serialized into Inertia PageProps."""

    id: int
    customer: str
    total_cents: int


@get("/invoices", component="Invoices/Index", sync_to_thread=False)
def list_invoices() -> dict[str, Any]:
    """Return Inertia page props via the ``component=`` route option."""
    return {
        "invoices": [
            InvoiceSummary(id=101, customer="Acme Corp", total_cents=12500),
            InvoiceSummary(id=102, customer="Globex", total_cents=8400),
        ]
    }


@get("/invoices/featured", component="Invoices/Show", sync_to_thread=False)
def show_featured_invoice() -> InertiaResponse[InvoiceSummary]:
    """Return an explicit ``InertiaResponse`` with history encryption enabled."""
    return InertiaResponse(InvoiceSummary(id=101, customer="Acme Corp", total_cents=12500), encrypt_history=True)


@post("/invoices/checkout", sync_to_thread=False)
def start_external_checkout(request: Request[Any, Any, Any]) -> InertiaExternalRedirect:
    """Trigger an external ``409 Conflict`` + ``X-Inertia-Location`` redirect."""
    return InertiaExternalRedirect(request, redirect_to="https://billing.example.com/checkout")


def create_app() -> Litestar:
    """Create a Litestar app with Inertia v2 page and redirect handlers."""
    vite_config = ViteConfig(
        mode="hybrid",
        dev_mode=True,
        inertia=InertiaConfig(root_template="index.html"),
        runtime=RuntimeConfig(start_dev_server=False),
    )
    return Litestar(
        route_handlers=[list_invoices, show_featured_invoice, start_external_checkout],
        plugins=[VitePlugin(config=vite_config)],
    )


def main() -> None:
    """Verify Inertia page responses and redirect primitives."""
    app = create_app()
    assert app is not None
    response = InertiaResponse(InvoiceSummary(id=101, customer="Acme Corp", total_cents=12500), encrypt_history=True)
    assert response.encrypt_history is True
    assert InertiaRedirect is not None


__all__ = ("InvoiceSummary", "create_app", "list_invoices", "main", "show_featured_invoice", "start_external_checkout")
