"""Angular CLI example - shared "Library" backend for Angular CLI frontend.

All examples in this repository expose the same backend:
- `/api/summary` - overview + featured book
- `/api/books` - list of books
- `/api/books/{book_id}` - single book

Development:
    Angular CLI dev server runs on port 4200 (`ng serve`).
    Litestar proxies non-API requests to Angular CLI using external_proxy mode.
    Run both servers: `ng serve` and `litestar run --reload`.

Production:
    Built assets in `dist/browser` are served by the VitePlugin.
    Set DEV_MODE=false or unset it.
"""

from pathlib import Path

from litestar import Controller, Litestar, get
from litestar.exceptions import NotFoundException
from msgspec import Struct

from litestar_vite import ExternalDevServer, PathConfig, RuntimeConfig, ViteConfig, VitePlugin

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


# VitePlugin with external_proxy mode for Angular CLI:
# - Dev: Proxies to Angular CLI dev server (ng serve on port 4200)
# - Prod: Serves built assets from dist/browser
vite = VitePlugin(
    config=ViteConfig(
        mode="spa",
        paths=PathConfig(
            root=here,
            bundle_dir=here / "dist" / "browser",
            resource_dir=here / "src",
        ),
        runtime=RuntimeConfig(
            proxy_mode="external_proxy",
            external_dev_server=ExternalDevServer(target="http://localhost:4200"),
            # Angular CLI handles its own dev server (ng serve)
            start_dev_server=False,
        ),
    )
)

app = Litestar(
    route_handlers=[LibraryController],
    plugins=[vite],
    debug=True,
)
