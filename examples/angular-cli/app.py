"""Angular CLI example - shared "Library" backend for Angular CLI frontend.

All examples in this repository expose the same backend:
- `/api/summary` - overview + featured book
- `/api/books` - list of books
- `/api/books/{book_id}` - single book

Dev mode (default):
    litestar --app-dir examples/angular-cli run

Production mode (serves static build):
    VITE_DEV_MODE=false litestar --app-dir examples/angular-cli run
"""

import os
from pathlib import Path

from litestar import Controller, Litestar, get
from litestar.exceptions import NotFoundException
from msgspec import Struct

from litestar_vite import ExternalDevServer, PathConfig, RuntimeConfig, TypeGenConfig, ViteConfig, VitePlugin

here = Path(__file__).parent
dist_dir = here / "dist" / "browser"
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
    """Build summary data."""
    return Summary(
        app="litestar-vite library",
        headline="One backend, many frontends",
        total_books=len(BOOKS),
        featured=BOOKS[0],
    )


class LibraryController(Controller):
    """Library API controller."""

    @get("/api/summary")
    async def summary(self) -> Summary:
        """Overview endpoint used across all examples."""
        return _get_summary()

    @get("/api/books")
    async def books(self) -> list[Book]:
        """Return all books."""
        return BOOKS

    @get("/api/books/{book_id:int}")
    async def book_detail(self, book_id: int) -> Book:
        """Return a single book by id."""
        return _get_book(book_id)


# VitePlugin for development proxy, type generation, and production static serving
# - Dev: Auto-starts Angular CLI (ng serve) and proxies to port 4200
# - Prod: mode="external" auto-serves bundle_dir as static files
vite = VitePlugin(
    config=ViteConfig(
        mode="external",
        dev_mode=DEV_MODE,
        paths=PathConfig(root=here, bundle_dir=dist_dir),
        types=TypeGenConfig(),
        runtime=RuntimeConfig(
            external_dev_server=ExternalDevServer(
                target="http://localhost:4200",
                command=["npm", "run", "start"],
                build_command=["npm", "run", "build"],
            ),
        ),
    )
)

app = Litestar(
    route_handlers=[LibraryController],
    plugins=[vite],
    debug=True,
)
