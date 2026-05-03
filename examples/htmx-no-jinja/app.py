"""HTMX example without Jinja — handlers return raw HTML strings.

Demonstrates the C1 contract: ``mode="template"`` is valid even when no
``TemplateConfig`` is wired and Jinja2 is not installed. Handlers serve raw
HTML directly. The Vite asset pipeline still ships the HTMX runtime through
``resources/main.js``.

All examples in this repository expose the same library backend:
- ``/api/summary`` - overview + featured book
- ``/api/books`` - list of books
- ``/api/books/{book_id}`` - single book
"""

import os
from pathlib import Path

from litestar import Controller, Litestar, Response, get
from litestar.exceptions import NotFoundException
from msgspec import Struct

from litestar_vite import PathConfig, RuntimeConfig, TypeGenConfig, ViteConfig, VitePlugin

here = Path(__file__).parent
DEV_MODE = os.getenv("VITE_DEV_MODE", "true").lower() in {"true", "1", "yes"}


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
    """Build summary data.

    Returns:
        The summary data.
    """
    return Summary(
        app="litestar-vite library", headline="One backend, many frontends", total_books=len(BOOKS), featured=BOOKS[0]
    )


def _book_card(book: Book) -> str:
    tags = " · ".join(book.tags)
    return (
        f'<article class="space-y-2 rounded-xl border border-slate-200 bg-white p-4 shadow-sm" id="book-{book.id}">'
        f'  <h3 class="text-lg font-semibold text-[#202235]">{book.title}</h3>'
        f'  <p class="mt-1 text-slate-600">{book.author} • {book.year}</p>'
        f'  <p class="mt-1 text-sm text-[#202235]">{tags}</p>'
        f"</article>"
    )


def _index_html(summary: Summary, books: list[Book]) -> str:
    cards = "\n".join(_book_card(book) for book in books)
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>HTMX (no Jinja)</title>
  <script type="module" src="/static/resources/main.js"></script>
</head>
<body hx-ext="litestar">
  <main class="mx-auto max-w-5xl space-y-6 px-4 py-10" hx-boost="true">
    <header class="space-y-2">
      <p class="text-sm font-semibold uppercase tracking-[0.14em] text-[#edb641]">Litestar · Vite</p>
      <h1 class="text-3xl font-semibold text-[#202235]">Library (HTMX, no Jinja)</h1>
      <p class="text-slate-600">{summary.headline}</p>
      <p class="text-slate-500 text-sm">
        Template mode without a TemplateConfig — handlers return raw HTML strings.
      </p>
    </header>
    <section id="books" class="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3" aria-label="Books">
      {cards}
    </section>
    <section id="book-detail" class="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
      <button
        class="rounded-lg bg-[#edb641] px-4 py-2 text-sm font-semibold text-[#202235] shadow"
        hx-get="/fragments/book/1"
        hx-target="#book-detail"
        hx-swap="innerHTML"
      >
        Load Book 1 fragment
      </button>
    </section>
  </main>
</body>
</html>
"""


# [docs-start:htmx-no-jinja-controller]
class LibraryController(Controller):
    """Library API and HTMX page controller."""

    @get("/")
    async def index(self) -> Response[str]:
        """Serve the home page as raw HTML — no template engine involved.

        Returns:
            A raw HTML response.
        """
        return Response(content=_index_html(_get_summary(), BOOKS), media_type="text/html")

    @get("/fragments/book/{book_id:int}")
    async def book_fragment(self, book_id: int) -> Response[str]:
        """Return a book card fragment for HTMX swaps.

        Returns:
            A raw HTML fragment response.
        """
        return Response(content=_book_card(_get_book(book_id)), media_type="text/html")

    @get("/api/summary")
    async def summary(self) -> Summary:
        return _get_summary()

    @get("/api/books")
    async def books(self) -> list[Book]:
        return BOOKS

    @get("/api/books/{book_id:int}")
    async def book_detail(self, book_id: int) -> Book:
        return _get_book(book_id)


# [docs-end:htmx-no-jinja-controller]


# [docs-start:htmx-no-jinja-vite-config]
vite = VitePlugin(
    config=ViteConfig(
        mode="template",  # template mode is valid without a TemplateConfig
        dev_mode=DEV_MODE,
        paths=PathConfig(root=here, resource_dir="resources"),
        types=TypeGenConfig(generate_sdk=False),
        runtime=RuntimeConfig(port=5060),
    )
)

app = Litestar(route_handlers=[LibraryController], plugins=[vite], debug=True)
# [docs-end:htmx-no-jinja-vite-config]
