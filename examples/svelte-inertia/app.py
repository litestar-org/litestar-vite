"""Svelte 5 + Inertia.js example - template-less Inertia using mode='hybrid'.

This example demonstrates Inertia.js without Jinja templates.
Page data is injected into index.html at runtime via HTML transformation.

All examples in this repository expose the same library backend:
- ``/api/summary`` - overview + featured book
- ``/api/books`` - list of books
- ``/api/books/{book_id}`` - single book
"""

import os
from pathlib import Path

from litestar import Controller, Litestar, get
from litestar.exceptions import NotFoundException
from litestar.middleware.session.client_side import CookieBackendConfig
from msgspec import Struct

from litestar_vite import InertiaConfig, PathConfig, RuntimeConfig, TypeGenConfig, ViteConfig, VitePlugin

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
        """Serve the home page.

        Returns:
            The result.
        """
        return Message(message="Welcome to Svelte Inertia!")

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
        # litestar-vite defaults to the script-element bootstrap for Inertia.
        # Inertia v3 uses that transport automatically.
        # If you pin Inertia v2, add defaults.future.useScriptElementForInitialPage
        # in the browser/SSR entry or set use_script_element=False on the server.
        inertia=InertiaConfig(),
        types=TypeGenConfig(output=Path("resources/generated")),
        runtime=RuntimeConfig(port=5023),
    )
)

app = Litestar(route_handlers=[LibraryController], plugins=[vite], middleware=[session_backend.middleware], debug=True)
