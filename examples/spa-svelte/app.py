"""SPA Svelte example - shared "Library" backend + SPA frontend.

Common endpoints across all examples:
- `/api/summary`
- `/api/books`
- `/api/books/{book_id}`
"""

from pathlib import Path

from anyio import Path as AsyncPath
from litestar import Litestar, get
from litestar.exceptions import NotFoundException
from litestar.response import Response
from msgspec import Struct

from litestar_vite import ViteConfig, VitePlugin

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
    return Summary(
        app="litestar-vite library",
        headline="One backend, many frontends",
        total_books=len(BOOKS),
        featured=BOOKS[0],
    )


@get("/api/books")
async def books() -> list[Book]:
    return BOOKS


@get("/api/books/{book_id:int}")
async def book_detail(book_id: int) -> Book:
    return _get_book(book_id)


vite = VitePlugin(config=ViteConfig())

app = Litestar(
    route_handlers=[index, summary, books, book_detail],
    plugins=[vite],
    debug=True,
)
