"""Angular CLI example - shared "Library" backend for Angular CLI frontend.

All examples in this repository expose the same backend:
- `/api/summary` - overview + featured book
- `/api/books` - list of books
- `/api/books/{book_id}` - single book

Dev mode (default):
    litestar --app-dir examples/angular-cli run

Production mode (serves static build):
    VITE_DEV_MODE=false litestar --app-dir examples/angular-cli run
"""

import os
from pathlib import Path

from litestar import Controller, Litestar, get
from litestar.exceptions import NotFoundException
from litestar.static_files import create_static_files_router
from msgspec import Struct

from litestar_vite import ExternalDevServer, PathConfig, RuntimeConfig, TypeGenConfig, ViteConfig, VitePlugin

here = Path(__file__).parent
dist_dir = here / "dist" / "browser"
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


# VitePlugin for development proxy and type generation
# - Dev: Auto-starts Angular CLI (ng serve) and proxies to port 4200
# - Prod: TypeGen only (static files served by Litestar below)
vite = VitePlugin(
    config=ViteConfig(
        mode="template",  # Don't use SPA mode - we handle static files ourselves
        dev_mode=DEV_MODE,
        paths=PathConfig(root=here, bundle_dir=dist_dir),
        types=TypeGenConfig(),  # output defaults to "src/generated"
        # External dev server auto-sets proxy_mode="proxy"
        runtime=RuntimeConfig(
            external_dev_server=ExternalDevServer(
                target="http://localhost:4200",
                command=["npm", "run", "start"],
                build_command=["npm", "run", "build"],
            ),
        ),
    )
)

# Static file router for production (serves Angular CLI built assets)
# Only active when not in dev mode and dist/browser exists
static_files = (
    create_static_files_router(
        path="/",
        directories=[dist_dir],
        html_mode=True,  # SPA fallback - serves index.html for non-file routes
    )
    if not DEV_MODE and dist_dir.exists()
    else None
)

app = Litestar(
    route_handlers=[LibraryController, *([static_files] if static_files else [])],
    plugins=[vite],
    debug=True,
)
