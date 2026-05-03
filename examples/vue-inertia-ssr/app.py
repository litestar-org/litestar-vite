"""Vue + Inertia.js with server-side rendering (hybrid mode).

Demonstrates the Inertia SSR contract:
- ``InertiaSSRConfig(command=...)`` tells the plugin to spawn the Node /render
  server (port 13714 by default) alongside the Vite dev server. Litestar POSTs
  the page payload from inside the handler frame and injects the returned head
  tags + body into the SPA shell.

One command, two processes:

.. code-block:: bash

    npm install
    litestar --app-dir examples/vue-inertia-ssr run

The Inertia SSR HTTP path is independent of the dev ``proxy_mode``;
single-port via ASGI still applies to browser traffic.
"""

import os
from pathlib import Path

from litestar import Controller, Litestar, get
from litestar.exceptions import NotFoundException
from litestar.middleware.session.client_side import CookieBackendConfig
from msgspec import Struct

from litestar_vite import InertiaConfig, PathConfig, RuntimeConfig, TypeGenConfig, ViteConfig, VitePlugin
from litestar_vite.config import InertiaSSRConfig

here = Path(__file__).parent
DEV_MODE = os.getenv("VITE_DEV_MODE", "true").lower() in {"true", "1", "yes"}
SECRET_KEY = os.environ.get("SECRET_KEY", "development-only-secret-32-chars")
session_backend = CookieBackendConfig(secret=SECRET_KEY.encode("utf-8"))


class Message(Struct):
    message: str


class Book(Struct):
    id: int
    title: str
    author: str
    year: int
    tags: list[str]


class Summary(Struct):
    app: str
    headline: str
    total_books: int
    featured: Book


BOOKS: list[Book] = [
    Book(id=1, title="Async Python", author="C. Developer", year=2024, tags=["python", "async"]),
    Book(id=2, title="Type-Safe Web", author="J. Dev", year=2025, tags=["typescript", "api"]),
    Book(id=3, title="Frontend Patterns", author="A. Designer", year=2023, tags=["frontend", "ux"]),
]


def _get_book(book_id: int) -> Book:
    for book in BOOKS:
        if book.id == book_id:
            return book
    raise NotFoundException(detail=f"Book {book_id} not found")


def _get_summary() -> Summary:
    return Summary(
        app="litestar-vite library", headline="One backend, many frontends", total_books=len(BOOKS), featured=BOOKS[0]
    )


class LibraryController(Controller):
    """Library API and Inertia page controller."""

    @get("/", component="Home")
    async def index(self) -> Message:
        """Serve the home page (server-side rendered).

        Returns:
            The result.
        """
        return Message(message="Welcome to Vue Inertia SSR!")

    @get("/books", component="Books")
    async def books_page(self) -> dict[str, object]:
        """Books list page (shares API payloads).

        Returns:
            The result.
        """
        return {"summary": _get_summary(), "books": BOOKS}

    @get("/api/summary")
    async def summary(self) -> Summary:
        return _get_summary()

    @get("/api/books")
    async def books(self) -> list[Book]:
        return BOOKS

    @get("/api/books/{book_id:int}")
    async def book_detail(self, book_id: int) -> Book:
        return _get_book(book_id)


vite = VitePlugin(
    config=ViteConfig(
        # mode="hybrid" auto-derives from Inertia + index.html presence
        dev_mode=DEV_MODE,
        paths=PathConfig(root=here, resource_dir="resources"),
        # The plugin starts the Node /render server itself via the configured command —
        # no second terminal needed. Litestar POSTs to InertiaSSRConfig.url
        # (default 127.0.0.1:13714/render) inside the handler frame.
        inertia=InertiaConfig(ssr=InertiaSSRConfig(command=["npm", "run", "dev:ssr"])),
        types=TypeGenConfig(output=Path("resources/generated"), generate_zod=True),
        runtime=RuntimeConfig(port=5014),
    )
)

app = Litestar(route_handlers=[LibraryController], plugins=[vite], middleware=[session_backend.middleware], debug=True)
