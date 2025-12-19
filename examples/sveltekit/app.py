"""SvelteKit example - shared "Library" backend for SvelteKit SSR frontend.

SvelteKit runs as an SSR server. In dev mode, Litestar proxies all non-API
routes to the SvelteKit dev server. In production, SvelteKit's `hooks.server.ts`
proxies /api/* requests to the Litestar backend.

All examples in this repository expose the same backend:
- `/api/summary` - overview + featured book
- `/api/books` - list of books
- `/api/books/{book_id}` - single book

Dev mode (default):
    litestar --app-dir examples/sveltekit run

Production (two terminals):
    # Terminal 1: Install deps, build, and serve SvelteKit SSR server
    litestar --app-dir examples/sveltekit assets install
    litestar --app-dir examples/sveltekit assets build
    litestar --app-dir examples/sveltekit assets serve

    # Terminal 2: Litestar API server
    VITE_DEV_MODE=false litestar --app-dir examples/sveltekit run

The SvelteKit server includes `hooks.server.ts` which proxies /api/* requests
to the Litestar backend (configurable via LITESTAR_API env var, default: localhost:8000).
"""

import os
from pathlib import Path

from litestar import Controller, Litestar, get
from litestar.exceptions import NotFoundException
from msgspec import Struct

from litestar_vite import PathConfig, RuntimeConfig, TypeGenConfig, ViteConfig, VitePlugin

here = Path(__file__).parent
DEV_MODE = os.getenv("VITE_DEV_MODE", "true").lower() in {"true", "1", "yes"}


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
    """Build summary data.

    Returns:
        The summary data.
    """
    return Summary(
        app="litestar-vite library", headline="One backend, many frontends", total_books=len(BOOKS), featured=BOOKS[0]
    )


class LibraryController(Controller):
    """Library API controller."""

    @get("/api/summary")
    async def summary(self) -> Summary:
        """Overview endpoint used across all examples.

        Returns:
            The result.
        """
        return _get_summary()

    @get("/api/books")
    async def books(self) -> list[Book]:
        """Return all books.

        Returns:
            The result.
        """
        return BOOKS

    @get("/api/books/{book_id:int}")
    async def book_detail(self, book_id: int) -> Book:
        """Return a single book by id.

        Returns:
            The result.
        """
        return _get_book(book_id)


vite = VitePlugin(
    config=ViteConfig(
        mode="ssr",  # SSR mode: proxy in dev, Node serves HTML in prod
        dev_mode=DEV_MODE,
        paths=PathConfig(root=here),
        types=TypeGenConfig(output=Path("src/lib/generated"), generate_zod=True),
        # Fixed port for E2E tests - can be removed for local dev or customized for production
        runtime=RuntimeConfig(port=5022),
    )
)

app = Litestar(route_handlers=[LibraryController], plugins=[vite], debug=True)
