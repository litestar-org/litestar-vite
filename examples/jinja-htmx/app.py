"""HTMX + Alpine.js + Litestar template example (shared "Library" backend)."""

from pathlib import Path

from litestar import Controller, Litestar, get
from litestar.contrib.jinja import JinjaTemplateEngine
from litestar.exceptions import NotFoundException
from litestar.response import Template
from litestar.template.config import TemplateConfig
from litestar_htmx import HTMXPlugin, HTMXRequest
from litestar_htmx.response import HTMXTemplate
from msgspec import Struct

from litestar_vite import PathConfig, RuntimeConfig, ViteConfig, VitePlugin

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
    async def index(self, request: HTMXRequest) -> Template:
        """Serve the home page with initial data."""
        context = {"summary": _get_summary(), "books": BOOKS, "request": request}
        return Template(template_name="index.html.j2", context=context)

    @get("/fragments/book/{book_id:int}")
    async def book_fragment(self, book_id: int) -> Template:
        """Return a book card fragment for HTMX swaps."""
        book = _get_book(book_id)
        return HTMXTemplate(
            template_name="partials/book_card.html.j2",
            context={"book": book},
            re_target="#book-detail",
            re_swap="innerHTML",
            push_url=False,
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


vite = VitePlugin(
    config=ViteConfig(
        mode="template",
        paths=PathConfig(root=here, resource_dir="resources", bundle_dir="public"),
        # Fixed port for E2E tests - can be removed for local dev or customized for production
        runtime=RuntimeConfig(port=5061),
        # dev_mode reads from VITE_DEV_MODE env var (defaults to False/production)
    )
)
templates = TemplateConfig(directory=here / "templates", engine=JinjaTemplateEngine)

app = Litestar(
    route_handlers=[LibraryController],
    plugins=[vite, HTMXPlugin()],
    template_config=templates,
    debug=True,
)
