"""Fullstack typed example - shared "Library" backend + React Inertia.

Demonstrates:
- Inertia.js for server-driven SPA routing
- React frontend
- OpenAPI + routes export for typed client generation
"""

import os
from pathlib import Path

from litestar import Controller, Litestar, get
from litestar.contrib.jinja import JinjaTemplateEngine
from litestar.exceptions import NotFoundException
from litestar.middleware.session.client_side import CookieBackendConfig
from litestar.template import TemplateConfig
from msgspec import Struct

from litestar_vite import PathConfig, TypeGenConfig, ViteConfig, VitePlugin
from litestar_vite.inertia import InertiaConfig, InertiaPlugin

here = Path(__file__).parent
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
    """Build summary data."""
    return Summary(
        app="litestar-vite library",
        headline="One backend, many frontends",
        total_books=len(BOOKS),
        featured=BOOKS[0],
    )


class LibraryController(Controller):
    """Library API and Inertia page controller."""

    @get("/", component="Home")
    async def index(self) -> Message:
        """Serve the home page."""
        return Message(message="Welcome to fullstack-typed!")

    @get("/books", component="Books")
    async def books_page(self) -> dict[str, object]:
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
        paths=PathConfig(root=here, resource_dir="resources", bundle_dir="public"),
        types=TypeGenConfig(
            enabled=True,
            output=Path("resources/generated"),
            generate_zod=True,
            generate_sdk=False,
        ),
    )
)
inertia = InertiaPlugin(config=InertiaConfig(root_template="index.html"))
templates = TemplateConfig(directory=here / "templates", engine=JinjaTemplateEngine)

app = Litestar(
    route_handlers=[LibraryController],
    plugins=[vite, inertia],
    template_config=templates,
    middleware=[session_backend.middleware],
    debug=True,
)
