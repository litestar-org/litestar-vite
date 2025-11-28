"""SPA React example - shared "Library" backend + SPA frontend.

All examples expose the same backend endpoints so you can compare
frameworks side-by-side:

- `/api/summary` – overview + featured book
- `/api/books` – list of books
- `/api/books/{book_id}` – single book
"""

from pathlib import Path

from anyio import Path as AsyncPath
from litestar import Litestar, get
from litestar.exceptions import NotFoundException
from litestar.response import Response
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


@get("/")
async def index() -> Response[bytes]:
    """Serve the SPA index.html."""
    content = await AsyncPath(here / "index.html").read_bytes()
    return Response(content=content, media_type="text/html")


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


vite = VitePlugin(
    config=ViteConfig(
        dev_mode=True,
        types=True,
        # Point the Vite process at this example directory so /src/* resolves
        paths=PathConfig(root=here),
    )
)

app = Litestar(
    route_handlers=[index, summary, books, book_detail],
    plugins=[vite],
    debug=True,
)
