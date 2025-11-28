"""Fullstack typed example - shared "Library" backend + React Inertia.

Demonstrates:
- Inertia.js for server-driven SPA routing
- React frontend
- OpenAPI + routes export for typed client generation
"""

from pathlib import Path

from litestar import Litestar, get
from litestar.contrib.jinja import JinjaTemplateEngine
from litestar.exceptions import NotFoundException
from litestar.middleware.session.server_side import ServerSideSessionConfig
from litestar.stores.memory import MemoryStore
from litestar.template import TemplateConfig
from msgspec import Struct

from litestar_vite import ViteConfig, VitePlugin
from litestar_vite.inertia import InertiaConfig, InertiaPlugin

here = Path(__file__).parent


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


@get("/", component="Home")
async def index() -> Message:
    """Serve the home page."""
    return Message(message="Welcome to fullstack-typed!")


@get("/books", component="Books")
async def books_page() -> dict[str, object]:
    return {"summary": await summary(), "books": await books()}


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
    for book in BOOKS:
        if book.id == book_id:
            return book
    raise NotFoundException(detail=f"Book {book_id} not found")


vite = VitePlugin(config=ViteConfig(dev_mode=True))
inertia = InertiaPlugin(config=InertiaConfig(root_template="index.html"))
templates = TemplateConfig(engine=JinjaTemplateEngine(directory=here / "templates"))

app = Litestar(
    route_handlers=[index],
    plugins=[vite, inertia],
    template_config=templates,
    middleware=[ServerSideSessionConfig().middleware],
    stores={"sessions": MemoryStore()},
    debug=True,
)
