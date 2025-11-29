"""HTMX + Alpine.js + Litestar template example (shared "Library" backend)."""

from pathlib import Path

from litestar import Controller, Litestar, get
from litestar.contrib.jinja import JinjaTemplateEngine
from litestar.exceptions import NotFoundException
from litestar.response import Template
from litestar.template import TemplateConfig
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


def _get_summary() -> Summary:
    """Build summary data."""
    return Summary(
        app="litestar-vite library",
        headline="One backend, many frontends",
        total_books=len(BOOKS),
        featured=BOOKS[0],
    )


class LibraryController(Controller):
    """Library API and web controller."""

    @get("/")
    async def index(self) -> Template:
        """Serve the home page with initial data."""
        return Template(
            template_name="index.html.j2",
            context={"summary": _get_summary(), "books": BOOKS},
        )

    @get("/api/summary")
    async def summary(self) -> Summary:
        return _get_summary()

    @get("/api/books")
    async def books(self) -> list[Book]:
        return BOOKS

    @get("/api/books/{book_id:int}")
    async def book_detail(self, book_id: int) -> Book:
        return _get_book(book_id)


vite = VitePlugin(config=ViteConfig(dev_mode=True))
templates = TemplateConfig(engine=JinjaTemplateEngine(directory=here / "templates"))

app = Litestar(
    route_handlers=[LibraryController],
    plugins=[vite],
    template_config=templates,
    debug=True,
)
