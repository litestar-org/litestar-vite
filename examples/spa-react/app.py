"""SPA React example - shared "Library" backend + SPA frontend.

All examples expose the same backend endpoints so you can compare
frameworks side-by-side:

- `/api/summary` - overview + featured book
- `/api/books` - list of books
- `/api/books/{book_id}` - single book

The VitePlugin automatically handles serving the SPA index.html for all
non-API routes when mode="spa" (auto-detected or explicit).
"""

from pathlib import Path

from litestar import Litestar, get
from litestar.exceptions import NotFoundException
from msgspec import Struct

from litestar_vite import PathConfig, ViteConfig, VitePlugin

here = Path(__file__).parent


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


@get("/api/summary")
async def summary() -> Summary:
    """Overview endpoint shared across examples."""
    return Summary(
        app="litestar-vite library",
        headline="One backend, many frontends",
        total_books=len(BOOKS),
        featured=BOOKS[0],
    )


@get("/api/books")
async def books() -> list[Book]:
    """Return all books."""
    return BOOKS


@get("/api/books/{book_id:int}")
async def book_detail(book_id: int) -> Book:
    """Return a single book."""
    return _get_book(book_id)


# VitePlugin with mode="spa" automatically:
# - Registers catch-all route for index.html
# - Injects route metadata as window.__LITESTAR_ROUTES__ for client-side routing
vite = VitePlugin(
    config=ViteConfig(
        mode="spa",
        paths=PathConfig(root=here),
    )
)

app = Litestar(
    route_handlers=[summary, books, book_detail],  # Just API routes
    plugins=[vite],
    debug=True,
)
