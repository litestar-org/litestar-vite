"""Vue + Inertia.js + Jinja shell with server-side rendering (template mode).

Combines the Jinja2 page shell pattern (``examples/vue-inertia-jinja``)
with the Inertia SSR pipeline (``examples/vue-inertia-ssr``). Demonstrates:

- ``mode="template"`` + ``TemplateConfig(JinjaTemplateEngine)``
- ``InertiaConfig(ssr=InertiaSSRConfig(target_selector="#app"))``
- The Jinja-rendered HTML's ``#app`` element gets its outer HTML replaced
  with the Node-rendered Inertia tree before the page is sent to the browser.

Run two processes:

.. code-block:: bash

    npm install
    npm run build:ssr
    npm run start:ssr  # Terminal 1

    litestar --app-dir examples/vue-inertia-jinja-ssr run  # Terminal 2
"""

import os
from pathlib import Path

from litestar import Controller, Litestar, get
from litestar.contrib.jinja import JinjaTemplateEngine
from litestar.exceptions import NotFoundException
from litestar.middleware.session.client_side import CookieBackendConfig
from litestar.template import TemplateConfig
from msgspec import Struct

from litestar_vite import (
    InertiaConfig,
    InertiaSSRConfig,
    PathConfig,
    RuntimeConfig,
    TypeGenConfig,
    ViteConfig,
    VitePlugin,
)

here = Path(__file__).parent
DEV_MODE = os.getenv("VITE_DEV_MODE", "true").lower() in {"true", "1", "yes"}
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
    return Summary(
        app="litestar-vite library", headline="One backend, many frontends", total_books=len(BOOKS), featured=BOOKS[0]
    )


class LibraryController(Controller):
    """Library API and Inertia page controller."""

    @get("/", component="Home")
    async def index(self) -> Message:
        """Serve the home page (server-side rendered into the Jinja shell).

        Returns:
            The result.
        """
        return Message(message="Welcome to Vue Inertia SSR (Jinja shell)!")

    @get("/books", component="Books")
    async def books_page(self) -> dict[str, object]:
        """Books list page (shares API payloads).

        Returns:
            The result.
        """
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


templates = TemplateConfig(directory=here / "templates", engine=JinjaTemplateEngine)

vite = VitePlugin(
    config=ViteConfig(
        mode="template",  # Explicit template mode for Jinja-based Inertia SSR
        dev_mode=DEV_MODE,
        paths=PathConfig(root=here, resource_dir="resources"),
        # Explicit InertiaSSRConfig so target_selector="#app" is documented inline.
        # The Jinja shell renders <div id="app"></div>; SSR replaces that element
        # outerHTML with the Node-rendered Inertia tree.
        inertia=InertiaConfig(ssr=InertiaSSRConfig(target_selector="#app")),
        types=TypeGenConfig(output=Path("resources/generated"), generate_zod=True),
        runtime=RuntimeConfig(port=5015),
    )
)

app = Litestar(
    route_handlers=[LibraryController],
    plugins=[vite],
    template_config=templates,
    middleware=[session_backend.middleware],
    debug=True,
)
