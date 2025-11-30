"""Flash messages example - shared "Library" demo with flash messages.

All examples in this repository expose the same backend:
- `/api/summary` - overview + featured book
- `/api/books` - list of books
- `/api/books/{book_id}` - single book

This example demonstrates the Litestar flash plugin with Vite.
"""

import os
from pathlib import Path
from typing import Any

from litestar import Controller, Litestar, Request, get
from litestar.contrib.jinja import JinjaTemplateEngine
from litestar.exceptions import NotFoundException
from litestar.middleware.session.client_side import CookieBackendConfig
from litestar.plugins.flash import FlashConfig, FlashPlugin, flash
from litestar.response import Template
from litestar.template.config import TemplateConfig
from msgspec import Struct

from litestar_vite import PathConfig, TypeGenConfig, ViteConfig, VitePlugin

here = Path(__file__).parent
SECRET_KEY = os.environ.get("SECRET_KEY", "development-only-secret-32-chars")
session_backend = CookieBackendConfig(secret=SECRET_KEY.encode("utf-8"))


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
    """Library API and web controller with flash messages."""

    opt = {"exclude_from_auth": True}
    include_in_schema = False

    @get("/")
    async def index(self, request: Request[Any, Any, Any]) -> Template:
        """Serve site root with flash message demo."""
        flash(request, "Oh no! I've been flashed!", category="error")
        return Template(
            template_name="index.html.j2",
            context={"summary": _get_summary(), "books": BOOKS},
        )

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
templates = TemplateConfig(directory=here / "templates", engine=JinjaTemplateEngine)
flasher = FlashPlugin(config=FlashConfig(template_config=templates))

app = Litestar(
    route_handlers=[LibraryController],
    plugins=[vite, flasher],
    template_config=templates,
    middleware=[session_backend.middleware],
    debug=True,
)
